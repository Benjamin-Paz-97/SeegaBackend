"""
Reglas de Captura (Custodia)
"""
from app.domain.models import GameState, Board, CellState


def check_captures(state: GameState, x: int, y: int, player: int) -> list[tuple[int, int]]:
    """
    Verifica si el movimiento a (x, y) del jugador resulta en capturas.
    
    Regla de custodia:
    Si hay una pieza enemiga adyacente y del otro lado (en línea) hay otra pieza propia,
    la pieza enemiga es capturada.
    
    Excepción: Las piezas en el refugio (2, 2) NO pueden ser capturadas.
    
    Retorna: lista de coordenadas de piezas capturadas
    """
    captured = []
    opponent = 2 if player == 1 else 1
    
    # 4 direcciones: derecha, izquierda, abajo, arriba
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    
    for dx, dy in directions:
        enemy_x = x + dx
        enemy_y = y + dy
        support_x = x + 2 * dx
        support_y = y + 2 * dy
        
        # Verificar que ambas posiciones están dentro del tablero
        if not state.board.is_valid_position(enemy_x, enemy_y):
            continue
        if not state.board.is_valid_position(support_x, support_y):
            continue
        
        # Verificar que hay una pieza enemiga en medio
        if state.board.get(enemy_x, enemy_y) != opponent:
            continue
        
        # Verificar que NO está en el refugio (excepción)
        if state.board.is_refuge(enemy_x, enemy_y):
            continue
        
        # Verificar que hay una pieza propia del otro lado (apoyo)
        if state.board.get(support_x, support_y) == player:
            captured.append((enemy_x, enemy_y))
    
    return captured


def apply_captures(state: GameState, captures: list[tuple[int, int]]):
    """
    Aplica las capturas: elimina las piezas capturadas del tablero.
    """
    for x, y in captures:
        player = state.board.get(x, y)
        state.board.set(x, y, CellState.EMPTY)
        state.pieces_count[player] -= 1


def has_capture_chain(state: GameState, x: int, y: int, player: int) -> bool:
    """
    Verifica si desde la posición (x, y) el jugador puede realizar otra captura.
    Esto determina si hay "turno extra".
    """
    possible_moves = []
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    for dx, dy in directions:
        new_x, new_y = x + dx, y + dy
        
        if state.board.is_valid_position(new_x, new_y) and state.board.is_empty(new_x, new_y):
            possible_moves.append((new_x, new_y))
    
    # Por cada movimiento posible, verificar si resulta en captura
    for move_x, move_y in possible_moves:
        # Simular movimiento temporalmente
        state.board.set(x, y, CellState.EMPTY)
        state.board.set(move_x, move_y, player)
        
        # Verificar capturas
        captures = check_captures(state, move_x, move_y, player)
        
        # Revertir movimiento
        state.board.set(move_x, move_y, CellState.EMPTY)
        state.board.set(x, y, player)
        
        if len(captures) > 0:
            return True
    
    return False

