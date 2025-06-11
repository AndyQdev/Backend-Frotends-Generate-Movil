import json
# from fastapi import APIRouter, Depends, HTTPException, Path, Body
from fastapi import APIRouter, Depends, HTTPException, Path, Body, Query
from sqlalchemy.orm import Session
# from app.routes.utils.flutter_generator import build_flutter_project
from app.routes.utils.flutter_generator import build_flutter_project, build_specific_files
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
    ProyectoUpdate, PageUpdate, ColaboradorResponse, ColaboradoresResponse,
    ColaboradorUpdate, ColaboradorUpdateResponse
)
from app.services.vision import components_from_image
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


@router.post("/", response_model=Proyecto)
def crear_proyecto(
    name: str = Form(...),
    descripcion: str = Form(...),
    resolution_w: Optional[int] = Form(None),
    resolution_h: Optional[int] = Form(None),
    colaboradorId: Optional[str] = Form(None),  # Opción: lo recibimos como string tipo '12,13'
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        nuevo_proyecto = ProyectoModel(
            name=name,
            descripcion=descripcion,
            status="En proceso",
            owner_id=current_user.id,
            create_date=datetime.utcnow(),
            resolution_w=resolution_w or 390,
            resolution_h=resolution_h or 844,
            pages=[]  # inicialmente vacío
        )
        db.add(nuevo_proyecto)
        db.flush()  # Para obtener el ID del proyecto
        
        pagina_inicial = Page(
            name="Página 1",
            order=1,
            proyecto_id=nuevo_proyecto.id,
            components=[]  # JSON vacío
        )
        db.add(pagina_inicial)
        db.flush()

        if colaboradorId:
            print("="*50)
            print("DEBUG - Creación de colaboradores:")
            print(f"Tipo de colaboradorId: {type(colaboradorId)}")
            print(f"Valor de colaboradorId: {colaboradorId}")
            print(f"Proyecto ID: {nuevo_proyecto.id}")
            print("="*50)
            
            # Convertir el string de IDs a lista
            colaboradores_ids = [int(id.strip()) for id in colaboradorId.split(',') if id.strip()]
            print(f"IDs de colaboradores procesados: {colaboradores_ids}")
            
            # Verificar que el usuario existe antes de crear la relación
            for colaborador_id in colaboradores_ids:
                usuario = db.query(Usuario).filter(Usuario.id == colaborador_id).first()
                if not usuario:
                    print(f"ERROR: Usuario con ID {colaborador_id} no existe en la base de datos")
                    raise HTTPException(400, f"Usuario con ID {colaborador_id} no existe en la base de datos")
                    
                relacion = ColaboradorProyecto(
                    usuario_id=colaborador_id,
                    proyecto_id=nuevo_proyecto.id,
                    permisos="ver"  # por defecto, luego puedes asignar permisos específicos
                )
                db.add(relacion)

        db.commit()
        db.refresh(nuevo_proyecto)
        return nuevo_proyecto

    except Exception as e:
        db.rollback()
        print(f"Error al crear proyecto: {str(e)}")
        raise HTTPException(500, f"Error al crear el proyecto: {str(e)}")

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
    # if proyecto.owner_id != current_user.id:
    #     raise HTTPException(403, "No autorizado")

    # 2. ─────────── actualizar campos simples del proyecto
    for campo in ("name", "descripcion", "status", "last_modified"):
        nuevo_valor = getattr(data, campo, None)
        if nuevo_valor is not None:
            setattr(proyecto, campo, nuevo_valor)

    # 3. ─────────── actualizar colaboradores si se proporcionan
    if data.colaboradores is not None:
        print("="*50)
        print("DEBUG - Actualización de colaboradores:")
        print(f"Tipo de colaboradores: {type(data.colaboradores)}")
        print(f"Valor de colaboradores: {data.colaboradores}")
        print(f"Proyecto ID: {proyecto.id}")
        print("="*50)
        
        # Eliminar colaboradores existentes
        db.query(ColaboradorProyecto).filter(
            ColaboradorProyecto.proyecto_id == proyecto.id
        ).delete()
        
        # Agregar nuevos colaboradores
        for colaborador_id in data.colaboradores:
            usuario = db.query(Usuario).filter(Usuario.id == colaborador_id).first()
            if not usuario:
                print(f"ERROR: Usuario con ID {colaborador_id} no existe en la base de datos")
                continue
                
            relacion = ColaboradorProyecto(
                usuario_id=colaborador_id,
                proyecto_id=proyecto.id,
                permisos="ver"  # por defecto
            )
            db.add(relacion)

    # 4. ─────────── procesar cada página recibida
    #    usamos un dicc para saber cuáles páginas ya estaban
    existentes = {p.id: p for p in proyecto.pages}

    for pagina_in in data.pages:
        # 4.a ── UPDATE de página existente
        if pagina_in.id:
            page_obj = existentes.get(pagina_in.id)
            if not page_obj:
                raise HTTPException(
                    400,
                    f"Página con id {pagina_in.id} no pertenece al proyecto",
                )
        # 4.b ── INSERT de una nueva página
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

    # 5. ─────────── commit (esto disparará el `onupdate` y refrescará last_modified)
    db.commit()
    db.refresh(proyecto)

    return {"data": proyecto}

@router.post("/{project_id}/pages", response_model=PageResponse, status_code=201)
async def crear_pagina_en_proyecto(
    project_id: int,
    page_in: PageCreateIn = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    print("=== DATOS RECIBIDOS EN CREAR PÁGINA ===")
    print("Project ID:", project_id)
    print("Page Data (raw):", page_in)
    print("Page Data (dict):", page_in.model_dump())
    print("Name recibido:", page_in.name)
    print("Usuario actual:", current_user.email)
    print("=====================================")

    proyecto = (
        db.query(ProyectoModel)
          .filter(ProyectoModel.id == project_id)
          .first()
    )
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    total_pages = db.query(func.count(Page.id))\
                    .filter(Page.proyecto_id == project_id).scalar()
    nuevo_order = (total_pages or 0) + 1
    nombre_def  = f"Página {nuevo_order}"

    # Asegurarnos de que el nombre se asigne correctamente
    nombre_final = page_in.name if page_in.name and page_in.name.strip() else nombre_def
    print("Nombre final asignado:", nombre_final)

    nueva_pagina = Page(
        name             = nombre_final,
        order            = page_in.order if page_in.order is not None else nuevo_order,
        background_color = page_in.background_color,
        grid_enabled     = page_in.grid_enabled,
        device_mode      = page_in.device_mode,
        components       = page_in.components or [],
        proyecto_id      = project_id,
    )

    db.add(nueva_pagina)
    proyecto.last_modified = datetime.utcnow()
    db.commit(); db.refresh(nueva_pagina)

    print("Página creada exitosamente:", nueva_pagina.id)
    return {"data": nueva_pagina}

@router.post("/{project_id}/pages/{page_id}/process-image", response_model=PageResponse)
async def procesar_imagen_pagina(
    project_id: int,
    page_id: int,
    img: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    print("=== PROCESANDO IMAGEN PARA PÁGINA ===")
    print("Project ID:", project_id)
    print("Page ID:", page_id)
    print("Imagen recibida:", img.filename)
    print("Usuario actual:", current_user.email)
    print("=====================================")

    # Verificar que el proyecto existe y pertenece al usuario
    proyecto = db.query(ProyectoModel).filter(ProyectoModel.id == project_id).first()
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    # if proyecto.owner_id != current_user.id:
    #     raise HTTPException(403, "No autorizado para modificar este proyecto")

    # Buscar la página
    pagina = db.query(Page).filter(
        Page.id == page_id,
        Page.proyecto_id == project_id
    ).first()
    if not pagina:
        raise HTTPException(404, "Página no encontrada")

    # Procesar la imagen
    res_w = proyecto.resolution_w or 390
    res_h = proyecto.resolution_h or 844
    
    print("Procesando imagen de boceto...")
    img_bytes = await img.read()
    comps_valid = components_from_image(
        img_bytes,
        img.content_type,
        res_w,
        res_h
    )
    print("Componentes extraídos de imagen:", comps_valid)
    
    # Actualizar los componentes de la página
    componentes = [c.model_dump(mode="json") for c in comps_valid]
    pagina.components = componentes
    
    proyecto.last_modified = datetime.utcnow()
    db.commit()
    db.refresh(pagina)

    print("Imagen procesada exitosamente")
    return {"data": pagina}

def slugify(text: str) -> str:
    """'Página X' → 'pagina-x'  (ASCII, minúsculas, guiones)"""
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

@router.get("/{proyecto_id}/colaboradores", response_model=ColaboradoresResponse)
def obtener_colaboradores_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Verificar que el usuario tenga acceso al proyecto
    proyecto = db.query(ProyectoModel).filter_by(id=proyecto_id).first()
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    # Verificar que el usuario sea el propietario o un colaborador
    if proyecto.owner_id != current_user.id:
        es_colaborador = db.query(ColaboradorProyecto).filter_by(
            proyecto_id=proyecto_id,
            usuario_id=current_user.id
        ).first()
        if not es_colaborador:
            raise HTTPException(403, "No tienes acceso a este proyecto")

    # Obtener todos los colaboradores del proyecto
    colaboradores = (
        db.query(Usuario, ColaboradorProyecto.permisos)
        .join(ColaboradorProyecto, ColaboradorProyecto.usuario_id == Usuario.id)
        .filter(ColaboradorProyecto.proyecto_id == proyecto_id)
        .all()
    )

    # Transformar los resultados al formato esperado
    colaboradores_formateados = [
        {
            "id": c.Usuario.id,
            "email": c.Usuario.email,
            "name": c.Usuario.name,
            "permisos": c.permisos
        }
        for c in colaboradores
    ]

    return {
        "data": colaboradores_formateados,
        "countData": len(colaboradores_formateados)
    }

@router.put("/colaboradores/{colaborador_id}", response_model=ColaboradorUpdateResponse)
def actualizar_colaborador(
    colaborador_id: int,
    data: ColaboradorUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Verificar que el usuario a actualizar existe
    colaborador = db.query(Usuario).filter_by(id=colaborador_id).first()
    if not colaborador:
        raise HTTPException(404, "Colaborador no encontrado")

    # Verificar que el usuario actual es administrador
    if not current_user.is_main:
        raise HTTPException(403, "No tienes permisos para actualizar colaboradores")

    # Actualizar datos básicos del colaborador
    if data.name is not None:
        colaborador.name = data.name
    if data.email is not None:
        colaborador.email = data.email
    if data.telefono is not None:
        colaborador.telefono = data.telefono

    # Actualizar proyectos si se proporcionan
    if data.proyectos_ids is not None:
        # Eliminar relaciones existentes
        db.query(ColaboradorProyecto).filter_by(usuario_id=colaborador_id).delete()
        
        # Crear nuevas relaciones
        for proyecto_id in data.proyectos_ids:
            relacion = ColaboradorProyecto(
                usuario_id=colaborador_id,
                proyecto_id=proyecto_id,
                permisos="ver"  # por defecto "ver"
            )
            db.add(relacion)

    db.commit()
    db.refresh(colaborador)

    # Obtener los permisos actuales para la respuesta
    permisos = db.query(ColaboradorProyecto.permisos).filter_by(usuario_id=colaborador_id).first()
    
    return {
        "data": {
            "id": colaborador.id,
            "email": colaborador.email,
            "name": colaborador.name,
            "permisos": permisos.permisos if permisos else "ver"
        }
    }

@router.delete("/pages/{page_id}")
def eliminar_pagina(
    page_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Buscar la página y su proyecto asociado
    pagina = db.query(Page).filter(Page.id == page_id).first()
    if not pagina:
        raise HTTPException(404, "Página no encontrada")

    # Verificar que el usuario es el propietario del proyecto
    # if pagina.proyecto.owner_id != current_user.id:
    #     raise HTTPException(403, "No autorizado para eliminar esta página")

    # Eliminar la página
    db.delete(pagina)
    db.commit()

    return {"message": "Página eliminada exitosamente"}

@router.delete("/{proyecto_id}")
def eliminar_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        # Buscar el proyecto
        proyecto = db.query(ProyectoModel).filter(ProyectoModel.id == proyecto_id).first()
        if not proyecto:
            raise HTTPException(404, "Proyecto no encontrado")

        # Verificar que el usuario es el propietario del proyecto
        if proyecto.owner_id != current_user.id:
            raise HTTPException(403, "No autorizado para eliminar este proyecto")

        # Eliminar las relaciones con colaboradores primero
        db.query(ColaboradorProyecto).filter(
            ColaboradorProyecto.proyecto_id == proyecto_id
        ).delete()

        # Eliminar el proyecto (esto eliminará también las páginas por cascade)
        db.delete(proyecto)
        db.commit()

        return {"message": "Proyecto eliminado exitosamente"}
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar proyecto: {str(e)}")
        raise HTTPException(500, f"Error al eliminar el proyecto: {str(e)}")


# desde aqui
@router.get("/{project_id}/download-specific")
def descargar_archivos_especificos(
    project_id: int,
    files: str = Query(..., description="Lista de archivos a descargar separados por coma. Ejemplos: 'main,page_131,page_132'"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Descarga archivos específicos del proyecto Flutter.

    Args:
        project_id: ID del proyecto
        files: Lista de archivos a descargar separados por coma. Opciones:
            - 'main': Para descargar el archivo main.dart
            - 'page_X': Para descargar una página por ID real (ej: 'page_131')
    """
    # Obtener el proyecto
    proj = db.query(ProyectoModel).filter_by(id=project_id).first()
    if not proj:
        raise HTTPException(404, "Proyecto no encontrado")

    # Validar y procesar archivos
    file_types = [f.strip() for f in files.split(',')]
    proj_dict = Proyecto.model_validate(proj).model_dump()
    page_ids_validos = {p["id"] for p in proj_dict["pages"]}

    final_file_types = []
    for file_type in file_types:
        if file_type == "main":
            final_file_types.append("main")
        elif file_type.startswith("page_"):
            try:
                page_id = int(file_type.split("_")[1])
            except ValueError:
                raise HTTPException(400, f"Formato inválido en archivo: {file_type}")
            if page_id not in page_ids_validos:
                raise HTTPException(404, f"La página {page_id} no existe en el proyecto")
            final_file_types.append(file_type)
        else:
            raise HTTPException(400, f"Tipo de archivo inválido: {file_type}")

    # Generar el zip con los archivos específicos
    zip_path = build_specific_files(proj_dict, final_file_types)

    # Generar nombre del archivo zip
    files_str = '_'.join(final_file_types)
    return FileResponse(
        zip_path,
        filename=f"flutter_files_{proj.id}_{files_str}.zip",
        media_type="application/zip"
    )

