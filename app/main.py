from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.routes import proyectos
from app.routes import ia as ia_router
from app.sockets.realtime import sio  # Traer el mismo sio
from socketio import ASGIApp

app = FastAPI()

origins = [
    "http://localhost:5173",  # desarrollo local
    "https://generador-frontends.premiumshop.shop",  # dominio en producción
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(proyectos.router)
app.include_router(ia_router.router)

socket_app = ASGIApp(sio, other_asgi_app=app)  # aquí sí creamos socket_app global
