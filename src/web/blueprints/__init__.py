"""
Flask blueprints for Arcane Arsenal web interface.

- host: DM/Host interface for state management
- client: Player interface for character management
"""

from .host import host_bp
from .client import client_bp

__all__ = ['host_bp', 'client_bp']
