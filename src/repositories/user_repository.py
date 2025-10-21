# src/repositories/user_repository.py
import os
from pymongo import MongoClient, errors, WriteConcern # <-- AGREGAR WriteConcern aquí
from typing import Optional, Dict, List
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Para asegurar que las variables de entorno estén cargadas
load_dotenv()

class UserRepository:
    def __init__(self):
        uri = os.getenv("MONGO_URI")
        db_name = os.getenv("MONGO_DATABASE")
        
        # Conexión, usando authSource en el URI o como parámetro si es necesario
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Seleccionar la base de datos de destino
        self.db = self.client[db_name] 
        
        # Colecciones clave del dominio People
        self.personas = self.db['personas'] 
        self.versiones_persona = self.db['versiones_persona']

    def insert_one_person(self, person_data: Dict):
        """
        Inserta un nuevo documento en la colección personas, forzando 
        Write Concern Majority para asegurar consistencia (CP).
        """
        # 1. Definir el WriteConcern
        majority_write_concern = WriteConcern(w="majority")
        
        # 2. Usar with_options() en la colección para aplicar el Write Concern
        # Esto devuelve una nueva instancia de la colección con las opciones aplicadas.
        personas_collection_cp = self.personas.with_options(
            write_concern=majority_write_concern
        )
        
        # 3. Ejecutar la inserción en la colección con la opción CP
        return personas_collection_cp.insert_one(
            person_data
            # Ya NO se pasa write_concern como keyword arg aquí
        )

    def find_by_id(self, persona_id: str) -> Optional[Dict]:
        """
        Obtiene un perfil completo de MongoDB por su ID.
        RF 1. Modelo de Candidatos y Empleados.
        """
        # Se asume que la clave _id es un string hashado (no ObjectId)
        return self.personas.find_one({"_id": persona_id})

    def find_profile_history(self, persona_id: str) -> List[Dict]:
        """
        Obtiene el historial de cambios del perfil de la persona.
        RF 1. Historial de cambios y evolución en su perfil.
        Índice: { personaId: 1, version: -1 }.
        """
        # Se usa sort descendente en la versión para obtener el historial más reciente primero
        return list(self.versiones_persona.find({"personaId": persona_id}).sort("version", -1))
        
    def find_by_skill_name(self, skill_name: str) -> List[Dict]:
        """
        Busca todos los perfiles que poseen una habilidad específica.
        RF 6. Segmentaciones por skill.
        Índice clave: { "perfil.habilidades.nombre": 1 }.
        """
        query = {"perfil.habilidades.nombre": skill_name}
        # Solo retornar campos relevantes para listado
        projection = {"_id": 1, "datosPersonales.nombre": 1, "perfil.titulo": 1} 
        return list(self.personas.find(query, projection))

    def close_connection(self):
        self.client.close()