from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import Page
from app.services.ia import generate_component            # <-- ya importa ComponentJSON dentro
from app.services.ia import generate_action
from sqlalchemy.orm.attributes import flag_modified
from fastapi import UploadFile, File, Form
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv
from openai import OpenAI
import os
load_dotenv()
router = APIRouter(prefix="/ia", tags=["ia"])

class IARequest(BaseModel):
    prompt: str
    page_id: int

print("✅ KEY LEÍDA DE OPENIA:", repr(os.getenv("OPENIA_API_KEY")))
openai_key = os.getenv("OPENIA_API_KEY")
client = OpenAI(api_key=openai_key) 

@router.post("/from-audio")
async def transcribir_audio(
    file: UploadFile = File(...),
    page_id: int = Form(...),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    page = db.query(Page).filter_by(id=page_id).first()
    print("page_id:", page_id, "page:", page)
    if not page:
        raise HTTPException(404, "Página no encontrada")

    try:
        # Guardar audio temporalmente
        with NamedTemporaryFile(delete=False, suffix=".m4a") as temp_audio:
            temp_audio.write(await file.read())
            temp_audio_path = temp_audio.name

        # Transcribir con Whisper
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        prompt = transcript.strip()
        print("🎤 Transcripción:", prompt)

        return {"from": "audio", "prompt": prompt, "page_id": page_id}

    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

class HelpRequest(BaseModel):
    question: str
@router.post("/ia/help")
async def ask_help(req: HelpRequest, user=Depends(get_current_user)):
    messages = [
        {"role": "system", "content": "Eres un asistente experto del constructor visual de interfaces móviles del sistema. Ayudas al usuario a entender cómo usar las funciones del sistema como crear botones, subir imágenes, generar componentes por IA, etc."},
        {"role": "user", "content": req.question}
    ]
    response = client.ChatCompletion.create(
        model="gpt-4",  # o gpt-4-turbo
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    return {"answer": response.choices[0].message["content"]}

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

