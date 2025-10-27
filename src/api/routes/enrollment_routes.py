# enrollment_routes.py
from fastapi import APIRouter, Body, Request, HTTPException
from src.services.enrollment_service import EnrollmentService

from src.services.people_service import PeopleService

router = APIRouter(tags=["enrollments"])
svc = EnrollmentService()

@router.post("/courses/{course_id}/enroll/me")
def enroll(course_id: str, request: Request):
    # Requiere sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Resolver persona vinculada a la sesión
    people_svc = PeopleService()
    found = people_svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    pid = found[0].get("_id")

    return svc.enroll(pid, course_id)

@router.get("/people/me/enrollments")
def list_by_person(request: Request):
    # Requiere sesión para ver enrollments
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    people_svc = PeopleService()
    found = people_svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    pid = found[0].get("_id")

    return svc.list_by_person(pid)

@router.put("/enrollments/{enr_id}/progress")
def update_progress(enr_id: str, body: dict = Body(...)):
    return svc.update_progress(enr_id, body.get("progreso"), body.get("nota"))

@router.post("/enrollments/{enr_id}/complete")
def complete(enr_id: str, body: dict = Body({})):
    return svc.complete(enr_id, body.get("nota"), body.get("certificacionUrl"))
