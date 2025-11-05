"""
Unit tests for EventBus class.
"""

import pytest
from src.core.event_bus import EventBus
from src.core.storage import WorldStorage
from src.core.models import Event


@pytest.fixture
def storage():
    """Create an in-memory storage for testing."""
    storage = WorldStorage(':memory:')
    storage.initialize()
    # Register event types for testing
    storage.register_event_type('test.event1', 'Test event 1', 'test')
    storage.register_event_type('test.event2', 'Test event 2', 'test')
    yield storage
    storage.close()


@pytest.fixture
def event_bus(storage):
    """Create an event bus for testing."""
    return EventBus(storage)


class TestEventBus:
    """Test EventBus pub/sub functionality."""
    
    def test_subscribe(self, event_bus):
        """Test subscribing to events."""
        called = []
        
        def callback(event: Event):
            called.append(event)
        
        event_bus.subscribe('test.event1', callback)
        
        assert event_bus.get_listener_count('test.event1') == 1
        
    def test_subscribe_multiple_callbacks(self, event_bus):
        """Test subscribing multiple callbacks to same event type."""
        def callback1(event: Event):
            pass
        
        def callback2(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event1', callback2)
        
        assert event_bus.get_listener_count('test.event1') == 2
        
    def test_subscribe_duplicate_callback(self, event_bus):
        """Test that subscribing same callback twice doesn't duplicate."""
        def callback(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback)
        event_bus.subscribe('test.event1', callback)
        
        # Should only be subscribed once
        assert event_bus.get_listener_count('test.event1') == 1
        
    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        def callback(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback)
        assert event_bus.get_listener_count('test.event1') == 1
        
        event_bus.unsubscribe('test.event1', callback)
        assert event_bus.get_listener_count('test.event1') == 0
        
    def test_publish_calls_listeners(self, event_bus):
        """Test that publishing an event calls all listeners."""
        called = []
        
        def callback1(event: Event):
            called.append(('callback1', event))
        
        def callback2(event: Event):
            called.append(('callback2', event))
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event1', callback2)
        
        event = Event.create('test.event1', {'message': 'test'})
        event_bus.publish(event)
        
        assert len(called) == 2
        assert called[0][0] == 'callback1'
        assert called[1][0] == 'callback2'
        assert called[0][1].event_id == event.event_id
        
    def test_publish_logs_to_storage(self, event_bus, storage):
        """Test that published events are logged to storage."""
        event = Event.create('test.event1', {'message': 'test'})
        event_bus.publish(event)
        
        # Check that event was logged
        events = storage.get_events()
        assert len(events) >= 1
        
        logged = next((e for e in events if e.event_id == event.event_id), None)
        assert logged is not None
        assert logged.event_type == 'test.event1'
        
    def test_publish_only_calls_matching_listeners(self, event_bus):
        """Test that only listeners for the specific event type are called."""
        called1 = []
        called2 = []
        
        def callback1(event: Event):
            called1.append(event)
        
        def callback2(event: Event):
            called2.append(event)
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event2', callback2)
        
        event = Event.create('test.event1', {})
        event_bus.publish(event)
        
        assert len(called1) == 1
        assert len(called2) == 0
        
    def test_publish_handles_listener_errors(self, event_bus):
        """Test that listener errors don't stop other listeners."""
        called = []
        
        def bad_callback(event: Event):
            raise Exception("Callback error")
        
        def good_callback(event: Event):
            called.append(event)
        
        event_bus.subscribe('test.event1', bad_callback)
        event_bus.subscribe('test.event1', good_callback)
        
        event = Event.create('test.event1', {})
        event_bus.publish(event)
        
        # Good callback should still be called despite bad callback's error
        assert len(called) == 1
        
    def test_clear_listeners_specific_type(self, event_bus):
        """Test clearing listeners for specific event type."""
        def callback1(event: Event):
            pass
        
        def callback2(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event2', callback2)
        
        event_bus.clear_listeners('test.event1')
        
        assert event_bus.get_listener_count('test.event1') == 0
        assert event_bus.get_listener_count('test.event2') == 1
        
    def test_clear_all_listeners(self, event_bus):
        """Test clearing all listeners."""
        def callback1(event: Event):
            pass
        
        def callback2(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event2', callback2)
        
        event_bus.clear_listeners()
        
        assert event_bus.get_listener_count() == 0
        
    def test_get_listener_count_total(self, event_bus):
        """Test getting total listener count across all types."""
        def callback1(event: Event):
            pass
        
        def callback2(event: Event):
            pass
        
        def callback3(event: Event):
            pass
        
        event_bus.subscribe('test.event1', callback1)
        event_bus.subscribe('test.event1', callback2)
        event_bus.subscribe('test.event2', callback3)
        
        assert event_bus.get_listener_count() == 3
        
    def test_multiple_events_in_sequence(self, event_bus):
        """Test publishing multiple events in sequence."""
        events_received = []
        
        def callback(event: Event):
            events_received.append(event.event_type)
        
        event_bus.subscribe('test.event1', callback)
        event_bus.subscribe('test.event2', callback)
        
        event1 = Event.create('test.event1', {})
        event2 = Event.create('test.event2', {})
        event3 = Event.create('test.event1', {})
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        event_bus.publish(event3)
        
        assert events_received == ['test.event1', 'test.event2', 'test.event1']
