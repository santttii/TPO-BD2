# enrollment_routes.py
from fastapi import APIRouter, Body
from src.services.enrollment_service import EnrollmentService

router = APIRouter(tags=["enrollments"])
svc = EnrollmentService()

@router.post("/courses/{course_id}/enroll/{person_id}")
def enroll(course_id: str, person_id: str):
    return svc.enroll(person_id, course_id)

@router.get("/people/{person_id}/enrollments")
def list_by_person(person_id: str):
    return svc.list_by_person(person_id)

@router.put("/enrollments/{enr_id}/progress")
def update_progress(enr_id: str, body: dict = Body(...)):
    return svc.update_progress(enr_id, body.get("progreso"), body.get("nota"))

@router.post("/enrollments/{enr_id}/complete")
def complete(enr_id: str, body: dict = Body({})):
    return svc.complete(enr_id, body.get("nota"), body.get("certificacionUrl"))
