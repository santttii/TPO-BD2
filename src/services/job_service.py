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
           obligatorios = requisitos.get("obligatorios", [])
           deseables = requisitos.get("deseables", [])
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
        if updated:
            updated["_id"] = str(updated["_id"])
        return updated

    # ===============================================================
    # 🗑️ DELETE
    # ===============================================================
    def delete(self, job_id: str) -> bool:
        return self.repo.delete(job_id)

    # ===============================================================
    # 🧍 POSTULACIÓN (Person -> Job)
    # ===============================================================
    def apply(self, person_id: str, job_id: str) -> Dict[str, Any]:
        """
        Crea una relación de postulación entre una persona y un empleo.
        """
        try:
            self.graph_repo.apply_to_job(person_id, job_id)
            return {
                "message": f"Persona {person_id} postulada al Job {job_id}",
                "personId": person_id,
                "jobId": job_id
            }
        except Exception as e:
            raise Exception(f"Error creando relación POSTULA_A: {e}")

