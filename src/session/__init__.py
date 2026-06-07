"""
Session management module.

Provides SessionManager for handling session lifecycle, iterations, and metrics.
"""

from .session_manager import SessionManager
from .mask_utils import (
    initialize_iteration_masks,
    json_to_mask,
    batch_json_to_masks,
    validate_mask_json_pair,
    count_annotation_points,
    count_total_annotations
)

__all__ = [
    'SessionManager',
    'initialize_iteration_masks',
    'json_to_mask',
    'batch_json_to_masks',
    'validate_mask_json_pair',
    'count_annotation_points',
    'count_total_annotations',
]
