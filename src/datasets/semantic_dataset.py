"""
Semantic segmentation dataset for sparse point annotation training.

Handles loading images and sparse masks with synchronized transforms.
"""

import random
from pathlib import Path
from typing import List, Tuple, Optional, Callable
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import imageio.v2 as imageio


class SemanticDataset(Dataset):
    """
    Dataset for semantic segmentation with sparse point annotations.

    Handles synchronized transforms for images and masks to ensure
    augmentations are applied consistently.
    """

    def __init__(
        self,
        image_paths: List[Path],
        mask_paths: List[Path],
        transform: Optional[Callable] = None,
        transform_label: Optional[Callable] = None,
        ignore_index: int = 255,
        is_validation: bool = False
    ):
        """
        Initialize dataset.

        Args:
            image_paths: List of paths to image files
            mask_paths: List of paths to mask files
            transform: Transform to apply to images
            transform_label: Transform to apply to masks
            ignore_index: Value to use for ignore index in masks
            is_validation: Whether this is validation data (affects some transforms)
        """
        self.image_paths = [Path(p) for p in image_paths]
        self.mask_paths = [Path(p) for p in mask_paths]
        self.transform = transform
        self.transform_label = transform_label
        self.ignore_index = ignore_index
        self.is_validation = is_validation

        # Validate inputs
        if len(self.image_paths) != len(self.mask_paths):
            raise ValueError(
                f"Number of images ({len(self.image_paths)}) must match "
                f"number of masks ({len(self.mask_paths)})"
            )

        # Verify all files exist
        for img_path in self.image_paths:
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {img_path}")

        for mask_path in self.mask_paths:
            if not mask_path.exists():
                raise FileNotFoundError(f"Mask not found: {mask_path}")

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get image and mask pair at index.

        Args:
            index: Index of sample to retrieve

        Returns:
            Tuple of (image_tensor, mask_tensor)
        """
        # Load image and mask
        image = imageio.imread(self.image_paths[index])
        image = np.asarray(image, dtype='float32')

        mask = imageio.imread(self.mask_paths[index])
        mask = np.asarray(mask, dtype='int64')

        # Ensure mask values don't exceed ignore_index
        # Values > ignore_index are set to ignore_index
        mask[mask > self.ignore_index] = self.ignore_index

        # Generate random seed for synchronized transforms
        seed = np.random.randint(2147483647)

        # Apply transforms to image
        if self.transform:
            random.seed(seed)
            torch.manual_seed(seed)
            image = self.transform(image)

        # Apply transforms to mask with same seed
        if self.transform_label:
            random.seed(seed)
            torch.manual_seed(seed)
            mask = self.transform_label(mask)

            # Remove channel dimension if present (masks should be 2D)
            if mask.dim() == 3 and mask.shape[0] == 1:
                mask = mask.squeeze(0)

        return image, mask

    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self.image_paths)


def create_dataloaders(
    session_manager,
    iteration: int,
    dataset_config: dict,
    training_config: dict,
    preprocessing_fn: Optional[Callable] = None
) -> Tuple[DataLoader, Optional[DataLoader]]:
    """
    Create train and validation dataloaders for a specific iteration.

    Args:
        session_manager: SessionManager instance
        iteration: Iteration number to load masks from
        dataset_config: Dataset configuration dictionary
        training_config: Training configuration dictionary
        preprocessing_fn: Optional preprocessing function (e.g., from encoder)

    Returns:
        Tuple of (train_loader, val_loader) - val_loader is None if no validation data
    """
    from torchvision import transforms

    # Get paths from dataset config
    train_image_dir = Path(dataset_config['paths']['train_images'])

    # Check if validation data exists
    val_image_path = dataset_config['paths'].get('val_images')
    val_mask_path = dataset_config['paths'].get('val_masks')
    has_validation = val_image_path is not None and val_mask_path is not None

    # Get iteration-specific mask directory
    iteration_path = session_manager.get_iteration_path(iteration)
    train_mask_dir = iteration_path / 'masks'

    # Make paths absolute if relative
    if not train_image_dir.is_absolute():
        train_image_dir = Path.cwd() / train_image_dir

    # Get sorted list of training images and masks (support PNG, TIF, TIFF)
    train_images = sorted(list(train_image_dir.glob('*.png')) + list(train_image_dir.glob('*.tif')) + list(train_image_dir.glob('*.tiff')))
    train_masks = sorted(train_mask_dir.glob('*.png'))

    # Verify we have matching files
    if len(train_images) != len(train_masks):
        raise ValueError(
            f"Mismatch in training data: {len(train_images)} images, "
            f"{len(train_masks)} masks"
        )

    # Handle validation data
    val_images = []
    val_masks = []
    if has_validation:
        val_image_dir = Path(val_image_path)
        val_mask_dir = Path(val_mask_path)

        if not val_image_dir.is_absolute():
            val_image_dir = Path.cwd() / val_image_dir
        if not val_mask_dir.is_absolute():
            val_mask_dir = Path.cwd() / val_mask_dir

        # Get sorted list of validation images and masks (support PNG, TIF, TIFF)
        val_images = sorted(list(val_image_dir.glob('*.png')) + list(val_image_dir.glob('*.tif')) + list(val_image_dir.glob('*.tiff')))
        val_masks = sorted(val_mask_dir.glob('*.png'))

        if len(val_images) != len(val_masks):
            raise ValueError(
                f"Mismatch in validation data: {len(val_images)} images, "
                f"{len(val_masks)} masks"
            )

    # Define transforms
    transform_list = [transforms.ToTensor()]

    # Add preprocessing if provided (e.g., encoder-specific normalization)
    if preprocessing_fn is not None:
        transform_list.append(transforms.Lambda(lambda x: preprocessing_fn(x.numpy())))

    image_transform = transforms.Compose(transform_list)
    mask_transform = transforms.ToTensor()

    # Get ignore index from dataset config
    ignore_index = dataset_config['classes']['ignore_index']

    # Create datasets
    train_dataset = SemanticDataset(
        image_paths=train_images,
        mask_paths=train_masks,
        transform=image_transform,
        transform_label=mask_transform,
        ignore_index=ignore_index,
        is_validation=False
    )

    # Get batch sizes from training config
    train_batch_size = training_config['training']['batch_size']['train']
    val_batch_size = training_config['training']['batch_size']['val']
    num_workers = training_config['training'].get('num_workers', 0)

    # Create train dataloader
    train_loader = DataLoader(
        train_dataset,
        batch_size=train_batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )

    # Create val dataloader only if validation data exists
    val_loader = None
    if has_validation and len(val_images) > 0:
        val_dataset = SemanticDataset(
            image_paths=val_images,
            mask_paths=val_masks,
            transform=image_transform,
            transform_label=mask_transform,
            ignore_index=ignore_index,
            is_validation=True
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=val_batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available()
        )

    return train_loader, val_loader


def get_image_mask_pairs(image_dir: Path, mask_dir: Path) -> Tuple[List[Path], List[Path]]:
    """
    Get matched pairs of images and masks from directories.

    Args:
        image_dir: Directory containing images
        mask_dir: Directory containing masks

    Returns:
        Tuple of (image_paths, mask_paths) in matching order

    Raises:
        ValueError: If images and masks don't match
    """
    image_dir = Path(image_dir)
    mask_dir = Path(mask_dir)

    # Get all images and masks
    images = sorted(image_dir.glob('*.png'))
    masks = sorted(mask_dir.glob('*.png'))

    # Verify matching names
    image_stems = {img.stem for img in images}
    mask_stems = {mask.stem for mask in masks}

    missing_masks = image_stems - mask_stems
    extra_masks = mask_stems - image_stems

    if missing_masks:
        raise ValueError(f"Images without matching masks: {missing_masks}")

    if extra_masks:
        raise ValueError(f"Masks without matching images: {extra_masks}")

    # Return matched pairs
    matched_images = []
    matched_masks = []

    for img in images:
        mask = mask_dir / f"{img.stem}.png"
        matched_images.append(img)
        matched_masks.append(mask)

    return matched_images, matched_masks
