# services/vision.py
import os, json, base64, textwrap
from fastapi import HTTPException
from pydantic import TypeAdapter
from app.schemas.components import ComponentJSON
from openai import OpenAI
from dotenv import load_dotenv
from app.services.ia import ensure_style  #
load_dotenv()

print("✅ KEY LEÍDA DE OPENIA:", repr(os.getenv("OPENIA_API_KEY")))
openai_key = os.getenv("OPENIA_API_KEY")
openai_client = OpenAI(api_key=openai_key)   # Este es el que usas para imágenes

PROMPT_VISION = """
Eres un generador de componentes de UI móvil a partir de un boceto en imagen.

Tu salida debe ser SOLO un JSON con este formato:
{
  "components": [ … ]
}

ℹ️  **No devuelvas texto fuera del JSON ni comentarios**.

────────────────────────  REGLAS GENERALES  ────────────────────────
1. **Texto visible**
   · button      → "label"  
   · input       → "placeholder"  
   · textArea    → "placeholder"  
   · label       → "text"  
   · search      → "placeholder"  
   Si no hay texto, deja el campo vacío ("").

2. **Tipos permitidos (campo "type")**
   • button         – botón rectangular.  
   • input          – caja de texto (una sola línea).  
   • textArea       – área de texto multilínea.  
   • select         – caja con flecha desplegable.  
   • checklist      – lista con casillas cuadradas.  
   • radiobutton    – lista con círculos.  
   • calendar       – campo de fecha (input date).  
   • search         – campo de búsqueda con icono de lupa.  
   • imagen         – imagen decorativa/ilustrativa.  
   • label          – texto estático.  
   • card           – contenedor con fondo y borde redondeado.

3. **Coordenadas**
   x, y, width, height → porcentajes enteros (0-100) respecto a {h}px alto × {w}px ancho
   Nunca superes 100.

4. **Campo obligatorio "style"**  
   Usa este valor cuando no puedas detectar estilos:
   "style": {
     "backgroundColor": "#ffffff",
     "borderRadius": 8,
     "padding": { "top": 0, "right": 0, "bottom": 0, "left": 10 },
     "textStyle": {
       "fontSize": 16,
       "fontWeight": "normal",
       "color": "#000000"
     }
   }

5. **Reglas de altura recomendada**
   • button, input, search, select, calendar → 6 – 10  
   • checklist / radiobutton                → 10 – 16  
   • textArea                               → 12 – 20  
   • card                                   → 20 – 40  
   Mantén un salto vertical (∆y) de +2 % a +4 % entre componentes sucesivos.

6. **Campos específicos adicionales**
   · select / checklist / radiobutton → "options" (mínimo 2)  
   · radiobutton                      → "selectedOption" (opcional)  
   · calendar                         → "selectedDate" en formato "YYYY-MM-DD" (opcional)  
   · imagen                           → "src" (URL).  
       Si la imagen no puede detectarse, usa una aleatoria de:  
       ["https://wallpapers.com/images/high/cool-neon-green-profile-picture-uvhf8r1q7ekwuzwu.webp",
        "https://wallpapers.com/images/featured-full/imagenes-de-perfil-geniales-4co57dtwk64fb7lv.jpg",
        "https://wallpapers.com/images/high/cool-profile-picture-purple-astronaut-mm73otj7x18b5r7m.webp"]

7. **Ejemplo de salida válido**
{
  "components": [
    {
      "type": "label",
      "text": "Formulario de registro",
      "x": 10, "y": 5, "width": 80, "height": 4,
      "style": { … }
    },
    {
      "type": "input",
      "placeholder": "Nombre",
      "x": 10, "y": 12, "width": 80, "height": 6,
      "style": { … }
    },
    {
      "type": "calendar",
      "selectedDate": "2025-06-01",
      "x": 10, "y": 20, "width": 80, "height": 8,
      "style": { … }
    },
    {
      "type": "search",
      "placeholder": "Buscar…",
      "x": 10, "y": 30, "width": 80, "height": 6,
      "style": { … }
    },
    {
      "type": "imagen",
      "src": "https://wallpapers.com/.../logo.webp",
      "x": 10, "y": 38, "width": 60, "height": 20,
      "style": { "borderRadius": 6 }
    },
    {
      "type": "button",
      "label": "Enviar",
      "x": 10, "y": 60, "width": 80, "height": 8,
      "style": { … }
    }
  ]
}
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
    for i, c in enumerate(data):
        data[i] = ensure_style(c)
    return TypeAdapter(list[ComponentJSON]).validate_python(data)