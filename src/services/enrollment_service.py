# enrollment_service.py
from typing import Any, Dict, List, Optional
# en src/services/course_service.py y enrollment_service.py
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository

from datetime import datetime

class EnrollmentService:
    def __init__(self):
        self.repo = MongoRepository("enrollments")
        self.people = MongoRepository("people")
        self.courses = MongoRepository("courses")
        self.graph = Neo4jRepository()
        try:
            self.repo.collection.create_index([("personId", 1), ("courseId", 1)], unique=True)
            self.repo.collection.create_index("personId")
        except Exception:
            pass

    def _now(self): return datetime.utcnow().isoformat()

    def enroll(self, person_id: str, course_id: str) -> Dict[str, Any]:
        if not self.people.find_by_id(person_id):
            raise ValueError("Person no existe")
        if not self.courses.find_by_id(course_id):
            raise ValueError("Course no existe")

        payload = {
            "personId": person_id,
            "courseId": course_id,
            "estado": "inscripto",
            "progreso": 0,
            "historial": [{"ts": self._now(), "tipo": "enroll", "detalle": "inscripto"}],
            "createdAt": self._now(),
            "updatedAt": self._now()
        }
        try:
            _id = self.repo.create(payload)
        except Exception:
            # ya existía -> devolver el actual
            doc = self.repo.find_one({"personId": person_id, "courseId": course_id})
            doc["id"] = str(doc.pop("_id"))
            return doc

        # Neo4j: INSCRIPTO_EN
        self.graph.link_person_to_course(person_id, course_id)

        payload["id"] = str(_id)
        return payload

    def list_by_person(self, person_id: str) -> List[Dict[str, Any]]:
        items = self.repo.find({"personId": person_id}, sort=[("createdAt", -1)])
        for it in items: it["id"] = str(it.pop("_id"))
        return items

    def update_progress(self, enr_id: str, progreso: int, nota: Optional[int] = None) -> Dict[str, Any]:
        if not (0 <= int(progreso) <= 100):
            raise ValueError("progreso debe estar entre 0 y 100")
        upd = {
            "progreso": int(progreso),
            "updatedAt": self._now(),
        }
        if 0 < int(progreso) < 100:
            upd["estado"] = "en_progreso"
        if nota is not None:
            upd["nota"] = int(nota)
        enr = self.repo.update_by_id(enr_id, {
            **upd,
            "$push": {"historial": {"ts": self._now(), "tipo": "progress", "detalle": f"{progreso}%"}}
        })
        if not enr: raise ValueError("Enrollment no existe")
        enr["id"] = str(enr.pop("_id"))
        return enr

    def complete(self, enr_id: str, nota: Optional[int] = None, certificacionUrl: Optional[str] = None) -> Dict[str, Any]:
        enr = self.repo.find_by_id(enr_id)
        if not enr: raise ValueError("Enrollment no existe")

        person_id = enr["personId"]; course_id = enr["courseId"]
        updates = {
            "estado": "completo",
            "progreso": 100,
            "updatedAt": self._now(),
        }
        if nota is not None:
            updates["nota"] = int(nota)
        if certificacionUrl:
            updates["certificacionUrl"] = certificacionUrl

        enr = self.repo.update_by_id(enr_id, {
            **updates,
            "$push": {"historial": {"ts": self._now(), "tipo": "complete", "detalle": "curso completado"}}
        })
        # Neo4j: marcar COMPLETO (y opcionalmente podrías eliminar INSCRIPTO_EN)
        self.graph.mark_course_completed(person_id, course_id, nota=updates.get("nota"))

        enr["id"] = str(enr.pop("_id"))
        return enr
