"""
Score Tracker - tracks and calculates scores based on captured pieces.
"""

from typing import Dict
from .event_manager import EventManager, Event, EventType


class ScoreTracker:
    """
    Tracks game score based on captured pieces.
    Each piece type has a specific point value.
    """
    
    # Point values for each piece type
    PIECE_VALUES = {
        'P': 1,  # Pawn
        'N': 3,  # Knight 
        'B': 3,  # Bishop
        'R': 5,  # Rook
        'Q': 9,  # Queen
        'K': 0   # King (capturing king ends game, no points)
    }
    
    def __init__(self, event_manager: EventManager):
        self._white_score = 0
        self._black_score = 0
        self.captured_pieces = {'W': [], 'B': []}  # Track individual captured pieces
        self.event_manager = event_manager
        
        # Subscribe to relevant events
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, self.on_piece_captured)
        self.event_manager.subscribe(EventType.GAME_STARTED, self.on_game_started)
        self.event_manager.subscribe(EventType.GAME_ENDED, self.on_game_ended)
    
    def on_piece_captured(self, event: Event):
        """Handle piece capture events and update scores."""
        data = event.data
        captured_piece_id = data.get('piece_type', '')
        
        if len(captured_piece_id) < 2:
            return  # Invalid piece ID
        
        piece_type = captured_piece_id[0]  # P, N, B, R, Q, K
        piece_color = captured_piece_id[1]  # W or B
        
        # Get point value for this piece type
        piece_value = self.PIECE_VALUES.get(piece_type, 0)
        
        # Add points to the opposing player's score
        if piece_color == 'W':  # White piece captured by black
            self._black_score += piece_value
            self.captured_pieces['B'].append(captured_piece_id)  # Black made a capture
        elif piece_color == 'B':  # Black piece captured by white
            self._white_score += piece_value
            self.captured_pieces['W'].append(captured_piece_id)  # White made a capture
        
        # Print score update
        print(f"SCORE UPDATE: {captured_piece_id} captured (+{piece_value} points)")
        print(f"Current Score - White: {self._white_score}, Black: {self._black_score}")
    
    def on_game_started(self, event: Event):
        """Reset scores when game starts."""
        self._white_score = 0
        self._black_score = 0
        self.captured_pieces = {'W': [], 'B': []}
        print("SCORE: Game started - scores reset to 0-0")
    
    def on_game_ended(self, event: Event):
        """Print final scores when game ends."""
        print("=== FINAL SCORE ===")
        print(f"White: {self._white_score} points")
        print(f"Black: {self._black_score} points")
        
        winner = "White" if self._white_score > self._black_score else "Black" if self._black_score > self._white_score else "Tie"
        print(f"Score Winner: {winner}")
        
        self.print_captured_pieces()
    
    def get_scores(self) -> tuple:
        """Get current scores for both players as a tuple (white_score, black_score)."""
        return (self._white_score, self._black_score)
    
    def get_score_difference(self) -> int:
        """Get score difference (positive = white leading, negative = black leading)."""
        return self._white_score - self._black_score
    
    def get_leading_player(self) -> str:
        """Get which player is currently leading."""
        diff = self.get_score_difference()
        if diff > 0:
            return 'White'
        elif diff < 0:
            return 'Black'
        else:
            return 'Tied'
    
    def get_capture_count(self, color: str) -> int:
        """Get total number of pieces captured by the specified color."""
        color_key = 'W' if color.lower() == 'white' else 'B'
        return len(self.captured_pieces.get(color_key, []))
    
    def get_captured_pieces(self) -> Dict[str, list]:
        """Get lists of captured pieces for each color."""
        return self.captured_pieces.copy()
    
    def print_current_score(self):
        """Print current score to console."""
        diff = self.get_score_difference()
        leader = "White" if diff > 0 else "Black" if diff < 0 else "Tied"
        
        print(f"Current Score: White {self._white_score} - {self._black_score} Black")
        if diff != 0:
            print(f"Leader: {leader} by {abs(diff)} points")
    
    def print_captured_pieces(self):
        """Print detailed list of captured pieces."""
        print("\nCaptured Pieces:")
        print(f"White captured: {', '.join(self.captured_pieces['W']) if self.captured_pieces['W'] else 'None'}")
        print(f"Black captured: {', '.join(self.captured_pieces['B']) if self.captured_pieces['B'] else 'None'}")
    
    def get_piece_count_by_type(self, color: str) -> Dict[str, int]:
        """Get count of captured pieces by type for a specific color."""
        if color not in self.captured_pieces:
            return {}
        
        count = {}
        for piece_id in self.captured_pieces[color]:
            piece_type = piece_id[0]
            count[piece_type] = count.get(piece_type, 0) + 1
        
        return count
