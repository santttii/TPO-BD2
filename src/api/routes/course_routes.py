# course_routes.py
from fastapi import APIRouter, Body, Query
from src.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])
svc = CourseService()

@router.post("")
def create_course(body: dict = Body(...)):
    return svc.create(body)

@router.get("")
def list_courses(
    q: str | None = Query(None), skill: str | None = Query(None),
    dificultad: str | None = Query(None), limit: int = 20, offset: int = 0):
    return svc.list({"q": q, "skill": skill, "dificultad": dificultad, "limit": limit, "offset": offset})

@router.get("/{course_id}")
def get_course(course_id: str):
    return svc.get(course_id)

@router.put("/{course_id}")
def update_course(course_id: str, body: dict = Body(...)):
    return svc.update(course_id, body)

@router.delete("/{course_id}")
def delete_course(course_id: str):
    return {"deleted": svc.delete(course_id)}
