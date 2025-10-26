# src/api/routes/hiring.py
from fastapi import APIRouter
from src.services.hiring_service import HiringService 

router = APIRouter(
    prefix="/hiring",
    tags=["Jobs & Selection Process"]
)

hiring_service = HiringService()

@router.get("/jobs/{job_id}")
async def get_job_listing(job_id: str):
    """
    RF 2: Obtiene el detalle de una posición laboral publicada.
    Fuente: MongoDB (colección empleos)[cite: 131].
    """
    job = hiring_service.get_job_listing(job_id)
    return {"status": "success", "data": job}

@router.post("/jobs/{job_id}/match")
async def trigger_matching(job_id: str):
    """
    RF 2: Dispara el matching inteligente para una posición laboral.
    Fuente: Neo4j (cálculo de afinidad) y Redis (almacenamiento de ranking top-K)[cite: 299, 360].
    """
    result = hiring_service.run_matching(job_id)
    return {"status": "accepted", "message": f"Matching initiated for job {job_id}", "details": result}

@router.patch("/applications/{app_id}/status")
async def update_application_status(app_id: str, new_status: str):
    """
    RF 3: Actualiza el estado de un proceso de selección.
    Fuente: MongoDB (colección postulaciones)[cite: 153].
    """
    # Requiere Transacción ACID y auditoría para integridad [cite: 56]
    result = hiring_service.update_application_status(app_id, new_status)
    return {"status": "success", "message": f"Application {app_id} status updated to {new_status}"}