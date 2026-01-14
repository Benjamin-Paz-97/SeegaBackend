"""
Reglas de Victoria y Fin de Partida
"""
from app.domain.models import GameState, Phase
from app.domain.rules_phase2 import get_all_valid_moves


def check_victory(state: GameState) -> tuple[bool, int | None, str]:
    """
    Verifica las condiciones de victoria.
    
    Condiciones:
    1. Un jugador tiene menos de 2 piezas → pierde
    2. Un jugador no tiene movimientos legales (bloqueo) → pierde
       (gana quien tenga más piezas; empate si iguales)
    
    Retorna: (hay_ganador, número_ganador, razón)
    """
    # Solo verificar en Fase 2
    if state.phase != Phase.MOVEMENT:
        return False, None, ""
    
    p1_pieces = state.pieces_count[1]
    p2_pieces = state.pieces_count[2]
    
    # Condición 1: Menos de 2 piezas
    if p1_pieces < 2:
        return True, 2, "Jugador 1 tiene menos de 2 piezas"
    
    if p2_pieces < 2:
        return True, 1, "Jugador 2 tiene menos de 2 piezas"
    
    # Condición 2: Sin movimientos legales (bloqueo)
    current_moves = get_all_valid_moves(state, state.current_player)
    
    if len(current_moves) == 0:
        # El jugador actual no puede mover → pierde
        # Gana quien tenga más piezas
        if p1_pieces > p2_pieces:
            return True, 1, "Jugador 2 bloqueado, Jugador 1 tiene más piezas"
        elif p2_pieces > p1_pieces:
            return True, 2, "Jugador 1 bloqueado, Jugador 2 tiene más piezas"
        else:
            # Empate: arbitrariamente gana el que no está bloqueado
            winner = 2 if state.current_player == 1 else 1
            return True, winner, f"Jugador {state.current_player} bloqueado, empate en piezas"
    
    return False, None, ""


def is_stalemate(state: GameState, player: int) -> bool:
    """
    Verifica si un jugador está en bloqueo (sin movimientos posibles).
    """
    if state.phase != Phase.MOVEMENT:
        return False
    
    moves = get_all_valid_moves(state, player)
    return len(moves) == 0

