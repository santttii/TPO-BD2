# src/models/company_model.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson import ObjectId

class CompanyIn(BaseModel):
    nombre: str
    industria: str
    pais: str
    ciudad: str

class CompanyOut(CompanyIn):
    id: Optional[str] = Field(default=None, alias="_id")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )
