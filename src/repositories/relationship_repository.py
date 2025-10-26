# src/repositories/relationship_repository.py
import os
from neo4j import GraphDatabase
from typing import Optional, List, Dict
from dotenv import load_dotenv
from src.models.person import Person # Importamos el modelo de MongoDB

load_dotenv()

class RelationshipRepository:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        
        # El driver es un recurso caro, se inicializa una sola vez.
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def _execute_read(self, query: str, parameters: Dict = None) -> List[Dict]:
        """Helper para ejecutar transacciones de lectura."""
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def _execute_write(self, query: str, parameters: Dict = None):
        """Helper para ejecutar transacciones de escritura (Creación/Actualización)."""
        # 🚨 ADD THIS METHOD 🚨
        with self.driver.session() as session:
            session.execute_write(lambda tx: tx.run(query, parameters)) 

    def sync_person_node(self, person_data: Person):
        """
        [Polyglot Integration] Sincroniza un perfil de MongoDB como nodo en Neo4j.
        Crea/Actualiza el nodo Persona y sus relaciones de Habilidad e Intereses.
        Fuente: Nodo Persona, Relaciones POSEE_HABILIDAD y TIENE_INTERES_EN.
        """
        person_id = person_data.id

        # 1. MERGE del Nodo Persona principal
        person_query = """
        MERGE (p:Persona {idPersona: $id})
        ON CREATE SET p.nombre = $nombre, p.rol = $rol, p.creadoEn = TIMESTAMP()
        ON MATCH SET p.actualizadoEn = TIMESTAMP()
        """
        self._execute_write(person_query, {
            "id": person_id,
            "nombre": person_data.datosPersonales.nombre,
            "rol": person_data.rol
        })

        # 2. Sincronizar POSEE_HABILIDAD (Borra viejas y crea nuevas)
        self._execute_write("MATCH (p:Persona {idPersona: $id})-[r:POSEE_HABILIDAD]->() DELETE r", {"id": person_id})
        for skill in person_data.perfil.habilidades:
            skill_query = """
            MERGE (h:Habilidad {nombre: $skillName})
            MERGE (p:Persona {idPersona: $id})
            MERGE (p)-[:POSEE_HABILIDAD {nivel: $level}]->(h)
            """
            self._execute_write(skill_query, {"id": person_id, "skillName": skill.nombre, "level": skill.nivel})
        
        # 3. Sincronizar TIENE_INTERES_EN
        self._execute_write("MATCH (p:Persona {idPersona: $id})-[r:TIENE_INTERES_EN]->() DELETE r", {"id": person_id})
        for interest in person_data.perfil.intereses:
            interest_query = """
            MERGE (h:Habilidad {nombre: $interestName})
            MERGE (p:Persona {idPersona: $id})
            MERGE (p)-[:TIENE_INTERES_EN]->(h)
            """
            self._execute_write(interest_query, {"id": person_id, "interestName": interest})

    def calculate_affinity(self, persona_id: str, empleo_id: str) -> float:
        """
        Calcula el nivel de afinidad entre un candidato y un empleo.
        RF 2. Matching automático.
        Implementa la fórmula ponderada (Coincidencias exactas: 0.6, Intereses: 0.15, etc.)[cite: 306, 308].
        """
        query = """
        MATCH (p:Persona {idPersona: $personaId})
        MATCH (e:Empleo {idEmpleo: $empleoId})
        
        // 1. Coincidencias exactas (Peso 0.6)
        OPTIONAL MATCH (p)-[:POSEE_HABILIDAD]->(h:Habilidad)<-[:REQUERIMIENTO_DE]-(e)
        WITH p, e, COUNT(DISTINCT h) AS exactMatches

        // 2. Habilidades relacionadas (Peso 0.15) - Simplificado por ahora
        // OPTIONAL MATCH (p)-[:POSEE_HABILIDAD]->()-[:RELACIONADA_CON]->(hr:Habilidad)<-[:REQUERIMIENTO_DE]-(e)
        // WITH p, e, exactMatches, COUNT(DISTINCT hr) AS relatedMatches

        // 3. Intereses del candidato (Peso 0.15)
        OPTIONAL MATCH (p)-[:TIENE_INTERES_EN]->(i:Habilidad)<-[:REQUERIMIENTO_DE]-(e)
        WITH p, e, exactMatches, COUNT(DISTINCT i) AS interestMatches
        
        // CÁLCULO SIMPLIFICADO: Solo contamos las coincidencias directas e intereses
        // En producción, se usaría un factor de normalización y todos los pesos.
        WITH (exactMatches * 0.6) + (interestMatches * 0.15) AS affinityScore
        RETURN affinityScore
        """
        params = {"personaId": persona_id, "empleoId": empleo_id}
        result = self._execute_read(query, params)
        
        # Devolver 0.0 si no hay resultado, o el puntaje
        return result[0]['affinityScore'] if result and 'affinityScore' in result[0] else 0.0

    def get_course_recommendations(self, persona_id: str) -> List[Dict]:
        """
        Recomendaciones de cursos basadas en intereses del usuario.
        RF 5. Sistema de Recomendaciones (por intereses)[cite: 296].
        """
        query = """
        MATCH (p:Persona {idPersona: $personaId})-[:TIENE_INTERES_EN]->(h:Habilidad)<-[:ENSEÑA]-(c:Curso)
        RETURN c.nombre AS courseName, c.nivelDificultad AS level
        LIMIT 5
        """
        return self._execute_read(query, {"personaId": persona_id})

    def close_connection(self):
        self.driver.close()