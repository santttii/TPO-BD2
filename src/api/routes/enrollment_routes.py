# enrollment_routes.py
from fastapi import APIRouter, Body, Request, HTTPException
from src.services.enrollment_service import EnrollmentService

from src.services.people_service import PeopleService

router = APIRouter(tags=["enrollments"])
svc = EnrollmentService()  # <- asegúrate de tener una única instancia

@router.post("/courses/{course_id}/enroll/me")
def enroll_me(course_id: str, request: Request):
    # 1) Requiere sesión
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # 2) Resolver persona vinculada al user_id de la sesión
    people_svc = PeopleService()
    persons = people_svc.list({"userId": user_id})
    if not persons:
        raise HTTPException(status_code=404, detail="Persona no encontrada para este usuario")

    p0 = persons[0]
    # soporta 'id' ya string o '_id' como ObjectId
    person_id = p0.get("id") or p0.get("_id")
    if person_id is None:
        raise HTTPException(status_code=500, detail="Persona sin id válido")
    person_id = str(person_id)

    # 3) Inscribir (EnrollmentService valida que exista el curso/persona)
    try:
        out = svc.enroll(person_id, course_id)
        return out
    except ValueError as ve:
        # ValueErrors del servicio -> 400/404 semánticos
        msg = str(ve)
        if "no existe" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        # Log detallado del error
        print(f"Error en enrollment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inscribiendo al curso: {str(e)}")

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
