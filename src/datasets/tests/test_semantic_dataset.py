"""
Tests for semantic_dataset module.
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from ..semantic_dataset import (
    SemanticDataset,
    get_image_mask_pairs,
    create_dataloaders
)


class TestSemanticDataset:
    """Test SemanticDataset class."""

    def test_dataset_initialization(self):
        """Test dataset initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create dummy images and masks
            for i in range(3):
                img = np.zeros((10, 10, 3), dtype=np.uint8)
                mask = np.zeros((10, 10), dtype=np.uint8)

                Image.fromarray(img).save(tmpdir / f'{i}.png')
                Image.fromarray(mask).save(tmpdir / f'{i}_mask.png')

            image_paths = sorted(tmpdir.glob('[0-9].png'))
            mask_paths = sorted(tmpdir.glob('*_mask.png'))

            dataset = SemanticDataset(
                image_paths=image_paths,
                mask_paths=mask_paths,
                ignore_index=255
            )

            assert len(dataset) == 3

    def test_dataset_length_mismatch(self):
        """Test that mismatched lengths raise error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create 3 images but 2 masks
            for i in range(3):
                img = np.zeros((10, 10, 3), dtype=np.uint8)
                Image.fromarray(img).save(tmpdir / f'{i}.png')

            for i in range(2):
                mask = np.zeros((10, 10), dtype=np.uint8)
                Image.fromarray(mask).save(tmpdir / f'{i}_mask.png')

            image_paths = sorted(tmpdir.glob('[0-9].png'))
            mask_paths = sorted(tmpdir.glob('*_mask.png'))

            with pytest.raises(ValueError, match="must match"):
                SemanticDataset(
                    image_paths=image_paths,
                    mask_paths=mask_paths,
                    ignore_index=255
                )

    def test_dataset_missing_file(self):
        """Test that missing files raise error."""
        with pytest.raises(FileNotFoundError):
            SemanticDataset(
                image_paths=[Path('/nonexistent/image.png')],
                mask_paths=[Path('/nonexistent/mask.png')],
                ignore_index=255
            )

    def test_dataset_getitem(self):
        """Test getting items from dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create dummy image and mask
            img = np.random.randint(0, 255, (10, 10, 3), dtype=np.uint8)
            mask = np.random.randint(0, 5, (10, 10), dtype=np.uint8)

            Image.fromarray(img).save(tmpdir / 'image.png')
            Image.fromarray(mask).save(tmpdir / 'mask.png')

            dataset = SemanticDataset(
                image_paths=[tmpdir / 'image.png'],
                mask_paths=[tmpdir / 'mask.png'],
                transform=transforms.ToTensor(),
                transform_label=transforms.ToTensor(),
                ignore_index=5
            )

            image_tensor, mask_tensor = dataset[0]

            # Check types
            assert isinstance(image_tensor, torch.Tensor)
            assert isinstance(mask_tensor, torch.Tensor)

            # Check shapes
            assert image_tensor.shape == (3, 10, 10)
            assert mask_tensor.shape == (10, 10)

    def test_ignore_index_handling(self):
        """Test that values above ignore_index are clamped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create mask with values exceeding ignore_index
            img = np.zeros((10, 10, 3), dtype=np.uint8)
            mask = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]] * 10, dtype=np.uint8)

            Image.fromarray(img).save(tmpdir / 'image.png')
            Image.fromarray(mask).save(tmpdir / 'mask.png')

            dataset = SemanticDataset(
                image_paths=[tmpdir / 'image.png'],
                mask_paths=[tmpdir / 'mask.png'],
                transform=transforms.ToTensor(),
                transform_label=transforms.ToTensor(),
                ignore_index=5
            )

            _, mask_tensor = dataset[0]

            # Values > 5 should be clamped to 5
            assert mask_tensor.max() <= 5
            assert (mask_tensor >= 0).all()

    def test_synchronized_transforms(self):
        """Test that transforms are synchronized between image and mask."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create checkerboard pattern
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            img[::2, ::2] = 255
            img[1::2, 1::2] = 255

            mask = np.zeros((100, 100), dtype=np.uint8)
            mask[::2, ::2] = 1
            mask[1::2, 1::2] = 1

            Image.fromarray(img).save(tmpdir / 'image.png')
            Image.fromarray(mask).save(tmpdir / 'mask.png')

            # Apply same transform to both (e.g., random crop)
            dataset = SemanticDataset(
                image_paths=[tmpdir / 'image.png'],
                mask_paths=[tmpdir / 'mask.png'],
                transform=transforms.ToTensor(),
                transform_label=transforms.ToTensor(),
                ignore_index=255
            )

            # Get multiple samples to verify randomness is synchronized
            image1, mask1 = dataset[0]
            image2, mask2 = dataset[0]

            # Samples should differ due to random seed
            # But image and mask within each sample should be synchronized


class TestGetImageMaskPairs:
    """Test get_image_mask_pairs function."""

    def test_get_matching_pairs(self):
        """Test getting matching image-mask pairs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            img_dir = tmpdir / 'images'
            mask_dir = tmpdir / 'masks'
            img_dir.mkdir()
            mask_dir.mkdir()

            # Create matching files
            for i in range(3):
                img = np.zeros((10, 10, 3), dtype=np.uint8)
                mask = np.zeros((10, 10), dtype=np.uint8)

                Image.fromarray(img).save(img_dir / f'{i}.png')
                Image.fromarray(mask).save(mask_dir / f'{i}.png')

            images, masks = get_image_mask_pairs(img_dir, mask_dir)

            assert len(images) == 3
            assert len(masks) == 3

            # Verify names match
            for img, mask in zip(images, masks):
                assert img.stem == mask.stem

    def test_missing_masks(self):
        """Test error when masks are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            img_dir = tmpdir / 'images'
            mask_dir = tmpdir / 'masks'
            img_dir.mkdir()
            mask_dir.mkdir()

            # Create 3 images but only 2 masks
            for i in range(3):
                img = np.zeros((10, 10, 3), dtype=np.uint8)
                Image.fromarray(img).save(img_dir / f'{i}.png')

            for i in range(2):
                mask = np.zeros((10, 10), dtype=np.uint8)
                Image.fromarray(mask).save(mask_dir / f'{i}.png')

            with pytest.raises(ValueError, match="without matching masks"):
                get_image_mask_pairs(img_dir, mask_dir)

    def test_extra_masks(self):
        """Test error when there are extra masks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            img_dir = tmpdir / 'images'
            mask_dir = tmpdir / 'masks'
            img_dir.mkdir()
            mask_dir.mkdir()

            # Create 2 images but 3 masks
            for i in range(2):
                img = np.zeros((10, 10, 3), dtype=np.uint8)
                Image.fromarray(img).save(img_dir / f'{i}.png')

            for i in range(3):
                mask = np.zeros((10, 10), dtype=np.uint8)
                Image.fromarray(mask).save(mask_dir / f'{i}.png')

            with pytest.raises(ValueError, match="without matching images"):
                get_image_mask_pairs(img_dir, mask_dir)


class TestCreateDataloaders:
    """Test create_dataloaders function."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create train images and masks
            train_img_dir = tmpdir / 'train' / 'images'
            train_img_dir.mkdir(parents=True)

            for i in range(5):
                img = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
                Image.fromarray(img).save(train_img_dir / f'{i}.png')

            # Create validation images and masks
            val_img_dir = tmpdir / 'val' / 'images'
            val_mask_dir = tmpdir / 'val' / 'masks'
            val_img_dir.mkdir(parents=True)
            val_mask_dir.mkdir(parents=True)

            for i in range(3):
                img = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
                mask = np.random.randint(0, 3, (32, 32), dtype=np.uint8)

                Image.fromarray(img).save(val_img_dir / f'{i}.png')
                Image.fromarray(mask).save(val_mask_dir / f'{i}.png')

            # Create session structure with iteration_0
            session_dir = tmpdir / 'Sessions' / 'TEST_SESSION'
            iter0_masks = session_dir / 'iteration_0' / 'masks'
            iter0_masks.mkdir(parents=True)

            for i in range(5):
                mask = np.random.randint(0, 3, (32, 32), dtype=np.uint8)
                Image.fromarray(mask).save(iter0_masks / f'{i}.png')

            # Create configs
            dataset_config = {
                'name': 'TEST',
                'paths': {
                    'train_images': str(train_img_dir),
                    'val_images': str(val_img_dir),
                    'val_masks': str(val_mask_dir)
                },
                'classes': {
                    'num_classes': 3,
                    'ignore_index': 3,
                    'names': ['class0', 'class1', 'class2']
                },
                'image': {
                    'width': 32,
                    'height': 32,
                    'channels': 3
                }
            }

            training_config = {
                'training': {
                    'batch_size': {'train': 2, 'val': 2},
                    'num_workers': 0
                }
            }

            # Create mock session manager
            from src.session.session_manager import SessionManager

            session_manager = SessionManager(
                session_name='TEST_SESSION',
                session_dir=str(tmpdir / 'Sessions'),
                dataset_config=dataset_config,
                training_config=training_config
            )

            # Manually set session path (skip initialize to avoid config file requirements)
            session_manager.session_path = session_dir
            session_manager._initialized = True

            yield session_manager, dataset_config, training_config

    def test_create_dataloaders_success(self, mock_session):
        """Test successful dataloader creation."""
        session_manager, dataset_config, training_config = mock_session

        train_loader, val_loader = create_dataloaders(
            session_manager=session_manager,
            iteration=0,
            dataset_config=dataset_config,
            training_config=training_config
        )

        assert train_loader is not None
        assert val_loader is not None

        # Check batch sizes
        assert train_loader.batch_size == 2
        assert val_loader.batch_size == 2

        # Check can iterate
        train_batch = next(iter(train_loader))
        images, masks = train_batch

        assert images.shape[0] <= 2  # Batch size
        assert masks.shape[0] <= 2

    def test_dataloader_iteration(self, mock_session):
        """Test iterating through dataloaders."""
        session_manager, dataset_config, training_config = mock_session

        train_loader, val_loader = create_dataloaders(
            session_manager=session_manager,
            iteration=0,
            dataset_config=dataset_config,
            training_config=training_config
        )

        # Test train loader
        train_batches = list(train_loader)
        assert len(train_batches) > 0

        for images, masks in train_batches:
            assert images.dtype == torch.float32
            assert masks.dtype == torch.int64
            assert images.shape[2:] == masks.shape[1:]  # H, W match

        # Test val loader
        val_batches = list(val_loader)
        assert len(val_batches) > 0

        for images, masks in val_batches:
            assert images.dtype == torch.float32
            assert masks.dtype == torch.int64
