"""
Tests for Move Tracker - tracking piece movements and captures.
"""

import unittest
from events.event_manager import EventManager, Event, EventType
from events.move_tracker import MoveTracker


class TestMoveTracker(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.event_manager = EventManager()
        self.move_tracker = MoveTracker(self.event_manager)
    
    def test_piece_moved_tracking(self):
        """Test tracking of piece movements."""
        # Publish a piece moved event
        event = Event(EventType.PIECE_MOVED, {
            'piece': 'PW1',
            'from': (6, 0),
            'to': (4, 0),
            'game_time_ms': 1500
        })
        self.event_manager.publish(event)
        
        # Check that move was recorded
        moves = self.move_tracker.get_move_history()
        self.assertEqual(len(moves), 1)
        self.assertIn('PW1', moves[0])
        self.assertIn('(6, 0) -> (4, 0)', moves[0])
        self.assertIn('[1500ms]', moves[0])
    
    def test_piece_captured_tracking(self):
        """Test tracking of piece captures."""
        # Publish a piece captured event
        event = Event(EventType.PIECE_CAPTURED, {
            'piece_type': 'PB1',
            'captured_by': 'QW1',
            'position': (4, 4),
            'game_time_ms': 2000
        })
        self.event_manager.publish(event)
        
        # Check that capture was recorded
        moves = self.move_tracker.get_move_history()
        self.assertEqual(len(moves), 1)
        self.assertIn('CAPTURE', moves[0])
        self.assertIn('PB1 captured by QW1', moves[0])
        self.assertIn('(4, 4)', moves[0])
        self.assertIn('[2000ms]', moves[0])
    
    def test_game_started_tracking(self):
        """Test game start event handling."""
        # Add some moves first
        move_event = Event(EventType.PIECE_MOVED, {
            'piece': 'PW1',
            'from': (6, 0),
            'to': (4, 0),
            'game_time_ms': 1000
        })
        self.event_manager.publish(move_event)
        
        # Publish game started event
        start_event = Event(EventType.GAME_STARTED, {})
        self.event_manager.publish(start_event)
        
        # Should clear previous moves and add game started marker
        moves = self.move_tracker.get_move_history()
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0], "=== GAME STARTED ===")
    
    def test_multiple_moves_sequence(self):
        """Test tracking multiple moves in sequence."""
        # Publish several events
        events = [
            Event(EventType.PIECE_MOVED, {
                'piece': 'PW1', 'from': (6, 0), 'to': (4, 0), 'game_time_ms': 1000
            }),
            Event(EventType.PIECE_MOVED, {
                'piece': 'PB1', 'from': (1, 0), 'to': (3, 0), 'game_time_ms': 1500
            }),
            Event(EventType.PIECE_CAPTURED, {
                'piece_type': 'PB1', 'captured_by': 'PW1', 'position': (3, 0), 'game_time_ms': 2000
            })
        ]
        
        for event in events:
            self.event_manager.publish(event)
        
        # Should have all moves recorded
        moves = self.move_tracker.get_move_history()
        self.assertEqual(len(moves), 3)
        
        # Check order and content
        self.assertIn('PW1', moves[0])
        self.assertIn('PB1', moves[1])
        self.assertIn('CAPTURE', moves[2])
    
    def test_get_last_moves(self):
        """Test getting last N moves."""
        # Add 5 moves
        for i in range(5):
            event = Event(EventType.PIECE_MOVED, {
                'piece': f'P{i}',
                'from': (6, i),
                'to': (4, i),
                'game_time_ms': 1000 + i * 100
            })
            self.event_manager.publish(event)
        
        # Get last 3 moves
        last_moves = self.move_tracker.get_last_moves(3)
        self.assertEqual(len(last_moves), 3)
        
        # Should be the last 3 moves (P2, P3, P4)
        self.assertIn('P2', last_moves[0])
        self.assertIn('P3', last_moves[1])
        self.assertIn('P4', last_moves[2])
    
    def test_get_last_moves_more_than_available(self):
        """Test getting more moves than available."""
        # Add only 2 moves
        for i in range(2):
            event = Event(EventType.PIECE_MOVED, {
                'piece': f'P{i}',
                'from': (6, i),
                'to': (4, i),
                'game_time_ms': 1000
            })
            self.event_manager.publish(event)
        
        # Request 5 moves (more than available)
        last_moves = self.move_tracker.get_last_moves(5)
        self.assertEqual(len(last_moves), 2)  # Should return all available
    
    def test_get_move_count(self):
        """Test getting total move count (excluding markers)."""
        # Add game started marker
        self.event_manager.publish(Event(EventType.GAME_STARTED, {}))
        
        # Add 3 moves
        for i in range(3):
            event = Event(EventType.PIECE_MOVED, {
                'piece': f'P{i}',
                'from': (6, i),
                'to': (4, i),
                'game_time_ms': 1000
            })
            self.event_manager.publish(event)
        
        # Should count only actual moves, not markers
        self.assertEqual(self.move_tracker.get_move_count(), 3)
    
    def test_move_tracker_initialization(self):
        """Test that MoveTracker properly subscribes to events."""
        # Check that the tracker subscribed to the right events
        self.assertEqual(
            self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 1
        )
        self.assertEqual(
            self.event_manager.get_subscriber_count(EventType.PIECE_CAPTURED), 1
        )
        self.assertEqual(
            self.event_manager.get_subscriber_count(EventType.GAME_STARTED), 1
        )
    
    def test_empty_move_history(self):
        """Test behavior with empty move history."""
        moves = self.move_tracker.get_move_history()
        self.assertEqual(len(moves), 0)
        
        last_moves = self.move_tracker.get_last_moves(5)
        self.assertEqual(len(last_moves), 0)
        
        move_count = self.move_tracker.get_move_count()
        self.assertEqual(move_count, 0)
    
    def test_format_time(self):
        """Test the new game time formatting (MM:SS format)."""
        # Test various time values
        test_cases = [
            (0, "00:00"),           # 0ms = 0:00
            (1000, "00:01"),        # 1000ms = 0:01  
            (30000, "00:30"),       # 30000ms = 0:30
            (60000, "01:00"),       # 60000ms = 1:00
            (90000, "01:30"),       # 90000ms = 1:30
            (120000, "02:00"),      # 120000ms = 2:00
            (3661000, "61:01"),     # 3661000ms = 61:01 (over 1 hour)
        ]
        
        for game_time_ms, expected_format in test_cases:
            with self.subTest(game_time_ms=game_time_ms):
                result = self.move_tracker._format_time(game_time_ms)
                self.assertEqual(result, expected_format, 
                    f"Expected {game_time_ms}ms to format as {expected_format}, got {result}")


if __name__ == '__main__':
    unittest.main()
