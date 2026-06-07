"""
Performance Components - Optimization utilities

This module contains performance optimization components:
- layer_cache: Optimized rendering with layer caching
- memory_manager: Memory cleanup and management
- async_operations: Asynchronous operations for UI responsiveness
"""

from .base_performance import BasePerformance, PerformanceProtocol

__all__ = [
    'BasePerformance',
    'PerformanceProtocol'
]