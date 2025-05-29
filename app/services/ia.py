# NEW – usa tu esquema unificado
from app.schemas.components import ActionJSON, ComponentJSON          # ⬅️
from uuid import uuid4
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError
from pydantic import TypeAdapter
load_dotenv()

print("✅ KEY LEÍDA:", repr(os.getenv("OPENROUTER_API_KEY")))
client = OpenAI(
    api_key="",
    base_url="https://openrouter.ai/api/v1"
)
# client = OpenAI(
#     api_key=os.getenv("OPENROUTER_API_KEY"),
#     base_url="https://openrouter.ai/api/v1",
#     default_headers={
#         "HTTP-Referer": "http://localhost:5173",
#         "X-Title": "UI-Sketch Dev"
#     }
# )
# ───────── SYSTEM PROMPT con pocos-ejemplos ─────────
SYSTEM_PROMPT = """
Eres un generador de componentes JSON para un UI Builder.
Devuelve **solo** un objeto JSON y nada más.

Ejemplo 1 (button):
{
 "type":"button","label":"Aceptar","x":40,"y":500,"width":300,"height":60,
 "style":{"backgroundColor":"#2563eb","borderRadius":8,
          "textStyle":{"fontSize":20,"fontWeight":"bold","color":"#ffffff"}}
}

Ejemplo 2 (input):
{
 "type":"input","placeholder":"Email","inputType":"email",
 "x":40,"y":300,"width":340,"height":48
}

Ejemplo 3 (select):
{
 "type":"select","options":["Perú","Bolivia","Chile"],
 "x":40,"y":380,"width":340,"height":48
}

Si el usuario quiere MODIFICAR un componente existente:
- Devuelve un objeto JSON con "action":"update",
  "target": { "by":"color", "value":"#ffff00" },  // ejemplo
  "changes": { "style": { "backgroundColor":"#ff0000" } }

Si el usuario quiere AGREGAR algo nuevo:
- Devuelve { "action":"create", "component": { ...estructura completa... } }

IMPORTANTE:
- El objeto target DEBE tener SIEMPRE las claves "by" y "value".
- Ejemplo correcto para buscar por id:
  "target": { "by":"id", "value":"633956234655844404" }
NO devuelvas nada más que el JSON.
"""  # ← pocos-shhots ayudan a que respete la unión discriminada


def generate_component(prompt: str) -> ComponentJSON:
    """Llama a GPT-4 Turbo y valida con ComponentJSON (union)."""
    resp = client.chat.completions.create(
        model="openai/gpt-4-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt.strip()}
        ],
        temperature=0.2,
        max_tokens=500
    )
    raw = resp.choices[0].message.content.strip()

    # elimina ```json … ``` si aparece
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*|```$", "", raw, flags=re.I|re.S).strip()

    data = json.loads(raw)
    data.setdefault("id", str(uuid4().int >> 64))

    try:
        adapter = TypeAdapter(ComponentJSON)
        return adapter.validate_python(data)   # 🔥 validación unificada
    except ValidationError as e:
        raise ValueError(f"JSON inválido: {e}") from None

def generate_action(prompt: str, components: list[dict]) -> ActionJSON:
    resp = client.chat.completions.create(
        model="openai/gpt-4-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            # contexto: los componentes actuales
            {"role": "assistant", "content": json.dumps({"components": components})},
            {"role": "user", "content": prompt.strip()}
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[-1].strip()
    data = json.loads(raw)

    adapter = TypeAdapter(ActionJSON)
    return adapter.validate_python(data)