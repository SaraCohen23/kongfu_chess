"""
Game Logic for Server

Extends the existing Game class to work without graphics and keyboard input.

Used by the server to validate moves and manage game state.

Architecture:
- Inherits all game logic from Game.py
- Disables graphics for server use
- Adds server-specific validation and serialization
- Maintains compatibility with original game mechanics
"""

from typing import List, Dict, Tuple, Optional
import logging

from Game import Game
from Board import Board
from Piece import Piece
from Command import Command

logger = logging.getLogger(__name__)

class ServerGame(Game):
    """
    Server-side game logic without graphics or keyboard input.
    
    Validates moves and maintains authoritative game state.
    
    Inherits from: Game.py (full chess game logic)
    
    Key differences from Game.py:
    - Graphics disabled
    - No keyboard input handling
    - Added move validation for server
    - Added state serialization for WebSocket
    """
    
    def __init__(self, pieces: List[Piece], board: Board, pieces_root=None, img_factory=None):
        """Initialize ServerGame
        
        Args:
            pieces: List of game pieces from Game.py
            board: Game board from Game.py
            pieces_root: Path to pieces directory
            img_factory: Image factory (unused in server)
        """
        super().__init__(pieces, board, pieces_root, img_factory)
        self.graphics_enabled = False
        
    def validate_move(self, piece_id: str, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """
        Validate if a move is legal using existing Game.py logic
        
        Args:
            piece_id (str): ID of piece to move
            from_pos (Tuple[int, int]): Starting position
            to_pos (Tuple[int, int]): Target position
            
        Returns:
            bool: True if move is valid
            
        Uses Game.py methods:
        - piece_by_id
        - current_cell()
        - board dimensions for bounds checking
        - pos mapping for collision detection
        - _side_of(): Check piece colors
        """
        try:
            piece = self.piece_by_id.get(piece_id)
            if not piece:
                logger.warning(f"Piece {piece_id} not found")
                return False
            
            current_pos = piece.current_cell()
            if current_pos != from_pos:
                logger.warning(f"Piece {piece_id} is at {current_pos}, not {from_pos}")
                return False
            
            if not (0 <= to_pos[0] < self.board.H_cells and 0 <= to_pos[1] < self.board.W_cells):
                logger.warning(f"Invalid destination position: {to_pos}")
                return False
            
            target_pieces = self.pos.get(to_pos, [])
            for target_piece in target_pieces:
                if self._side_of(piece.id) == self._side_of(target_piece.id):
                    logger.warning(f"Cannot capture own piece at {to_pos}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating move: {e}")
            return False
    
    def execute_move(self, piece_id: str, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """
        Execute a validated move using the original game logic.
        
        Args:
            piece_id (str): ID of piece to move
            from_pos (Tuple[int, int]): Starting position
            to_pos (Tuple[int, int]): Target position
            
        Returns:
            bool: True if move was executed successfully
            
        Uses Game.py methods:
        - validate_move()
        - Command
        - _process_input()
        - game_time_ms()
        """
        try:
            if not self.validate_move(piece_id, from_pos, to_pos):
                return False
            
            cmd = Command(
                timestamp=self.game_time_ms(),
                piece_id=piece_id,
                type="move",
                params=[from_pos, to_pos]
            )
            
            self._process_input(cmd)
            
            logger.info(f"Move executed: {piece_id} from {from_pos} to {to_pos}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing move: {e}")
            return False
    
    def get_game_state_dict(self) -> Dict:
        """Get current game state as a dictionary for serialization
        
        Returns:
            Dict: Game state with piece positions and info
        """
        pieces_data = []
        for piece in self.pieces:
            current_pos = piece.current_cell()
            
            pieces_data.append({
                "id": piece.id,
                "position": list(current_pos),
                "type": piece.id[0] if len(piece.id) > 0 else "unknown",
                "color": piece.id[1] if len(piece.id) > 1 else "unknown"
            })
        
        logger.debug(f"Sending game state with {len(pieces_data)} pieces")
        return {
            "pieces": pieces_data
        }
    
    def _draw(self):
        """Disabled for server"""
        pass
    
    def _show(self):
        """Disabled for server"""
        pass
    
    def run(self):
        """Override run method - server doesn't run the main game loop"""
        logger.warning("ServerGame.run() called - this should not happen on server")
