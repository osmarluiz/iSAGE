"""
Dataset module for semantic segmentation.

Provides SemanticDataset and dataloader creation utilities.
"""

from .semantic_dataset import (
    SemanticDataset,
    create_dataloaders,
    get_image_mask_pairs
)

__all__ = [
    'SemanticDataset',
    'create_dataloaders',
    'get_image_mask_pairs',
]
