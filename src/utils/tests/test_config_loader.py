"""
Tests for config_loader module.
"""

import pytest
import tempfile
from pathlib import Path
import yaml
from ..config_loader import (
    load_dataset_config,
    load_training_config,
    validate_dataset_config,
    validate_training_config,
    save_config_to_yaml
)


class TestDatasetConfigLoading:
    """Test dataset configuration loading."""

    def test_load_valid_dataset_config(self):
        """Test loading the actual vaihingen.yaml config."""
        config = load_dataset_config('configs/datasets/vaihingen.yaml')

        assert config['name'] == 'VAIHINGEN'
        assert 'paths' in config
        assert 'classes' in config
        assert 'image' in config
        assert config['classes']['num_classes'] == 6
        assert len(config['classes']['names']) == 6

    def test_load_nonexistent_config(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_dataset_config('configs/datasets/nonexistent.yaml')

    def test_load_invalid_yaml(self):
        """Test that invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:\n  - broken")
            temp_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                load_dataset_config(temp_path)
        finally:
            Path(temp_path).unlink()


class TestTrainingConfigLoading:
    """Test training configuration loading."""

    def test_load_valid_training_config(self):
        """Test loading the actual training config."""
        config = load_training_config('configs/training/unet_efficientnet_b7.yaml')

        assert config['name'] == 'UNet-EfficientNetB7'
        assert 'model' in config
        assert 'training' in config
        assert 'loss' in config
        assert config['model']['encoder'] == 'efficientnet-b7'
        assert config['training']['num_epochs'] == 100

    def test_load_nonexistent_training_config(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_training_config('configs/training/nonexistent.yaml')


class TestDatasetConfigValidation:
    """Test dataset configuration validation."""

    def test_validate_valid_config(self):
        """Test that valid config passes validation."""
        valid_config = {
            'name': 'TEST',
            'paths': {
                'train_images': 'path/to/train',
                'train_dense_masks': 'path/to/dense',
                'val_images': 'path/to/val',
                'val_masks': 'path/to/val_masks'
            },
            'classes': {
                'num_classes': 2,
                'ignore_index': 2,
                'names': ['class0', 'class1'],
                'colors': [[255, 0, 0], [0, 255, 0]]
            },
            'image': {
                'width': 512,
                'height': 512,
                'channels': 3
            }
        }

        is_valid, error_msg = validate_dataset_config(valid_config)
        assert is_valid
        assert error_msg == ""

    def test_validate_missing_required_key(self):
        """Test that missing required key fails validation."""
        invalid_config = {
            'name': 'TEST',
            'paths': {},
            # Missing 'classes' and 'image'
        }

        is_valid, error_msg = validate_dataset_config(invalid_config)
        assert not is_valid
        assert 'Missing required key' in error_msg

    def test_validate_mismatched_class_names(self):
        """Test that mismatched number of class names fails."""
        invalid_config = {
            'name': 'TEST',
            'paths': {
                'train_images': 'path',
                'train_dense_masks': 'path',
                'val_images': 'path',
                'val_masks': 'path'
            },
            'classes': {
                'num_classes': 3,
                'ignore_index': 3,
                'names': ['class0', 'class1'],  # Only 2 names for 3 classes
                'colors': [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
            },
            'image': {
                'width': 512,
                'height': 512,
                'channels': 3
            }
        }

        is_valid, error_msg = validate_dataset_config(invalid_config)
        assert not is_valid
        assert 'class names' in error_msg.lower()

    def test_validate_invalid_color_format(self):
        """Test that invalid color format fails validation."""
        invalid_config = {
            'name': 'TEST',
            'paths': {
                'train_images': 'path',
                'train_dense_masks': 'path',
                'val_images': 'path',
                'val_masks': 'path'
            },
            'classes': {
                'num_classes': 2,
                'ignore_index': 2,
                'names': ['class0', 'class1'],
                'colors': [[255, 0], [0, 255, 0]]  # First color missing B channel
            },
            'image': {
                'width': 512,
                'height': 512,
                'channels': 3
            }
        }

        is_valid, error_msg = validate_dataset_config(invalid_config)
        assert not is_valid
        assert 'Color' in error_msg

    def test_validate_negative_num_classes(self):
        """Test that negative num_classes fails validation."""
        invalid_config = {
            'name': 'TEST',
            'paths': {
                'train_images': 'path',
                'train_dense_masks': 'path',
                'val_images': 'path',
                'val_masks': 'path'
            },
            'classes': {
                'num_classes': -1,
                'ignore_index': 2,
                'names': [],
                'colors': []
            },
            'image': {
                'width': 512,
                'height': 512,
                'channels': 3
            }
        }

        is_valid, error_msg = validate_dataset_config(invalid_config)
        assert not is_valid
        assert 'positive integer' in error_msg


class TestTrainingConfigValidation:
    """Test training configuration validation."""

    def test_validate_valid_config(self):
        """Test that valid training config passes validation."""
        valid_config = {
            'name': 'TestModel',
            'model': {
                'architecture': 'Unet',
                'encoder': 'resnet34',
                'activation': 'softmax'
            },
            'training': {
                'learning_rate': 0.001,
                'batch_size': {'train': 4, 'val': 8},
                'num_epochs': 50,
                'device': 'cuda'
            },
            'loss': {
                'train': {'name': 'DiceLoss', 'params': {}},
                'validation': {'name': 'CrossEntropyLoss', 'params': {}}
            },
            'optimizer': {
                'name': 'Adam',
                'params': {'lr': 0.001}
            }
        }

        is_valid, error_msg = validate_training_config(valid_config)
        assert is_valid
        assert error_msg == ""

    def test_validate_missing_batch_size_keys(self):
        """Test that missing batch_size.train or .val fails."""
        invalid_config = {
            'name': 'TestModel',
            'model': {
                'architecture': 'Unet',
                'encoder': 'resnet34',
                'activation': 'softmax'
            },
            'training': {
                'learning_rate': 0.001,
                'batch_size': {'train': 4},  # Missing 'val'
                'num_epochs': 50,
                'device': 'cuda'
            },
            'loss': {
                'train': {'name': 'DiceLoss', 'params': {}},
                'validation': {'name': 'CrossEntropyLoss', 'params': {}}
            },
            'optimizer': {
                'name': 'Adam',
                'params': {}
            }
        }

        is_valid, error_msg = validate_training_config(invalid_config)
        assert not is_valid
        assert 'batch_size.val' in error_msg

    def test_validate_negative_learning_rate(self):
        """Test that negative learning rate fails validation."""
        invalid_config = {
            'name': 'TestModel',
            'model': {
                'architecture': 'Unet',
                'encoder': 'resnet34',
                'activation': 'softmax'
            },
            'training': {
                'learning_rate': -0.001,
                'batch_size': {'train': 4, 'val': 8},
                'num_epochs': 50,
                'device': 'cuda'
            },
            'loss': {
                'train': {'name': 'DiceLoss', 'params': {}},
                'validation': {'name': 'CrossEntropyLoss', 'params': {}}
            },
            'optimizer': {
                'name': 'Adam',
                'params': {}
            }
        }

        is_valid, error_msg = validate_training_config(invalid_config)
        assert not is_valid
        assert 'learning_rate' in error_msg


class TestConfigSaving:
    """Test configuration saving."""

    def test_save_config_to_yaml(self):
        """Test saving config to YAML file."""
        test_config = {
            'name': 'TEST',
            'value': 42,
            'nested': {'key': 'value'}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'test_config.yaml'
            save_config_to_yaml(test_config, str(output_path))

            assert output_path.exists()

            # Load and verify
            with open(output_path, 'r') as f:
                loaded = yaml.safe_load(f)

            assert loaded == test_config
