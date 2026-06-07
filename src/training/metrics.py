"""
Metrics calculation for semantic segmentation.

Provides functions for calculating IoU, pixel accuracy, and confusion matrices.
"""

from typing import Dict, List
import numpy as np


def calculate_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int,
    ignore_index: int = 255
) -> np.ndarray:
    """
    Computes confusion matrix for semantic segmentation.

    Args:
        y_true: Ground truth labels (H, W) or (N, H, W)
        y_pred: Predicted labels (H, W) or (N, H, W)
        num_classes: Number of classes (excluding ignore_index)
        ignore_index: Value to ignore in calculations

    Returns:
        Confusion matrix of shape (num_classes, num_classes)
    """
    # Flatten arrays
    y_true = y_true.flatten()
    y_pred = y_pred.flatten()

    # Create mask for valid pixels (not ignore_index)
    valid_mask = y_true != ignore_index

    # Filter out ignore_index pixels
    y_true = y_true[valid_mask]
    y_pred = y_pred[valid_mask]

    # Clip predictions to valid range
    y_pred = np.clip(y_pred, 0, num_classes - 1)
    y_true = np.clip(y_true, 0, num_classes - 1)

    # Compute confusion matrix
    # Using bincount for efficiency
    confusion = np.bincount(
        num_classes * y_true + y_pred,
        minlength=num_classes ** 2
    ).reshape(num_classes, num_classes)

    return confusion


def calculate_iou_from_confusion(confusion: np.ndarray) -> np.ndarray:
    """
    Calculate IoU for each class from confusion matrix.

    Args:
        confusion: Confusion matrix of shape (num_classes, num_classes)

    Returns:
        Array of IoU values for each class
    """
    # Intersection: diagonal elements
    intersection = np.diag(confusion)

    # Union: sum of row + sum of column - intersection
    ground_truth_set = confusion.sum(axis=1)
    predicted_set = confusion.sum(axis=0)
    union = ground_truth_set + predicted_set - intersection

    # Avoid division by zero
    iou = np.zeros(len(intersection))
    valid = union > 0
    iou[valid] = intersection[valid] / union[valid]

    return iou


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int,
    ignore_index: int = 255
) -> Dict[str, any]:
    """
    Calculate comprehensive metrics for semantic segmentation.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        num_classes: Number of classes
        ignore_index: Value to ignore in calculations

    Returns:
        Dictionary containing:
            - miou: Mean Intersection over Union
            - per_class_iou: List of IoU values per class
            - pixel_accuracy: Overall pixel accuracy
            - per_class_accuracy: List of accuracy values per class
            - confusion_matrix: Confusion matrix
    """
    # Calculate confusion matrix
    confusion = calculate_confusion_matrix(y_true, y_pred, num_classes, ignore_index)

    # Calculate IoU
    per_class_iou = calculate_iou_from_confusion(confusion)
    miou = np.nanmean(per_class_iou)

    # Calculate pixel accuracy
    # Flatten and filter
    y_true_flat = y_true.flatten()
    y_pred_flat = y_pred.flatten()
    valid_mask = y_true_flat != ignore_index
    y_true_flat = y_true_flat[valid_mask]
    y_pred_flat = y_pred_flat[valid_mask]

    # Clip to valid range
    y_pred_flat = np.clip(y_pred_flat, 0, num_classes - 1)
    y_true_flat = np.clip(y_true_flat, 0, num_classes - 1)

    # Overall accuracy
    correct = (y_true_flat == y_pred_flat).sum()
    total = len(y_true_flat)
    pixel_accuracy = correct / total if total > 0 else 0.0

    # Per-class accuracy
    per_class_accuracy = []
    for class_id in range(num_classes):
        class_mask = y_true_flat == class_id
        if class_mask.sum() > 0:
            class_correct = ((y_true_flat == class_id) & (y_pred_flat == class_id)).sum()
            class_acc = class_correct / class_mask.sum()
            per_class_accuracy.append(float(class_acc))
        else:
            per_class_accuracy.append(0.0)

    return {
        'miou': float(miou),
        'per_class_iou': per_class_iou.tolist(),
        'pixel_accuracy': float(pixel_accuracy),
        'per_class_accuracy': per_class_accuracy,
        'confusion_matrix': confusion.tolist()
    }


def format_metrics_for_display(metrics: Dict, class_names: List[str]) -> str:
    """
    Pretty-prints metrics with class names.

    Args:
        metrics: Dictionary of metrics from calculate_metrics()
        class_names: List of class names

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("=" * 60)
    lines.append("METRICS SUMMARY")
    lines.append("=" * 60)

    # Overall metrics
    lines.append(f"\nOverall Performance:")
    lines.append(f"  Mean IoU:        {metrics['miou']:.4f}")
    lines.append(f"  Pixel Accuracy:  {metrics['pixel_accuracy']:.4f}")

    # Per-class metrics
    lines.append(f"\nPer-Class Performance:")
    lines.append("-" * 60)
    lines.append(f"{'Class':<20} {'IoU':>10} {'Accuracy':>10}")
    lines.append("-" * 60)

    per_class_iou = metrics.get('per_class_iou', [])
    per_class_acc = metrics.get('per_class_accuracy', [])

    for i, class_name in enumerate(class_names):
        iou = per_class_iou[i] if i < len(per_class_iou) else 0.0
        acc = per_class_acc[i] if i < len(per_class_acc) else 0.0
        lines.append(f"{class_name:<20} {iou:>10.4f} {acc:>10.4f}")

    lines.append("=" * 60)

    return "\n".join(lines)


def aggregate_batch_metrics(
    batch_metrics_list: List[Dict],
    weights: List[int] = None
) -> Dict:
    """
    Aggregate metrics from multiple batches with optional weighting.

    Args:
        batch_metrics_list: List of metric dictionaries
        weights: Optional list of weights (e.g., batch sizes) for weighted average

    Returns:
        Aggregated metrics dictionary
    """
    if not batch_metrics_list:
        return {}

    if weights is None:
        weights = [1] * len(batch_metrics_list)

    total_weight = sum(weights)

    # Aggregate scalar metrics (weighted average)
    scalar_keys = ['miou', 'pixel_accuracy']
    aggregated = {}

    for key in scalar_keys:
        if key in batch_metrics_list[0]:
            weighted_sum = sum(
                metrics[key] * weight
                for metrics, weight in zip(batch_metrics_list, weights)
            )
            aggregated[key] = weighted_sum / total_weight

    # Aggregate per-class metrics (weighted average)
    if 'per_class_iou' in batch_metrics_list[0]:
        num_classes = len(batch_metrics_list[0]['per_class_iou'])
        aggregated['per_class_iou'] = []

        for class_id in range(num_classes):
            weighted_sum = sum(
                metrics['per_class_iou'][class_id] * weight
                for metrics, weight in zip(batch_metrics_list, weights)
            )
            aggregated['per_class_iou'].append(weighted_sum / total_weight)

    if 'per_class_accuracy' in batch_metrics_list[0]:
        num_classes = len(batch_metrics_list[0]['per_class_accuracy'])
        aggregated['per_class_accuracy'] = []

        for class_id in range(num_classes):
            weighted_sum = sum(
                metrics['per_class_accuracy'][class_id] * weight
                for metrics, weight in zip(batch_metrics_list, weights)
            )
            aggregated['per_class_accuracy'].append(weighted_sum / total_weight)

    return aggregated
