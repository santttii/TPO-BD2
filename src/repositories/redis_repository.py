from src.config.database import get_redis_client
import json
from typing import Optional, Dict, Any


class RedisRepository:
    """
    Repositorio unificado para Redis.
    Usa la conexión global definida en src/config/database.py.
    Mantiene métodos de caché y ranking.
    """

    def _init_(self):
        # 🔗 Conectarse a Redis usando la función global
        self.client = get_redis_client()

    # ===============================================================
    # 🧍 Caching de personas
    # ===============================================================
    def cache_person(self, person_id: str, data: Dict[str, Any], ttl_minutes: int = 10):
        """Guarda el perfil de una persona en caché (JSON) durante X minutos."""
        key = f"cache:person:{person_id}"
        self.client.setex(key, ttl_minutes * 60, json.dumps(data))

    def get_cached_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el perfil cacheado, o None si expiró."""
        key = f"cache:person:{person_id}"
        cached = self.client.get(key)
        return json.loads(cached) if cached else None

    def invalidate_person(self, person_id: str):
        """Elimina manualmente la caché de una persona."""
        key = f"cache:person:{person_id}"
        self.client.delete(key)

    # ===============================================================
    # 🧠 Rankings por empleo (ZSET)
    # ===============================================================
    def get_job_ranking(self, job_id: str, top_k: int = 10) -> list[dict]:
        """Obtiene el top-K de candidatos para un empleo desde un ZSET."""
        key = f"match:job:{job_id}:top"
        ranking_data = self.client.zrevrange(key, 0, top_k - 1, withscores=True)

        return [
            {"persona_id": pid, "affinity_score": score}
            for pid, score in ranking_data
        ]

    def set_job_ranking(self, job_id: str, ranking_dict: Dict[str, float], ttl_minutes: int = 15):
        """Guarda un ranking de afinidad en un ZSET (expira en X minutos)."""
        key = f"match:job:{job_id}:top"
        self.client.zadd(key, ranking_dict)
        self.client.expire(key, ttl_minutes * 60)