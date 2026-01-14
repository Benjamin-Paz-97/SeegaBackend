"""
Rutas REST para gestión de partidas
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.schemas import (
    CreateGameResponse,
    JoinGameRequest,
    JoinGameResponse,
    GameStateResponse,
    PlaceActionRequest,
    MoveActionRequest,
    ActionResponse,
    LeaveGameResponse
)
from app.services.game_service import GameService
from app.services.repo_memory import InMemoryGameRepository

router = APIRouter()

# Instancia única del servicio (singleton en memoria)
game_repo = InMemoryGameRepository()
game_service = GameService(game_repo)


@router.post("/games", response_model=CreateGameResponse)
async def create_game():
    """
    Crea una nueva partida.
    El jugador 1 recibe un gameId y un token para autenticarse.
    """
    result = game_service.create_game()
    return result


@router.post("/games/{game_id}/join", response_model=JoinGameResponse)
async def join_game(
    game_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    El jugador 2 se une a una partida existente.
    Si se proporciona un token válido, permite reconectar a un jugador existente.
    """
    token = None
    if authorization:
        try:
            token = _extract_token(authorization)
        except:
            pass  # Si el token es inválido, continuar como nuevo jugador
    
    result = game_service.join_game(game_id, token)
    return result


@router.post("/games/{game_id}/reconnect", response_model=JoinGameResponse)
async def reconnect_game(
    game_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Permite a un jugador reconectarse a una partida existente usando su token.
    """
    token = _extract_token(authorization)
    result = game_service.reconnect_game(game_id, token)
    return result


@router.get("/games/{game_id}", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Obtiene el estado actual de una partida.
    Requiere token de autorización.
    """
    token = _extract_token(authorization)
    state = game_service.get_game_state(game_id, token)
    return state


@router.post("/games/{game_id}/place", response_model=ActionResponse)
async def place_piece(
    game_id: str,
    action: PlaceActionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Coloca una pieza en la Fase 1 (posicionamiento).
    """
    token = _extract_token(authorization)
    result = game_service.place_piece(game_id, token, action.x, action.y)
    return result


@router.post("/games/{game_id}/move", response_model=ActionResponse)
async def move_piece(
    game_id: str,
    action: MoveActionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Mueve una pieza en la Fase 2 (movimiento).
    """
    token = _extract_token(authorization)
    result = game_service.move_piece(
        game_id, 
        token, 
        action.from_x, 
        action.from_y, 
        action.to_x, 
        action.to_y
    )
    return result


@router.get("/games/{game_id}/valid-actions")
async def get_valid_actions(
    game_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Obtiene las acciones válidas para el jugador actual.
    Útil para UI (mostrar celdas/movimientos permitidos).
    """
    token = _extract_token(authorization)
    actions = game_service.get_valid_actions(game_id, token)
    return actions


@router.delete("/games/{game_id}/leave", response_model=LeaveGameResponse)
async def leave_game(
    game_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Un jugador abandona la partida.
    Si ambos jugadores abandonan, la partida se elimina.
    """
    token = _extract_token(authorization)
    result = game_service.leave_game(game_id, token)
    return result


def _extract_token(authorization: Optional[str]) -> str:
    """Extrae el token del header Authorization: Bearer {token}"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Formato de token inválido")
    
    return parts[1]

