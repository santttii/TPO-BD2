# src/services/course_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from bson import ObjectId

from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository


class CourseService:
    def __init__(self) -> None:
        self.repo = MongoRepository("courses")
        self.graph = Neo4jRepository()
        # índice único por slug (ignora si ya existe)
        try:
            # muchos repos exponen .collection (pymongo)
            if getattr(self.repo, "collection", None):
                self.repo.collection.create_index("slug", unique=True)
        except Exception:
            pass

    # -------------------- helpers internos --------------------
    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _extract_id(self, inserted: Any) -> str:
        """
        Soporta distintos retornos de create():
        - ObjectId
        - InsertOneResult (prop .inserted_id)
        - dict con _id
        - fallback a str(inserted)
        """
        if isinstance(inserted, ObjectId):
            return str(inserted)
        inserted_id = getattr(inserted, "inserted_id", None)
        if isinstance(inserted_id, ObjectId):
            return str(inserted_id)
        if isinstance(inserted, dict) and "_id" in inserted:
            return str(inserted["_id"])
        return str(inserted)

    def _clean_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    # -------------------- CRUD --------------------
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 1) Normalizamos/validamos entrada
        course: Dict[str, Any] = {
            "titulo": payload["titulo"],
            "slug": payload["slug"],
            "descripcion": payload.get("descripcion"),
            "skillsOtorgadas": payload.get("skillsOtorgadas", []),  # [{nombre, nivelMin?}]
            "Pdfs": payload.get("Pdfs", []),  # lista de PDFs asociados al curso
            "metadata": payload.get("metadata", {}),
            "createdAt": self._now(),
            "updatedAt": self._now(),
        }

        # 2) Persistimos en Mongo
        inserted = self.repo.create(course)
        course_id = self._extract_id(inserted)
        course["id"] = course_id
        course.pop("_id", None)  # blindaje contra ObjectId en respuesta

        # 3) Side-effects en Neo4j (no deben romper la API)
        try:
            proveedor = (course.get("metadata") or {}).get("proveedor")
            self.graph.create_course_node(course_id, course["titulo"], proveedor)
            for s in course.get("skillsOtorgadas", []):
                if isinstance(s, dict) and s.get("nombre"):
                    self.graph.link_course_to_skill(course_id, s["nombre"], s.get("nivelMin"))
        except Exception as e:
            logging.warning(f"[courses.create] Neo4j omitido por error: {e}")

        return course

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if filters:
            if filters.get("q"):
                q["titulo"] = {"$regex": filters["q"], "$options": "i"}
            if filters.get("skill"):
                q["skillsOtorgadas.nombre"] = {"$regex": f"^{filters['skill']}$", "$options": "i"}
            if filters.get("dificultad"):
                q["metadata.dificultad"] = filters["dificultad"]

        # Si tu repo.find no soporta limit/skip/sort por parámetros,
        # igual funciona con solo el query.
        items = self.repo.find(q)

        # Normalizamos ids
        cleaned: List[Dict[str, Any]] = []
        for it in items:
            it = dict(it)
            if "_id" in it:
                it["id"] = str(it.pop("_id"))
            cleaned.append(it)

        # Paginación simple (si la querés aplicar desde filtros)
        if filters:
            try:
                offset = int(filters.get("offset", 0))
                limit = int(filters.get("limit", 20))
                cleaned = cleaned[offset: offset + limit]
            except Exception:
                pass

        return cleaned

    def get(self, course_id: str) -> Optional[Dict[str, Any]]:
        doc = self.repo.find_one(course_id)
        return self._clean_doc(doc)

    def update(self, course_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates = dict(updates or {})
        updates["updatedAt"] = self._now()

        # El repositorio ya aplica $set dentro de su método update(),
        # por lo que debemos pasarle el diccionario de campos directamente.
        # Evitamos envolver en {"$set": ...} para no producir un update inválido.
        try:
            doc = self.repo.update(course_id, updates)
        except Exception:
            # Fallback por compatibilidad si el repo expone otra API
            if hasattr(self.repo, "update_by_id"):
                doc = self.repo.update_by_id(course_id, updates)
            else:
                # re-lanzar la excepción para que el caller vea el error
                raise

        out = self._clean_doc(doc)
        if not out:
            return None

        # ---- Sincronía Neo4j (best-effort) ----
        try:
            # refrescar nodo solo si cambió titulo o proveedor
            if "titulo" in updates or "metadata" in updates:
                titulo = updates.get("titulo", out.get("titulo"))
                proveedor = (updates.get("metadata") or out.get("metadata") or {}).get("proveedor") \
                            if isinstance(updates.get("metadata") or out.get("metadata"), dict) else None
                if titulo is not None:
                    self.graph.create_course_node(course_id, titulo, proveedor)

            # si cambiaron las skills, refrescar relaciones
            if "skillsOtorgadas" in updates and isinstance(out.get("skillsOtorgadas"), list):
                self.graph.delete_course_skill_links(course_id)
                for s in out["skillsOtorgadas"]:
                    if isinstance(s, dict) and s.get("nombre"):
                        self.graph.link_course_to_skill(course_id, s["nombre"], s.get("nivelMin"))
        except Exception as e:
            logging.warning(f"[courses.update] Neo4j omitido por error: {e}")

        return out


    def delete(self, course_id: str) -> bool:
        # Borramos primero en Neo4j (DETACH borra relaciones)
        try:
            self.graph.delete_course_node(course_id)
        except Exception as e:
            logging.warning(f"[courses.delete] Neo4j omitido por error: {e}")
        # Luego en Mongo
        return bool(self.repo.delete(course_id))
