"""
Repositorio en memoria para almacenar partidas.
Más adelante se puede reemplazar por un repositorio con BD.
"""
from typing import Dict, Optional
from abc import ABC, abstractmethod

from app.domain.models import GameState


class GameRepository(ABC):
    """Interfaz para repositorios de partidas"""
    
    @abstractmethod
    def save(self, state: GameState) -> None:
        """Guarda o actualiza una partida"""
        pass
    
    @abstractmethod
    def get(self, game_id: str) -> Optional[GameState]:
        """Obtiene una partida por ID"""
        pass
    
    @abstractmethod
    def delete(self, game_id: str) -> None:
        """Elimina una partida"""
        pass


class InMemoryGameRepository(GameRepository):
    """
    Implementación en memoria del repositorio.
    Los datos se pierden al reiniciar el servidor.
    """
    
    def __init__(self):
        self._games: Dict[str, GameState] = {}
    
    def save(self, state: GameState) -> None:
        """Guarda o actualiza una partida en memoria"""
        self._games[state.game_id] = state
    
    def get(self, game_id: str) -> Optional[GameState]:
        """Obtiene una partida por ID"""
        return self._games.get(game_id)
    
    def delete(self, game_id: str) -> None:
        """Elimina una partida de memoria"""
        if game_id in self._games:
            del self._games[game_id]
    
    def list_all(self) -> list[GameState]:
        """Lista todas las partidas (útil para debug)"""
        return list(self._games.values())
    
    def count(self) -> int:
        """Cuenta las partidas activas"""
        return len(self._games)

