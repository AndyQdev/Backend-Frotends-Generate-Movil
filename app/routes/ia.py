from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Page
from app.services.ia import generate_component            # <-- ya importa ComponentJSON dentro

router = APIRouter(prefix="/ia", tags=["ia"])

class IARequest(BaseModel):
    prompt: str
    page_id: int

@router.post("/component")
def crear_componente_con_ia(
    body: IARequest,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    page = db.query(Page).filter_by(id=body.page_id).first()
    if not page:
        raise HTTPException(404, "Página no encontrada")

    # 1. GPT-4 → JSON validado
    try:
        comp = generate_component(body.prompt)
    except ValueError as e:
        raise HTTPException(422, str(e))

    # 2. Asegúrate de que page.components sea lista
    if page.components is None:
        page.components = []
    comp_dict = comp.model_dump(mode="json")

    # 2️⃣ Reasignar generando nueva lista
    page.components = (page.components or []) + [comp_dict]

    db.commit()
    db.refresh(page)

    return {
        "component": comp_dict,
        "page": page  # ahora incluirá el nuevo componente
    }
