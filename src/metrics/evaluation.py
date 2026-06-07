"""
Metrics evaluation module for semantic segmentation.

Provides detailed per-class metrics computation matching the format
used in metrics_history.csv for comparison across different losses.

Matches the old notebook approach: collect all predictions, flatten, then compute metrics.
"""
import numpy as np
import torch
from tqdm import tqdm
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def compute_detailed_metrics(model, val_loader, device, num_classes, ignore_index=None):
    """
    Compute detailed per-class metrics on validation set.

    Matches old notebook approach:
    1. Collect ALL predictions and ground truth
    2. Flatten everything
    3. Compute metrics on entire dataset using sklearn

    Args:
        model: PyTorch model for inference
        val_loader: Validation dataloader
        device: Device (cuda/cpu)
        num_classes: Number of classes
        ignore_index: Optional index to ignore in metrics computation

    Returns:
        dict: Metrics dictionary with keys:
            - Iteration: Iteration number (to be filled by caller)
            - Total_TP, Total_FP, Total_FN: Sum across all classes
            - mPrecision, mRecall, mF1-Score, mIoU: Macro-averaged metrics
            - Class_{c}_TP, Class_{c}_FP, Class_{c}_FN: Per-class confusion matrix
            - Class_{c}_Precision, Class_{c}_Recall, Class_{c}_F1-Score, Class_{c}_IoU: Per-class metrics
    """
    model.eval()

    # Collect ALL predictions and ground truth (matching old notebook)
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, masks in tqdm(val_loader, desc="Collecting predictions"):
            images = images.to(device)

            # Get predictions
            outputs = model(images)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()

            # Flatten and extend (matching old notebook)
            all_preds.extend(preds.flatten())
            all_targets.extend(masks.numpy().flatten())

    # Convert to numpy arrays (matching old notebook)
    print("Computing metrics on entire flattened dataset...")
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    # Filter out ignore_index if specified (matching old notebook)
    if ignore_index is not None:
        valid_mask = all_targets != ignore_index
        all_preds = all_preds[valid_mask]
        all_targets = all_targets[valid_mask]

    # Compute confusion matrix (matching old notebook)
    cm = confusion_matrix(all_targets, all_preds, labels=list(range(num_classes)))

    # Extract per-class TP, FP, FN (matching old notebook)
    tp = np.diag(cm)  # True Positives for each class
    fn = cm.sum(axis=1) - tp  # False Negatives
    fp = cm.sum(axis=0) - tp  # False Positives

    # Compute precision, recall, and F1-score for each class (matching old notebook)
    precision, recall, f1_score, _ = precision_recall_fscore_support(
        all_targets, all_preds, average=None, labels=list(range(num_classes)), zero_division=0
    )

    # Compute per-class IoU (matching old notebook)
    iou_per_class = tp / (tp + fp + fn + 1e-8)  # Avoid division by zero
    mean_iou = np.mean(iou_per_class)

    # Build metrics dict (matching old notebook format)
    metrics_dict = {
        'Total_TP': int(tp.sum()),
        'Total_FP': int(fp.sum()),
        'Total_FN': int(fn.sum()),
        'mPrecision': float(np.mean(precision)),
        'mRecall': float(np.mean(recall)),
        'mF1-Score': float(np.mean(f1_score)),
        'mIoU': float(mean_iou),
    }

    # Add per-class metrics
    for c in range(num_classes):
        metrics_dict[f'Class_{c}_TP'] = int(tp[c])
        metrics_dict[f'Class_{c}_FP'] = int(fp[c])
        metrics_dict[f'Class_{c}_FN'] = int(fn[c])
        metrics_dict[f'Class_{c}_Precision'] = float(precision[c])
        metrics_dict[f'Class_{c}_Recall'] = float(recall[c])
        metrics_dict[f'Class_{c}_F1-Score'] = float(f1_score[c])
        metrics_dict[f'Class_{c}_IoU'] = float(iou_per_class[c])

    return metrics_dict
