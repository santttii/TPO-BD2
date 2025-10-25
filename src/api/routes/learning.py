# src/api/routes/learning.py
from fastapi import APIRouter
from src.services.learning_service import LearningService 

router = APIRouter(
    prefix="/learning",
    tags=["Training & Certifications"]
)

learning_service = LearningService()

@router.get("/catalog")
async def get_course_catalog():
    """
    RF 4: Retorna el catálogo de cursos.
    Fuente: MongoDB (colección cursos)[cite: 205].
    """
    catalog = learning_service.get_course_catalog()
    return {"status": "success", "data": catalog}