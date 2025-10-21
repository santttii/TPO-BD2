# src/services/cache_service.py
from typing import Dict, List
from src.repositories.cache_repository import CacheRepository
import json

class CacheService:
    def __init__(self):
        self.cache_repo = CacheRepository()

    def get_job_ranking_cache(self, job_id: str) -> List[Dict]:
        """
        Acceso directo a la caché del ranking de afinidad para un empleo.
        Fuente: Redis ZSET.
        """
        return self.cache_repo.get_job_ranking(job_id)

    def set_profile_cache_and_notify(self, user_id: str, profile_data: Dict):
        """
        Simula el almacenamiento en caché y la notificación de invalidación.
        Fuente: Redis String y Pub/Sub.
        """
        profile_json = json.dumps(profile_data)
        
        # 1. Almacenar el perfil agregado en caché
        self.cache_repo.set_profile_cache(user_id, profile_json)

        # 2. Publicar un evento de invalidación (ejemplo usando Pub/Sub, si se implementara)
        # Esto sería útil para notificar a otras instancias o servicios que la caché cambió.
        # self.cache_repo.client.publish(f"invalidate:person:{user_id}", "updated")
        
        return {"status": "Cache updated", "notification_sent": "Simulated"}