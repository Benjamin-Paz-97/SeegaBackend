"""
Schemas Pydantic para requests y responses de la API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ==================== RESPONSES ====================

class CreateGameResponse(BaseModel):
    """Respuesta al crear una partida"""
    gameId: str
    playerToken: str
    playerNumber: int
    status: str


class JoinGameResponse(BaseModel):
    """Respuesta al unirse a una partida"""
    gameId: str
    playerToken: str
    playerNumber: int
    status: str


class GameStateResponse(BaseModel):
    """Estado completo del juego"""
    gameId: str
    board: List[List[int]]
    phase: str
    status: str
    currentPlayer: int
    yourPlayerNumber: int
    isYourTurn: bool
    piecesCount: Dict[int, int]
    placementRemaining: int
    chainCapturePiece: Optional[tuple[int, int]]
    winner: Optional[int]
    gameOver: bool


class CaptureInfo(BaseModel):
    """Información de una captura"""
    x: int
    y: int


class MoveResultInfo(BaseModel):
    """Resultado de una acción (place o move)"""
    success: bool
    captures: List[CaptureInfo] = []
    extraTurn: bool = False
    phaseChanged: bool = False
    gameOver: bool = False
    winner: Optional[int] = None
    message: str = ""


class ActionResponse(BaseModel):
    """Respuesta después de una acción (place o move)"""
    state: GameStateResponse
    result: MoveResultInfo


class LeaveGameResponse(BaseModel):
    """Respuesta al abandonar una partida"""
    message: str
    gameDeleted: bool


# ==================== REQUESTS ====================

class JoinGameRequest(BaseModel):
    """Request para unirse a una partida (opcional, puede ser vacío)"""
    pass


class PlaceActionRequest(BaseModel):
    """Request para colocar una pieza"""
    x: int = Field(..., ge=0, le=4, description="Coordenada X (0-4)")
    y: int = Field(..., ge=0, le=4, description="Coordenada Y (0-4)")


class MoveActionRequest(BaseModel):
    """Request para mover una pieza"""
    from_x: int = Field(..., ge=0, le=4, description="Coordenada X origen (0-4)")
    from_y: int = Field(..., ge=0, le=4, description="Coordenada Y origen (0-4)")
    to_x: int = Field(..., ge=0, le=4, description="Coordenada X destino (0-4)")
    to_y: int = Field(..., ge=0, le=4, description="Coordenada Y destino (0-4)")

