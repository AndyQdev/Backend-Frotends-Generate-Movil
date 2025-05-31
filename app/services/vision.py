# services/vision.py
import os, json, base64, textwrap
from fastapi import HTTPException
from pydantic import TypeAdapter
from app.schemas.components import ComponentJSON
from openai import OpenAI
from dotenv import load_dotenv
import pprint
load_dotenv()

print("✅ KEY LEÍDA DE OPENIA:", repr(os.getenv("OPENIA_API_KEY")))
openai_key = os.getenv("OPENIA_API_KEY")
openai_client = OpenAI(api_key=openai_key)   # Este es el que usas para imágenes


PROMPT_VISION = """
Eres un generador de componentes de UI móvil a partir de un boceto en imagen.

1. **Lee** el texto visible y úsalo:
   • "label" en botones  • "placeholder" en inputs
   • Si no hay texto, deja "".

2. **Coordenadas**:
   • "x", "y", "width", "height" → porcentajes enteros (0-100) relativos a {h}px de alto × {w}px de ancho.

3. **Estilo visual**:
   • Todos los componentes deben tener el campo "style", aunque uses valores por defecto.
   • Los colores siempre devuelvelos en hexadecimal.
   • Usa este estilo por defecto si no puedes detectarlo:
     "style": {
         "backgroundColor": "#ffffff",
         "borderRadius": 8,
         "padding": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
         "textStyle": {
             "fontSize": 16,
             "fontWeight": "normal",
             "color": "#000000"
         }
     }

4. **Reglas de tamaño**:
   • Inputs y selects → height entre 5 y 8 %.
   • Botones → height entre 6 y 10 %.
   • Mantén un margin-top ≃ 2–4 % entre componentes sucesivos.

5. **Salida esperada**:
{
  "components": [ … ]
}
ℹ️ No devuelvas texto fuera del JSON. No comentes nada.
"""
# models = client.models.list()
# ids = [m.id for m in models.data]

# vision_ids = [mid for mid in ids if any(k in mid.lower() for k in ("vision","vl","image"))]
# pprint.pp(vision_ids[:30])
def components_from_image(img_bytes: bytes, content_type: str,
                          device_w: int, device_h: int) -> list[ComponentJSON]:

    b64 = base64.b64encode(img_bytes).decode()
    data_uri = f"data:{content_type};base64,{b64}"
    # prompt = PROMPT_VISION.format(w=device_w, h=device_h)

    resp = openai_client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": PROMPT_VISION},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Detecta los componentes de la interfaz y devuélvelos."},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ]
    )

    content = resp.choices[0].message.content
    data = json.loads(content)["components"]
    return TypeAdapter(list[ComponentJSON]).validate_python(data)