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
        # timestamps por defecto
        now = datetime.utcnow()
        data.setdefault("versionActual", 1)
        data.setdefault("creadoEn", now)
        data.setdefault("actualizadoEn", now)

        # 👇 Si vino _id, upsert con ese _id (conversión a ObjectId si corresponde)
        _id = data.get("_id")
        if _id is not None:
            # Convertir _id str → ObjectId si parece un hex de 24 chars
            if isinstance(_id, str) and len(_id) == 24:
                try:
                    _id = ObjectId(_id)
                    data["_id"] = _id
                except Exception:
                    pass  # si no convierte, lo deja como vino (Mongo también acepta str como _id)

            self.col.replace_one({"_id": _id}, data, upsert=True)
            created = self.col.find_one({"_id": _id})
            return self._stringify_id(created)

    # 👇 Sin _id → insert normal
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
    

