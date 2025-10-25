from pydantic import BaseModel
from typing import Literal

class ConnectionIn(BaseModel):
    """Relación entre dos personas"""
    type: Literal["friendship", "mentorship", "coworker", "collaboration"] = "friendship"
    since: str = "2025-01-01"  # ISO-8601 o fecha simple
