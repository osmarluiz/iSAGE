"""
Helper functions for computing class weights from sparse annotations.

For use with DWCDL and DWCDLMulticlass losses in active learning scenarios.
"""

import json
import torch
from pathlib import Path
from typing import Literal


def compute_class_weights_from_annotations(
    annotations_dir: Path,
    num_classes: int,
    ignore_index: int,
    mode: Literal['inverse', 'effective_samples'] = 'inverse',
    normalize: bool = True
) -> torch.Tensor:
    """
    Compute class weights from sparse annotation JSONs.

    Args:
        annotations_dir: Path to annotations folder (e.g., Sessions/BSB_LAYER0/iteration_0/annotations)
        num_classes: Number of classes (excluding ignore_index)
        ignore_index: Index to ignore
        mode: Weight computation method:
            - 'inverse': weights = 1 / count (simple inverse frequency)
            - 'effective_samples': weights = (1-beta) / (1-beta^count) (handles extreme imbalance)
        normalize: If True, normalize weights so mean = 1.0

    Returns:
        torch.Tensor of shape (num_classes,) with per-class weights

    Example:
        >>> from pathlib import Path
        >>> weights = compute_class_weights_from_annotations(
        ...     annotations_dir=Path('Sessions/BSB_LAYER0/iteration_0/annotations'),
        ...     num_classes=9,
        ...     ignore_index=9,
        ...     mode='inverse'
        ... )
        >>> print(f"Class weights: {weights}")
        Class weights: tensor([0.5, 2.0, 3.5, 1.0, 0.8, 5.0, 4.2, 10.0, 8.5])
    """
    annotations_dir = Path(annotations_dir)

    if not annotations_dir.exists():
        raise FileNotFoundError(f"Annotations directory not found: {annotations_dir}")

    # Count annotations per class
    class_counts = torch.zeros(num_classes, dtype=torch.float32)

    json_files = list(annotations_dir.glob('*.json'))
    if len(json_files) == 0:
        print(f"Warning: No annotation files found in {annotations_dir}")
        return torch.ones(num_classes)

    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                annotations = data.get('annotations', [])
                for annotation in annotations:
                    # Format: [x, y, class_id]
                    if len(annotation) >= 3:
                        class_id = annotation[2]
                        if class_id != ignore_index and 0 <= class_id < num_classes:
                            class_counts[class_id] += 1
        except Exception as e:
            print(f"Warning: Could not read {json_file.name}: {e}")
            continue

    # Compute weights based on mode
    if mode == 'inverse':
        # Simple inverse frequency
        # Add 1.0 to avoid division by zero for classes with no annotations
        weights = 1.0 / (class_counts + 1.0)

    elif mode == 'effective_samples':
        # Effective number of samples (better for extreme imbalance)
        # Paper: "Class-Balanced Loss Based on Effective Number of Samples"
        # beta controls how quickly weights saturate (higher = more aggressive)
        beta = 0.999
        effective_num = 1.0 - torch.pow(beta, class_counts)
        weights = (1.0 - beta) / (effective_num + 1e-7)

    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'inverse' or 'effective_samples'")

    # Normalize so mean weight = 1.0
    if normalize:
        weights = weights / (weights.mean() + 1e-8) * num_classes / num_classes

    # Print summary
    print("\nClass Weight Summary:")
    print(f"{'Class':<6} {'Count':<10} {'Weight':<10}")
    print("-" * 30)
    for i in range(num_classes):
        print(f"{i:<6} {int(class_counts[i]):<10} {weights[i].item():<10.3f}")
    print()

    return weights


def compute_class_weights_from_masks(
    masks_dir: Path,
    num_classes: int,
    ignore_index: int,
    mode: Literal['inverse', 'effective_samples'] = 'inverse',
    normalize: bool = True
) -> torch.Tensor:
    """
    Compute class weights from dense mask PNGs.

    Args:
        masks_dir: Path to masks folder (e.g., Sessions/BSB_LAYER0/iteration_0/masks)
        num_classes: Number of classes (excluding ignore_index)
        ignore_index: Index to ignore
        mode: Weight computation method ('inverse' or 'effective_samples')
        normalize: If True, normalize weights so mean = 1.0

    Returns:
        torch.Tensor of shape (num_classes,) with per-class weights

    Example:
        >>> weights = compute_class_weights_from_masks(
        ...     masks_dir=Path('Sessions/BSB_LAYER0/iteration_0/masks'),
        ...     num_classes=9,
        ...     ignore_index=9
        ... )
    """
    from PIL import Image
    import numpy as np

    masks_dir = Path(masks_dir)

    if not masks_dir.exists():
        raise FileNotFoundError(f"Masks directory not found: {masks_dir}")

    # Count pixels per class
    class_counts = torch.zeros(num_classes, dtype=torch.float32)

    mask_files = list(masks_dir.glob('*.png'))
    if len(mask_files) == 0:
        print(f"Warning: No mask files found in {masks_dir}")
        return torch.ones(num_classes)

    for mask_file in mask_files:
        try:
            mask = np.array(Image.open(mask_file))
            for class_id in range(num_classes):
                if class_id != ignore_index:
                    class_counts[class_id] += (mask == class_id).sum()
        except Exception as e:
            print(f"Warning: Could not read {mask_file.name}: {e}")
            continue

    # Compute weights (same logic as annotations)
    if mode == 'inverse':
        weights = 1.0 / (class_counts + 1.0)
    elif mode == 'effective_samples':
        beta = 0.999
        effective_num = 1.0 - torch.pow(beta, class_counts)
        weights = (1.0 - beta) / (effective_num + 1e-7)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if normalize:
        weights = weights / (weights.mean() + 1e-8)

    # Print summary
    print("\nClass Weight Summary (from masks):")
    print(f"{'Class':<6} {'Pixels':<10} {'Weight':<10}")
    print("-" * 30)
    for i in range(num_classes):
        print(f"{i:<6} {int(class_counts[i]):<10} {weights[i].item():<10.3f}")
    print()

    return weights
