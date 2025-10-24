# course_service.py
from typing import Any, Dict, List, Optional

from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository

from datetime import datetime

class CourseService:
    def __init__(self):
        self.repo = MongoRepository("courses")
        self.graph = Neo4jRepository()
        # Índices recomendados
        try:
            self.repo.collection.create_index("slug", unique=True)
        except Exception:
            pass

    def _now(self): return datetime.utcnow().isoformat()

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        course = {
            "titulo": payload["titulo"],
            "slug": payload["slug"],
            "descripcion": payload.get("descripcion"),
            "skillsRequeridos": payload.get("skillsRequeridos", []),  # [{nombre, nivelMin?}]
            "metadata": payload.get("metadata", {}),
            "createdAt": self._now(),
            "updatedAt": self._now()
        }
        _id = self.repo.create(course)
        course["id"] = str(_id)

        # Neo4j: nodo Course + relaciones a Skill
        self.graph.create_course_node(course["id"], course["titulo"], course["metadata"].get("proveedor"))
        for s in course["skillsRequeridos"]:
            self.graph.link_course_to_skill(course["id"], s["nombre"], s.get("nivelMin"))

        return course

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        q = {}
        if filters:
            if filters.get("q"):
                q["titulo"] = {"$regex": filters["q"], "$options": "i"}
            if filters.get("skill"):
                q["skillsRequeridos.nombre"] = {"$regex": f"^{filters['skill']}$", "$options": "i"}
            if filters.get("dificultad"):
                q["metadata.dificultad"] = filters["dificultad"]
        limit = int(filters.get("limit", 20)) if filters else 20
        offset = int(filters.get("offset", 0)) if filters else 0

        items = self.repo.find(q, limit=limit, skip=offset, sort=[("createdAt", -1)])
        for it in items: it["id"] = str(it.pop("_id"))
        return items

    def get(self, course_id: str) -> Optional[Dict[str, Any]]:
        doc = self.repo.find_by_id(course_id)
        if not doc: return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    def update(self, course_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["updatedAt"] = self._now()
        doc = self.repo.update_by_id(course_id, updates)
        if not doc: return None
        # Si cambiaron skillsRequeridos, refrescar relaciones
        if "skillsRequeridos" in updates:
            self.graph.delete_course_skill_links(course_id)
            for s in updates["skillsRequeridos"]:
                self.graph.link_course_to_skill(course_id, s["nombre"], s.get("nivelMin"))
        doc["id"] = str(doc.pop("_id"))
        return doc

    def delete(self, course_id: str) -> bool:
        ok = self.repo.delete_by_id(course_id)
        self.graph.delete_course_node(course_id)
        return bool(ok)
