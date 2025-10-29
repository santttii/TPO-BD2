from fastapi import APIRouter, HTTPException
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

@router.post("/{job_id}/apply/{person_id}")
def apply_to_job(job_id: str, person_id: str):
    """
    Crea una postulación (Person -> Job)
    """
    try:
        return svc.apply(person_id, job_id)
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

