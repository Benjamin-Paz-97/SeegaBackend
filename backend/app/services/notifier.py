"""
Gestor de conexiones WebSocket para notificaciones en tiempo real
"""
from fastapi import WebSocket
from typing import Dict, List, Set
import asyncio
import json


class ConnectionManager:
    """
    Gestiona las conexiones WebSocket de los jugadores.
    Permite enviar eventos a jugadores específicos o a todos en una partida.
    """
    
    def __init__(self):
        # game_id -> {player_token -> websocket}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, game_id: str, player_token: str, websocket: WebSocket):
        """Registra una nueva conexión WebSocket"""
        await websocket.accept()
        
        if game_id not in self._connections:
            self._connections[game_id] = {}
        
        self._connections[game_id][player_token] = websocket
    
    def disconnect(self, game_id: str, player_token: str):
        """Elimina una conexión WebSocket"""
        if game_id in self._connections:
            if player_token in self._connections[game_id]:
                del self._connections[game_id][player_token]
            
            # Si no quedan conexiones en la partida, limpiar
            if len(self._connections[game_id]) == 0:
                del self._connections[game_id]
    
    async def send_to_player(self, game_id: str, player_token: str, message: dict):
        """Envía un mensaje a un jugador específico"""
        if game_id in self._connections:
            if player_token in self._connections[game_id]:
                websocket = self._connections[game_id][player_token]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Error enviando mensaje a {player_token}: {e}")
                    self.disconnect(game_id, player_token)
    
    async def broadcast_to_game(
        self, 
        game_id: str, 
        message: dict, 
        exclude_token: str = None
    ):
        """
        Envía un mensaje a todos los jugadores de una partida.
        Opcionalmente excluye un jugador (útil para no notificar al que hizo la acción).
        """
        if game_id not in self._connections:
            print(f"⚠️ No hay conexiones WebSocket para game_id: {game_id}")
            return
        
        exclude_token_short = exclude_token[:8] + "..." if exclude_token else None
        print(f"📤 Enviando evento '{message.get('type')}' a partida {game_id}")
        print(f"   Excluyendo token: {exclude_token_short}")
        print(f"   Conexiones activas: {len(self._connections[game_id])} jugadores")
        for token in self._connections[game_id].keys():
            print(f"      - {token[:8]}...")
        
        disconnected = []
        sent_count = 0
        
        for player_token, websocket in self._connections[game_id].items():
            if exclude_token and player_token == exclude_token:
                print(f"   ⏭️ Saltando jugador {player_token[:8]}... (excluido - es quien hizo la acción)")
                continue
            
            try:
                await websocket.send_json(message)
                sent_count += 1
                print(f"   ✅ Enviado a jugador {player_token[:8]}... (total enviados: {sent_count})")
            except Exception as e:
                print(f"   ❌ Error enviando mensaje a {player_token[:8]}...: {e}")
                disconnected.append(player_token)
        
        if sent_count == 0:
            print(f"   ⚠️ No se envió el evento a ningún jugador")
        
        # Limpiar conexiones fallidas
        for token in disconnected:
            self.disconnect(game_id, token)
    
    def notify_game_event(
        self, 
        game_id: str, 
        event: dict, 
        exclude_token: str = None
    ):
        """
        Versión síncrona para notificar eventos.
        Crea una tarea asíncrona para enviar el mensaje.
        """
        try:
            # Obtener el event loop actual, o crear uno nuevo si no existe
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si el loop está corriendo, crear una tarea
                asyncio.create_task(
                    self.broadcast_to_game(game_id, event, exclude_token)
                )
            else:
                # Si no está corriendo, ejecutar directamente
                loop.run_until_complete(
                    self.broadcast_to_game(game_id, event, exclude_token)
                )
        except RuntimeError:
            # Si no hay event loop, crear uno nuevo
            asyncio.run(
                self.broadcast_to_game(game_id, event, exclude_token)
            )
    
    def notify_specific_player(self, game_id: str, player_token: str, event: dict):
        """
        Versión síncrona para notificar a un jugador específico.
        """
        try:
            # Obtener el event loop actual, o crear uno nuevo si no existe
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si el loop está corriendo, crear una tarea
                asyncio.create_task(
                    self.send_to_player(game_id, player_token, event)
                )
            else:
                # Si no está corriendo, ejecutar directamente
                loop.run_until_complete(
                    self.send_to_player(game_id, player_token, event)
                )
        except RuntimeError:
            # Si no hay event loop, crear uno nuevo
            asyncio.run(
                self.send_to_player(game_id, player_token, event)
            )
    
    def get_connected_players(self, game_id: str) -> int:
        """Retorna el número de jugadores conectados a una partida"""
        if game_id in self._connections:
            return len(self._connections[game_id])
        return 0


# Instancia global (singleton)
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Obtiene la instancia global del gestor de conexiones"""
    return _connection_manager

