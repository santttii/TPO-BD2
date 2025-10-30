from typing import Dict, Any, List, Optional
from datetime import datetime
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.repositories.mongo_repository import MongoRepository


class ApplicationService:
    def __init__(self):
        self.repo = MongoRepository("applications")
        self.graph_repo = Neo4jRepository()
        self.jobs_repo = MongoRepository("jobs")
        self.people_repo = MongoRepository("people")

    # ===============================================================
    # 📋 LISTADOS
    # ===============================================================
    def get_by_person(self, person_id: str) -> List[Dict[str, Any]]:
        query = {"$or": [{"person_id": person_id}, {"person_user_id": person_id}]}
        return self.repo.find(query)

    def get_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        return self.repo.find({"job_id": job_id})

    def get(self, application_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.find_one(application_id)

    # ===============================================================
    # 🔁 ESTADOS + Neo4j Sync
    # ===============================================================
    def update_estado(self, application_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza el estado actual y lo refleja en Neo4j con relaciones.
        data = {"estado": "en entrevista", "observacion": "Primera entrevista con RRHH"}
        """
        estado = data.get("estado")
        if not estado:
            raise Exception("Campo 'estado' requerido")

        observacion = data.get("observacion", None)
        nuevo_estado = {
            "estado": estado,
            "fecha": datetime.utcnow(),
            "observacion": observacion
        }

        # Buscar la postulación para obtener person_id y job_id
        app_doc = self.repo.find_one(application_id)
        if not app_doc:
            raise Exception("No se encontró la postulación")

        # En la colección applications guardamos tanto person_id (mongo _id)
        # como person_user_id (userId usado para nodos Neo4j). Para sincronizar
        # con Neo4j debemos preferir person_user_id cuando exista.
        person_id = app_doc.get("person_id")
        person_user_id = app_doc.get("person_user_id")
        node_person_id = person_user_id or person_id
        job_id = app_doc["job_id"]

        # 1️⃣ Actualizar estado en Mongo
        updated = self.repo.update(application_id, {
            "estado_actual": estado,
            "actualizadoEn": datetime.utcnow()
        })

        # 2️⃣ Agregar al historial
        self.repo.add_to_array(application_id, "historial_estados", nuevo_estado)

        # 3️⃣ Reflejar en Neo4j
        try:
            # Limpiar relaciones previas de proceso (opcional)
            self.graph_repo.delete_relationship(node_person_id, job_id, rel_type=None)

            estado_map = {
                "en entrevista": "EN_ENTREVISTA_CON",
                "evaluado": "EVALUADO_PARA",
                "oferta": "OFERTA_DE",
                "contratado": "TRABAJA_EN",
                "rechazado": "RECHAZADO_EN",
                "postulado": "POSTULA_A"
            }

            rel_type = estado_map.get(estado.lower(), "EN_PROCESO")

            # Crear relación base Persona → Job (usar node_person_id)
            self.graph_repo.create_relationship(node_person_id, job_id, rel_type)

            # Si es contratado, crear vínculo laboral permanente TRABAJA_EN y guardar experiencia en Mongo
            if estado.lower() == "contratado":
                job_doc = self.jobs_repo.find_one(job_id)
                empresa_id = job_doc.get("empresaId") if job_doc else None
                if empresa_id:
                    # Crear relación laboral permanente TRABAJA_EN hacia la empresa
                    try:
                        self.graph_repo.create_relationship(node_person_id, empresa_id, "TRABAJA_EN")
                    except Exception:
                        # No queremos que la falla en esta relación impida la respuesta principal
                        pass

                    # Actualizar experiencia en el documento people (MongoDB)
                    try:
                        # person_id (mongo) preferible para update
                        pid = person_id or person_user_id
                        person = self.people_repo.find_one(pid)
                        if person is not None:
                            experiencia = person.get("experiencia", [])
                            # construir nuevo entry
                            started = datetime.utcnow().isoformat()
                            role = None
                            if job_doc:
                                role = job_doc.get("titulo")
                            entry = {"companyId": empresa_id, "rol": role, "startedAt": started}
                            # evitar duplicados simples (mismo companyId y rol)
                            exists = any((e.get("companyId") == empresa_id and e.get("rol") == role) for e in experiencia)
                            if not exists:
                                experiencia.append(entry)
                                self.people_repo.update(pid, {"experiencia": experiencia})
                    except Exception as e:
                        print(f"⚠️ Error actualizando experiencia en Mongo: {e}")

        except Exception as e:
            print(f"⚠️ Error sincronizando estado en Neo4j: {e}")

        return updated

    # ===============================================================
    # 💬 FEEDBACK
    # ===============================================================
    def agregar_feedback(self, application_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        feedback["fecha"] = datetime.utcnow()
        updated = self.repo.add_to_array(application_id, "feedback", feedback)
        if not updated:
            raise Exception("Error al agregar feedback")
        return updated

    # ===============================================================
    # 💼 OFERTA
    # ===============================================================
    def enviar_oferta(self, application_id: str, datos_oferta: Dict[str, Any]) -> Dict[str, Any]:
        datos_oferta["fecha_envio"] = datetime.utcnow()
        updated = self.repo.update(application_id, {
            "oferta": datos_oferta,
            "estado_actual": "oferta",
            "actualizadoEn": datetime.utcnow()
        })

        # Agregar al historial y reflejar en Neo4j
        self.repo.add_to_array(application_id, "historial_estados", {
            "estado": "oferta",
            "fecha": datetime.utcnow(),
            "observacion": "Oferta enviada al candidato"
        })

        try:
            app_doc = self.repo.find_one(application_id)
            if app_doc:
                person_user_id = app_doc.get("person_user_id")
                person_id = app_doc.get("person_id")
                node_person_id = person_user_id or person_id
                job_id = app_doc["job_id"]
                self.graph_repo.create_relationship(node_person_id, job_id, "OFERTA_DE")
        except Exception as e:
            print(f"⚠️ Error reflejando oferta en Neo4j: {e}")

        if not updated:
            raise Exception("Error al registrar oferta")
        return updated
