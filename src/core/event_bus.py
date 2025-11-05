"""
Event bus for Arcane Arsenal.

Provides pub/sub pattern for state change events. All events are logged
to storage and broadcasted to registered listeners.
"""

from typing import Callable, Dict, List
from .models import Event
from .storage import WorldStorage


class EventBus:
    """
    Event bus for publishing and subscribing to state change events.
    
    Implements pub/sub pattern where modules can subscribe to specific event
    types and get notified when those events occur.
    
    All events are automatically logged to storage.
    
    Attributes:
        storage: WorldStorage instance for persisting events
        listeners: Dict mapping event types to lists of callback functions
    """
    
    def __init__(self, storage: WorldStorage):
        """
        Initialize event bus.
        
        Args:
            storage: WorldStorage instance for event logging
        """
        self.storage = storage
        self.listeners: Dict[str, List[Callable[[Event], None]]] = {}
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of event to listen for (e.g., 'entity.created')
            callback: Function to call when event occurs.
                     Must accept Event as parameter.
        
        Examples:
            >>> def on_entity_created(event: Event):
            ...     print(f"Entity created: {event.data['name']}")
            >>> 
            >>> bus.subscribe('entity.created', on_entity_created)
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        
        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: Type of event
            callback: Callback function to remove
        """
        if event_type in self.listeners:
            if callback in self.listeners[event_type]:
                self.listeners[event_type].remove(callback)
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers and log to storage.
        
        Events are:
        1. Logged to storage (persistent audit trail)
        2. Broadcast to all registered listeners for that event type
        
        Args:
            event: Event to publish
        
        Examples:
            >>> event = Event.create(
            ...     'entity.created',
            ...     {'name': 'Test'},
            ...     entity_id='entity_123'
            ... )
            >>> bus.publish(event)
        """
        # Log event to storage first
        self.storage.log_event(event)
        
        # Notify all listeners for this event type
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Don't let one listener's error stop others
                    # In production, this should use proper logging
                    print(f"Error in event listener: {e}")
    
    def clear_listeners(self, event_type: str = None) -> None:
        """
        Clear listeners for a specific event type or all listeners.
        
        Args:
            event_type: Event type to clear listeners for.
                       If None, clears all listeners.
        
        Note:
            Primarily used for testing.
        """
        if event_type:
            if event_type in self.listeners:
                self.listeners[event_type] = []
        else:
            self.listeners = {}
    
    def get_listener_count(self, event_type: str = None) -> int:
        """
        Get the number of listeners for an event type.
        
        Args:
            event_type: Event type to count listeners for.
                       If None, returns total listener count across all types.
        
        Returns:
            Number of registered listeners
        """
        if event_type:
            return len(self.listeners.get(event_type, []))
        else:
            return sum(len(listeners) for listeners in self.listeners.values())
