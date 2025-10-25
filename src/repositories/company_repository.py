from src.config.database import get_mongo_db

class CompanyRepository:
    def __init__(self):
        db = get_mongo_db()
        self.collection = db["companies"]

    def create(self, data: dict):
        result = self.collection.insert_one(data)
        return self.collection.find_one({"_id": result.inserted_id})

    def find_all(self, filters: dict):
        return list(self.collection.find(filters))

    def find_one(self, company_id: str):
        from bson import ObjectId
        return self.collection.find_one({"_id": ObjectId(company_id)})

    def update(self, company_id: str, updates: dict):
        from bson import ObjectId
        self.collection.update_one({"_id": ObjectId(company_id)}, {"$set": updates})
        return self.find_one(company_id)

    def delete(self, company_id: str):
        from bson import ObjectId
        return self.collection.delete_one({"_id": ObjectId(company_id)}).deleted_count
