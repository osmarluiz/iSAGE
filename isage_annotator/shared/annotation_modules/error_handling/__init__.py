"""
Error Handling Module for Annotation System
Provides comprehensive error handling, recovery, and reporting.
Based on legacy ABILIUS error handling implementations.
"""

from .error_manager import ErrorManager, get_global_error_manager
from .error_reporter import ErrorReporter
from .error_recovery import ErrorRecovery
from .error_dialogs import ErrorDialogs
from .error_logger import ErrorLogger

__all__ = [
    'ErrorManager',
    'get_global_error_manager',
    'ErrorReporter',
    'ErrorRecovery',
    'ErrorDialogs',
    'ErrorLogger'
]