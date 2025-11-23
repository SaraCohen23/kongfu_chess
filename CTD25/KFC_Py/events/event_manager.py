"""
Event Manager for Publish/Subscribe pattern implementation.
"""

import time
from enum import Enum
from typing import Dict, List, Callable, Any
from collections import defaultdict


class EventType(Enum):
    """Types of events that can be published in the game."""
    PIECE_MOVED = "piece_moved"
    PIECE_CAPTURED = "piece_captured"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    TURN_CHANGED = "turn_changed"


class Event:
    """Event object containing event type, data, and timestamp."""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = time.time()
        self.game_time_ms = data.get('game_time_ms', 0)
    
    def __repr__(self):
        return f"Event(type={self.type.value}, data={self.data}, timestamp={self.timestamp})"


class EventManager:
    """
    Event Manager implementing Publish/Subscribe pattern.
    
    Allows objects to subscribe to specific event types and automatically
    notifies all subscribers when events are published.
    """
    
    def __init__(self):
        # Dictionary mapping event types to lists of callback functions
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = defaultdict(list)
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Subscribe a callback function to an event type.
        
        Args:
            event_type: The type of event to listen for
            callback: Function to call when event is published. Should accept Event parameter.
        """
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Unsubscribe a callback function from an event type.
        
        Args:
            event_type: The type of event to stop listening for
            callback: The callback function to remove
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
    
    def publish(self, event: Event):
        """
        Publish an event to all subscribers.
        
        Args:
            event: The event to publish
        """
        subscribers = self._subscribers[event.type]
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                # Log error but continue notifying other subscribers
                print(f"Error in event callback: {e}")
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get the number of subscribers for a specific event type."""
        return len(self._subscribers[event_type])
    
    def clear_all_subscribers(self):
        """Remove all subscribers (useful for testing)."""
        self._subscribers.clear()
