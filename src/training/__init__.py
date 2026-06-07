"""
Training module for active learning system.

Provides trainer class for model training and metrics calculation.
"""

from .trainer import ActiveLearningTrainer
from .metrics import (
    calculate_confusion_matrix,
    calculate_iou_from_confusion,
    calculate_metrics,
    format_metrics_for_display,
    aggregate_batch_metrics
)

__all__ = [
    'ActiveLearningTrainer',
    'calculate_confusion_matrix',
    'calculate_iou_from_confusion',
    'calculate_metrics',
    'format_metrics_for_display',
    'aggregate_batch_metrics'
]
