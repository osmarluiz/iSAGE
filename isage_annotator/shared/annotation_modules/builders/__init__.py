"""
Builders - Composition layer for creating annotation interfaces

This module contains builder components:
- annotation_builder: Main builder for composing annotation interfaces
- active_learning_preset: Pre-configured active learning setup with model integration
"""

from .base_builder import BaseBuilder, BuilderProtocol
from .annotation_builder import AnnotationBuilder
from .active_learning_preset import ActiveLearningPreset

__all__ = [
    'BaseBuilder',
    'BuilderProtocol',
    'AnnotationBuilder',
    'ActiveLearningPreset'
]