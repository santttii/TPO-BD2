from typing import List, Tuple, Optional
from src.config.database import get_redis_client


def _zrevrange_with_scores(name: str, top: int) -> List[Tuple[str, float]]:
    r = get_redis_client()
    items = r.zrevrange(name, 0, top - 1, withscores=True)
    # return list of (member, score)
    return [(m, float(s)) for m, s in items]


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


def top_jobs_by_applications(top: int = 10) -> List[Tuple[str, float]]:
    return _zrevrange_with_scores("applications_by_job", top)


def top_people_by_applications(top: int = 10) -> List[Tuple[str, float]]:
    return _zrevrange_with_scores("applications_by_person", top)


def top_people_by_connections(top: int = 10) -> List[Tuple[str, float]]:
    return _zrevrange_with_scores("connections_count", top)


def top_profile_views(top: int = 10) -> List[Tuple[str, float]]:
    return _zrevrange_with_scores("profile_views", top)


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
