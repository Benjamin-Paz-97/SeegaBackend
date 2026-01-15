"""
Servicio principal del juego: orquesta todas las reglas
"""
import uuid
import asyncio
import random
from fastapi import HTTPException

from app.domain.models import (
    GameState, Board, Phase, GameStatus, PlayerSession, MoveResult
)
from app.domain import rules_phase1, rules_phase2, rules_capture, rules_victory
from app.services.repo_memory import GameRepository
from app.services.notifier import get_connection_manager


class GameService:
    """
    Servicio que orquesta la lógica del juego.
    Valida reglas, aplica acciones y notifica a los jugadores.
    """
    
    def __init__(self, repository: GameRepository):
        self.repo = repository
        self.notifier = get_connection_manager()
    
    def create_game(self) -> dict:
        """
        Crea una nueva partida.
        Retorna: gameId, playerToken, playerNumber
        """
        game_id = self._generate_game_id()
        player_token = self._generate_token()
        
        # Crear estado inicial
        state = GameState(
            game_id=game_id,
            board=Board(),
            phase=Phase.PLACEMENT,
            status=GameStatus.WAITING,
            current_player=1,
            player1=PlayerSession(player_number=1, token=player_token),
            player2=None,
            pieces_count={1: 0, 2: 0},
            placement_remaining=2,
            total_pieces_placed=0
        )
        
        self.repo.save(state)
        
        return {
            "gameId": game_id,
            "playerToken": player_token,
            "playerNumber": 1,
            "status": GameStatus.WAITING
        }
    
    def join_game(self, game_id: str, existing_token: str = None) -> dict:
        """
        El jugador 2 se une a una partida existente.
        Si se proporciona un token válido, permite reconectar.
        """
        state = self.repo.get(game_id)
        if not state:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        # Si hay un token, verificar si es válido para reconexión
        if existing_token:
            if state.player1 and state.player1.token == existing_token:
                return {
                    "gameId": game_id,
                    "playerToken": existing_token,
                    "playerNumber": 1,
                    "status": state.status.value
                }
            if state.player2 and state.player2.token == existing_token:
                return {
                    "gameId": game_id,
                    "playerToken": existing_token,
                    "playerNumber": 2,
                    "status": state.status.value
                }
        
        # Si la partida ya está llena y no es reconexión
        if state.status != GameStatus.WAITING:
            # Si el jugador 2 ya existe pero no tiene token guardado, permitir reconexión
            # Esto maneja el caso donde el primer intento funcionó pero hubo error de red
            if state.player2 and not existing_token:
                # El jugador 2 ya existe, devolver su información para reconexión
                return {
                    "gameId": game_id,
                    "playerToken": state.player2.token,
                    "playerNumber": 2,
                    "status": state.status.value
                }
            raise HTTPException(status_code=400, detail="La partida ya está llena o terminada")
        
        # Nuevo jugador 2
        player_token = self._generate_token()
        state.player2 = PlayerSession(player_number=2, token=player_token)
        state.status = GameStatus.PLAYING
        
        # Seleccionar jugador inicial aleatoriamente (1 o 2)
        state.current_player = random.choice([1, 2])
        
        self.repo.save(state)
        
        # Notificar al jugador 1 que el rival se unió
        self.notifier.notify_game_event(
            game_id,
            {"type": "opponent_joined", "message": "Tu oponente se unió"},
            exclude_token=player_token
        )
        
        # Notificar que la partida comenzó a TODOS (sin excluir)
        # Esperar un momento para que el jugador 2 se conecte por WebSocket
        # Aumentar el delay para asegurar que ambos WebSockets estén conectados
        asyncio.create_task(self._notify_game_started_delayed(game_id, state))
        
        return {
            "gameId": game_id,
            "playerToken": player_token,
            "playerNumber": 2,
            "status": GameStatus.PLAYING
        }
    
    def reconnect_game(self, game_id: str, player_token: str) -> dict:
        """
        Permite a un jugador reconectarse a una partida existente.
        """
        state = self.repo.get(game_id)
        if not state:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        # Verificar que el token pertenece a alguno de los jugadores
        player_num = None
        if state.player1 and state.player1.token == player_token:
            player_num = 1
        elif state.player2 and state.player2.token == player_token:
            player_num = 2
        
        if not player_num:
            raise HTTPException(status_code=403, detail="Token inválido para esta partida")
        
        return {
            "gameId": game_id,
            "playerToken": player_token,
            "playerNumber": player_num,
            "status": state.status.value
        }
    
    def get_game_state(self, game_id: str, player_token: str) -> dict:
        """
        Obtiene el estado actual del juego para un jugador.
        """
        state = self._get_and_validate_game(game_id, player_token)
        player_num = self._get_player_number(state, player_token)
        
        return self._serialize_state(state, player_num)
    
    def place_piece(self, game_id: str, player_token: str, x: int, y: int) -> dict:
        """
        Coloca una pieza en la Fase 1.
        """
        state = self._get_and_validate_game(game_id, player_token)
        player_num = self._get_player_number(state, player_token)
        
        # Validar reglas
        can_place, message = rules_phase1.can_place_piece(state, x, y, player_num)
        if not can_place:
            raise HTTPException(status_code=400, detail=message)
        
        # Aplicar acción
        phase_changed = rules_phase1.place_piece(state, x, y, player_num)
        
        result = MoveResult(
            success=True,
            phase_changed=phase_changed,
            message="Pieza colocada exitosamente"
        )
        
        self.repo.save(state)
        
        # Notificar al oponente
        print(f"🎯 Jugador {player_num} colocó pieza en ({x}, {y})")
        print(f"   Notificando al oponente...")
        self._notify_opponent_action(
            game_id, 
            player_token, 
            "opponent_placed", 
            {"x": x, "y": y, "player": player_num}
        )
        print(f"   ✅ Notificación enviada")
        
        # Verificar si hay cambio de turno y si el nuevo jugador tiene movimientos
        if not result.phase_changed:
            # Verificar si cambió el turno (cuando placement_remaining == 0)
            # El turno ya cambió en rules_phase1.place_piece si placement_remaining == 0
            # Notificar al nuevo jugador que es su turno
            opponent_token = self._get_opponent_token(state, player_token)
            if opponent_token and state.current_player != player_num:
                # El turno cambió, notificar al oponente que es su turno
                self.notifier.notify_specific_player(
                    game_id,
                    opponent_token,
                    {"type": "your_turn"}
                )
            
            # Verificar si el nuevo jugador tiene movimientos (victoria por bloqueo)
            has_winner, winner, reason = rules_victory.check_victory(state)
            if has_winner:
                result.game_over = True
                result.winner = winner
                result.message = reason
                state.winner = winner
                state.game_over = True
                state.status = GameStatus.FINISHED
                self.repo.save(state)
                
                # Notificar fin de partida
                self.notifier.notify_game_event(
                    game_id,
                    {
                        "type": "game_over",
                        "winner": winner,
                        "reason": reason
                    }
                )
        
        if phase_changed:
            self.notifier.notify_game_event(
                game_id,
                {"type": "phase_changed", "phase": "movement"}
            )
        
        return {
            "state": self._serialize_state(state, player_num),
            "result": self._serialize_result(result)
        }
    
    def move_piece(
        self, 
        game_id: str, 
        player_token: str, 
        from_x: int, 
        from_y: int, 
        to_x: int, 
        to_y: int
    ) -> dict:
        """
        Mueve una pieza en la Fase 2.
        Aplica capturas y verifica victoria.
        """
        state = self._get_and_validate_game(game_id, player_token)
        player_num = self._get_player_number(state, player_token)
        
        # Validar reglas
        can_move, message = rules_phase2.can_move_piece(
            state, from_x, from_y, to_x, to_y, player_num
        )
        if not can_move:
            raise HTTPException(status_code=400, detail=message)
        
        # Aplicar movimiento
        rules_phase2.move_piece(state, from_x, from_y, to_x, to_y)
        
        # Verificar capturas
        captures = rules_capture.check_captures(state, to_x, to_y, player_num)
        
        result = MoveResult(success=True, captures=captures)
        
        if len(captures) > 0:
            # Aplicar capturas
            rules_capture.apply_captures(state, captures)
            
            # Verificar si hay cadena de captura posible
            has_chain = rules_capture.has_capture_chain(state, to_x, to_y, player_num)
            
            if has_chain:
                # Turno extra: debe mover la misma pieza
                result.extra_turn = True
                state.chain_capture_piece = (to_x, to_y)
            else:
                # No hay más capturas posibles, cambiar turno
                state.chain_capture_piece = None
                state.switch_turn()
        else:
            # Sin capturas, cambiar turno
            state.chain_capture_piece = None
            state.switch_turn()
        
        # Verificar victoria
        has_winner, winner, reason = rules_victory.check_victory(state)
        if has_winner:
            result.game_over = True
            result.winner = winner
            result.message = reason
            state.winner = winner
            state.game_over = True
            state.status = GameStatus.FINISHED
        
        self.repo.save(state)
        
        # Notificar al oponente
        self._notify_opponent_action(
            game_id,
            player_token,
            "opponent_moved",
            {
                "from": {"x": from_x, "y": from_y},
                "to": {"x": to_x, "y": to_y},
                "captures": [{"x": cx, "y": cy} for cx, cy in captures],
                "extraTurn": result.extra_turn
            }
        )
        
        if result.game_over:
            self.notifier.notify_game_event(
                game_id,
                {
                    "type": "game_over",
                    "winner": winner,
                    "reason": reason
                }
            )
        elif not result.extra_turn:
            # Cambiar turno y verificar si el nuevo jugador tiene movimientos
            # Verificar victoria después de cambiar turno (por si el nuevo jugador está bloqueado)
            has_winner, winner, reason = rules_victory.check_victory(state)
            if has_winner:
                result.game_over = True
                result.winner = winner
                result.message = reason
                state.winner = winner
                state.game_over = True
                state.status = GameStatus.FINISHED
                self.repo.save(state)
                
                # Notificar fin de partida
                self.notifier.notify_game_event(
                    game_id,
                    {
                        "type": "game_over",
                        "winner": winner,
                        "reason": reason
                    }
                )
            else:
                # Notificar al oponente que es su turno
                opponent_token = self._get_opponent_token(state, player_token)
                self.notifier.notify_specific_player(
                    game_id,
                    opponent_token,
                    {"type": "your_turn"}
                )
        
        return {
            "state": self._serialize_state(state, player_num),
            "result": self._serialize_result(result)
        }
    
    def get_valid_actions(self, game_id: str, player_token: str) -> dict:
        """
        Retorna las acciones válidas para el jugador actual.
        """
        state = self._get_and_validate_game(game_id, player_token)
        player_num = self._get_player_number(state, player_token)
        
        if state.current_player != player_num:
            return {"canAct": False, "reason": "No es tu turno"}
        
        if state.phase == Phase.PLACEMENT:
            placements = rules_phase1.get_valid_placements(state)
            return {
                "canAct": True,
                "phase": "placement",
                "validPlacements": [{"x": x, "y": y} for x, y in placements],
                "remaining": state.placement_remaining
            }
        else:
            moves = rules_phase2.get_all_valid_moves(state, player_num)
            return {
                "canAct": True,
                "phase": "movement",
                "validMoves": {
                    f"{fx},{fy}": [{"x": tx, "y": ty} for tx, ty in targets]
                    for (fx, fy), targets in moves.items()
                },
                "chainCapture": state.chain_capture_piece
            }
    
    # Métodos auxiliares
    
    def _generate_game_id(self) -> str:
        """Genera un ID único para la partida (código corto)"""
        return uuid.uuid4().hex[:8].upper()
    
    def _generate_token(self) -> str:
        """Genera un token único para un jugador"""
        return uuid.uuid4().hex
    
    def _get_and_validate_game(self, game_id: str, player_token: str) -> GameState:
        """Obtiene y valida que el juego existe y el token es válido"""
        state = self.repo.get(game_id)
        if not state:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        # Validar que el token pertenece a alguno de los jugadores
        if state.player1 and state.player1.token == player_token:
            return state
        if state.player2 and state.player2.token == player_token:
            return state
        
        raise HTTPException(status_code=403, detail="Token inválido")
    
    def _get_player_number(self, state: GameState, player_token: str) -> int:
        """Obtiene el número de jugador (1 o 2) a partir del token"""
        if state.player1 and state.player1.token == player_token:
            return 1
        if state.player2 and state.player2.token == player_token:
            return 2
        raise HTTPException(status_code=403, detail="Token inválido")
    
    def _get_opponent_token(self, state: GameState, player_token: str) -> str:
        """Obtiene el token del oponente"""
        if state.player1 and state.player1.token == player_token:
            return state.player2.token if state.player2 else None
        elif state.player2 and state.player2.token == player_token:
            return state.player1.token if state.player1 else None
        return None
    
    def _serialize_state(self, state: GameState, player_num: int) -> dict:
        """Convierte el estado a formato JSON para enviar al cliente"""
        return {
            "gameId": state.game_id,
            "board": state.board.to_list(),
            "phase": state.phase.value,
            "status": state.status.value,
            "currentPlayer": state.current_player,
            "yourPlayerNumber": player_num,
            "isYourTurn": state.current_player == player_num,
            "piecesCount": state.pieces_count,
            "placementRemaining": state.placement_remaining,
            "chainCapturePiece": state.chain_capture_piece,
            "winner": state.winner,
            "gameOver": state.game_over
        }
    
    def _serialize_result(self, result: MoveResult) -> dict:
        """Convierte el resultado a formato JSON"""
        return {
            "success": result.success,
            "captures": [{"x": x, "y": y} for x, y in result.captures],
            "extraTurn": result.extra_turn,
            "phaseChanged": result.phase_changed,
            "gameOver": result.game_over,
            "winner": result.winner,
            "message": result.message
        }
    
    def _notify_opponent_action(
        self, 
        game_id: str, 
        player_token: str, 
        event_type: str, 
        data: dict
    ):
        """Notifica al oponente sobre una acción"""
        event_data = {
            "type": event_type,
            **data
        }
        print(f"📤 _notify_opponent_action: game_id={game_id}, event_type={event_type}, exclude_token={player_token[:8]}...")
        self.notifier.notify_game_event(
            game_id,
            event_data,
            exclude_token=player_token
        )
    
    def leave_game(self, game_id: str, player_token: str) -> dict:
        """
        Un jugador abandona la partida.
        Si ambos jugadores abandonan, la partida se elimina.
        """
        state = self.repo.get(game_id)
        if not state:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        # Identificar qué jugador está abandonando y obtener token del oponente ANTES de eliminarlo
        opponent_token = None
        if state.player1 and state.player1.token == player_token:
            # Jugador 1 abandona
            opponent_token = state.player2.token if state.player2 else None
            state.player1 = None
        elif state.player2 and state.player2.token == player_token:
            # Jugador 2 abandona
            opponent_token = state.player1.token if state.player1 else None
            state.player2 = None
        else:
            raise HTTPException(status_code=403, detail="Token inválido")
        
        # Notificar al oponente (si existe)
        if opponent_token:
            self.notifier.notify_specific_player(
                game_id,
                opponent_token,
                {
                    "type": "opponent_left",
                    "message": "Tu oponente abandonó la partida"
                }
            )
        
        # Verificar si ambos jugadores abandonaron
        if state.player1 is None and state.player2 is None:
            # Eliminar la partida
            self.repo.delete(game_id)
            return {
                "message": "Partida eliminada (ambos jugadores abandonaron)",
                "gameDeleted": True
            }
        else:
            # Solo un jugador abandonó, marcar como terminada
            state.status = GameStatus.FINISHED
            state.game_over = True
            # El jugador que quedó gana por abandono
            if state.player1:
                state.winner = 1
            elif state.player2:
                state.winner = 2
            self.repo.save(state)
            
            # Notificar al jugador que quedó que ganó
            if opponent_token:
                self.notifier.notify_specific_player(
                    game_id,
                    opponent_token,
                    {
                        "type": "game_over",
                        "winner": state.winner,
                        "reason": "Tu oponente abandonó la partida"
                    }
                )
            
            return {
                "message": "Has abandonado la partida",
                "gameDeleted": False
            }
    
    def rematch_game(self, game_id: str, player_token: str) -> dict:
        """
        Solicita un rematch. Si ambos jugadores solicitan rematch, se resetea el juego.
        """
        state = self.repo.get(game_id)
        if not state:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        # Verificar que el juego haya terminado
        if not state.game_over:
            raise HTTPException(status_code=400, detail="El juego aún no ha terminado")
        
        # Identificar qué jugador está solicitando rematch
        player_num = None
        if state.player1 and state.player1.token == player_token:
            player_num = 1
        elif state.player2 and state.player2.token == player_token:
            player_num = 2
        else:
            raise HTTPException(status_code=403, detail="Token inválido")
        
        # Marcar que este jugador quiere rematch
        if not hasattr(state, 'rematch_requests'):
            state.rematch_requests = set()
        state.rematch_requests.add(player_num)
        
        # Verificar si ambos jugadores quieren rematch
        if len(state.rematch_requests) >= 2:
            # Resetear el juego
            state.board = Board()
            state.phase = Phase.PLACEMENT
            state.status = GameStatus.PLAYING
            state.current_player = random.choice([1, 2])
            state.pieces_count = {1: 0, 2: 0}
            state.placement_remaining = 2
            state.total_pieces_placed = 0
            state.winner = None
            state.game_over = False
            state.chain_capture_piece = None
            state.rematch_requests = set()
            
            self.repo.save(state)
            
            # Notificar a ambos jugadores que el rematch comenzó
            self.notifier.notify_game_event(
                game_id,
                {
                    "type": "rematch_started",
                    "phase": "placement",
                    "currentPlayer": state.current_player
                }
            )
            
            return {
                "message": "Rematch iniciado",
                "rematchStarted": True,
                "currentPlayer": state.current_player
            }
        else:
            # Solo un jugador quiere rematch, notificar al oponente
            opponent_num = 2 if player_num == 1 else 1
            opponent_token = state.player1.token if opponent_num == 1 else state.player2.token
            
            self.notifier.notify_specific_player(
                game_id,
                opponent_token,
                {
                    "type": "rematch_requested",
                    "message": "Tu oponente quiere jugar de nuevo"
                }
            )
            
            self.repo.save(state)
            
            return {
                "message": "Esperando confirmación del oponente",
                "rematchStarted": False
            }
    
    async def _notify_game_started_delayed(self, game_id: str, state: GameState):
        """Notifica game_started con un pequeño delay para asegurar conexiones WebSocket"""
        # Esperar un poco más para asegurar que ambos WebSockets estén conectados
        await asyncio.sleep(0.8)  # Esperar 800ms para que ambos se conecten
        
        # Verificar que el estado sigue siendo PLAYING antes de enviar
        current_state = self.repo.get(game_id)
        if current_state and current_state.status == GameStatus.PLAYING:
            self.notifier.notify_game_event(
                game_id,
                {
                    "type": "game_started",
                    "phase": current_state.phase.value,
                    "currentPlayer": current_state.current_player
                }
            )

