"""
Reglas de la Fase 2: Movimiento
"""
from app.domain.models import GameState, Board, Phase, CellState


def can_move_piece(
    state: GameState, 
    from_x: int, 
    from_y: int, 
    to_x: int, 
    to_y: int, 
    player: int
) -> tuple[bool, str]:
    """
    Verifica si un jugador puede mover una pieza.
    
    Reglas:
    - Solo en Fase 2
    - Es el turno del jugador
    - La pieza origen es del jugador
    - El destino está vacío
    - Movimiento ortogonal (1 celda)
    - Si hay cadena de captura, solo se puede mover esa pieza
    """
    if state.phase != Phase.MOVEMENT:
        return False, "No estás en la fase de movimiento"
    
    if state.current_player != player:
        return False, "No es tu turno"
    
    # Validar posiciones
    if not state.board.is_valid_position(from_x, from_y):
        return False, "Posición origen inválida"
    
    if not state.board.is_valid_position(to_x, to_y):
        return False, "Posición destino inválida"
    
    # Verificar que la pieza origen es del jugador
    if state.board.get(from_x, from_y) != player:
        return False, "No es tu pieza"
    
    # Verificar que el destino está vacío
    if not state.board.is_empty(to_x, to_y):
        return False, "El destino no está vacío"
    
    # Verificar movimiento ortogonal (1 celda)
    dx = abs(to_x - from_x)
    dy = abs(to_y - from_y)
    
    if not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
        return False, "Solo puedes mover 1 celda en dirección ortogonal"
    
    # Si hay cadena de captura, solo se puede mover esa pieza específica
    if state.chain_capture_piece is not None:
        chain_x, chain_y = state.chain_capture_piece
        if from_x != chain_x or from_y != chain_y:
            return False, f"Debes continuar moviendo la pieza en ({chain_x}, {chain_y})"
    
    return True, "OK"


def move_piece(
    state: GameState, 
    from_x: int, 
    from_y: int, 
    to_x: int, 
    to_y: int
):
    """
    Mueve una pieza en el tablero.
    No verifica reglas (eso se hace con can_move_piece antes).
    """
    player = state.board.get(from_x, from_y)
    state.board.set(from_x, from_y, CellState.EMPTY)
    state.board.set(to_x, to_y, player)


def get_valid_moves_for_piece(
    state: GameState, 
    x: int, 
    y: int
) -> list[tuple[int, int]]:
    """
    Retorna todas las posiciones válidas a las que puede moverse una pieza.
    """
    if state.phase != Phase.MOVEMENT:
        return []
    
    player = state.board.get(x, y)
    if player == CellState.EMPTY:
        return []
    
    valid_moves = []
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # arriba, abajo, derecha, izquierda
    
    for dx, dy in directions:
        new_x, new_y = x + dx, y + dy
        
        if state.board.is_valid_position(new_x, new_y) and state.board.is_empty(new_x, new_y):
            valid_moves.append((new_x, new_y))
    
    return valid_moves


def get_all_valid_moves(state: GameState, player: int) -> dict:
    """
    Retorna todos los movimientos válidos para un jugador.
    Formato: {(from_x, from_y): [(to_x, to_y), ...]}
    """
    if state.phase != Phase.MOVEMENT:
        return {}
    
    # Si hay cadena de captura, solo esa pieza puede moverse
    if state.chain_capture_piece is not None:
        x, y = state.chain_capture_piece
        moves = get_valid_moves_for_piece(state, x, y)
        return {(x, y): moves} if moves else {}
    
    # Buscar todas las piezas del jugador
    all_moves = {}
    for y in range(Board.SIZE):
        for x in range(Board.SIZE):
            if state.board.get(x, y) == player:
                moves = get_valid_moves_for_piece(state, x, y)
                if moves:
                    all_moves[(x, y)] = moves
    
    return all_moves

