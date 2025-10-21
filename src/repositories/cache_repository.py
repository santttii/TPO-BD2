# src/repositories/cache_repository.py
import os
import redis
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

class CacheRepository:
    def __init__(self):
        uri = os.getenv("REDIS_URI")
        # El cliente es thread-safe y se reutiliza
        self.client = redis.from_url(uri)

    def get_job_ranking(self, job_id: str) -> List[Dict]:
        """
        Obtiene el ranking top-K de candidatos para un empleo desde un ZSET.
        RF 2. Matching automático (acceso al ranking). Clave: match:job:{empleoId}:top[cite: 360].
        """
        key = f"match:job:{job_id}:top"
        # ZRANGE con_scores=True retorna una lista de tuplas [(member, score), ...]
        ranking_data = self.client.zrevrange(key, 0, 9, withscores=True) # Top 10
        
        ranking = []
        for persona_id_bytes, score in ranking_data:
            ranking.append({
                "persona_id": persona_id_bytes.decode('utf-8'),
                "affinity_score": score
            })
        return ranking

    def set_job_ranking(self, job_id: str, ranking_dict: Dict[str, float], ttl_minutes: int = 15):
        """
        Almacena un nuevo ranking de afinidad después de ejecutar el matching.
        """
        key = f"match:job:{job_id}:top"
        # Usamos ZADD para el ranking
        self.client.zadd(key, ranking_dict)
        self.client.expire(key, ttl_minutes * 60) # TTL: 15 minutos [cite: 360, 443]

    def set_profile_cache(self, persona_id: str, profile_json: str, ttl_minutes: int = 10):
        """
        Cacha un perfil agregado de MongoDB/Neo4j. Clave: cache:person:{personaId}[cite: 352].
        """
        key = f"cache:person:{persona_id}"
        self.client.set(key, profile_json, ex=ttl_minutes * 60)

    def get_profile_cache(self, persona_id: str) -> Optional[str]:
        """Recupera el perfil cacheado (reduce golpes a Mongo/Neo)[cite: 353]."""
        key = f"cache:person:{persona_id}"
        data = self.client.get(key)
        return data.decode('utf-8') if data else None