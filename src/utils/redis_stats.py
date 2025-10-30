from typing import Optional
from src.config.database import get_redis_client


def record_application(person_id: str, job_id: str):
    r = get_redis_client()
    # increment job ranking
    r.zincrby("applications_by_job", 1, job_id)
    # increment person ranking for applications
    r.zincrby("applications_by_person", 1, person_id)


def record_connection(person_a: str, person_b: str):
    r = get_redis_client()
    # increment connection counts for both
    r.zincrby("connections_count", 1, person_a)
    r.zincrby("connections_count", 1, person_b)


def record_profile_view(person_id: str):
    r = get_redis_client()
    r.zincrby("profile_views", 1, person_id)


def record_job_view(job_id: str):
    r = get_redis_client()
    r.zincrby("job_views", 1, job_id)


def person_stats(person_id: str) -> dict:
    r = get_redis_client()
    apps = r.zscore("applications_by_person", person_id) or 0
    conns = r.zscore("connections_count", person_id) or 0
    views = r.zscore("profile_views", person_id) or 0
    return {
        "person_id": person_id,
        "applications": int(float(apps)),
        "connections": int(float(conns)),
        "profile_views": int(float(views)),
    }


def job_stats(job_id: str) -> dict:
    r = get_redis_client()
    applications = r.zscore("applications_by_job", job_id) or 0
    views = r.zscore("job_views", job_id) or 0
    return {
        "applications": int(float(applications)),
        "views": int(float(views))
    }