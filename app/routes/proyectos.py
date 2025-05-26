import json
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.routes.utils.flutter_generator import build_flutter_project
from app.schemas.proyecto import ProyectoCreate, Proyecto
from app.models.models import Proyecto as ProyectoModel, Usuario, Page
from app.database import SessionLocal
from app.auth.dependencies import get_current_user
from datetime import datetime
from typing import List, Optional
from app.schemas.proyecto import ProyectoListResponse, ProyectoResponse, PageCreateIn, PageResponse
from app.models.models import ColaboradorProyecto
from sqlalchemy import desc
from app.schemas.proyecto import (
    ProyectoCreate, Proyecto, ProyectoListResponse, ProyectoResponse,
    ProyectoUpdate, PageUpdate        #  <-- importa los nuevos
)
import copy
import cv2, numpy as np, pytesseract, unicodedata, difflib, uuid, json
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from xml.etree.ElementTree import fromstring
from faker import Faker
from fastapi import UploadFile, File, Form
from sqlalchemy import func
import unicodedata
import re
import os
import zipfile
import shutil
from jinja2 import Template
from fastapi.responses import FileResponse
from xml.etree.ElementTree import fromstring

router = APIRouter(prefix="/projects", tags=["Proyectos"])
ANGULAR_BASE = "angular_base"  # carpeta base con estructura angular vacía
TEMP_DIR = "/mnt/data/generated_projects"
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extraer_clases(xml: bytes) -> list[dict]:
    """
    Extrae clases UML de un XMI 2.x (StarUML, EA, etc.)
    Devuelve: [{'nombre': 'User', 'atributos': ['id', 'nombre', ...]}, …]
    """
    root = fromstring(xml)

    ns = {
        "xmi": "http://schema.omg.org/spec/XMI/2.1",
        "uml": "http://schema.omg.org/spec/UML/2.0",
    }

    clases = []
    # 1)  Clases declaradas como <uml:Class …>
    for elem in root.findall(".//uml:Class", ns):
        nombre = elem.get("name", "Clase")
        atributos = [
            att.get("name")
            for att in elem.findall("./ownedAttribute", ns)
            if att.get("name")
        ]
        clases.append({"nombre": nombre, "atributos": atributos})

    # 2)  Clases declaradas con xmi:type="uml:Class" (por si la herramienta las suelta así)
    for elem in root.findall(".//*[@xmi:type='uml:Class']", ns):
        nombre = elem.get("name", "Clase")
        if nombre not in [c["nombre"] for c in clases]:    # evita duplicados
            atributos = [
                att.get("name")
                for att in elem.findall("./ownedAttribute", ns)
                if att.get("name")
            ]
            clases.append({"nombre": nombre, "atributos": atributos})

    return clases

ICONOS_SUGERIDOS = {
    "usuario": "user",
    "rol": "plus",
    "permiso": "cog",
    "producto": "folder",
    "sucursal": "home",
}
def icono_para(clase: str) -> str:
    return ICONOS_SUGERIDOS.get(clase.lower(), "folder")

faker = Faker("es_ES")

def fila_dummy(atributos):
    # Devuelve una lista del mismo largo con valores falsos
    vals = []
    for att in atributos:
        if 'id' in att.lower():
            vals.append(str(faker.random_int(1, 9999)))
        elif 'fecha' in att.lower():
            vals.append(faker.date())
        elif 'descripcion' in att.lower():
            vals.append(faker.sentence(nb_words=6))
        else:
            vals.append(faker.word())
    return vals
# -----------------------------------------------------
# Login estático tal cual tu JSON
TEMPLATE_LOGIN =  {
                        "id": "1745729450641",
                        "type": "login",
                        "x": 581.9572258528419,
                        "y": 139.3523736744362,
                        "width": 433,
                        "height": 388,
                        "styles": "",
                        "card": {
                            "id": "1745729450641-card",
                            "type": "card",
                            "x": 0,
                            "y": 0,
                            "width": 400,
                            "height": 600,
                            "styles": "p-6 flex flex-col items-center justify-center gap-4",
                            "backgroundColor": "#ffffff",
                            "borderRadius": "20px",
                            "padding": "1.5rem",
                            "shadow": True
                        },
                        "title": {
                            "id": "1745729450641-title",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 30,
                            "text": "Bienvenido a Te ayudo",
                            "styles": "text-2xl font-bold text-black"
                        },
                        "subtitle": {
                            "id": "1745729450641-subtitle",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 20,
                            "text": "Enter your email below to login to your account",
                            "styles": "text-gray-500 text-sm"
                        },
                        "emailInput": {
                            "id": "1745729450641-email",
                            "type": "input",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "border border-gray-300 bg-white rounded px-3 py-2 w-full",
                            "placeholder": "m@example.com",
                            "borderRadius": "0.375rem",
                            "value": ""
                        },
                        "passwordInput": {
                            "id": "1745729450641-password",
                            "type": "input",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "border border-gray-300 bg-white rounded px-3 py-2 w-full",
                            "placeholder": "",
                            "borderRadius": "0.375rem",
                            "value": ""
                        },
                        "loginButton": {
                            "id": "1745729450641-login-button",
                            "type": "button",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "bg-black text-white w-full py-2 rounded",
                            "label": "Login",
                            "backgroundColor": "#a855f7",
                            "borderRadius": "0.375rem",
                            "route": "31"
                        },
                        "googleButton": {
                            "id": "1745729450641-google-button",
                            "type": "button",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "bg-white text-black border border-gray-300 w-full py-2 rounded",
                            "label": "Login with Google",
                            "backgroundColor": "#ffffff",
                            "borderRadius": "0.375rem",
                            "route": "31"
                        },
                        "signupLink": {
                            "id": "1745729450641-signup",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 20,
                            "text": "Don't have an account? Sign up",
                            "styles": "text-sm text-gray-600",
                            "route": "31"
                        }
                    }
  # ← pega aquí el bloque completo de la página Login
# Sidebar base (la estructura de “Usuarios”):
SIDEBAR_BASE = {
                        "id": "1745569520491",
                        "type": "sidebar",
                        "title": "Te Ayudo",
                        "x": -0.399993896484375,
                        "y": 0,
                        "width": 257,
                        "height": 729,
                        "styles": "bg-white shadow-lg p-4",
                        "asideBg": "#ffffff",
                        "mainColor": "#a855f7",
                        "sections": [
                            {
                                "icon": "user",
                                "label": "Usuarios",
                                "route": "31"
                            },
                            {
                                "icon": "plus",
                                "label": "Roles",
                                "route": "30"
                            },
                            {
                                "icon": "cog",
                                "label": "Permisos",
                                "route": "33"
                            },
                            {
                                "icon": "folder",
                                "label": "Productos",
                                "route": "34"
                            },
                            {
                                "icon": "home",
                                "label": "Sucursales",
                                "route": "35"
                            }
                        ],
                        "select": 0
            }
                    
# Header base (de “Usuarios”):
HEADER_BASE  =  {
                        "id": "1745701587012",
                        "type": "header",
                        "x": 254.69680712695413,
                        "y": 2.01019287110471e-05,
                        "width": 1282,
                        "height": 61,
                        "styles": "flex justify-between items-center p-4 border border-gray-300",
                        "backgroundColor": "#ffffff",
                        "sections": [
                            {
                                "label": "Te ayudo",
                                "route": "32"
                            },
                            {
                                "label": "Usuarios",
                                "route": "31"
                            }
                        ],
                        "buttons": [
                            {
                                "icon": "bell"
                            },
                            {
                                "icon": "user"
                            }
                        ],
                        "activeColor": "#a855f7"
            }

# Listar base (de “Usuarios”):
LISTAR_BASE  = {
                        "id": "1745649192323",
                        "type": "listar",
                        "x": 371.8843501003208,
                        "y": 162.06279010331542,
                        "width": 1050,
                        "height": 334,
                        "styles": "",
                        "button": {
                            "id": "1745649192323-btn",
                            "type": "button",
                            "label": "Agregar",
                            "x": 0,
                            "y": 0,
                            "width": 120,
                            "height": 40,
                            "styles": "bg-blue-600 text-white px-4 py-2 rounded",
                            "backgroundColor": "#a855f7"
                        },
                        "label": {
                            "id": "1745649192323-lbl",
                            "type": "label",
                            "text": "Todos los Usuarios",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 30,
                            "styles": "text-lg font-semibold text-black"
                        },
                        "search": {
                            "id": "1745649192323-search",
                            "type": "search",
                            "placeholder": "Buscar por nombre...",
                            "x": 0,
                            "y": 0,
                            "width": 250,
                            "height": 40,
                            "styles": "border-gray-300 rounded bg-white px-3 py-1"
                        },
                        "dataTable": {
                            "id": "1745649192323-table",
                            "type": "datatable",
                            "x": 0,
                            "y": 0,
                            "width": 1000,
                            "height": 200,
                            "styles": "",
                            "headers": [
                                "Id",
                                "Nombre",
                                "Descripción",
                                "Fecha de creación",
                                "Estado"
                            ],
                            "backgroundColor": "#ffffff",
                            "rows": [
                                [
                                    "1",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "2",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "3",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "4",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ]
                            ]
                        },
                        "pagination": {
                            "id": "1745649192323-pg",
                            "type": "pagination",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "text-black",
                            "currentPage": 1,
                            "totalPages": 5
                        },
                        "dialog": {
                            "id": "1745649192323-dialog",
                            "type": "dialog",
                            "x": 0,
                            "y": 0,
                            "width": 400,
                            "height": 500,
                            "styles": "",
                            "title": "Agregar nuevo proyecto",
                            "fields": [
                                {
                                    "label": "Id",
                                    "type": {
                                        "id": "1745649192323-input-Id",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese id",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Nombre",
                                    "type": {
                                        "id": "1745649192323-input-Nombre",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese nombre",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Descripción",
                                    "type": {
                                        "id": "1745649192323-input-Descripción",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese descripción",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Fecha de creación",
                                    "type": {
                                        "id": "1745649192323-input-Fecha de creación",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese fecha de creación",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Estado",
                                    "type": {
                                        "id": "1745649192323-input-Estado",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese estado",
                                        "value": ""
                                    }
                                }
                            ]
                        },
                        "size": {
                            "width": None
                        }
                }

import copy, time

def page_para_clase(clase: dict, secciones_sidebar: list, idx_sel: int, order: int) -> dict:
    ts = int(time.time()*1000)
    nombre = clase['nombre'].capitalize()

    # --- Sidebar ---
    sidebar = copy.deepcopy(SIDEBAR_BASE)
    sidebar['id'] = f"{ts}-sb"
    sidebar['select'] = idx_sel
    sidebar['sections'] = secciones_sidebar   # mismas secciones para todas

    # --- Header --- 
    header = copy.deepcopy(HEADER_BASE)
    header['id'] = f"{ts}-hdr"
    header['sections'][1]['label'] = nombre   # migaja actual
    header['sections'][1]['route'] = str(order)  # id de página
    header['activeColor'] = "#a855f7"

    # --- Listar / DataTable ---
    listar = copy.deepcopy(LISTAR_BASE)
    listar['id'] = f"{ts}-lst"
    listar['label']['text'] = f"Todos los {nombre}"
    listar['button']['backgroundColor'] = "#a855f7"
    listar['dialog']['title'] = f"Agregar nuevo {nombre.lower()}"

    # headers = atributos
    listar['dataTable']['headers'] = clase['atributos']

    # filas dummy
    filas = [fila_dummy(clase['atributos']) for _ in range(4)]
    listar['dataTable']['rows'] = filas

    # también replica los fields del diálogo
    listar['dialog']['fields'] = [
        {
            "label": att,
            "type": {
                "id": f"{ts}-{att}",
                "type": "input",
                "x": 0, "y": 0, "width": 300, "height": 40,
                "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                "placeholder": f"Ingrese {att.lower()}",
                "value": ""
            }
        } for att in clase['atributos']
    ]

    # --- Página completa ---
    return  {
        "id": order,              # o autogenerado en BD
        "name": nombre,
        "order": order,
        "background_color": "#ffffff",
        "grid_enabled": False,
        "device_mode": "desktop",
        "components": [sidebar, listar, header]
    }

def generar_pages_desde_xml(xml: bytes) -> list[dict]:
    clases = extraer_clases(xml)
    print("Clases extraídas del XML:", clases)
    # 1️⃣ Login siempre primero
    pages = [{
        "id": 1,  # id autogenerado ficticio
        "name": "Login",
        "order": 1,
        "background_color": "#ffffff",
        "grid_enabled": False,
        "device_mode": "desktop",
        "components": [copy.deepcopy(TEMPLATE_LOGIN)]  # Aquí lo corregimos
    }]

    # 2️⃣ Construir secciones únicas para TODO el sidebar
    secciones_sidebar = [
        {
            "icon": icono_para(cls['nombre']),
            "label": cls['nombre'].capitalize(),
            "route": str(i+2)   # +2 porque 1 es Login
        }
        for i, cls in enumerate(clases)
    ]

    # 3️⃣ Una página por clase
    for i, cls in enumerate(clases, start=2):
        pages.append(
            page_para_clase(cls, secciones_sidebar, idx_sel=i-2, order=i)
        )

    return pages

def set_routes_sidebar(pg, name_to_id):
    comps = copy.deepcopy(pg.components)          # ← copia
    changed = False
    for comp in comps:
        if comp.get('type') == 'sidebar':
            for sec in comp['sections']:
                dest = name_to_id.get(sec['label'].lower())
                if dest and sec['route'] != str(dest):
                    sec['route'] = str(dest)
                    changed = True
    if changed:
        pg.components = comps    # ← re-asignación marca sucio
    return changed

def set_login_buttons(login_pg, id_segunda):
    comps = copy.deepcopy(login_pg.components)
    for comp in comps:
        if comp.get('type') == 'login':
            for _, sub in comp.items():
                if isinstance(sub, dict) and sub.get('type') == 'button':
                    sub['route'] = str(id_segunda)
    login_pg.components = comps   # ← re-asignación
COMPONENTES = ["button","input","sidebar","label","datatable","header"]

def normaliza(txt):
    t = unicodedata.normalize("NFKD", txt).encode("ascii","ignore").decode()
    return t.lower().strip()

def match_tipo(txt):
    txt = normaliza(txt)
    candidato = difflib.get_close_matches(txt, COMPONENTES, n=1, cutoff=0.6)
    return candidato[0] if candidato else "unknown"

def detectar_componentes_desde_imagen(b: bytes) -> list[dict]:
    nparr = np.frombuffer(b, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=2)

    conts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    componentes = []
    for cnt in conts:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < 500:                 
            continue

        roi = gray[y:y + h, x:x + w]
        # 3) usa modo PSM 6 (una línea de texto) y quita saltos
        txt = pytesseract.image_to_string(roi, config="--psm 6").strip().lower()

        tipo = match_tipo(txt)

        # 4) heurística por proporciones si OCR falla
        if tipo == "unknown":
            if h > 2.5 * w:
                tipo = "sidebar"
            elif w > 3 * h:
                tipo = "header"
            elif 1.5 * h < w < 6 * h:
                tipo = "button"

        if tipo != "unknown":
            comp_id = str(uuid.uuid4().int >> 100)
            base = {"id": comp_id, "x": int(x), "y": int(y),
                    "width": int(w), "height": int(h)}

            if tipo == "button":
                componentes.append({**base, "type": "button",
                                    "label": "Botón",
                                    "styles": "flex items-center justify-center "
                                              "bg-blue-600 text-white rounded"})
            elif tipo == "input":
                componentes.append({**base, "type": "input", "placeholder": "..."})
            elif tipo == "label":
                componentes.append({**base, "type": "label", "text": "Texto"})
            elif tipo == "sidebar":
                componentes.append({**base, "type": "sidebar",
                                    "title": "Sidebar", "sections": []})
            elif tipo == "datatable":
                componentes.append({**base, "type": "datatable",
                                    "headers": ["Id", "Nombre"], "rows": []})
            elif tipo == "header":
                componentes.append({**base, "type": "header",
                                    "sections": [], "buttons": []})

    componentes.sort(key=lambda c: (c["y"], c["x"]))
    return componentes

@router.post("/", response_model=Proyecto)
def crear_proyecto(
    name: str = Form(...),
    descripcion: str = Form(...),
    colaboradorId: Optional[str] = Form(None),  # Opción: lo recibimos como string tipo '12,13'
    archivo_xml: UploadFile = File(None),
    imagen_boceto: UploadFile = File(None), 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    nuevo_proyecto = ProyectoModel(
        name=name,
        descripcion=descripcion,
        status="En proceso",
        owner_id=current_user.id,
        create_date=datetime.utcnow(),
        pages=[]  # inicialmente vacío
    )
    db.add(nuevo_proyecto)
    db.commit()
    db.refresh(nuevo_proyecto)
    
    if archivo_xml:
        xml_bytes = archivo_xml.file.read()
        listado_pages = generar_pages_desde_xml(xml_bytes)

        pages_temp: list[Page] = []

        # 1️⃣ Insertamos todas las páginas y llenamos pages_temp
        for p_dict in listado_pages:
            page_obj = Page(
                name=p_dict['name'],
                order=p_dict['order'],
                proyecto_id=nuevo_proyecto.id,
                components=p_dict['components']
            )
            db.add(page_obj)
            pages_temp.append(page_obj)

        db.flush()          

        # 2️⃣ Creamos mapa nombre → id
        name_to_id = {p.name.lower(): p.id for p in pages_temp}

        # 3️⃣ Botones del Login  → id segunda página
        if len(pages_temp) >= 2:
            set_login_buttons(pages_temp[0], pages_temp[1].id)

        # 4️⃣ Sidebars → id real de la página correspondiente
        for pg in pages_temp:
            set_routes_sidebar(pg, name_to_id)

        db.commit() 
    elif imagen_boceto:
        bytes_img = imagen_boceto.file.read()
        componentes = detectar_componentes_desde_imagen(bytes_img)  # 👈 tu función OCR + CV
        print("Componentes detectados:", componentes)
        pagina_diseñada = Page(
            name="Página generada",
            order=1,
            proyecto_id=nuevo_proyecto.id,
            components=componentes
        )
        db.add(pagina_diseñada)
        db.commit()
        db.refresh(pagina_diseñada)
    else:
        pagina_inicial = Page(
            name="Página 1",
            order=1,
            proyecto_id=nuevo_proyecto.id,
            components=[]  # JSON vacío
        )
        db.add(pagina_inicial)
        db.commit()
        db.refresh(pagina_inicial)

    if colaboradorId:
        for colaborador_id in colaboradorId:
            relacion = ColaboradorProyecto(
                usuario_id=colaborador_id,
                proyecto_id=nuevo_proyecto.id,
                permisos="ver"  # por defecto, luego puedes asignar permisos específicos
            )
            db.add(relacion)
        db.commit()

    return nuevo_proyecto

@router.get("/", response_model=ProyectoListResponse)
def listar_proyectos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.is_main:
        # Usuario es administrador: proyectos que creó
        proyectos = db.query(ProyectoModel).filter_by(owner_id=current_user.id).all()
    else:
        # Usuario es colaborador: proyectos donde fue asignado
        proyectos = (
            db.query(ProyectoModel)
            .join(ColaboradorProyecto, ColaboradorProyecto.proyecto_id == ProyectoModel.id)
            .filter(ColaboradorProyecto.usuario_id == current_user.id)
            .all()
        )

    return {
        "data": proyectos,
        "countData": len(proyectos)
    }

@router.get("/last-worked", response_model=ProyectoResponse)
def obtener_ultimo_proyecto(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. proyectos donde es owner
    owner_q = db.query(ProyectoModel).filter(
        ProyectoModel.owner_id == current_user.id
    )
    print("Owner Query:", owner_q)
    # 2. proyectos donde es colaborador
    colaborador_q = (
        db.query(ProyectoModel)
        .join(ColaboradorProyecto,
              ColaboradorProyecto.proyecto_id == ProyectoModel.id)
        .filter(ColaboradorProyecto.usuario_id == current_user.id)
    )

    print("Colaborador Query:", colaborador_q)
    # 3. UNION ALL y ordenamos por last_modified
    ultimo = (
        owner_q.union_all(colaborador_q)
               .order_by(desc(ProyectoModel.last_modified))
               .limit(1)
               .first()
    )

    if not ultimo:
        raise HTTPException(404, "No tienes proyectos todavía")

    return {
        "data": ultimo,
    }

@router.get("/{proyecto_id}", response_model=ProyectoResponse)
def obtener_proyecto_por_id(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Buscar el proyecto donde sea owner
    proyecto = db.query(ProyectoModel).filter_by(id=proyecto_id, owner_id=current_user.id).first()

    if not proyecto:
        # Si no es owner, buscamos si es colaborador
        proyecto = (
            db.query(ProyectoModel)
            .join(ColaboradorProyecto, ColaboradorProyecto.proyecto_id == ProyectoModel.id)
            .filter(
                ColaboradorProyecto.usuario_id == current_user.id,
                ProyectoModel.id == proyecto_id
            )
            .first()
        )

    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado o no tienes acceso")

    return {
        "data": proyecto
    }

@router.put("/", response_model=ProyectoResponse)
def actualizar_proyecto(
    data: ProyectoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. ─────────── obtener proyecto y validar propietario
    proyecto = (
        db.query(ProyectoModel)
          .filter(ProyectoModel.id == data.id)
          .first()
    )
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    if proyecto.owner_id != current_user.id:
        raise HTTPException(403, "No autorizado")

    # 2. ─────────── actualizar campos simples del proyecto
    for campo in ("name", "descripcion", "status", "last_modified"):
        nuevo_valor = getattr(data, campo, None)
        if nuevo_valor is not None:
            setattr(proyecto, campo, nuevo_valor)

    # 3. ─────────── procesar cada página recibida
    #    usamos un dicc para saber cuáles páginas ya estaban
    existentes = {p.id: p for p in proyecto.pages}

    for pagina_in in data.pages:
        # 3.a ── UPDATE de página existente
        if pagina_in.id:
            page_obj = existentes.get(pagina_in.id)
            if not page_obj:
                raise HTTPException(
                    400,
                    f"Página con id {pagina_in.id} no pertenece al proyecto",
                )
        # 3.b ── INSERT de una nueva página
        else:
            page_obj = Page(proyecto_id=proyecto.id)
            db.add(page_obj)

        # Actualizamos campos de la página
        for campo in (
            "name",
            "order",
            "background_color",
            "grid_enabled",
            "device_mode",
            "components",
        ):
            nuevo_valor = getattr(pagina_in, campo, None)
            if nuevo_valor is not None:
                setattr(page_obj, campo, nuevo_valor)

    # 4. ─────────── commit (esto disparará el `onupdate` y refrescará last_modified)
    db.commit()
    db.refresh(proyecto)

    return {"data": proyecto}

@router.post(
    "/{project_id}/pages",
    response_model=PageResponse,   # ahora sí coincide con lo que devolvemos
    status_code=201
)
def crear_pagina_en_proyecto(
    project_id: int,
    page_in: PageCreateIn,         # ⬅ sin Depends()
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. Verificar proyecto
    proyecto = (
        db.query(ProyectoModel)
          .filter(ProyectoModel.id == project_id)
          .first()
    )
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    # (opcional) validar permisos…

    # 2. Calcular order y nombre por defecto
    total_pages  = db.query(func.count(Page.id))\
                     .filter(Page.proyecto_id == project_id).scalar()
    nuevo_order  = (total_pages or 0) + 1
    nombre_def   = f"Página {nuevo_order}"

    nueva_pagina = Page(
        name             = page_in.name  or nombre_def,
        order            = page_in.order if page_in.order is not None else nuevo_order,
        background_color = page_in.background_color,
        grid_enabled     = page_in.grid_enabled,
        device_mode      = page_in.device_mode,
        components       = page_in.components,
        proyecto_id      = project_id
    )

    db.add(nueva_pagina)

    # 3. Actualizar timestamp del proyecto
    proyecto.last_modified = datetime.utcnow()

    db.commit()
    db.refresh(nueva_pagina)

    # 4. Devolver SOLO la página creada en el envoltorio `data`
    return {"data": nueva_pagina}

def slugify(text: str) -> str:
    """‘Página X’ → 'pagina-x'  (ASCII, minúsculas, guiones)"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", text)

def pascal_from_slug(slug: str) -> str:
    """'pagina-x' → 'PaginaXComponent'"""
    return "".join(word.capitalize() for word in slug.split("-")) + "Component"

@router.get("/{project_id}/download")
def descargar_proyecto_angular(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Obtener el proyecto
    proj = db.query(ProyectoModel).filter_by(id=project_id).first()
    if not proj:
        raise HTTPException(404, "Proyecto no encontrado")

    # -- serializa ORM → dict (puedes usar Pydantic)
    proj_dict = Proyecto.model_validate(proj).model_dump()

    zip_path  = build_flutter_project(proj_dict)   # ← util de arriba
    return FileResponse(zip_path,
                        filename=f"frontend_flutter_{proj.id}.zip",
                        media_type="application/zip")