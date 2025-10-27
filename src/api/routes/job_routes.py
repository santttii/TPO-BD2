from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from src.models.job_model import JobIn, JobOut
from src.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])
svc = JobService()

# =============================
# CRUD
# =============================

@router.post("/", response_model=JobOut)
def create_job(job: JobIn):
    try:
        return svc.create(job.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[JobOut])
def list_jobs():
    try:
        return svc.list({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str):
    job = svc.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job

@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: str, updates: Dict[str, Any]):
    updated = svc.update(job_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return updated

@router.delete("/{job_id}")
def delete_job(job_id: str):
    try:
        svc.delete(job_id)
        return {"message": "Job eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/apply/me")
def apply_to_job(job_id: str, request: Request):
    """
    Crea una postulación (Person -> Job). Requiere sesión válida y que el
    person_id en la URL coincida con la sesión.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Buscar la persona vinculada al user en sesión y usar su Mongo _id
    from src.services.people_service import PeopleService
    people_svc = PeopleService()
    found = people_svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    # Para sincronizar con Neo4j usamos el id que se usó como id del nodo.
    # Las personas creadas en el registro tienen `userId` como id del nodo en Neo4j;
    # si no existe, usamos el _id de Mongo.
    person_doc = found[0]
    target_person_id = person_doc.get("userId") or person_doc.get("_id")

    try:
        return svc.apply(target_person_id, job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/applicants")
def get_applicants(job_id: str):
    """
    Lista todas las personas que se postularon a un Job.
    """
    try:
        return svc.get_applicants(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

