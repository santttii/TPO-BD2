from pymongo import MongoClient
import os

def probar_mongo():
    uri = os.getenv("MONGO_URI")
    client = MongoClient(uri)
    db = client.get_default_database()
    print(f"🟢 Mongo conectado a la base: {db.name}")


