"""
Seega Game - Backend API
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_games, routes_ws

app = FastAPI(
    title="Seega Game API",
    description="Backend para el juego Seega online",
    version="1.0.0"
)

# CORS para permitir peticiones desde Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Registrar routers
app.include_router(routes_games.router, prefix="/api", tags=["games"])
app.include_router(routes_ws.router, prefix="/api", tags=["websocket"])


@app.get("/")
async def root():
    return {
        "message": "Seega Game API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Maneja las peticiones OPTIONS para CORS preflight"""
    return {"message": "OK"}

