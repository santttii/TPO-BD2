# src/services/enrollment_service.py
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from bson import ObjectId

from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository


class EnrollmentService:
    def __init__(self):
        self.repo = MongoRepository("enrollments")
        self.people = MongoRepository("people")
        self.courses = MongoRepository("courses")
        self.graph = Neo4jRepository()
        try:
            # índices útiles (si ya existen, ignora)
            self.repo.col.create_index([("personId", 1), ("courseId", 1)], unique=True)
            self.repo.col.create_index("personId")
        except Exception:
            pass

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _clean(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        d = dict(doc)
        # tu repo ya suele “stringificar”, pero por las dudas:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
        return d

    # -------------------- API --------------------

    # src/services/enrollment_service.py
    from typing import Any, Dict, List, Optional
    from datetime import datetime
    import logging
    from bson import ObjectId

    from src.repositories.mongo_repository import MongoRepository
    from src.repositories.neo4j_repository import Neo4jRepository


    class EnrollmentService:
        def __init__(self):
            self.repo = MongoRepository("enrollments")
            self.people = MongoRepository("people")
            self.courses = MongoRepository("courses")
            self.graph = Neo4jRepository()
            try:
                # índices útiles (si ya existen, ignora)
                self.repo.col.create_index([("personId", 1), ("courseId", 1)], unique=True)
                self.repo.col.create_index("personId")
            except Exception:
                pass

        def _now(self) -> str:
            return datetime.utcnow().isoformat()

        def _clean(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not doc:
                return None
            d = dict(doc)
            # tu repo ya suele “stringificar”, pero por las dudas:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
            return d

        # -------------------- API --------------------

        def enroll(self, person_id: str, course_id: str) -> Dict[str, Any]:
            # Validaciones mínimas (existencia)
            person_doc = self.people.find_one(person_id)
            if not person_doc:
                raise ValueError("Person no existe")
            if not self.courses.find_one(course_id):
                raise ValueError("Course no existe")

            payload = {
                "personId": person_id,
                "courseId": course_id,
                "estado": "No empezó",
                "progreso": 0,
                "historial": [{"ts": self._now(), "tipo": "enroll", "detalle": "inscripto"}],
                "createdAt": self._now(),
                "updatedAt": self._now(),
            }

            try:
                created = self.repo.create(payload)  # tu repo suele devolver el doc
                out = self._clean(created) or payload
            except Exception:
                # Si hay duplicado (índice único personId+courseId), devolvemos el existente
                doc = self.repo.col.find_one({"personId": person_id, "courseId": course_id})
                out = self._clean(doc) or {}

            # Neo4j: una sola relación INSCRIPTO_EN con props (best-effort)
            try:
                # Determinar el id del nodo Person en Neo4j: preferimos userId (si existe)
                node_person_id = person_doc.get("userId") or person_id
                # upsert con progreso=0 y estado "No empezó"
                self.graph.upsert_inscripcion(node_person_id, course_id, progreso=0, estado="No empezó")
            except Exception as e:
                logging.warning(f"[enroll] Neo4j omitido por error: {e}")

            return out


        def list_by_person(self, person_id: str) -> List[Dict[str, Any]]:
            items = self.repo.find({"personId": person_id})
            # si querés orden: items = list(self.repo.col.find({"personId": person_id}).sort("createdAt", -1))
            return [self._clean(i) for i in items if i]


        def update_progress(self, enr_id: str, progreso: int, nota: Optional[int] = None) -> Dict[str, Any]:
            progreso = int(progreso)
            if not (0 <= progreso <= 100):
                raise ValueError("progreso debe estar entre 0 y 100")

            # Estado según progreso
            estado = "Completado" if progreso >= 100 else ("Cursando" if progreso > 0 else "No empezó")

            set_fields: Dict[str, Any] = {
                "progreso": progreso,
                "estado": estado,
                "updatedAt": self._now(),
            }
            if nota is not None:
                set_fields["nota"] = int(nota)

            # Mongo: $set + $push (historial)
            self.repo.col.update_one(
                {"_id": ObjectId(enr_id)},
                {
                    "$set": set_fields,
                    "$push": {"historial": {"ts": self._now(), "tipo": "progress", "detalle": f"{progreso}%"}},
                },
            )
            doc = self.repo.find_one(enr_id)
            if not doc:
                raise ValueError("Enrollment no existe")

            # Neo4j: actualizar progreso/estado en la MISMA relación INSCRIPTO_EN (best-effort)
            try:
                # doc["personId"] almacena el _id de Mongo; traducir a node id si existe userId
                person_mongo_id = doc.get("personId")
                person_doc = self.people.find_one(person_mongo_id)
                node_person_id = (person_doc.get("userId") if person_doc else None) or person_mongo_id
                self.graph.set_inscripcion_progreso(node_person_id, doc["courseId"], progreso)
            except Exception as e:
                logging.warning(f"[progress] Neo4j omitido por error: {e}")

            return self._clean(doc) or {}


        def complete(self, enr_id: str, nota: Optional[int] = None, certificacionUrl: Optional[str] = None) -> Dict[str, Any]:
            # Leemos doc para obtener personId/courseId
            curr = self.repo.find_one(enr_id)
            if not curr:
                raise ValueError("Enrollment no existe")
            person_mongo_id = curr["personId"]
            course_id = curr["courseId"]

            set_fields: Dict[str, Any] = {
                "estado": "Completado",
                "progreso": 100,
                "updatedAt": self._now(),
            }
            if nota is not None:
                set_fields["nota"] = int(nota)
            if certificacionUrl:
                set_fields["certificacionUrl"] = certificacionUrl

            # Mongo: $set + $push (historial)
            self.repo.col.update_one(
                {"_id": ObjectId(enr_id)},
                {
                    "$set": set_fields,
                    "$push": {"historial": {"ts": self._now(), "tipo": "complete", "detalle": "curso completado"}},
                },
            )

            # Neo4j: marcar completado en la MISMA relación INSCRIPTO_EN (best-effort)
            try:
                person_doc = self.people.find_one(person_mongo_id)
                node_person_id = (person_doc.get("userId") if person_doc else None) or person_mongo_id
                self.graph.set_inscripcion_completa(
                    node_person_id, course_id,
                    nota=set_fields.get("nota"),
                    certificacionUrl=set_fields.get("certificacionUrl"),
                )
            except Exception as e:
                logging.warning(f"[complete] Neo4j omitido por error: {e}")

            doc = self.repo.find_one(enr_id)
            return self._clean(doc) or {}