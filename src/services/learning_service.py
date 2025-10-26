# src/services/learning_service.py

# Suponemos la existencia de un LearningRepository para cursos/inscripciones

class LearningService:
    def __init__(self):
        # self.learning_repo = LearningRepository()
        pass

    def get_course_catalog(self):
        """
        RF 4: Retorna el catálogo de cursos disponibles.
        Fuente: MongoDB (colección cursos).
        """
        # Lógica: return self.learning_repo.get_all_courses()
        return [{"id": "c_101", "name": "Introducción a NoSQL", "source": "MongoDB Catalog"}]

    def enroll_user(self, user_id: str, course_id: str):
        """
        RF 4: Registra la inscripción de un usuario a un curso.
        Fuente: MongoDB (colección inscripciones).
        """
        # Lógica: Se asegura la unicidad (PersonaId, CursoId) e inserta.
        return {"user_id": user_id, "course_id": course_id, "status": "Inscripción creada"}
        
    def get_user_progress(self, user_id: str):
        """
        RF 4: Consulta el progreso de cursos de un usuario.
        Fuente: MongoDB (colección inscripciones).
        """
        # Lógica: return self.learning_repo.get_user_enrollments(user_id)
        return [{"course": "c_101", "progress": 0.85, "status": "activo"}]