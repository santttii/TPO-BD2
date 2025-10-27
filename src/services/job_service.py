from typing import Dict, Any, List, Optional
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository


class JobService:
    def __init__(self):
        self.repo = MongoRepository("jobs")
        self.graph_repo = Neo4jRepository()

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
                # eliminar links previos y volver a crear según updated
                try:
                    self.graph_repo.delete_job_skill_links(job_id)
                except Exception:
                    pass

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
        Crea una relación de postulación entre una persona y un empleo.
        """
        try:
            # 1) Asegurarnos de que el nodo Job exista en Neo4j. Si no existe,
            # intentar crearlo a partir del documento en Mongo.
            try:
                job_exists = self.graph_repo.node_exists("Job", job_id)
            except Exception:
                job_exists = False

            if not job_exists:
                job_doc = None
                try:
                    job_doc = self.repo.find_one(job_id)
                except Exception:
                    job_doc = None

                if job_doc:
                    titulo = job_doc.get("titulo", "Sin Titulo")
                    empresa_id = job_doc.get("empresaId")
                    try:
                        self.graph_repo.create_job_node(job_id=job_id, titulo=titulo, empresa_id=empresa_id)
                    except Exception as e:
                        print(f"⚠️ Error creando Job en Neo4j: {e}")

            # Re-check
            if not self.graph_repo.node_exists("Job", job_id):
                raise Exception(f"Job node {job_id} no existe en Neo4j y no pudo crearse")

            # 2) Asegurarnos de que exista el nodo Person en Neo4j. Si no, intentar
            # reconstruirlo desde la colección `people` en Mongo.
            try:
                person_exists = self.graph_repo.node_exists("Person", person_id)
            except Exception:
                person_exists = False

            if not person_exists:
                people_repo = MongoRepository("people")
                person_doc = None
                # Buscar por userId
                try:
                    found = people_repo.find({"userId": person_id})
                    if found:
                        person_doc = found[0]
                except Exception:
                    person_doc = None

                # Si no se encontró, intentar por _id
                if not person_doc:
                    try:
                        person_doc = people_repo.find_one(person_id)
                    except Exception:
                        person_doc = None

                if person_doc:
                    node_id = person_doc.get("userId") or person_doc.get("_id")
                    node_id = str(node_id)
                    nombre = person_doc.get("datosPersonales", {}).get("nombre", "Desconocido")
                    rol = person_doc.get("rol", "Sin Rol")
                    try:
                        self.graph_repo.create_person_node(person_id=node_id, nombre=nombre, rol=rol)

                        # Vincular habilidades si existieran
                        habilidades = []
                        if "habilidades" in person_doc:
                            habilidades = person_doc.get("habilidades", [])
                        elif "perfil" in person_doc and "skills" in person_doc["perfil"]:
                            habilidades = person_doc["perfil"]["skills"]

                        for skill in habilidades:
                            if isinstance(skill, str):
                                self.graph_repo.link_person_to_skill(node_id, skill, nivel=1)
                            elif isinstance(skill, dict):
                                nombre_skill = skill.get("nombre")
                                nivel = skill.get("nivel", 1)
                                if nombre_skill:
                                    self.graph_repo.link_person_to_skill(node_id, nombre_skill, nivel=nivel)

                        # Usar el node_id real para la postulación
                        person_id = node_id
                    except Exception as e:
                        print(f"⚠️ Error creando Person node en Neo4j: {e}")

            # 3) Finalmente crear la relación POSTULA_A
            self.graph_repo.apply_to_job(person_id, job_id)

            return {
                "message": f"Persona {person_id} postulada al Job {job_id}",
                "personId": person_id,
                "jobId": job_id
            }

        except Exception as e:
            raise Exception(f"Error creando relación POSTULA_A: {e}")

