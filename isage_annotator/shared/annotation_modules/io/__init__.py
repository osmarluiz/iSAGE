"""
Input/Output Components - Annotation persistence

This module contains I/O components:
- json_saver: JSON annotation saving with validation and backup
- json_loader: JSON annotation loading with migration support
- auto_saver: Automatic saving functionality with change detection
- session_manager: Session management with recovery support
- data_validator: Data validation and repair functionality
"""

from .base_io import BaseIO, IOProtocol
from .json_saver import JsonSaver
from .json_loader import JsonLoader
from .auto_saver import AutoSaver
from .session_manager import SessionManager
from .data_validator import DataValidator

__all__ = [
    'BaseIO',
    'IOProtocol',
    'JsonSaver',
    'JsonLoader',
    'AutoSaver',
    'SessionManager',
    'DataValidator'
]