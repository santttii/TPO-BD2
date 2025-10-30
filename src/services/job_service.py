from typing import Dict, Any, List, Optional
from datetime import datetime
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.utils.redis_stats import record_application


class JobService:
    def __init__(self):
        self.repo = MongoRepository("jobs")
        self.graph_repo = Neo4jRepository()
        self.applications_repo = MongoRepository("applications")

    # ===============================================================
    # 🏗️ CREATE
    # ===============================================================
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        job = self.repo.create(payload)
        job_id = str(job["_id"])
        try:
            # 1️⃣ Crear nodo Job
            self.graph_repo.create_job_node(
                job_id=job_id,
                titulo=payload["titulo"],
                empresa_id=payload["empresaId"]
            )
            # 2️⃣ Crear relaciones con Skills
            requisitos = payload.get("requisitos", {})
            obligatorios = requisitos.get("obligatorios", []) if isinstance(requisitos, dict) else []
            deseables = requisitos.get("deseables", []) if isinstance(requisitos, dict) else []
            for skill in obligatorios:
                self.graph_repo.link_job_to_skill(job_id, skill, tipo="REQUERIMIENTO_DE")
            for skill in deseables:
                self.graph_repo.link_job_to_skill(job_id, skill, tipo="DESEA")
        except Exception as e:
            print(f"⚠️ Error creando nodo Job y relaciones en Neo4j: {e}")
        job["_id"] = job_id
        return job

    # ===============================================================
    # 📋 LIST
    # ===============================================================
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        jobs = self.repo.find(filters or {})
        for j in jobs:
            j["_id"] = str(j["_id"])
        return jobs

    # ===============================================================
    # 🔎 GET BY ID
    # ===============================================================
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.repo.find_one(job_id)
        if job:
            job["_id"] = str(job["_id"])
        return job

    # ===============================================================
    # ✏️ UPDATE
    # ===============================================================
    def update(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updated = self.repo.update(job_id, updates)
        if not updated:
            return None

        updated["_id"] = str(updated["_id"])

        # Sincronizar requisitos con Neo4j si cambiaron
        try:
            if "requisitos" in updates:
                self.graph_repo.delete_job_skill_links(job_id)
                requisitos = updated.get("requisitos", {})
                obligatorios = requisitos.get("obligatorios", []) if isinstance(requisitos, dict) else []
                deseables = requisitos.get("deseables", []) if isinstance(requisitos, dict) else []
                for skill in obligatorios:
                    self.graph_repo.link_job_to_skill(job_id, skill, tipo="REQUERIMIENTO_DE")
                for skill in deseables:
                    self.graph_repo.link_job_to_skill(job_id, skill, tipo="DESEA")
        except Exception as e:
            print(f"⚠️ Error sincronizando Job en Neo4j: {e}")

        return updated

    # ===============================================================
    # 🗑️ DELETE
    # ===============================================================
    def delete(self, job_id: str) -> bool:
        deleted = self.repo.delete(job_id)
        if deleted:
            try:
                self.graph_repo.delete_node_by_id(job_id, label="Job")
            except Exception:
                pass
        return bool(deleted)

    def get_applicants(self, job_id: str):
        try:
            return self.graph_repo.get_applicants_for_job(job_id)
        except Exception as e:
            raise Exception(f"Error obteniendo applicants desde Neo4j: {e}")

    # ===============================================================
    # 🧍 POSTULACIÓN (Person -> Job)
    # ===============================================================
    def apply(self, person_id: str, job_id: str) -> Dict[str, Any]:
        """
        Crea la relación SE_POSTULO en Neo4j y un registro de Application en MongoDB.
        """
        try:
            # 🔹 1) Validar existencia del Job
            if not self.graph_repo.node_exists("Job", job_id):
                job_doc = self.repo.find_one(job_id)
                if not job_doc:
                    raise Exception("Job no encontrado en MongoDB")
                self.graph_repo.create_job_node(
                    job_id=job_id,
                    titulo=job_doc.get("titulo", "Sin Título"),
                    empresa_id=job_doc.get("empresaId")
                )

            # 🔹 2) Localizar persona en Mongo (aceptamos person_id como userId o como _id)
            people_repo = MongoRepository("people")
            person_doc = None
            try:
                # 1) Intentar como _id (find_one espera _id)
                person_doc = people_repo.find_one(person_id)
            except Exception:
                person_doc = None

            if not person_doc:
                # 2) Intentar encontrar por userId
                found = people_repo.find({"userId": person_id})
                if found:
                    person_doc = found[0]

            if not person_doc:
                raise Exception("Persona no encontrada en MongoDB")

            # Determinar nodo id que usamos en Neo4j (preferir userId si está)
            node_person_id = person_doc.get("userId") or str(person_doc.get("_id"))
            nombre = person_doc.get("datosPersonales", {}).get("nombre", "Desconocido")
            rol = person_doc.get("rol", "Sin Rol")

            # Si el nodo Person no existe en Neo4j, crearlo
            if not self.graph_repo.node_exists("Person", node_person_id):
                self.graph_repo.create_person_node(person_id=node_person_id, nombre=nombre, rol=rol)

            # 🔹 3) Crear relación SE_POSTULO en Neo4j usando el node id
            self.graph_repo.apply_to_job(node_person_id, job_id)

            # 🔹 4) Registrar la postulación en MongoDB usando el person _id (string)
            #    y también guardar el person_user_id (userId) si existe. Mantener ambos
            #    campos evita romper consultas y facilita migraciones.
            person_mongo_id = str(person_doc.get("_id"))
            person_user_id = person_doc.get("userId")
            data = {
                "person_id": person_mongo_id,
                "person_user_id": person_user_id,
                "job_id": job_id,
                "estado": "postulado",
                "creadoEn": datetime.utcnow(),
                "actualizadoEn": datetime.utcnow()
            }
            application = self.applications_repo.create(data)

            # Record statistics in Redis (applications per job/person)
            try:
                stats_person_id = person_user_id or person_mongo_id
                record_application(stats_person_id, job_id)
            except Exception:
                pass

            return {
                "message": f"Persona {person_id} se postuló al job {job_id}",
                "person_id": person_id,
                "job_id": job_id,
                "application_id": str(application["_id"]),
                "estado": "postulado"
            }

        except Exception as e:
            raise Exception(f"Error creando postulación: {e}")
