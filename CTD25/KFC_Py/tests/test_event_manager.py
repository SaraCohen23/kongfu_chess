"""
Tests for Event Manager - Publish/Subscribe pattern implementation.
"""

import unittest
from events.event_manager import EventManager, Event, EventType


class TestEventManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.event_manager = EventManager()
        self.received_events = []
    
    def test_subscription_and_publishing(self):
        """Test basic subscription and event publishing."""
        def callback(event):
            self.received_events.append(event)
        
        # Subscribe to PIECE_MOVED events
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback)
        
        # Create and publish an event
        event = Event(EventType.PIECE_MOVED, {'piece': 'PW1', 'from': (6, 0), 'to': (4, 0)})
        self.event_manager.publish(event)
        
        # Check that callback was called
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0].type, EventType.PIECE_MOVED)
        self.assertEqual(self.received_events[0].data['piece'], 'PW1')
    
    def test_multiple_subscribers(self):
        """Test that multiple subscribers receive the same event."""
        callbacks_called = [False, False, False]
        
        def callback1(event):
            callbacks_called[0] = True
        
        def callback2(event):
            callbacks_called[1] = True
        
        def callback3(event):
            callbacks_called[2] = True
        
        # Subscribe all callbacks to the same event type
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, callback1)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, callback2)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, callback3)
        
        # Publish event
        event = Event(EventType.PIECE_CAPTURED, {'piece_type': 'PB1'})
        self.event_manager.publish(event)
        
        # All callbacks should have been called
        self.assertTrue(all(callbacks_called))
    
    def test_different_event_types(self):
        """Test that subscribers only receive events they subscribed to."""
        moved_events = []
        captured_events = []
        
        def move_callback(event):
            moved_events.append(event)
        
        def capture_callback(event):
            captured_events.append(event)
        
        # Subscribe to different event types
        self.event_manager.subscribe(EventType.PIECE_MOVED, move_callback)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, capture_callback)
        
        # Publish different events
        move_event = Event(EventType.PIECE_MOVED, {'piece': 'NW1'})
        capture_event = Event(EventType.PIECE_CAPTURED, {'piece_type': 'PB1'})
        
        self.event_manager.publish(move_event)
        self.event_manager.publish(capture_event)
        
        # Each callback should only receive its subscribed event type
        self.assertEqual(len(moved_events), 1)
        self.assertEqual(len(captured_events), 1)
        self.assertEqual(moved_events[0].type, EventType.PIECE_MOVED)
        self.assertEqual(captured_events[0].type, EventType.PIECE_CAPTURED)
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        def callback(event):
            self.received_events.append(event)
        
        # Subscribe and publish event
        self.event_manager.subscribe(EventType.GAME_STARTED, callback)
        event1 = Event(EventType.GAME_STARTED, {})
        self.event_manager.publish(event1)
        
        # Unsubscribe and publish another event
        self.event_manager.unsubscribe(EventType.GAME_STARTED, callback)
        event2 = Event(EventType.GAME_STARTED, {})
        self.event_manager.publish(event2)
        
        # Should only receive first event
        self.assertEqual(len(self.received_events), 1)
    
    def test_subscriber_count(self):
        """Test getting subscriber count."""
        def callback1(event): pass
        def callback2(event): pass
        
        # Initially no subscribers
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 0)
        
        # Add subscribers
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback1)
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 1)
        
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback2)
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 2)
        
        # Remove subscriber
        self.event_manager.unsubscribe(EventType.PIECE_MOVED, callback1)
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 1)
    
    def test_duplicate_subscription(self):
        """Test that duplicate subscriptions are ignored."""
        def callback(event): pass
        
        # Subscribe same callback twice
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback)
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback)
        
        # Should only have one subscriber
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 1)
    
    def test_error_handling_in_callback(self):
        """Test that errors in one callback don't affect others."""
        successful_callback_called = False
        
        def error_callback(event):
            raise Exception("Test error")
        
        def successful_callback(event):
            nonlocal successful_callback_called
            successful_callback_called = True
        
        # Subscribe both callbacks
        self.event_manager.subscribe(EventType.PIECE_MOVED, error_callback)
        self.event_manager.subscribe(EventType.PIECE_MOVED, successful_callback)
        
        # Publish event - should not raise exception
        event = Event(EventType.PIECE_MOVED, {})
        self.event_manager.publish(event)
        
        # Successful callback should still be called
        self.assertTrue(successful_callback_called)
    
    def test_clear_all_subscribers(self):
        """Test clearing all subscribers."""
        def callback(event): pass
        
        # Add subscribers to different event types
        self.event_manager.subscribe(EventType.PIECE_MOVED, callback)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, callback)
        
        # Clear all
        self.event_manager.clear_all_subscribers()
        
        # Should have no subscribers
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_MOVED), 0)
        self.assertEqual(self.event_manager.get_subscriber_count(EventType.PIECE_CAPTURED), 0)


class TestEvent(unittest.TestCase):
    
    def test_event_creation(self):
        """Test Event object creation and properties."""
        data = {'piece': 'KW1', 'position': (7, 4)}
        event = Event(EventType.PIECE_MOVED, data)
        
        self.assertEqual(event.type, EventType.PIECE_MOVED)
        self.assertEqual(event.data, data)
        self.assertIsInstance(event.timestamp, float)
        self.assertGreater(event.timestamp, 0)
    
    def test_event_repr(self):
        """Test Event string representation."""
        event = Event(EventType.GAME_STARTED, {})
        repr_str = repr(event)
        
        self.assertIn('Event', repr_str)
        self.assertIn('game_started', repr_str)


if __name__ == '__main__':
    unittest.main()
