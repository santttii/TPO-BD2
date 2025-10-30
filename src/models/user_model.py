from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserIn(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: str
    username: str
    created_at: Optional[datetime]


class UserDB(BaseModel):
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disabled: bool = False
