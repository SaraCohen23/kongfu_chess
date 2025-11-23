"""
Fixed Chess Game Client with Graphics

This client connects to a chess server via WebSocket and displays the game using the original Game.py graphics.

Architecture Overview:
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Client        │◄───────────────►│   Server        │
│  (fixed_client) │                 │   (server.py)   │
│                 │                 │                 │
│ • Game.py loop  │                 │ • ServerGame    │
│ • Graphics      │                 │ • Validation    │
│ • User Input    │                 │ • Authority     │
│ • Sound         │                 │                 │
└─────────────────┘                 └─────────────────┘

Code Reuse Strategy:
- Client: Uses Game.py directly for all game logic
- Server: Uses ServerGame (extends Game.py) for validation
- No duplicate game mechanics
- Shared utility functions

Flow:
1. User makes move in client
2. Client sends move to server
3. Server validates using Game.py logic
4. Server broadcasts result to all clients
5. Clients update display

Architecture:
- Client handles display and user input locally
- Server validates moves and maintains authoritative game state
- All moves are sent to server for validation
"""

import asyncio
import websockets
import json
import logging
import threading
import time
import queue
import time
import os
import cv2
from typing import Dict, List, Optional, Tuple

# Import existing game components
from GameFactory import create_game
from GraphicsFactory import ImgFactory
from events.event_manager import EventType, Event

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pieces_path():
    """Get the path to pieces directory - no duplicate code!
    
    Returns:
        str: Path to pieces directory 
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(current_dir), "pieces")

class FixedChessClient:
    """Chess game client with WebSocket communication and full graphics"""
    def __init__(self, server_url="ws://localhost:8765"):
        self.server_url = server_url
        self.websocket = None
        self.player_id = None
        self.player_color = None
        self.current_turn = "white"
        self.game_status = "waiting"
        
        # Game components
        self.game = None
        self.should_exit = False
        
        # Initialize the game display
        self.init_game()
        
    def init_game(self):
        """Initialize the game display using existing components"""
        try:
            pieces_path = get_pieces_path()
            logger.info(f"Initializing game with pieces path: {pieces_path}")
            
            # Create the full game with graphics
            self.game = create_game(pieces_path, ImgFactory())
            
            # Subscribe to events
            self.game.event_manager.subscribe(EventType.PIECE_MOVED, self._on_piece_moved)
            self.game.event_manager.subscribe(EventType.PIECE_CAPTURED, self._on_piece_captured)
            
            self.game.should_exit = False
            
            logger.info("Game display components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize game display: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def connect(self):
        """Connect to the chess server"""
        try:
            logger.info(f"Connecting to server at {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            logger.info("Connected to server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")
    
    async def send_message(self, data):
        """Send a message to the server"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(data))
                logger.debug(f"Sent to server: {data}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
    
    async def listen_for_messages(self):
        """Listen for messages from the server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_server_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to server lost")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
    
    async def handle_server_message(self, data):
        """Handle messages received from the server"""
        message_type = data.get("type")
        logger.info(f"Received from server: {data}")
        
        if message_type == "welcome":
            self.player_id = data.get("player_id")
            self.player_color = data.get("color")
            logger.info(f"Assigned as {self.player_color} player")
            
        elif message_type == "game_started":
            logger.info("Game has started!")
            await self.request_game_state()
            
        elif message_type == "game_state":
            self.update_game_state(data.get("state", {}))
            
        elif message_type == "move_executed":
            self.track_move(data)
            
        elif message_type == "capture_executed":
            logger.info(f"Capture executed: {data.get('piece_id')} captured {data.get('captured')}")
            self.track_move(data)
            self.track_capture(data)
            
        elif message_type == "error":
            logger.error(f"Server error: {data.get('message')}")
            
        elif message_type == "player_disconnected":
            logger.warning("Other player disconnected")
    
    def update_game_state(self, state):
        """Update local game state based on server data"""
        try:
            self.current_turn = state.get("current_turn", "white")
            self.game_status = state.get("game_status", "waiting")
            
            logger.info(f"Game state updated. Current turn: {self.current_turn}")
            logger.info(f"Game status: {self.game_status}")
            
        except Exception as e:
            logger.error(f"Error updating game state: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def request_game_state(self):
        """Request current game state from server"""
        await self.send_message({"type": "get_state"})
    
    async def send_move(self, piece_id, from_pos, to_pos):
        """Send a move request to the server"""
        target_pieces = self.game.pos.get(to_pos, [])
        target_piece = target_pieces[0] if target_pieces else None
        move_type = "move"
        
        if target_piece:
            piece_side = self.game._side_of(piece_id)
            target_side = self.game._side_of(target_piece.id)
            if piece_side != target_side:
                move_type = "capture"
                logger.info(f"Detected capture move: {piece_id} will capture {target_piece.id}")
        
        move_data = {
            "type": move_type,
            "piece_id": str(piece_id),
            "from": list(from_pos),
            "to": list(to_pos)
        }
        
        if move_type == "capture" and target_piece:
            move_data["captured_piece"] = target_piece.id
        
        await self.send_message(move_data)
        logger.info(f"Sent {move_type} to server: {piece_id} from {from_pos} to {to_pos}")
    
    def draw_game(self):
        """Draw game (stub)"""
        pass

    def _draw_player_cursor_only(self):
        """Draw only the current player's cursor"""
        if not self.game or not self.player_color:
            return
            
        player_num = 1 if self.player_color == "white" else 2
        
        if player_num == 1 and self.game.kp1:
            kp = self.game.kp1
            last_attr = 'last_cursor1'
        elif player_num == 2 and self.game.kp2:
            kp = self.game.kp2
            last_attr = 'last_cursor2'
        else:
            return
            
        r, c = kp.get_cursor()
        
        y1 = r * self.game.board.cell_H_pix + self.game.board.board_offset_y
        x1 = c * self.game.board.cell_W_pix + self.game.board.board_offset_x
        y2 = y1 + self.game.board.cell_H_pix - 1
        x2 = x1 + self.game.board.cell_W_pix - 1
        
        black_color = (0, 0, 0)
        white_color = (255, 255, 255)
        blue_color = (255, 0, 0)  # BGR
        
        if player_num == 1:
            main_color = white_color
            border_color = blue_color
        else:
            main_color = black_color
            border_color = blue_color
        
        cv2.rectangle(self.game.curr_board.img.img, 
                     (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), 
                     border_color, 3)
        
        cv2.rectangle(self.game.curr_board.img.img, 
                     (x1, y1), (x2, y2), 
                     main_color, 2)
        
        prev = getattr(self.game, last_attr)
        if prev != (r, c):
            logger.debug("Player %s cursor moved to (%s, %s)", player_num, r, c)
            setattr(self.game, last_attr, (r, c))
    
    async def run(self):
        """Main client loop matching Game.py logic"""
        if not await self.connect():
            return
            
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        logger.info("Starting client display...")
        
        try:
            logger.info("Client started. Game window should be open with full functionality.")
            
            self.game.event_manager.publish(Event(
                EventType.GAME_STARTED,
                {'game_time_ms': self.game.game_time_ms()}
            ))
            
            self.game.show_cursors = False
            
            self.game.add_temp_message("Welcome to Chess Kingdom! Let the battle begin!", 4000)
            
            self.game.start_user_input_thread()
            
            start_ms = self.game.START_NS
            for p in self.game.pieces:
                p.reset(start_ms)
            
            self.game._update_cell2piece_map()
            
            self.game._draw()
            self._draw_player_cursor_only()
            self.game._show()
            
            await asyncio.sleep(0.1)
            
            while not self.should_exit and not self.game.should_exit:
                now = self.game.game_time_ms()

                for p in self.game.pieces:
                    p.update(now)

                self.game._ensure_promoted_queens_graphics()
                self.game._update_cell2piece_map()

                while not self.game.user_input_queue.empty():
                    cmd = self.game.user_input_queue.get()
                    self.game._process_input(cmd)

                self.game._draw()
                self._draw_player_cursor_only()
                self.game._show()

                self.game._resolve_collisions()
                self.game._check_post_collision_promotions()
                self.game._check_and_announce_win()

                await asyncio.sleep(0.05)
                
        except KeyboardInterrupt:
            logger.info("Client interrupted by user")
        finally:
            listen_task.cancel()
            await self.disconnect()
    
    def track_move(self, move_data):
        """Track a move for display"""
        try:
            if not self.game or not hasattr(self.game, 'event_manager'):
                return
                
            piece_id = move_data.get('piece_id', '')
            from_pos = move_data.get('from', [])
            to_pos = move_data.get('to', [])
            player = move_data.get('player', '')
            
            if isinstance(from_pos, list) and len(from_pos) == 2:
                from_pos = tuple(from_pos)
            if isinstance(to_pos, list) and len(to_pos) == 2:
                to_pos = tuple(to_pos)
            
            event = Event(
                event_type=EventType.PIECE_MOVED,
                data={
                    'piece': piece_id,
                    'from': from_pos,
                    'to': to_pos,
                    'player': player,
                    'game_time_ms': self.game.game_time_ms() if hasattr(self.game, 'game_time_ms') else 0
                }
            )
            
            self.game.event_manager.publish(event)
            logger.info(f"Published move event: {piece_id} from {from_pos} to {to_pos} by {player}")
            
        except Exception as e:
            logger.error(f"Error tracking move: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def track_capture(self, capture_data):
        """Track capture moves for display"""
        try:
            piece_id = capture_data.get('piece_id', '')
            captured_piece = capture_data.get('captured', '')
            from_pos = capture_data.get('from', [])
            to_pos = capture_data.get('to', [])
            player = capture_data.get('player', '')
            
            if isinstance(from_pos, list) and len(from_pos) == 2:
                from_pos = tuple(from_pos)
            if isinstance(to_pos, list) and len(to_pos) == 2:
                to_pos = tuple(to_pos)
            
            capture_event = Event(
                event_type=EventType.PIECE_CAPTURED,
                data={
                    'piece_type': captured_piece,
                    'captured_by': piece_id,
                    'from_position': from_pos,
                    'position': to_pos,
                    'player': player,
                    'game_time_ms': self.game.game_time_ms() if hasattr(self.game, 'game_time_ms') else 0
                }
            )
            
            self.game.event_manager.publish(capture_event)
            logger.info(f"Published capture event: {piece_id} captured {captured_piece} at {to_pos}")
            
        except Exception as e:
            logger.error(f"Error tracking capture: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_piece_moved(self, event):
        """Handle piece moved events from the game"""
        try:
            if event.event_type == EventType.PIECE_MOVED:
                data = event.data
                piece_id = data.get('piece', '')
                from_pos = data.get('from', ())
                to_pos = data.get('to', ())
                
                if piece_id and self.game:
                    piece_side = self.game._side_of(piece_id)
                    piece_color = 'white' if piece_side == 'W' else 'black'
                    if piece_color == self.player_color:
                        asyncio.create_task(self.send_move(piece_id, from_pos, to_pos))
                        
        except Exception as e:
            logger.error(f"Error handling piece moved event: {e}")
    
    def _on_piece_captured(self, event):
        """Handle piece captured events from the game"""
        try:
            if event.event_type == EventType.PIECE_CAPTURED:
                logger.info(f"Piece captured: {event.data}")
                        
        except Exception as e:
            logger.error(f"Error handling piece captured event: {e}")

# Main client entry point
async def main():
    client = FixedChessClient()
    await client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
