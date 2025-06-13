# NEW – usa tu esquema unificado
from app.schemas.components import ActionJSON, ComponentJSON          # ⬅️
from uuid import uuid4
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError
import random
from pydantic import TypeAdapter
load_dotenv()

print("✅ KEY LEÍDA DE OPENROUTER:", repr(os.getenv("OPENROUTER_API_KEY")))
client = OpenAI(
    api_key= os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

SYSTEM_PROMPT = """
Eres un generador de componentes JSON para un UI Builder.
Devuelve **solo** un objeto JSON y nada más.

⚠️ IMPORTANTE:
- Los campos "x", "y", "width" y "height" son porcentajes (no píxeles).
- Sus valores deben estar entre 0 y 100.
- NO deben exceder 100 bajo ninguna circunstancia.

Ejemplo 1 (button):
{
 "type":"button","label":"Aceptar","x":10,"y":70,"width":80,"height":8,
 "style":{"backgroundColor":"#2563eb","borderRadius":8,
          "textStyle":{"fontSize":20,"fontWeight":"bold","color":"#ffffff"}}
}

Ejemplo 2 (input):
{
 "type":"input","placeholder":"Email","inputType":"email",
 "x":10,"y":50,"width":80,"height":6
}

Ejemplo 3 (select):
{
 "type":"select","options":["Perú","Bolivia","Chile"],
 "x":10,"y":60,"width":80,"height":6
}

Ejemplo 4 (checklist):
{
 "type":"checklist","label":"Selecciona tus gustos",
 "options":["Café","Té","Jugo"],
 "x":10,"y":40,"width":80,"height":15
}

Ejemplo 5 (radiobutton):
{
 "type":"radiobutton","label":"Género",
 "options":["Masculino","Femenino"], "selectedOption":"Masculino",
 "x":10,"y":60,"width":80,"height":10
}

Ejemplo 6 (card):
{
 "type":"card","title":"Resumen","content":"Este es el contenido",
 "x":5,"y":20,"width":90,"height":20,
 "style":{"backgroundColor":"#f8fafc","borderRadius":12}
}

Ejemplo 7 (label):
{
 "type":"label","text":"Este es un texto estático",
 "x":10,"y":30,"width":80,"height":4,
 "style":{"textStyle":{"fontSize":16,"color":"#111827"}}
}

Ejemplo 8 (calendar):
{
  "type": "calendar",
  "selectedDate": "2025-06-01",
  "x": 10,
  "y": 30,
  "width": 80,
  "height": 12,
  "style": {
    "backgroundColor": "#ffffff",
    "borderRadius": 8
  }
}

Ejemplo 9 (search):
{
  "type": "search",
  "placeholder": "Buscar producto...",
  "value": "",
  "x": 10,
  "y": 20,
  "width": 80,
  "height": 6,
  "style": {
    "backgroundColor": "#f1f5f9",
    "borderRadius": 6,
    "textStyle": {
      "fontSize": 14,
      "color": "#111827"
    }
  }
}

Ejemplo 10 (textArea):
{
  "type": "textArea",
  "placeholder": "Escribe tu mensaje",
  "value": "",
  "x": 10,
  "y": 40,
  "width": 80,
  "height": 14,
  "style": {
    "backgroundColor": "#ffffff",
    "borderRadius": 8,
    "textStyle": {
      "fontSize": 16,
      "color": "#111827"
    }
  }
}

Ejemplo 11 (imagen):
{
  "type": "imagen",
  "src": "https://example.com/logo.png",
  "x": 10,
  "y": 10,
  "width": 60,
  "height": 20,
  "style": {
    "borderRadius": 6
  }
}
Ejemplo 12 (datatable):
{
  "type": "datatable",
  "x": 5,
  "y": 30,
  "width": 90,
  "height": 20,
  "headers": ["ID", "Nombre", "Descripción"],
  "rows": [
    ["1", "Ejemplo A", "Fila de prueba"],
    ["2", "Ejemplo B", "Otra fila"],
    ["3", "Ejemplo C", "Más datos"]
  ],
  "backgroundColor": "#f8fafc"
}

Ejemplo 13 (icon):
{
  "type": "icon",
  "icon": "Airplay",
  "color": "#2563eb",
  "size": 60,
  "x": 10,
  "y": 10,
  "width": 10,
  "height": 10
}
Ejemplo 14 (login): Componente compuesto que contiene una card, un título, dos inputs (email + contraseña) y un botón.
{
  "type": "login",
  "x": 10,
  "y": 20,
  "width": 80,
  "height": 40,
  "card": {
    "type": "card",
    "title": "",
    "content": "",
    "x": 0,
    "y": 0,
    "width": 100,
    "height": 100,
    "style": {
      "backgroundColor": "#ffffff",
      "borderRadius": 12
    }
  },
  "label": {
    "type": "label",
    "text": "Inicia sesión",
    "x": 0,
    "y": 0,
    "width": 100,
    "height": 10,
    "style": {
      "textStyle": {
        "fontSize": 20,
        "fontWeight": "bold",
        "color": "#111827"
      }
    }
  },
  "inputs": [
    {
      "type": "input",
      "placeholder": "Email",
      "inputType": "email",
      "x": 0,
      "y": 0,
      "width": 100,
      "height": 10
    },
    {
      "type": "input",
      "placeholder": "Contraseña",
      "inputType": "password",
      "x": 0,
      "y": 0,
      "width": 100,
      "height": 10
    }
  ],
  "button": {
    "type": "button",
    "label": "Ingresar",
    "x": 0,
    "y": 0,
    "width": 100,
    "height": 10,
    "style": {
      "backgroundColor": "#2563eb",
      "borderRadius": 8,
      "textStyle": {
        "fontSize": 16,
        "fontWeight": "bold",
        "color": "#ffffff"
      }
    }
  }
}

Ejemplo 15 (formulario): Componente compuesto que contiene un título (label), una lista de campos (inputs, selects, etc.) y un botón.
{
  "type": "formulario",
  "x": 5,
  "y": 15,
  "width": 90,
  "height": 60,
  "title": {
    "type": "label",
    "text": "Formulario de contacto",
    "x": 0,
    "y": 0,
    "width": 100,
    "height": 10,
    "style": {
      "textStyle": {
        "fontSize": 18,
        "fontWeight": "bold",
        "color": "#111827"
      }
    }
  },
  "fields": [
    {
      "type": "input",
      "placeholder": "Nombre completo",
      "inputType": "text",
      "x": 0,
      "y": 10,
      "width": 100,
      "height": 10
    },
    {
      "type": "input",
      "placeholder": "Correo electrónico",
      "inputType": "email",
      "x": 0,
      "y": 20,
      "width": 100,
      "height": 10
    },
    {
      "type": "select",
      "label": "Motivo",
      "options": ["Soporte", "Consulta", "Reclamo"],
      "x": 0,
      "y": 30,
      "width": 100,
      "height": 10
    }
  ],
  "button": {
    "type": "button",
    "label": "Enviar",
    "x": 0,
    "y": 40,
    "width": 100,
    "height": 10,
    "style": {
      "backgroundColor": "#2563eb",
      "borderRadius": 8,
      "textStyle": {
        "fontSize": 16,
        "fontWeight": "bold",
        "color": "#ffffff"
      }
    }
  }
}

⚠️ Sobre íconos:
- El campo `"icon"` debe estar en formato **PascalCase**
- El nombre debe coincidir con un ícono válido de la librería **lucide_icons: ^0.257.0** de Flutter
- No uses nombres inventados ni en camelCase

Si el usuario quiere MODIFICAR un componente existente:
- Devuelve un objeto JSON con "action":"update",
  "target": { "by":"color", "value":"#ffff00" },  // ejemplo
  "changes": { "style": { "backgroundColor":"#ff0000" } }

Si el usuario quiere AGREGAR algo nuevo:
- Devuelve un objeto con "action":"create" y "components": [ ...lista de componentes... ]

REGLAS:
- SIEMPRE usa "components": [ ... ] incluso si hay UN solo componente.
- NO uses "component" en singular.
- El objeto target DEBE tener SIEMPRE las claves "by" y "value".
- Ejemplo correcto para buscar por id:
  "target": { "by":"id", "value":"633956234655844404" }

PADDING:
- Siempre que un componente tenga campo `"style"`, incluye también `"padding"`, especialmente para:
  - button, input, textArea, select, search, calendar, card
- El padding debe seguir esta estructura:

  "padding": {
    "top": <entero 4 a 12>,
    "right": <entero 6 a 16>,
    "bottom": <entero 4 a 12>,
    "left": <entero 6 a 16>
  }

- No exageres: los valores deben mantenerse **moderados** para que el diseño se vea natural y legible en dispositivos móviles.
- No repitas el mismo valor exacto en los 4 lados; usa pequeñas variaciones como top/bottom ligeramente menor que left/right.

Ejemplo de padding recomendado:
```json
"padding": {
  "top": 6,
  "right": 12,
  "bottom": 6,
  "left": 10
}

NO devuelvas nada más que el JSON. No agregues explicaciones ni comentarios.

Ejemplo final (varios):
{
 "action":"create",
 "components":[
   {
     "type":"button",
     "label":"Enviar",
     "x":10,"y":80,"width":80,"height":8,
     "style":{"backgroundColor":"#2563eb","borderRadius":8,
              "textStyle":{"fontSize":20,"fontWeight":"bold","color":"#ffffff"}}
   },
   {
     "type":"input",
     "placeholder":"Email",
     "inputType":"email",
     "x":10,"y":60,"width":80,"height":6
   }
 ]
}
"""

DEFAULT_IMAGES = [
    "https://wallpapers.com/images/high/cool-neon-green-profile-picture-uvhf8r1q7ekwuzwu.webp",
    "https://wallpapers.com/images/featured-full/imagenes-de-perfil-geniales-4co57dtwk64fb7lv.jpg",
    "https://wallpapers.com/images/high/cool-profile-picture-purple-astronaut-mm73otj7x18b5r7m.webp"
]

def ensure_defaults(component: dict) -> dict:
    if component.get("type") == "imagen":
        src = component.get("src", "")
        if not src or "example.com" in src:
            component["src"] = random.choice(DEFAULT_IMAGES)
    return component

def default_style():
    return {
        "backgroundColor": "#ffffff",
        "borderRadius": 0,
        "padding": {"top": 0, "right": 0, "bottom": 0, "left": 10},
        "textStyle": {"fontSize": 14, "fontWeight": "normal", "color": "#000000"}
    }

def ensure_style(component: dict) -> dict:
    if component.get("style") is None:
        component["style"] = default_style()
    else:
        component["style"] = {
            "backgroundColor": component["style"].get("backgroundColor", "#ffffff"),
            "borderRadius": component["style"].get("borderRadius", 0),
            "padding": {
                "top": component["style"].get("padding", {}).get("top", 0),
                "right": component["style"].get("padding", {}).get("right", 0),
                "bottom": component["style"].get("padding", {}).get("bottom", 0),
                "left": component["style"].get("padding", {}).get("left", 10),
            },
            "textStyle": {
                "fontSize": component["style"].get("textStyle", {}).get("fontSize", 14),
                "fontWeight": component["style"].get("textStyle", {}).get("fontWeight", "normal"),
                "color": component["style"].get("textStyle", {}).get("color", "#000000")
            }
        }
    return component
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
    data = ensure_defaults(data) 
    data = ensure_style(data)
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
    if data.get("action") == "create" and "components" in data:
        for i, comp in enumerate(data["components"]):
            comp = ensure_defaults(comp)
            data["components"][i] = ensure_style(comp)
    adapter = TypeAdapter(ActionJSON)
    return adapter.validate_python(data)