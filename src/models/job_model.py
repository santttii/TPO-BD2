from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson import ObjectId


class JobIn(BaseModel):
    titulo: str
    descripcion: str
    ubicacion: str
    salario: float
    empresaId: str


class JobOut(JobIn):
    id: Optional[str] = Field(default=None, alias="_id")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
