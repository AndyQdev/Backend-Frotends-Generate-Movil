# realtime.py
import socketio
from fastapi import FastAPI 
from app.auth.auth_utils import decode_token    # usarás decode_token
from app.models.models import Usuario, Proyecto, ColaboradorProyecto
from app.database import SessionLocal
from typing import Dict

# project_users: { project_id: { sid: user_info } }
project_users: Dict[int, Dict[str, dict]] = {}



async def get_user_from_token(token: str) -> Usuario:
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise Exception("Token inválido")

    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    db.close()
    if user is None:
        raise Exception("Usuario no encontrado")
    return user

async def user_can_access_project(user: Usuario, project_id: int) -> bool:
    db = SessionLocal()
    if user.is_main:
        # Si es Admin, verifica que sea el dueño del proyecto
        proyecto = db.query(Proyecto).filter_by(id=project_id, owner_id=user.id).first()
        db.close()
        return proyecto is not None
    else:
        # Si es colaborador, revisa si está asignado al proyecto
        colaboracion = db.query(ColaboradorProyecto).filter_by(usuario_id=user.id, proyecto_id=project_id).first()
        db.close()
        return colaboracion is not None
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[],
    ping_interval=25, ping_timeout=60
)

app = FastAPI()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

@sio.event
async def connect(sid, environ, auth):
    try:
        user = await get_user_from_token(auth["token"])
    except Exception:
        return False   # Rechazar conexión si token inválido

    project_id = int(auth["project_id"])

    if not await user_can_access_project(user, project_id):
        return False   # Rechazar conexión si no tiene acceso

    await sio.save_session(sid, {"user_id": user.id, "project_id": project_id})
    await sio.enter_room(sid, f"project_{project_id}")

    # Aquí podrías enviar snapshot inicial si quieres
    await sio.emit("initial_state", {"message": "snapshot inicial"}, room=sid)

async def persist_create(data: dict):
    db = SessionLocal()
    try:
        component_data = data["component"]
        page_id = data["page_id"]

        from app.models.models import Componente  # Ajusta según tu modelo real

        new_component = Componente(
            page_id=page_id,
            type=component_data["type"],
            x=component_data["x"],
            y=component_data["y"],
            width=component_data["width"],
            height=component_data["height"],
            z_index=component_data.get("z_index", 1),
            is_locked=component_data.get("is_locked", False),
            properties=component_data.get("properties", {}),
            styles=component_data.get("styles", {})
        )
        db.add(new_component)
        db.commit()
        db.refresh(new_component)

        # Actualizamos el ID en el payload para que otros clientes lo sepan
        data["component"]["id"] = new_component.id

    finally:
        db.close()

async def persist_update(data: dict):
    db = SessionLocal()
    try:
        component_data = data["component"]

        from app.models.models import Componente

        comp = db.query(Componente).filter(Componente.id == component_data["id"]).first()
        if comp:
            comp.x = component_data["x"]
            comp.y = component_data["y"]
            comp.width = component_data["width"]
            comp.height = component_data["height"]
            comp.z_index = component_data.get("z_index", comp.z_index)
            comp.is_locked = component_data.get("is_locked", comp.is_locked)
            comp.properties = component_data.get("properties", comp.properties)
            comp.styles = component_data.get("styles", comp.styles)
            db.commit()
    finally:
        db.close()

async def persist_delete(data: dict):
    db = SessionLocal()
    try:
        component_id = data["component"]["id"]

        from app.models.models import Componente

        comp = db.query(Componente).filter(Componente.id == component_id).first()
        if comp:
            db.delete(comp)
            db.commit()
    finally:
        db.close()

async def _relay(sid, event, payload):
    room = f"project_{payload['project_id']}"
    # skip_sid → evita eco al emisor
    await sio.emit(event, payload, room=room, skip_sid=sid)

@sio.event
async def component_created(sid, data):
    # • data = {"project_id": 5, "page_id": 12, "component": {...}}
    try:
        await persist_create(data)          # ① guarda en BD
    except Exception as e:                  # log opcional
        print("error persist_create:", e)
    await _relay(sid, "component_created", data)  # ② re-emite al room

@sio.event
async def component_updated(sid, data):
    try:
        await persist_update(data)
    except Exception as e:
        print("error persist_update:", e)
    await _relay(sid, "component_updated", data)

@sio.event
async def component_deleted(sid, data):
    try:
        await persist_delete(data)
    except Exception as e:
        print("error persist_delete:", e)
    await _relay(sid, "component_deleted", data)
@sio.event
async def disconnect(sid):
    sess = await sio.get_session(sid)
    if sess:
        await sio.leave_room(sid, f"project_{sess['project_id']}")

@sio.event
async def component_moving(sid, data):
    # sólo rebota a los demás
    await _relay(sid, "component_moving", data)

@sio.event
async def component_resizing(sid, data):
    await _relay(sid, "component_resizing", data)

@sio.event
async def component_props_changed(sid, data):
    # rebota al resto, no persiste en BD
    print("props_changed", data) 
    await _relay(sid, "component_props_changed", data)

@sio.event
async def connect(sid, environ, auth):
    try:
        user = await get_user_from_token(auth["token"])
    except Exception:
        return False   # Rechazar conexión si token inválido

    project_id = int(auth["project_id"])

    if not await user_can_access_project(user, project_id):
        return False   # Rechazar conexión si no tiene acceso

    await sio.save_session(sid, {"user_id": user.id, "project_id": project_id})

    await sio.enter_room(sid, f"project_{project_id}")

    # Guardar usuario en la lista global
    if project_id not in project_users:
        project_users[project_id] = {}
    project_users[project_id][sid] = {
        "id": user.id,
        "name": user.name,  # Ajusta el campo con el nombre real que uses
        # puedes añadir más datos como avatar, email, etc.
    }

    # Emitir lista actualizada a todos en la sala
    users_list = list(project_users[project_id].values())
    await sio.emit("usersInProject", users_list, room=f"project_{project_id}")

    # Envía snapshot inicial si quieres
    await sio.emit("initial_state", {"message": "snapshot inicial"}, room=sid)


@sio.event
async def disconnect(sid):
    sess = await sio.get_session(sid)
    if not sess:
        return
    project_id = sess.get("project_id")
    if project_id is None:
        return

    # Quitar usuario de la lista
    if project_id in project_users and sid in project_users[project_id]:
        del project_users[project_id][sid]

        # Emitir lista actualizada a todos en la sala
        users_list = list(project_users[project_id].values())
        await sio.emit("usersInProject", users_list, room=f"project_{project_id}")

    await sio.leave_room(sid, f"project_{project_id}")

@sio.event
async def leaveProject(sid, project_id: int):
    if project_id in project_users and sid in project_users[project_id]:
        del project_users[project_id][sid]
        users_list = list(project_users[project_id].values())
        await sio.emit("usersInProject", users_list, room=f"project_{project_id}")
    await sio.leave_room(sid, f"project_{project_id}")

@sio.event
async def component_selected(sid, data):
    # data = { project_id, page_id, component_id, user_id, user_name, origin }
    room = f"project_{data['project_id']}"
    await sio.emit('component_selected', data, room=room, skip_sid=sid)

@sio.event
async def page_created(sid, data):
    # data = {"project_id": 5, "page": {...}}
    room = f"project_{data['project_id']}"
    await _relay(sid, "page_created", data)

@sio.event
async def page_deleted(sid, data):
    # data = {"project_id": 5, "page_id": "123"}
    room = f"project_{data['project_id']}"
    await _relay(sid, "page_deleted", data)