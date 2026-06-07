"""
Tests for metrics module.
"""

import pytest
import numpy as np
from ..metrics import (
    calculate_confusion_matrix,
    calculate_iou_from_confusion,
    calculate_metrics,
    format_metrics_for_display,
    aggregate_batch_metrics
)


class TestConfusionMatrix:
    """Test confusion matrix calculation."""

    def test_perfect_prediction(self):
        """Test confusion matrix with perfect predictions."""
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 2])

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3)

        # Should be identity matrix (perfect prediction)
        expected = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 2]
        ])

        assert np.array_equal(confusion, expected)

    def test_ignore_index(self):
        """Test that ignore_index pixels are excluded."""
        y_true = np.array([0, 1, 2, 255, 255])
        y_pred = np.array([0, 1, 2, 0, 1])

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3, ignore_index=255)

        # Only first 3 pixels should be counted
        expected = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ])

        assert np.array_equal(confusion, expected)

    def test_misclassification(self):
        """Test confusion matrix with misclassifications."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 1, 1, 2, 2, 0])

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3)

        expected = np.array([
            [1, 1, 0],  # True class 0: 1 correct, 1 predicted as 1
            [0, 1, 1],  # True class 1: 1 correct, 1 predicted as 2
            [1, 0, 1]   # True class 2: 1 correct, 1 predicted as 0
        ])

        assert np.array_equal(confusion, expected)

    def test_2d_input(self):
        """Test confusion matrix with 2D input (image-like)."""
        y_true = np.array([
            [0, 1, 2],
            [0, 1, 2]
        ])
        y_pred = np.array([
            [0, 1, 2],
            [0, 1, 2]
        ])

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3)

        expected = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 2]
        ])

        assert np.array_equal(confusion, expected)

    def test_3d_input(self):
        """Test confusion matrix with 3D input (batch of images)."""
        y_true = np.array([
            [[0, 1], [2, 0]],
            [[1, 2], [0, 1]]
        ])
        y_pred = np.array([
            [[0, 1], [2, 0]],
            [[1, 2], [0, 1]]
        ])

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3)

        expected = np.array([
            [3, 0, 0],
            [0, 3, 0],
            [0, 0, 2]
        ])

        assert np.array_equal(confusion, expected)

    def test_clip_out_of_range(self):
        """Test that out-of-range predictions are clipped."""
        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 10])  # 10 is out of range

        confusion = calculate_confusion_matrix(y_true, y_pred, num_classes=3)

        # Prediction 10 should be clipped to 2
        expected = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ])

        assert np.array_equal(confusion, expected)


class TestIoUCalculation:
    """Test IoU calculation from confusion matrix."""

    def test_perfect_iou(self):
        """Test IoU with perfect predictions."""
        confusion = np.array([
            [10, 0, 0],
            [0, 10, 0],
            [0, 0, 10]
        ])

        iou = calculate_iou_from_confusion(confusion)

        expected = np.array([1.0, 1.0, 1.0])
        assert np.allclose(iou, expected)

    def test_zero_iou(self):
        """Test IoU with completely wrong predictions."""
        confusion = np.array([
            [0, 5, 5],
            [5, 0, 5],
            [5, 5, 0]
        ])

        iou = calculate_iou_from_confusion(confusion)

        expected = np.array([0.0, 0.0, 0.0])
        assert np.allclose(iou, expected)

    def test_partial_iou(self):
        """Test IoU with partial overlap."""
        confusion = np.array([
            [5, 5, 0],   # Class 0: TP=5, FP=5, FN=5, IoU=5/(5+5+5)=1/3
            [5, 5, 0],   # Class 1: TP=5, FP=5, FN=5, IoU=5/(5+5+5)=1/3
            [0, 0, 10]   # Class 2: TP=10, FP=0, FN=0, IoU=1.0
        ])

        iou = calculate_iou_from_confusion(confusion)

        expected = np.array([1/3, 1/3, 1.0])
        assert np.allclose(iou, expected)

    def test_missing_class(self):
        """Test IoU when a class is not present."""
        confusion = np.array([
            [10, 0, 0],
            [0, 0, 0],  # Class 1 never appears
            [0, 0, 10]
        ])

        iou = calculate_iou_from_confusion(confusion)

        # Class 1 should have IoU=0 (division by zero handled)
        expected = np.array([1.0, 0.0, 1.0])
        assert np.allclose(iou, expected)


class TestCalculateMetrics:
    """Test comprehensive metrics calculation."""

    def test_perfect_metrics(self):
        """Test metrics with perfect predictions."""
        y_true = np.array([[0, 1, 2], [0, 1, 2]])
        y_pred = np.array([[0, 1, 2], [0, 1, 2]])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        assert pytest.approx(metrics['miou'], rel=1e-5) == 1.0
        assert pytest.approx(metrics['pixel_accuracy'], rel=1e-5) == 1.0
        assert all(pytest.approx(acc, rel=1e-5) == 1.0 for acc in metrics['per_class_accuracy'])
        assert all(pytest.approx(iou, rel=1e-5) == 1.0 for iou in metrics['per_class_iou'])

    def test_zero_metrics(self):
        """Test metrics with completely wrong predictions."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([1, 2, 0, 2, 0, 1])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        # All predictions are wrong
        assert pytest.approx(metrics['miou'], rel=1e-5) == 0.0
        assert pytest.approx(metrics['pixel_accuracy'], rel=1e-5) == 0.0

    def test_ignore_index_in_metrics(self):
        """Test that ignore_index pixels are excluded from metrics."""
        y_true = np.array([0, 1, 2, 255, 255, 255])
        y_pred = np.array([0, 1, 2, 0, 1, 2])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3, ignore_index=255)

        # Only first 3 pixels should be counted (all correct)
        assert pytest.approx(metrics['miou'], rel=1e-5) == 1.0
        assert pytest.approx(metrics['pixel_accuracy'], rel=1e-5) == 1.0

    def test_partial_metrics(self):
        """Test metrics with partial accuracy."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 1, 1, 1, 2, 0])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        # Pixel accuracy: 4/6 = 0.6667
        assert pytest.approx(metrics['pixel_accuracy'], rel=1e-3) == 4/6

        # Class 0: 1 correct out of 2 = 0.5
        # Class 1: 2 correct out of 2 = 1.0
        # Class 2: 1 correct out of 2 = 0.5
        assert pytest.approx(metrics['per_class_accuracy'][0], rel=1e-3) == 0.5
        assert pytest.approx(metrics['per_class_accuracy'][1], rel=1e-3) == 1.0
        assert pytest.approx(metrics['per_class_accuracy'][2], rel=1e-3) == 0.5

    def test_confusion_matrix_in_output(self):
        """Test that confusion matrix is included in output."""
        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 2])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        assert 'confusion_matrix' in metrics
        assert isinstance(metrics['confusion_matrix'], list)
        assert len(metrics['confusion_matrix']) == 3

    def test_metrics_keys(self):
        """Test that all expected keys are present."""
        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 2])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        expected_keys = ['miou', 'per_class_iou', 'pixel_accuracy', 'per_class_accuracy', 'confusion_matrix']
        for key in expected_keys:
            assert key in metrics

    def test_metrics_types(self):
        """Test that metrics are returned as correct types."""
        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 2])

        metrics = calculate_metrics(y_true, y_pred, num_classes=3)

        assert isinstance(metrics['miou'], float)
        assert isinstance(metrics['pixel_accuracy'], float)
        assert isinstance(metrics['per_class_iou'], list)
        assert isinstance(metrics['per_class_accuracy'], list)
        assert isinstance(metrics['confusion_matrix'], list)


class TestFormatMetrics:
    """Test metrics formatting for display."""

    def test_format_basic(self):
        """Test basic metrics formatting."""
        metrics = {
            'miou': 0.75,
            'pixel_accuracy': 0.85,
            'per_class_iou': [0.7, 0.8, 0.75],
            'per_class_accuracy': [0.8, 0.85, 0.9]
        }
        class_names = ['class0', 'class1', 'class2']

        output = format_metrics_for_display(metrics, class_names)

        # Check that output contains expected strings
        assert 'METRICS SUMMARY' in output
        assert 'Mean IoU' in output
        assert 'Pixel Accuracy' in output
        assert '0.7500' in output  # mIoU
        assert '0.8500' in output  # pixel accuracy
        assert 'class0' in output
        assert 'class1' in output
        assert 'class2' in output

    def test_format_with_different_class_names(self):
        """Test formatting with custom class names."""
        metrics = {
            'miou': 0.6,
            'pixel_accuracy': 0.7,
            'per_class_iou': [0.5, 0.6, 0.7],
            'per_class_accuracy': [0.6, 0.7, 0.8]
        }
        class_names = ['background', 'foreground', 'boundary']

        output = format_metrics_for_display(metrics, class_names)

        assert 'background' in output
        assert 'foreground' in output
        assert 'boundary' in output

    def test_format_structure(self):
        """Test that formatted output has expected structure."""
        metrics = {
            'miou': 0.5,
            'pixel_accuracy': 0.6,
            'per_class_iou': [0.5],
            'per_class_accuracy': [0.6]
        }
        class_names = ['single_class']

        output = format_metrics_for_display(metrics, class_names)

        lines = output.split('\n')

        # Check structure
        assert '=' * 60 in output  # Header separator
        assert '-' * 60 in output  # Table separator
        assert 'Class' in output
        assert 'IoU' in output
        assert 'Accuracy' in output


class TestAggregateBatchMetrics:
    """Test batch metrics aggregation."""

    def test_aggregate_uniform_weights(self):
        """Test aggregation with uniform weights."""
        batch_metrics = [
            {'miou': 0.5, 'pixel_accuracy': 0.6, 'per_class_iou': [0.4, 0.6], 'per_class_accuracy': [0.5, 0.7]},
            {'miou': 0.7, 'pixel_accuracy': 0.8, 'per_class_iou': [0.6, 0.8], 'per_class_accuracy': [0.7, 0.9]}
        ]

        aggregated = aggregate_batch_metrics(batch_metrics)

        # Simple average
        assert pytest.approx(aggregated['miou'], rel=1e-5) == 0.6
        assert pytest.approx(aggregated['pixel_accuracy'], rel=1e-5) == 0.7
        assert pytest.approx(aggregated['per_class_iou'][0], rel=1e-5) == 0.5
        assert pytest.approx(aggregated['per_class_iou'][1], rel=1e-5) == 0.7

    def test_aggregate_weighted(self):
        """Test aggregation with custom weights."""
        batch_metrics = [
            {'miou': 0.5, 'pixel_accuracy': 0.6},
            {'miou': 0.8, 'pixel_accuracy': 0.9}
        ]
        weights = [1, 3]  # Second batch has 3x weight

        aggregated = aggregate_batch_metrics(batch_metrics, weights)

        # Weighted average: (0.5*1 + 0.8*3) / 4 = 0.6875
        assert pytest.approx(aggregated['miou'], rel=1e-5) == 0.6875
        # Weighted average: (0.6*1 + 0.9*3) / 4 = 0.825
        assert pytest.approx(aggregated['pixel_accuracy'], rel=1e-5) == 0.825

    def test_aggregate_per_class_metrics(self):
        """Test that per-class metrics are aggregated correctly."""
        batch_metrics = [
            {'per_class_iou': [0.4, 0.6, 0.8], 'per_class_accuracy': [0.5, 0.7, 0.9]},
            {'per_class_iou': [0.6, 0.8, 1.0], 'per_class_accuracy': [0.7, 0.9, 1.0]}
        ]

        aggregated = aggregate_batch_metrics(batch_metrics)

        # Per-class averages
        assert pytest.approx(aggregated['per_class_iou'][0], rel=1e-5) == 0.5
        assert pytest.approx(aggregated['per_class_iou'][1], rel=1e-5) == 0.7
        assert pytest.approx(aggregated['per_class_iou'][2], rel=1e-5) == 0.9

    def test_aggregate_empty_list(self):
        """Test aggregation with empty list."""
        aggregated = aggregate_batch_metrics([])

        assert aggregated == {}

    def test_aggregate_single_batch(self):
        """Test aggregation with single batch."""
        batch_metrics = [
            {'miou': 0.75, 'pixel_accuracy': 0.85}
        ]

        aggregated = aggregate_batch_metrics(batch_metrics)

        # Should return same values
        assert pytest.approx(aggregated['miou'], rel=1e-5) == 0.75
        assert pytest.approx(aggregated['pixel_accuracy'], rel=1e-5) == 0.85
