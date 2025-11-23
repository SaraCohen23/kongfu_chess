"""
Tests for Score Tracker - tracking game scoring based on captured pieces.
"""

import unittest
from events.event_manager import EventManager, Event, EventType
from events.score_tracker import ScoreTracker


class TestScoreTracker(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.event_manager = EventManager()
        self.score_tracker = ScoreTracker(self.event_manager)
    
    def test_initial_scores(self):
        """Test that initial scores are zero."""
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 0)
        self.assertEqual(black_score, 0)
    
    def test_white_captures_black_pawn(self):
        """Test white capturing black pawn."""
        event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'PB1',
            'captured_by': 'QW1',
            'position': (4, 4),
            'game_time_ms': 1000
        })
        self.event_manager.publish(event)
        
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 1)  # Pawn = 1 point
        self.assertEqual(black_score, 0)
    
    def test_black_captures_white_queen(self):
        """Test black capturing white queen."""
        event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'QW1',
            'captured_by': 'RB1',
            'position': (3, 3),
            'game_time_ms': 1500
        })
        self.event_manager.publish(event)
        
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 0)
        self.assertEqual(black_score, 9)  # Queen = 9 points
    
    def test_multiple_captures(self):
        """Test multiple captures affecting both scores."""
        captures = [
            # White captures black knight
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'NB1', 'captured_by': 'PW1',
                'position': (4, 4), 'game_time_ms': 1000
            }),
            # Black captures white bishop
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'BW1', 'captured_by': 'QB1',
                'position': (5, 5), 'game_time_ms': 1500
            }),
            # White captures black rook
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'RB1', 'captured_by': 'QW1',
                'position': (0, 0), 'game_time_ms': 2000
            })
        ]
        
        for event in captures:
            self.event_manager.publish(event)
        
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 8)  # Knight(3) + Rook(5) = 8
        self.assertEqual(black_score, 3)  # Bishop(3) = 3
    
    def test_piece_values(self):
        """Test all piece values individually."""
        piece_tests = [
            ('PB1', 1),  # Pawn
            ('NW1', 3),  # Knight
            ('BB1', 3),  # Bishop
            ('RW1', 5),  # Rook
            ('QB1', 9),  # Queen
        ]
        
        for piece_type, expected_value in piece_tests:
            # Reset scores
            self.score_tracker._white_score = 0
            self.score_tracker._black_score = 0
            
            # Determine who captured (opposite color)
            captured_by = 'QW1' if piece_type[1] == 'B' else 'QB1'
            
            event = Event(EventType.PIECE_CAPTURED, {
                'piece_type': piece_type,
                'captured_by': captured_by,
                'position': (4, 4),
                'game_time_ms': 1000
            })
            self.event_manager.publish(event)
            
            white_score, black_score = self.score_tracker.get_scores()
            
            if piece_type[1] == 'B':  # Black piece captured by white
                self.assertEqual(white_score, expected_value)
                self.assertEqual(black_score, 0)
            else:  # White piece captured by black
                self.assertEqual(white_score, 0)
                self.assertEqual(black_score, expected_value)
    
    def test_king_capture_no_score(self):
        """Test that king captures don't add to score (game ender)."""
        event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'KB1',
            'captured_by': 'QW1',
            'position': (4, 4),
            'game_time_ms': 1000
        })
        self.event_manager.publish(event)
        
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 0)  # King capture = 0 points
        self.assertEqual(black_score, 0)
    
    def test_game_started_resets_scores(self):
        """Test that game started event resets scores."""
        # Add some scores first
        capture_event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'QB1',
            'captured_by': 'PW1',
            'position': (4, 4),
            'game_time_ms': 1000
        })
        self.event_manager.publish(capture_event)
        
        # Verify scores are non-zero
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 9)
        
        # Start new game
        start_event = Event(EventType.GAME_STARTED, {})
        self.event_manager.publish(start_event)
        
        # Scores should be reset
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 0)
        self.assertEqual(black_score, 0)
    
    def test_get_score_difference(self):
        """Test getting score difference (positive = white ahead)."""
        # White ahead by 5
        self.score_tracker._white_score = 8
        self.score_tracker._black_score = 3
        self.assertEqual(self.score_tracker.get_score_difference(), 5)
        
        # Black ahead by 2  
        self.score_tracker._white_score = 3
        self.score_tracker._black_score = 5
        self.assertEqual(self.score_tracker.get_score_difference(), -2)
        
        # Tied
        self.score_tracker._white_score = 5
        self.score_tracker._black_score = 5
        self.assertEqual(self.score_tracker.get_score_difference(), 0)
    
    def test_get_leading_player(self):
        """Test getting which player is leading."""
        # White leading
        self.score_tracker._white_score = 10
        self.score_tracker._black_score = 5
        self.assertEqual(self.score_tracker.get_leading_player(), 'White')
        
        # Black leading
        self.score_tracker._white_score = 3
        self.score_tracker._black_score = 8
        self.assertEqual(self.score_tracker.get_leading_player(), 'Black')
        
        # Tied
        self.score_tracker._white_score = 5
        self.score_tracker._black_score = 5
        self.assertEqual(self.score_tracker.get_leading_player(), 'Tied')
    
    def test_unknown_piece_type(self):
        """Test handling of unknown piece types."""
        event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'XB1',  # Unknown piece type
            'captured_by': 'QW1',
            'position': (4, 4),
            'game_time_ms': 1000
        })
        self.event_manager.publish(event)
        
        # Should not crash, should not add to score
        white_score, black_score = self.score_tracker.get_scores()
        self.assertEqual(white_score, 0)
        self.assertEqual(black_score, 0)
    
    def test_score_tracker_initialization(self):
        """Test that ScoreTracker properly subscribes to events."""
        # Check that the tracker subscribed to the right events
        self.assertEqual(
            self.event_manager.get_subscriber_count(EventType.PIECE_CAPTURED), 1
        )
        self.assertEqual(
            self.event_manager.get_subscriber_count(EventType.GAME_STARTED), 1
        )
    
    def test_capture_count_tracking(self):
        """Test tracking of capture counts by color."""
        captures = [
            # White captures
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'PB1', 'captured_by': 'QW1',
                'position': (4, 4), 'game_time_ms': 1000
            }),
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'NB1', 'captured_by': 'BW1',
                'position': (5, 5), 'game_time_ms': 1500
            }),
            # Black captures  
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'PW1', 'captured_by': 'RB1',
                'position': (6, 6), 'game_time_ms': 2000
            })
        ]
        
        for event in captures:
            self.event_manager.publish(event)
        
        white_captures = self.score_tracker.get_capture_count('white')
        black_captures = self.score_tracker.get_capture_count('black')
        
        self.assertEqual(white_captures, 2)
        self.assertEqual(black_captures, 1)


if __name__ == '__main__':
    unittest.main()
