# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class LoginRequest(BaseModel):
    email: str
    password: str

class UserDetailData(BaseModel):
    id: int
    email: str
    name: Optional[str]
    telefono: Optional[str]
    rol: str
    total_colaboradores: int
    proyectos: List[dict]
    admin: Optional[dict] = None

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    data: UserDetailData

    class Config:
        from_attributes = True
