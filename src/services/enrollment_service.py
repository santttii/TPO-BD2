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

            # --- Actualizar el modelo people en MongoDB ---
            try:
                # Buscar persona
                person_doc = self.people.find_one(person_id)
                if person_doc is not None:
                    cursos = person_doc.get("cursos", [])
                    # Buscar si ya existe el curso
                    found = False
                    for c in cursos:
                        if c.get("cursoId") == course_id:
                            c["estado"] = payload["estado"]
                            found = True
                            break
                    if not found:
                        cursos.append({"cursoId": course_id, "estado": payload["estado"], "certificacion": None})
                    self.people.update(person_id, {"cursos": cursos})
            except Exception as e:
                logging.warning(f"[enroll] No se pudo actualizar cursos en people: {e}")

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

            # --- Actualizar el atributo 'cursos' en el documento de la persona ---
            try:
                person_mongo_id = doc.get("personId")
                if person_mongo_id:
                    pdoc = self.people.find_one(person_mongo_id)
                    if pdoc is not None:
                        cursos = pdoc.get("cursos", [])
                        found = False
                        for c in cursos:
                            if c.get("cursoId") == doc.get("courseId"):
                                # actualizar sólo el estado, manteniendo la certificación si existe
                                c["estado"] = estado
                                found = True
                                break
                        if not found:
                            cursos.append({"cursoId": doc.get("courseId"), "estado": estado, "certificacion": None})
                        self.people.update(person_mongo_id, {"cursos": cursos})
            except Exception as e:
                logging.warning(f"[progress] No se pudo actualizar cursos en people: {e}")

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
                # Marcar completado en la relación INSCRIPTO_EN
                self.graph.set_inscripcion_completa(
                    node_person_id, course_id,
                    nota=set_fields.get("nota"),
                    certificacionUrl=set_fields.get("certificacionUrl"),
                )

                # --- NUEVO: agregar las skills que otorga el curso a la persona ---
                try:
                    course_doc = self.courses.find_one(course_id)
                    if course_doc:
                        skills = course_doc.get("skillsOtorgadas") or []
                        for s in skills:
                            # soporta formato dict {"nombre":..., "nivelMin":...} o string
                            if isinstance(s, dict):
                                skill_name = s.get("nombre") or s.get("name")
                                nivel = s.get("nivelMin") or s.get("nivel") or 1
                            elif isinstance(s, str):
                                skill_name = s
                                nivel = 1
                            else:
                                continue

                            if not skill_name:
                                continue

                            try:
                                # link_person_to_skill hace MERGE del nodo Skill si hace falta
                                self.graph.link_person_to_skill(node_person_id, skill_name, nivel=int(nivel))
                            except Exception as e:
                                logging.warning(f"[complete] fallo vinculando skill '{skill_name}' a persona {node_person_id}: {e}")
                except Exception as e:
                    logging.warning(f"[complete] No se pudieron asignar skills del curso en Neo4j: {e}")
            except Exception as e:
                logging.warning(f"[complete] Neo4j omitido por error: {e}")

            doc = self.repo.find_one(enr_id)
            # --- Actualizar el atributo 'cursos' en el documento de la persona (estado = Completado) ---
            try:
                p = self.people.find_one(person_mongo_id)
                if p is not None:
                    cursos = p.get("cursos", [])
                    found = False
                    # construir objeto de certificación a insertar en el curso
                    cert_url = set_fields.get("certificacionUrl")
                    cert_obj = None
                    try:
                        course_doc = self.courses.find_one(course_id)
                        # prioridad: certificacionUrl pasada en el request; si no existe, intentar extraer del course_doc
                        if cert_url:
                            cert_obj = {"nombre": (course_doc.get("titulo") if course_doc else "Certificado"), "url": cert_url, "nota": set_fields.get("nota"), "emitidoEn": self._now()}
                        else:
                            # intentar extraer una certificación desde el documento del curso
                            if course_doc:
                                cinfo = course_doc.get("certificaciones") or (course_doc.get("metadata") or {}).get("certificaciones")
                                if cinfo:
                                    # tomar la primera certificación si existe
                                    first = cinfo[0]
                                    if isinstance(first, dict):
                                        cert_obj = {"nombre": first.get("nombre") or course_doc.get("titulo"), "url": first.get("url"), "nota": set_fields.get("nota"), "emitidoEn": self._now()}
                                    elif isinstance(first, str):
                                        cert_obj = {"nombre": first, "url": None, "nota": set_fields.get("nota"), "emitidoEn": self._now()}
                    except Exception:
                        cert_obj = cert_obj

                    for c in cursos:
                        if c.get("cursoId") == course_id:
                            c["estado"] = "Completado"
                            # insertar certificación dentro del curso
                            if cert_obj:
                                c["certificacion"] = cert_obj
                            found = True
                            break
                    if not found:
                        entry = {"cursoId": course_id, "estado": "Completado", "certificacion": cert_obj}
                        cursos.append(entry)
                    self.people.update(person_mongo_id, {"cursos": cursos})
            except Exception as e:
                logging.warning(f"[complete] No se pudo actualizar cursos en people: {e}")

            return self._clean(doc) or {}