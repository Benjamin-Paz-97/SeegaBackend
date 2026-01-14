"""
Rutas WebSocket para notificaciones en tiempo real
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json

from app.services.notifier import get_connection_manager
from app.services.repo_memory import InMemoryGameRepository
from app.domain.models import GameStatus
import asyncio

router = APIRouter()

# Usar la instancia global del gestor de conexiones (mismo que usa game_service)
connection_manager = get_connection_manager()
game_repo = InMemoryGameRepository()


@router.websocket("/games/{game_id}/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...)
):
    """
    Conecta un jugador vía WebSocket para recibir eventos en tiempo real.
    
    Eventos que el servidor puede enviar:
    - game_started: La partida comenzó (ambos jugadores conectados)
    - opponent_joined: El rival se unió
    - opponent_placed: El rival colocó una pieza
    - opponent_moved: El rival movió una pieza
    - your_turn: Es tu turno
    - phase_changed: Cambió de fase (1 -> 2)
    - game_over: La partida terminó
    - opponent_disconnected: El rival se desconectó
    """
    await connection_manager.connect(game_id, token, websocket)
    
    try:
        # Enviar confirmación de conexión
        await websocket.send_json({
            "type": "connected",
            "message": "Conectado al juego exitosamente"
        })
        
        # Verificar si el juego ya está en PLAYING y ambos jugadores están conectados
        game_state = game_repo.get(game_id)
        if game_state and game_state.status == GameStatus.PLAYING:
            connected_count = connection_manager.get_connected_players(game_id)
            if connected_count >= 2:
                # Ambos jugadores conectados, enviar game_started a TODOS
                # Pequeño delay para asegurar que ambos WebSockets estén listos
                await asyncio.sleep(0.1)
                await connection_manager.broadcast_to_game(
                    game_id,
                    {
                        "type": "game_started",
                        "phase": game_state.phase.value,
                        "currentPlayer": game_state.current_player
                    }
                )
        
        # Mantener la conexión abierta y escuchar mensajes del cliente
        # Usar timeout para evitar que se quede bloqueado indefinidamente
        while True:
            try:
                # Esperar mensajes con timeout de 30 segundos
                # Si no hay mensajes, simplemente continuar el bucle
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                # Procesar mensajes del cliente si los hay (ping/pong, etc.)
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        # Responder con pong para mantener la conexión viva
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    # Ignorar mensajes que no sean JSON válido
                    pass
            except asyncio.TimeoutError:
                # Timeout: enviar ping para mantener la conexión viva
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # Si falla al enviar ping, la conexión probablemente se cerró
                    break
            except Exception as e:
                # Cualquier otro error, cerrar la conexión
                print(f"Error en WebSocket para {token[:8]}...: {e}")
                break
            
    except WebSocketDisconnect:
        print(f"🔌 WebSocket desconectado para {token[:8]}... (WebSocketDisconnect)")
        connection_manager.disconnect(game_id, token)
        # No notificar desconexión inmediatamente - puede ser solo un recarga
        # El jugador puede reconectarse rápidamente
    except Exception as e:
        print(f"❌ Error inesperado en WebSocket para {token[:8]}...: {e}")
        connection_manager.disconnect(game_id, token)

