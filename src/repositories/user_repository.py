from datetime import datetime
from src.config.database import get_mongo_db
from bson import ObjectId

class UserRepository:
    def __init__(self):
        db = get_mongo_db()
        self.collection = db["users"]

    def find_by_username(self, username: str):
        return self.collection.find_one({"username": username})

    def create(self, username: str, password_hash: str) -> str:
        doc = {
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.utcnow(),
        }
        res = self.collection.insert_one(doc)
        return str(res.inserted_id)
