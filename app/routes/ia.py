from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Page
from app.services.ia import generate_component            # <-- ya importa ComponentJSON dentro
from app.services.ia import generate_action
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter(prefix="/ia", tags=["ia"])

class IARequest(BaseModel):
    prompt: str
    page_id: int

# @router.post("/component")
# def crear_componente_con_ia(
#     body: IARequest,
#     db: Session = Depends(get_db),
#     _user = Depends(get_current_user)
# ):
#     page = db.query(Page).filter_by(id=body.page_id).first()
#     if not page:
#         raise HTTPException(404, "Página no encontrada")

#     # 1. GPT-4 → JSON validado
#     try:
#         comp = generate_component(body.prompt)
#     except ValueError as e:
#         raise HTTPException(422, str(e))

#     # 2. Asegúrate de que page.components sea lista
#     if page.components is None:
#         page.components = []
#     comp_dict = comp.model_dump(mode="json")

#     # 2️⃣ Reasignar generando nueva lista
#     page.components = (page.components or []) + [comp_dict]

#     db.commit()
#     db.refresh(page)

#     return {
#         "component": comp_dict,
#         "page": page  # ahora incluirá el nuevo componente
#     }

@router.post("/component")
def ia_component(body: IARequest, db: Session = Depends(get_db), _u = Depends(get_current_user)):
    page = db.query(Page).filter_by(id=body.page_id).first()
    if not page:
        raise HTTPException(404, "Página no encontrada")

    comps = page.components or []

    action = generate_action(body.prompt, comps)

    if action.action == 'create':
        # unificar: convertir a lista siempre
        comps_nuevos = (
            [action.component]                # <- si vino CreateSingle
            if hasattr(action, "component")
            else action.components            # <- CreateAction
        )

        new_dicts = [c.model_dump(mode="json") for c in comps_nuevos]
        page.components = (comps or []) + new_dicts

        flag_modified(page, "components")
        db.commit(); db.refresh(page)

        return {
            "action": "create",
            "components": new_dicts,          # lista
            "page": page
        }

    elif action.action == 'update':
        # encontrar componente
        target = None
        if action.target.by == 'id':
            target = next((c for c in comps if c['id'] == action.target.value), None)
        elif action.target.by == 'label':
            target = next((c for c in comps if c.get('label') == action.target.value), None)
        elif action.target.by == 'color':
            target = next(
              (c for c in comps if c.get('style',{}).get('backgroundColor') == action.target.value),
              None
            )
        if not target:
            raise HTTPException(404, "Componente objetivo no encontrado")

        # aplicar cambios recursivamente
        def deep_update(d, u):
            for k,v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k,{}), v)
                else:
                    d[k] = v
            return d
        deep_update(target, action.changes)

        page.components = [*comps]
        flag_modified(page, "components") 
        db.commit()
        db.refresh(page)
        return {
            "action": "update",
            "components": target,
            "page": page
        }
