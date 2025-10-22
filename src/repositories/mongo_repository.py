from src.config.database import get_mongo_db
from typing import Any, Dict, List, Optional
from bson import ObjectId
from datetime import datetime


class MongoRepository:
    def __init__(self, collection_name: str):
        # 🔗 Conectarse a Mongo usando la función global de config/database.py
        db = get_mongo_db()
        self.col = db[collection_name]

    @staticmethod
    def _stringify_id(doc: Dict[str, Any]) -> Dict[str, Any]:
        if not doc:
            return doc
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        return doc

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        data.setdefault("versionActual", 1)
        data.setdefault("creadoEn", now)
        data.setdefault("actualizadoEn", now)
        res = self.col.insert_one(data)
        created = self.col.find_one({"_id": res.inserted_id})
        return self._stringify_id(created)

    def find_one(self, _id: str) -> Optional[Dict[str, Any]]:
        doc = self.col.find_one({"_id": ObjectId(_id)})
        return self._stringify_id(doc) if doc else None

    def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [self._stringify_id(d) for d in self.col.find(query)]

    def update(self, _id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["actualizadoEn"] = datetime.utcnow()
        self.col.update_one({"_id": ObjectId(_id)}, {"$set": updates})
        doc = self.col.find_one({"_id": ObjectId(_id)})
        return self._stringify_id(doc)
