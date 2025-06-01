from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
from fastapi import UploadFile, File

class ComponentCreate(BaseModel):
    type: str
    x: int
    y: int
    width: int
    height: int
    z_index: Optional[int] = 1
    is_locked: Optional[bool] = False
    properties: Optional[dict] = {}
    styles: Optional[dict] = {}

class PageCreate(BaseModel):
    name: str
    order: int
    background_color: Optional[str] = "#ffffff"
    grid_enabled: Optional[bool] = False
    device_mode: Optional[Literal["desktop", "tablet", "mobile"]] = "desktop"
    components: Optional[List[dict]] = []  # Ya no es List[ComponentCreate]

class ProyectoCreate(BaseModel):
    name: str
    descripcion: Optional[str] = None  # si deseas incluir una descripción
    colaboradorId: Optional[List[int]] = []

class Component(BaseModel):
    id: int
    type: str
    x: int
    y: int
    width: int
    height: int
    z_index: int
    is_locked: bool
    properties: dict
    styles: dict

    class Config:
        from_attributes = True   

class Page(BaseModel):
    id: int
    name: str
    order: int
    background_color: str
    grid_enabled: bool
    device_mode: str
    components: List[dict] = []

    class Config:
        from_attributes = True

class Proyecto(BaseModel):
    id: int
    name: str
    descripcion: Optional[str] = None
    status: Optional[str] = "En proceso"
    create_date: datetime
    pages: List[Page] = []
    resolution_w: int | None = None
    resolution_h: int | None = None
    last_modified: datetime
    class Config:
        from_attributes = True

class ProyectoListResponse(BaseModel):
    data: List[Proyecto]
    countData: int

    class Config:
        from_attributes = True

class ProyectoResponse(BaseModel):
    data: Proyecto

    class Config:
        from_attributes = True

class PageUpdate(BaseModel):
    id: Optional[int]           # ⇢ si viene es UPDATE; si no, se creará
    name: Optional[str]
    order: Optional[int]
    background_color: Optional[str]
    grid_enabled: Optional[bool]
    device_mode: Optional[Literal["desktop", "tablet", "mobile"]]
    components: Optional[List[dict]]

class ProyectoUpdate(BaseModel):
    id: int
    name: Optional[str]
    descripcion: Optional[str]
    status: Optional[str]
    pages: List[PageUpdate]
    last_modified: datetime
    colaboradores: Optional[List[int]] = None  # Lista de IDs de usuarios colaboradores

class PageCreateIn(BaseModel):
    name: Optional[str]         = None
    order: Optional[int]        = None
    background_color: str       = "#ffffff"
    grid_enabled: bool          = False
    device_mode: Literal["desktop", "tablet", "mobile"] = "desktop"
    components: List[dict]      = []
    img: UploadFile | None = File(None)

class PageResponse(BaseModel):
    data: Page   # reutilizamos el Page que ya tienes

    class Config:
        from_attributes = True

class ColaboradorResponse(BaseModel):
    id: int
    email: str
    name: str
    permisos: str

    class Config:
        from_attributes = True

class ColaboradoresResponse(BaseModel):
    data: List[ColaboradorResponse]
    countData: int

    class Config:
        from_attributes = True

class ColaboradorUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    proyectos_ids: Optional[List[int]] = None  # Lista de IDs de proyectos

class ColaboradorUpdateResponse(BaseModel):
    data: ColaboradorResponse

    class Config:
        from_attributes = True