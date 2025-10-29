from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Dict, Any
from src.utils.redis_stats import (
    top_jobs_by_applications,
    top_people_by_applications,
    top_people_by_connections,
    top_profile_views,
    person_stats,
)

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/top/applications")
def get_top_jobs(top: int = Query(10, ge=1, le=100)):
    try:
        items = top_jobs_by_applications(top)
        return {"top": top, "jobs": [{"job_id": k, "applications": int(v)} for k, v in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/people/applications")
def get_top_people_apps(top: int = Query(10, ge=1, le=100)):
    try:
        items = top_people_by_applications(top)
        return {"top": top, "people": [{"person_id": k, "applications": int(v)} for k, v in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/people/connections")
def get_top_people_connections(top: int = Query(10, ge=1, le=100)):
    try:
        items = top_people_by_connections(top)
        return {"top": top, "people": [{"person_id": k, "connections": int(v)} for k, v in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/profile_views")
def get_top_profile_views(top: int = Query(10, ge=1, le=100)):
    try:
        items = top_profile_views(top)
        return {"top": top, "people": [{"person_id": k, "views": int(v)} for k, v in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/person/{person_id}")
def get_person_stats(person_id: str, request: Request):
    # require auth for per-person stats
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return person_stats(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
