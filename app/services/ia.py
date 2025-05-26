# NEW – usa tu esquema unificado
from app.schemas.components import ComponentJSON          # ⬅️
from uuid import uuid4
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError
from pydantic import TypeAdapter
load_dotenv()
client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

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
