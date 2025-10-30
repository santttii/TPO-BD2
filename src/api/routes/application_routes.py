from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from src.services.application_service import ApplicationService
from src.services.people_service import PeopleService

router = APIRouter(prefix="/applications", tags=["Applications"])
svc = ApplicationService()

# ===============================================================
# 📋 GET
# ===============================================================
@router.get("/person/{person_id}")
def get_applications_by_person(person_id: str, request: Request):
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        if person_id == "me":
            people_svc = PeopleService()
            found = people_svc.list({"userId": request.state.user_id})
            if not found:
                raise HTTPException(status_code=404, detail="Persona no encontrada")
            person_doc = found[0]
            node_id = person_doc.get("userId") or person_doc.get("_id")
            person_id = node_id

        return svc.get_by_person(person_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
def get_applications_by_job(job_id: str, request: Request):
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return svc.get_by_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================================
# 🔁 ESTADO
# ===============================================================
@router.put("/{application_id}/estado")
def update_estado(application_id: str, body: Dict[str, Any], request: Request):
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        if not body.get("estado"):
            raise HTTPException(status_code=400, detail="Campo 'estado' requerido")
        return svc.update_estado(application_id, body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================================
# 💬 FEEDBACK
# ===============================================================
@router.post("/{application_id}/feedback")
def agregar_feedback(application_id: str, feedback: Dict[str, Any], request: Request):
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return svc.agregar_feedback(application_id, feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================================
# 💼 OFERTA
# ===============================================================
@router.post("/{application_id}/oferta")
def enviar_oferta(application_id: str, datos_oferta: Dict[str, Any], request: Request):
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return svc.enviar_oferta(application_id, datos_oferta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
