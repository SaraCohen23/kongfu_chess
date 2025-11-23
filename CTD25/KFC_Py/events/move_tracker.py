"""
Move Tracker - tracks and logs all piece movements in the game.
"""

from typing import List, Tuple
from .event_manager import EventManager, Event, EventType


class MoveTracker:
    """
    Tracks all piece movements in the game using the event system.
    Subscribes to PIECE_MOVED events and maintains a history of moves.
    """
    
    def __init__(self, event_manager: EventManager):
        self.moves: List[str] = []
        # Separate move lists for each color with (time, move_text) tuples
        self.white_moves: List[Tuple[str, str]] = []  # (time, move_notation)
        self.black_moves: List[Tuple[str, str]] = []  # (time, move_notation)
        self.event_manager = event_manager
        
        # Subscribe to relevant events
        self.event_manager.subscribe(EventType.PIECE_MOVED, self.on_piece_moved)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, self.on_piece_captured)
        self.event_manager.subscribe(EventType.GAME_STARTED, self.on_game_started)
    
    def _format_time(self, game_time_ms: int) -> str:
        """Format game time as MM:SS from game start."""
        total_seconds = game_time_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted_time = f"{minutes:02d}:{seconds:02d}"
        return formatted_time
    
    def _pos_to_chess_notation(self, row: int, col: int) -> str:
        """Convert board position to chess notation (e.g., (7,4) -> e1)."""
        return f"{chr(ord('a') + col)}{8 - row}"
    
    def _format_move_notation(self, piece_id: str, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> str:
        """Format a move in clear English notation."""
        if len(piece_id) < 2:
            return f"{piece_id}?"
            
        piece_type = piece_id[0]  # P, N, B, R, Q, K
        piece_color = piece_id[1]  # W or B
        
        from_chess = self._pos_to_chess_notation(*from_pos)
        to_chess = self._pos_to_chess_notation(*to_pos)
        
        # Create clear piece names in English
        piece_names = {
            'P': 'Pawn', 'N': 'Knight', 'B': 'Bishop', 
            'R': 'Rook', 'Q': 'Queen', 'K': 'King'
        }
        
        piece_name = piece_names.get(piece_type, piece_type)
        color_name = 'White' if piece_color == 'W' else 'Black'
        
        # Check if this is an attempted move that failed
        if from_pos == to_pos:
            return f"{color_name} {piece_name} stays at {from_chess}"
        
        # Create clearer format: "W-Pawn e2 to e4" or "B-Knight b8 to c6"
        color_abbrev = 'W' if piece_color == 'W' else 'B'
        return f"{color_abbrev}-{piece_name} {from_chess} to {to_chess}"
    
    def on_piece_moved(self, event: Event):
        """Handle piece movement events."""
        data = event.data
        piece_id = data.get('piece', 'Unknown')
        from_pos = data.get('from', (0, 0))
        to_pos = data.get('to', (0, 0))
        game_time = data.get('game_time_ms', 0)
        
        # Format time and move notation
        time_str = self._format_time(game_time)
        move_notation = self._format_move_notation(piece_id, from_pos, to_pos)
        
        
        # Add to general moves list (for backward compatibility)
        move_str = f"{piece_id}: {from_pos} -> {to_pos} [{game_time}ms]"
        self.moves.append(move_str)
        
        # Add to color-specific lists for table display
        if len(piece_id) >= 2:
            if piece_id[1] == 'W':  # White piece
                self.white_moves.append((time_str, move_notation))
            elif piece_id[1] == 'B':  # Black piece
                self.black_moves.append((time_str, move_notation))
    
    def on_piece_captured(self, event: Event):
        """Handle piece capture events."""
        data = event.data
        captured_piece = data.get('piece_type', 'Unknown')  # e.g., 'PB1'
        captured_by = data.get('captured_by', 'Unknown')    # e.g., 'QW1'
        from_pos = data.get('from_position', (0, 0))
        position = data.get('position', (0, 0))
        game_time = data.get('game_time_ms', 0)
        
        # Format time
        time_str = self._format_time(game_time)
        
        # Create capture move notation in same format as regular moves
        if len(captured_by) >= 2:
            # Format as a capture move: piece moving from somewhere to capture position
            move_notation = self._format_move_notation(captured_by, from_pos, position)
            # Add capture indicator "captures" instead of "to"
            if ' to ' in move_notation:
                move_notation = move_notation.replace(' to ', ' captures at ')
            
            
            # Add to general moves list (for backward compatibility)
            capture_str = f"CAPTURE: {captured_piece} captured by {captured_by} at {position} [{game_time}ms]"
            self.moves.append(capture_str)
            
            # Add capture notation to color-specific lists (who made the capture)
            if captured_by[1] == 'W':  # White captured
                self.white_moves.append((time_str, move_notation))
            elif captured_by[1] == 'B':  # Black captured
                self.black_moves.append((time_str, move_notation))
        else:
            pass
    
    def on_game_started(self, event: Event):
        """Handle game start events."""
        self.moves.clear()
        self.white_moves.clear()
        self.black_moves.clear()
        self.moves.append("=== GAME STARTED ===")
    
    def get_white_moves(self, count: int = 8) -> List[Tuple[str, str]]:
        """Get the last N white moves as (time, move) tuples."""
        return self.white_moves[-count:] if count <= len(self.white_moves) else self.white_moves.copy()
    
    def get_black_moves(self, count: int = 8) -> List[Tuple[str, str]]:
        """Get the last N black moves as (time, move) tuples."""
        return self.black_moves[-count:] if count <= len(self.black_moves) else self.black_moves.copy()
    
    def get_all_moves_by_color(self, count: int = 8) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Get the last N moves for both colors. Returns (white_moves, black_moves)."""
        return (self.get_white_moves(count), self.get_black_moves(count))
    
    def get_move_history(self) -> List[str]:
        """Get a copy of the complete move history."""
        return self.moves.copy()
    
    def get_last_moves(self, count: int) -> List[str]:
        """Get the last N moves."""
        return self.moves[-count:] if count <= len(self.moves) else self.moves.copy()
    
    def get_move_count(self) -> int:
        """Get the total number of moves recorded."""
        return len([move for move in self.moves if not move.startswith("=")])
    
    def print_move_history(self):
        """Print the complete move history to console."""
        print("Move History:")
        print("-" * 40)
        for i, move in enumerate(self.moves, 1):
            print(f"{i:3d}. {move}")
    
    def export_to_file(self, filename: str):
        """Export move history to a text file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("KungFu Chess Move History\n")
                f.write("=" * 40 + "\n")
                for i, move in enumerate(self.moves, 1):
                    f.write(f"{i:3d}. {move}\n")
            print(f"Move history exported to {filename}")
        except Exception as e:
            print(f"Error exporting move history: {e}")
