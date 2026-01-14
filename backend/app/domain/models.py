"""
Modelos de dominio del juego Seega
"""
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass, field


class CellState(int, Enum):
    """Estado de una celda del tablero"""
    EMPTY = 0
    PLAYER1 = 1
    PLAYER2 = 2


class Phase(str, Enum):
    """Fase del juego"""
    PLACEMENT = "placement"  # Fase 1: colocación
    MOVEMENT = "movement"    # Fase 2: movimiento


class GameStatus(str, Enum):
    """Estado de la partida"""
    WAITING = "waiting"      # Esperando al jugador 2
    READY = "ready"          # Ambos jugadores conectados
    PLAYING = "playing"      # Partida en curso
    FINISHED = "finished"    # Partida terminada


@dataclass
class Board:
    """
    Tablero 5x5 del juego Seega.
    Coordenadas: board[fila][columna] donde fila,columna ∈ [0,4]
    Centro (refugio): (2, 2)
    """
    cells: List[List[int]] = field(default_factory=lambda: [[0]*5 for _ in range(5)])
    
    REFUGE_X = 2
    REFUGE_Y = 2
    SIZE = 5
    
    def get(self, x: int, y: int) -> int:
        """Obtiene el estado de una celda"""
        return self.cells[y][x]
    
    def set(self, x: int, y: int, value: int):
        """Establece el estado de una celda"""
        self.cells[y][x] = value
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Verifica si una posición está dentro del tablero"""
        return 0 <= x < self.SIZE and 0 <= y < self.SIZE
    
    def is_empty(self, x: int, y: int) -> bool:
        """Verifica si una celda está vacía"""
        return self.get(x, y) == CellState.EMPTY
    
    def is_refuge(self, x: int, y: int) -> bool:
        """Verifica si una posición es el refugio central"""
        return x == self.REFUGE_X and y == self.REFUGE_Y
    
    def to_list(self) -> List[List[int]]:
        """Convierte el tablero a lista para serialización"""
        return [row[:] for row in self.cells]


@dataclass
class PlayerSession:
    """Información de un jugador en la partida"""
    player_number: int  # 1 o 2
    token: str
    connected: bool = True


@dataclass
class GameState:
    """
    Estado completo de una partida
    """
    game_id: str
    board: Board
    phase: Phase
    status: GameStatus
    current_player: int  # 1 o 2
    
    # Jugadores
    player1: Optional[PlayerSession] = None
    player2: Optional[PlayerSession] = None
    
    # Contadores
    pieces_count: dict = field(default_factory=lambda: {1: 0, 2: 0})
    
    # Fase 1: piezas a colocar en este turno (0, 1 o 2)
    placement_remaining: int = 2
    
    # Fase 2: si hay captura en cadena, esta es la pieza que debe moverse
    chain_capture_piece: Optional[Tuple[int, int]] = None
    
    # Victoria
    winner: Optional[int] = None
    game_over: bool = False
    
    # Metadata
    total_pieces_placed: int = 0  # Total colocadas (max 24)
    
    def get_player_session(self, player_number: int) -> Optional[PlayerSession]:
        """Obtiene la sesión de un jugador"""
        return self.player1 if player_number == 1 else self.player2
    
    def get_opponent(self, player_number: int) -> int:
        """Obtiene el número del oponente"""
        return 2 if player_number == 1 else 1
    
    def switch_turn(self):
        """Cambia el turno al otro jugador"""
        self.current_player = self.get_opponent(self.current_player)
        if self.phase == Phase.PLACEMENT:
            self.placement_remaining = 2


@dataclass
class MoveResult:
    """Resultado de una acción (colocar o mover)"""
    success: bool
    captures: List[Tuple[int, int]] = field(default_factory=list)
    extra_turn: bool = False  # Si hay cadena de captura
    phase_changed: bool = False
    game_over: bool = False
    winner: Optional[int] = None
    message: str = ""

