"""
Event system for KungFu Chess game.
Implements Publish/Subscribe pattern for loose coupling between game components.
"""

from .event_manager import EventManager, Event, EventType
from .move_tracker import MoveTracker
from .score_tracker import ScoreTracker

__all__ = ['EventManager', 'Event', 'EventType', 'MoveTracker', 'ScoreTracker']
