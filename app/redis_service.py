import redis
import os

def probar_redis():
    uri = os.getenv("REDIS_URI")
    r = redis.from_url(uri)
    print(f"⚡ Redis conectado. Valor guardado: {r.get('saludo').decode()}")
