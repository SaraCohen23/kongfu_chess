"""
Chess Game Server

Handles WebSocket connections and manages game state between two clients.

Architecture:
- Server is the authoritative source for game state
- Validates all moves using Game.py logic
- Broadcasts game state updates to all clients
- Supports real-time gameplay with no turn restrictions
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from GameFactory import create_game
from GraphicsFactory import ImgFactory
from Game import Game
from server_game import ServerGame
from Command import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pieces_path():
    """Get the path to pieces directory - shared function used by both client and server"""
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(current_dir), "pieces")

class PlayerColor(Enum):
    WHITE = "white"
    BLACK = "black"

@dataclass
class GameState:
    """Represents the current state of the game that can be serialized to JSON"""
    pieces: List[Dict]
    current_turn: str
    game_status: str
    winner: Optional[str] = None
    board_state: Optional[Dict] = None

@dataclass
class ClientConnection:
    websocket: websockets.WebSocketServerProtocol
    player_id: str
    color: PlayerColor

class ChessGameServer:
    """WebSocket chess game server managing multiple clients
    
    This server:
    - Accepts WebSocket connections from chess clients
    - Validates moves using ServerGame
    - Maintains authoritative game state
    - Broadcasts updates to all connected clients
    - Supports real-time gameplay without turn restrictions
    """
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, ClientConnection] = {}
        self.game: Optional[Game] = None
        self.current_turn = PlayerColor.WHITE
        self.game_status = "waiting"  # "waiting", "playing", "finished"
        
    async def start_server(self):
        logger.info(f"Starting Chess Game Server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("Server is running. Waiting for clients...")
            await asyncio.Future()
    
    async def handle_client(self, websocket, path=None):
        client_id = f"player_{len(self.clients) + 1}"
        logger.info(f"New client connected: {client_id}")
        
        if len(self.clients) == 0:
            color = PlayerColor.WHITE
        elif len(self.clients) == 1:
            color = PlayerColor.BLACK
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Game is full. Only 2 players allowed."
            }))
            await websocket.close()
            return
            
        self.clients[client_id] = ClientConnection(websocket, client_id, color)
        
        await self.send_to_client(client_id, {
            "type": "welcome",
            "player_id": client_id,
            "color": color.value,
            "message": f"Welcome! You are playing as {color.value}"
        })
        
        if len(self.clients) == 2:
            await self.start_game()
            
        try:
            async for message in websocket:
                await self.handle_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Removed client {client_id}")
                if self.game_status == "playing" and len(self.clients) > 0:
                    await self.broadcast({
                        "type": "player_disconnected",
                        "message": "Other player disconnected. Game paused."
                    })
                    self.game_status = "waiting"
    
    async def handle_message(self, client_id: str, message: str):
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            logger.info(f"Received from {client_id}: {data}")
            
            if message_type in ["move", "capture"]:
                await self.handle_move(client_id, data)
            elif message_type == "get_state":
                await self.send_game_state(client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {client_id}: {message}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_to_client(client_id, {
                "type": "error", 
                "message": "Server error processing message"
            })
    
    async def handle_move(self, client_id: str, data: Dict):
        if self.game_status != "playing":
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Game is not in progress"
            })
            return
            
        client = self.clients[client_id]
        from_pos = tuple(data.get("from", []))
        to_pos = tuple(data.get("to", []))
        piece_id = data.get("piece_id")
        
        if not from_pos or not to_pos or not piece_id:
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Invalid move data. Need from, to, and piece_id"
            })
            return
            
        if not self.piece_belongs_to_player(piece_id, client.color):
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "You can only move your own pieces"
            })
            return
            
        try:
            target_piece = None
            if self.game and to_pos in self.game.pos:
                pieces_at_dest = self.game.pos.get(to_pos, [])
                for piece in pieces_at_dest:
                    if not self.piece_belongs_to_player(piece.id, client.color):
                        target_piece = piece
                        break
            
            success = await self.execute_move(piece_id, from_pos, to_pos)
            if success:
                captured_piece = None
                if target_piece and target_piece not in self.game.pieces:
                    captured_piece = target_piece.id
                
                move_info = {
                    "type": "move_executed",
                    "piece_id": piece_id,
                    "from": list(from_pos),
                    "to": list(to_pos),
                    "player": client.color.value
                }
                
                if captured_piece:
                    move_info["captured"] = captured_piece
                    move_info["type"] = "capture_executed"
                
                await self.broadcast(move_info)
                await self.broadcast_game_state()
                await self.check_game_end()
            else:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid move"
                })
        except Exception as e:
            logger.error(f"Error executing move: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Error executing move"
            })
    
    async def execute_move(self, piece_id: str, from_pos: tuple, to_pos: tuple) -> bool:
        if not self.game:
            return False
        try:
            return self.game.execute_move(piece_id, from_pos, to_pos)
        except Exception as e:
            logger.error(f"Error in execute_move: {e}")
            return False
    
    def piece_belongs_to_player(self, piece_id: str, player_color: PlayerColor) -> bool:
        if not self.game or not piece_id:
            return False
        piece_side = self.game._side_of(piece_id)
        if player_color == PlayerColor.WHITE:
            return piece_side == 'W'
        elif player_color == PlayerColor.BLACK:
            return piece_side == 'B'
        return False
    
    async def start_game(self):
        logger.info("Starting new game with 2 players")
        try:
            pieces_path = get_pieces_path()
            original_game = create_game(pieces_path, ImgFactory())
            self.game = ServerGame(
                pieces=original_game.pieces,
                board=original_game.board,
                pieces_root=original_game.pieces_root,
                img_factory=original_game.img_factory
            )
            self.game_status = "playing"
            self.current_turn = PlayerColor.WHITE
            await self.broadcast({
                "type": "game_started",
                "message": "Real-time chess game started! Both players can move anytime - no turns!"
            })
            await self.broadcast_game_state()
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            await self.broadcast({
                "type": "error",
                "message": "Failed to start game"
            })
    
    async def send_to_client(self, client_id: str, data: Dict):
        if client_id in self.clients:
            try:
                await self.clients[client_id].websocket.send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Failed to send to {client_id}: connection closed")
    
    async def broadcast(self, data: Dict):
        if self.clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.websocket.send(message) for client in self.clients.values()],
                return_exceptions=True
            )
    
    async def send_game_state(self, client_id: str):
        state = self.get_game_state()
        await self.send_to_client(client_id, {
            "type": "game_state",
            "state": asdict(state)
        })
    
    async def broadcast_game_state(self):
        state = self.get_game_state()
        await self.broadcast({
            "type": "game_state",
            "state": asdict(state)
        })
    
    def get_game_state(self) -> GameState:
        pieces_data = []
        if self.game:
            game_state_dict = self.game.get_game_state_dict()
            pieces_data = game_state_dict.get("pieces", [])
        
        return GameState(
            pieces=pieces_data,
            current_turn=self.current_turn.value,
            game_status=self.game_status,
            winner=None
        )
    
    async def check_game_end(self):
        pass

async def main():
    server = ChessGameServer()
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())
