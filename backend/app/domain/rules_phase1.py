"""
Reglas de la Fase 1: Posicionamiento
"""
from app.domain.models import GameState, Board, Phase


def can_place_piece(state: GameState, x: int, y: int, player: int) -> tuple[bool, str]:
    """
    Verifica si un jugador puede colocar una pieza en (x, y).
    
    Reglas:
    - Solo en Fase 1
    - La celda debe estar vacía
    - No se puede colocar en el refugio (2, 2)
    - Es el turno del jugador
    - Le quedan piezas por colocar en este turno
    """
    if state.phase != Phase.PLACEMENT:
        return False, "No estás en la fase de posicionamiento"
    
    if state.current_player != player:
        return False, "No es tu turno"
    
    if state.placement_remaining <= 0:
        return False, "Ya colocaste todas tus piezas este turno"
    
    if not state.board.is_valid_position(x, y):
        return False, "Posición fuera del tablero"
    
    if not state.board.is_empty(x, y):
        return False, "La celda ya está ocupada"
    
    if state.board.is_refuge(x, y):
        return False, "No se puede colocar en el refugio central"
    
    return True, "OK"


def place_piece(state: GameState, x: int, y: int, player: int):
    """
    Coloca una pieza en el tablero.
    Actualiza contadores y verifica si termina la Fase 1.
    """
    # Colocar pieza
    state.board.set(x, y, player)
    state.pieces_count[player] += 1
    state.total_pieces_placed += 1
    state.placement_remaining -= 1
    
    # Si colocó sus 2 piezas del turno, cambiar turno
    if state.placement_remaining == 0:
        state.switch_turn()
    
    # Si ya hay 24 piezas, cambiar a Fase 2
    # El jugador que colocó la última pieza mueve primero hacia el centro
    if state.total_pieces_placed >= 24:
        state.phase = Phase.MOVEMENT
        state.chain_capture_piece = None
        return True  # phase_changed
    
    return False


def get_valid_placements(state: GameState) -> list[tuple[int, int]]:
    """
    Retorna todas las posiciones válidas donde se puede colocar una pieza.
    """
    if state.phase != Phase.PLACEMENT:
        return []
    
    valid = []
    for y in range(Board.SIZE):
        for x in range(Board.SIZE):
            if state.board.is_empty(x, y) and not state.board.is_refuge(x, y):
                valid.append((x, y))
    
    return valid

