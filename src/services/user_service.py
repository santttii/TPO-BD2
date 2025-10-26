# src/services/user_service.py
import json
from typing import List, Dict, Optional
from src.repositories.user_repository import UserRepository 
from src.repositories.relationship_repository import RelationshipRepository
from src.repositories.cache_repository import CacheRepository
# Importamos el modelo para tipificar la salida
from src.models.person import Person 

class UserService:
    def __init__(self):
        # Inicialización de todos los repositorios necesarios para este dominio
        self.user_repo = UserRepository()
        self.rel_repo = RelationshipRepository()
        self.cache_repo = CacheRepository()

    def create_new_profile(self, new_profile_data: dict) -> Person:
        """
        [Polyglot Write] Crea un nuevo perfil en MongoDB y sincroniza Neo4j.
        """
        # 1. Crear instancia del modelo Pydantic validado para trabajar con objetos
        new_person = Person(**new_profile_data) 
        
        # 2. Persistencia en MongoDB (CP - Fuente de Verdad)
        # Aquí se insertaría el documento en la colección 'personas'
        # El método insert_one podría retornar el ID. Usamos el modelo Pydantic.
        # Asumiendo que new_person.id ya está poblado.
        self.user_repo.insert_one_person(new_person.dict(by_alias=True))
        
        # 3. Sincronización con Neo4j (AP - Red y Recomendaciones)
        self.rel_repo.sync_person_node(new_person) 
        
        # 4. Publicar evento (Opcional: invalidación/notificación)
        # self.cache_repo.client.publish("profile.created", new_person.id)

        return new_person # Retorna el objeto Persona completo

    def get_profile(self, user_id: str):
        """
        [AP: Cache-Aside] Obtiene el perfil de Redis o de MongoDB (maestro).
        """
        # 1. LECTURA AP: Cache Hit (Latencia sub-milisegundo)
        profile_cached = self.cache_repo.get_profile_cache(user_id)
        if profile_cached:
            return json.loads(profile_cached)

        # 2. CACHE MISS: Lectura CP (Consistencia) de MongoDB
        user_data = self.user_repo.find_by_id(user_id)

        if user_data:
            # 3. Escritura en Cache: Serializa el modelo y lo guarda en Redis.
            profile_obj = Person(**user_data)
            self.cache_repo.set_profile_cache(user_id, profile_obj.json())
            return profile_obj.dict(by_alias=True)
            
        return None

    def update_profile(self, user_id: str, updates: dict):
        """
        [Polyglot Write] Actualiza el perfil en Mongo y sincroniza Neo4j/Redis.
        """
        # 1. ESCRITURA CP: Actualizar MongoDB (colección 'personas')
        # user_repo.update_profile(user_id, updates, w:"majority") 
        
        # 2. Sincronizar Neo4j (Consistencia Eventual / AP)
        # Asumiendo que obtienes la Persona actualizada completa después de la escritura en Mongo
        updated_person_data = self.user_repo.find_by_id(user_id)
        if updated_person_data:
            updated_person = Person(**updated_person_data)
            self.rel_repo.sync_person_node(updated_person) 
            
            # 3. Invalidación de Caché (Redis Pub/Sub o Expire)
            # Para asegurar que la próxima lectura no use datos viejos.
            self.cache_repo.client.delete(f"cache:person:{user_id}")
            # self.cache_repo.client.publish(f"invalidate:person:{user_id}", "updated")
            
        return {"user_id": user_id, "status": "Updated", "data_stores": "Mongo, Neo4j, Redis"}

    def get_profile_version_history(self, user_id: str) -> List[Dict]:
        """
        Obtiene el historial de versiones del perfil desde MongoDB.
        RF 1. Historial de cambios y evolución.
        """
        # Esta es una lectura sensible (auditoría), va directamente a MongoDB (CP)
        return self.user_repo.find_profile_history(user_id)

    def get_recommendations(self, user_id: str) -> List[Dict]:
        """
        Obtiene recomendaciones de cursos basadas en intereses.
        RF 5. Sistema de Recomendaciones. Fuente principal: Neo4j (AP).
        """
        # La lógica de afinidad compleja se delega a Neo4j
        recommendations = self.rel_repo.get_course_recommendations(user_id)
        
        # Lógica de negocio adicional: podrías combinar recomendaciones por red social aquí
        return recommendations