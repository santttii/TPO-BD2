from pydantic import BaseModel
from typing import Optional


class UserIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
