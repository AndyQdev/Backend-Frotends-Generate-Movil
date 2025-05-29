# app/schemas/components.py
from typing import Literal, Annotated, Union, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, TypeAdapter

# ───────── utilidades comunes ──────────
class Padding(BaseModel):
    top:    Optional[int] = 0
    right:  Optional[int] = 0
    bottom: Optional[int] = 0
    left:   Optional[int] = 0

class TextStyle(BaseModel):
    fontSize:   Optional[int] = 16
    fontWeight: Optional[Literal['normal', 'bold', 'medium', 'light']] = 'normal'
    color:      Optional[str] = "#000000"

class ComponentStyle(BaseModel):
    backgroundColor: Optional[str] = "#ffffff"
    borderRadius:    Optional[int] = 0
    padding:         Optional[Padding] = Padding()
    textStyle:       Optional[TextStyle] | None = None
    # TODO: margin, boxShadow, etc.

# ────────── base genérico ───────────
class ComponentBase(BaseModel):
    id:    str = Field(default_factory=lambda: str(uuid4().int >> 64))
    x:     int
    y:     int
    width: int
    height: int
    style: Optional[ComponentStyle] = None
    route: Optional[str] = ""

# ───────── tipos concretos (discriminados por "type") ─────────
class ButtonComponent(ComponentBase):
    type: Literal['button']
    label: str

class InputComponent(ComponentBase):
    type: Literal['input']
    placeholder: str
    inputType: Literal['text', 'email', 'password'] = 'text'

class SelectComponent(ComponentBase):
    type: Literal['select']
    options: list[str]

# ───────── unión discriminada ─────────
# ➊ Con Pydantic v2 usamos el discriminador
ComponentJSON = Annotated[
    Union[ButtonComponent, InputComponent, SelectComponent],
    Field(discriminator='type')
]

class Target(BaseModel):
    by: Literal['id', 'label', 'color']
    value: str

class UpdatePatch(BaseModel):
    action: Literal['update']
    target: Target
    changes: dict

class CreateAction(BaseModel):
    action: Literal['create']
    component: ComponentJSON

ActionJSON = Annotated[
    Union[CreateAction, UpdatePatch],
    Field(discriminator='action')
]
