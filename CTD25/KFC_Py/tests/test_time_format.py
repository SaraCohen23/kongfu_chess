#!/usr/bin/env python3
"""
Quick test for the new time formatting function.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'KFC_Py'))

from events.event_manager import EventManager
from events.move_tracker import MoveTracker

def test_time_formatting():
    """Test the new game time formatting."""
    event_manager = EventManager()
    move_tracker = MoveTracker(event_manager)
    
    # Test cases: milliseconds -> expected MM:SS format
    test_cases = [
        (0, "00:00"),           # 0ms = 0:00
        (1000, "00:01"),        # 1000ms = 0:01
        (30000, "00:30"),       # 30000ms = 0:30
        (60000, "01:00"),       # 60000ms = 1:00
        (90000, "01:30"),       # 90000ms = 1:30
        (120000, "02:00"),      # 120000ms = 2:00
        (3661000, "61:01"),     # 3661000ms = 61:01 (over 1 hour)
    ]
    
    print("Testing time formatting:")
    for ms, expected in test_cases:
        result = move_tracker._format_time(ms)
        status = "✓" if result == expected else "✗"
        print(f"{status} {ms}ms -> {result} (expected: {expected})")
    
    print("\nTime formatting test completed!")

if __name__ == "__main__":
    test_time_formatting()
