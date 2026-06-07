"""
DataLoader creation module for training.
"""
from pathlib import Path
import numpy as np
import imageio
import torch
import torch.utils.data as data
from torchvision import transforms


class CustomDataset(data.Dataset):
    """
    Custom dataset for semantic segmentation.

    When augment=True, applies hflip/vflip/rot90 to image+mask with shared
    parameters drawn from numpy's global RNG. The global torch and python
    RNG state is never touched, so the training loop's randomness stays
    seeded by set_seed(SEED) at the top of the run.
    """
    def __init__(self, image_paths, mask_paths, ignore_index, transform=None, augment=False):
        self.image_paths = image_paths
        self.mask_paths = mask_paths
        self.ignore_index = ignore_index
        self.transform = transform
        self.augment = augment

    def __getitem__(self, index):
        image = imageio.imread(self.image_paths[index])
        image = np.asarray(image, dtype='float32')

        mask = imageio.imread(self.mask_paths[index])
        mask = np.asarray(mask, dtype='int64')
        mask[mask > self.ignore_index] = self.ignore_index

        if self.transform is not None:
            image = self.transform(image)

        mask = torch.from_numpy(mask).long()

        if self.augment:
            flip_h = bool(np.random.rand() < 0.5)
            flip_v = bool(np.random.rand() < 0.5)
            k = int(np.random.randint(0, 4))
            if flip_h:
                image = torch.flip(image, dims=[2])
                mask = torch.flip(mask, dims=[1])
            if flip_v:
                image = torch.flip(image, dims=[1])
                mask = torch.flip(mask, dims=[0])
            if k > 0:
                image = torch.rot90(image, k, dims=[1, 2])
                mask = torch.rot90(mask, k, dims=[0, 1])

        return image, mask

    def __len__(self):
        return len(self.image_paths)


def create_dataloaders(dataset_config, training_config, masks_dir):
    """
    Create train and validation dataloaders.

    Args:
        dataset_config: Dataset configuration dict
        training_config: Training configuration dict
        masks_dir: Path to training masks directory

    Returns:
        train_loader: Training dataloader
        val_loader: Validation dataloader
        train_images: List of training image paths (for prediction generation)
        base_transform: Base transform WITHOUT augmentation (for predictions)
        class_pixel_counts: Array of annotated pixel counts per class
    """
    print("Creating dataloaders...")

    # Check if dataset has normalization config
    normalization_config = dataset_config.get('normalization', None)

    if normalization_config:
        mean = normalization_config['mean']
        std = normalization_config['std']
        normalize = transforms.Normalize(mean=mean, std=std)
        print(f"  Normalization: ENABLED (dataset-specific)")
        print(f"    Mean: {mean}")
        print(f"    Std:  {std}")

        base_transform = transforms.Compose([
            transforms.ToTensor(),
            normalize
        ])
        train_transform = base_transform
    else:
        print(f"  Normalization: DISABLED (no config found)")

        base_transform = transforms.Compose([
            transforms.ToTensor()
        ])
        train_transform = base_transform

    print(f"  Augmentation: ENABLED (hflip + vflip + rot90, synced image+mask via numpy RNG)")

    # Get train images and masks
    train_images_dir = Path(dataset_config['paths']['train_images'])
    train_images = sorted(list(train_images_dir.glob('*.png')) +
                         list(train_images_dir.glob('*.tif')) +
                         list(train_images_dir.glob('*.tiff')))
    train_masks = sorted(list(Path(masks_dir).glob('*.png')))

    print(f"  Train images: {len(train_images)}")
    print(f"  Train masks:  {len(train_masks)}")

    if len(train_images) != len(train_masks):
        raise ValueError(f"Mismatch: {len(train_images)} images but {len(train_masks)} masks")

    # Get validation images and masks (optional — None or missing dir = no val pass)
    val_images_path = dataset_config['paths'].get('val_images')
    val_masks_path = dataset_config['paths'].get('val_masks')
    val_available = (
        val_images_path is not None
        and val_masks_path is not None
        and Path(val_images_path).exists()
        and Path(val_masks_path).exists()
    )
    if val_available:
        val_images_dir = Path(val_images_path)
        val_masks_dir = Path(val_masks_path)
        val_images = sorted(list(val_images_dir.glob('*.png')) +
                           list(val_images_dir.glob('*.tif')) +
                           list(val_images_dir.glob('*.tiff')))
        val_masks = sorted(list(val_masks_dir.glob('*.png')))
        print(f"  Val images:   {len(val_images)}")
        print(f"  Val masks:    {len(val_masks)}")
        if not val_images or not val_masks:
            val_available = False
            print(f"  → val directories empty; training without validation")
    else:
        print(f"  Val images:   (none — training without validation)")

    # Get ignore index from configuration
    ignore_index = dataset_config['classes']['ignore_index']
    print(f"  Ignore index: {ignore_index}")

    # Count annotated pixels per class
    num_classes = dataset_config['classes']['num_classes']
    class_names = dataset_config['classes']['names']
    class_pixel_counts = np.zeros(num_classes, dtype=np.int64)

    print(f"\n  Counting annotated pixels per class...")
    for mask_path in train_masks:
        mask = imageio.imread(mask_path)
        mask = np.asarray(mask, dtype='int64')
        for class_id in range(num_classes):
            class_pixel_counts[class_id] += np.sum(mask == class_id)

    print(f"  Annotated pixels by class:")
    total_pixels = 0
    for class_id in range(num_classes):
        count = class_pixel_counts[class_id]
        total_pixels += count
        if count > 0:
            print(f"    Class {class_id} ({class_names[class_id]}): {count:,} pixels")
        else:
            print(f"    Class {class_id} ({class_names[class_id]}): 0 pixels (no annotations)")
    print(f"  Total annotated pixels: {total_pixels:,}")
    print()

    train_dataset = CustomDataset(
        train_images,
        train_masks,
        ignore_index=ignore_index,
        transform=train_transform,
        augment=True,
    )

    # Create data loaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=training_config['training']['batch_size']['train'],
        shuffle=False,  # Like old notebook
        num_workers=0,
        pin_memory=True  # Faster CPU→GPU transfer
    )

    if val_available:
        val_dataset = CustomDataset(
            val_images,
            val_masks,
            ignore_index=ignore_index,
            transform=base_transform,
            augment=False,
        )
        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=training_config['training']['batch_size']['val'],
            shuffle=False,
            num_workers=0,
            pin_memory=True,
        )
    else:
        val_loader = None

    print(f"✓ Dataloaders created")
    print(f"  Train batches: {len(train_loader)}")
    if val_loader is not None:
        print(f"  Val batches:   {len(val_loader)}\n")
    else:
        print(f"  Val batches:   none\n")

    return train_loader, val_loader, train_images, base_transform, class_pixel_counts
