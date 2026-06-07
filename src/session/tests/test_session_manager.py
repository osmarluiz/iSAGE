"""
Tests for session_manager module.
"""

import pytest
import json
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image

from ..session_manager import SessionManager


@pytest.fixture
def sample_dataset_config():
    """Sample dataset configuration."""
    return {
        'name': 'TEST_DATASET',
        'paths': {
            'train_images': 'train/images',
            'train_dense_masks': 'train/masks',
            'val_images': 'val/images',
            'val_masks': 'val/masks'
        },
        'classes': {
            'num_classes': 3,
            'ignore_index': 3,
            'names': ['class_0', 'class_1', 'class_2'],
            'colors': [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
        },
        'image': {
            'width': 128,
            'height': 128,
            'channels': 3
        }
    }


@pytest.fixture
def sample_training_config():
    """Sample training configuration."""
    return {
        'name': 'TEST_MODEL',
        'model': {
            'architecture': 'Unet',
            'encoder': 'resnet34',
            'activation': 'softmax'
        },
        'training': {
            'learning_rate': 0.001,
            'batch_size': {'train': 4, 'val': 8},
            'num_epochs': 10,
            'device': 'cpu'
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


class TestSessionManagerInitialization:
    """Test session manager initialization and creation."""

    def test_create_new_session(self, sample_dataset_config, sample_training_config):
        """Test creating a new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )

            is_new = manager.initialize()

            assert is_new is True
            assert manager.session_path.exists()
            assert (manager.session_path / 'dataset_config.yaml').exists()
            assert (manager.session_path / 'training_config.yaml').exists()
            assert (manager.session_path / 'session_info.json').exists()
            assert (manager.session_path / 'metrics_history.csv').exists()

    def test_load_existing_session(self, sample_dataset_config, sample_training_config):
        """Test loading an existing session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create session first time
            manager1 = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            is_new1 = manager1.initialize()
            assert is_new1 is True

            # Load same session
            manager2 = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            is_new2 = manager2.initialize()
            assert is_new2 is False

    def test_session_info_content(self, sample_dataset_config, sample_training_config):
        """Test session info JSON content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            with open(manager.session_path / 'session_info.json', 'r') as f:
                info = json.load(f)

            assert info['session_name'] == 'test_session'
            assert info['dataset_name'] == 'TEST_DATASET'
            assert info['model_name'] == 'TEST_MODEL'
            assert 'created_at' in info
            assert 'current_iteration' in info

    def test_metrics_history_headers(self, sample_dataset_config, sample_training_config):
        """Test metrics history CSV has correct headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            df = pd.read_csv(manager.session_path / 'metrics_history.csv')

            assert 'iteration' in df.columns
            assert 'train_loss' in df.columns
            assert 'val_loss' in df.columns
            assert 'miou' in df.columns
            assert 'class_0_iou' in df.columns
            assert 'class_1_iou' in df.columns
            assert 'class_2_iou' in df.columns


class TestIterationManagement:
    """Test iteration management functions."""

    def test_get_current_iteration_empty(self, sample_dataset_config, sample_training_config):
        """Test getting current iteration when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            current = manager.get_current_iteration()
            assert current == 0

    def test_create_next_iteration(self, sample_dataset_config, sample_training_config):
        """Test creating next iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iteration_0 manually
            iter0_path = manager.session_path / 'iteration_0'
            for folder in ['masks', 'annotations', 'models', 'predictions']:
                (iter0_path / folder).mkdir(parents=True, exist_ok=True)

            # Create sample JSON in iteration_0
            sample_json = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 128, 'height': 128},
                'coordinates': [[10, 20]],
                'class': [1]
            }
            with open(iter0_path / 'annotations' / 'test.json', 'w') as f:
                json.dump(sample_json, f)

            # Create next iteration
            next_iter = manager.create_next_iteration()

            assert next_iter == 1
            iter1_path = manager.session_path / 'iteration_1'
            assert iter1_path.exists()
            assert (iter1_path / 'masks').exists()
            assert (iter1_path / 'annotations').exists()
            assert (iter1_path / 'models').exists()
            assert (iter1_path / 'predictions').exists()

            # Check JSON was copied
            assert (iter1_path / 'annotations' / 'test.json').exists()

    def test_get_iteration_path_integer(self, sample_dataset_config, sample_training_config):
        """Test getting iteration path with integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iteration_0
            iter0_path = manager.session_path / 'iteration_0'
            iter0_path.mkdir(parents=True, exist_ok=True)

            path = manager.get_iteration_path(0)
            assert path == iter0_path

    def test_get_iteration_path_latest(self, sample_dataset_config, sample_training_config):
        """Test getting iteration path with 'latest'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iterations
            (manager.session_path / 'iteration_0').mkdir()
            (manager.session_path / 'iteration_1').mkdir()
            (manager.session_path / 'iteration_2').mkdir()

            path = manager.get_iteration_path('latest')
            assert path == manager.session_path / 'iteration_2'


class TestMetricsManagement:
    """Test metrics saving and loading."""

    def test_save_iteration_metrics(self, sample_dataset_config, sample_training_config):
        """Test saving metrics for an iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iteration_0
            iter0_path = manager.session_path / 'iteration_0'
            iter0_path.mkdir(parents=True, exist_ok=True)

            # Save metrics
            metrics = {
                'train_loss': 0.5,
                'val_loss': 0.6,
                'miou': 0.75,
                'per_class_iou': [0.8, 0.7, 0.75],
                'pixel_accuracy': 0.85
            }

            manager.save_iteration_metrics(0, metrics)

            # Check metrics.json exists
            assert (iter0_path / 'metrics.json').exists()

            # Check metrics appended to history
            df = manager.load_metrics_history()
            assert len(df) == 1
            assert df.loc[0, 'iteration'] == 0
            assert df.loc[0, 'train_loss'] == 0.5
            assert df.loc[0, 'miou'] == 0.75

    def test_load_metrics_history(self, sample_dataset_config, sample_training_config):
        """Test loading metrics history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iterations and save metrics
            for i in range(3):
                iter_path = manager.session_path / f'iteration_{i}'
                iter_path.mkdir(parents=True, exist_ok=True)

                metrics = {
                    'train_loss': 0.5 - i * 0.1,
                    'val_loss': 0.6 - i * 0.1,
                    'miou': 0.7 + i * 0.05,
                    'per_class_iou': [0.7, 0.7, 0.7],
                    'pixel_accuracy': 0.8
                }
                manager.save_iteration_metrics(i, metrics)

            # Load history
            df = manager.load_metrics_history()

            assert len(df) == 3
            assert df.loc[0, 'iteration'] == 0
            assert df.loc[2, 'iteration'] == 2
            assert pytest.approx(df.loc[2, 'miou'], rel=1e-5) == 0.8  # 0.7 + 2 * 0.05


class TestModelAndPredictionPaths:
    """Test getting model and prediction paths."""

    def test_get_previous_model_path_iteration_zero(self, sample_dataset_config, sample_training_config):
        """Test that iteration 0 has no previous model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            path = manager.get_previous_model_path(0)
            assert path is None

    def test_get_previous_model_path_exists(self, sample_dataset_config, sample_training_config):
        """Test getting previous model path when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iteration_0 with model
            model_path = manager.session_path / 'iteration_0' / 'models' / 'best_model.pth'
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.touch()

            # Get previous model for iteration 1
            prev_model = manager.get_previous_model_path(1)
            assert prev_model == model_path

    def test_get_prediction_paths(self, sample_dataset_config, sample_training_config):
        """Test getting prediction paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create predictions
            pred_dir = manager.session_path / 'iteration_0' / 'predictions'
            pred_dir.mkdir(parents=True, exist_ok=True)

            for i in range(3):
                (pred_dir / f'{i}_pred.png').touch()

            paths = manager.get_prediction_paths(0)
            assert len(paths) == 3
            assert all(p.suffix == '.png' for p in paths)


class TestAnnotationCounting:
    """Test annotation counting."""

    def test_get_annotation_count(self, sample_dataset_config, sample_training_config):
        """Test counting total annotations in iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(
                session_name='test_session',
                session_dir=tmpdir,
                dataset_config=sample_dataset_config,
                training_config=sample_training_config
            )
            manager.initialize()

            # Create iteration_0 with annotations
            annotations_dir = manager.session_path / 'iteration_0' / 'annotations'
            annotations_dir.mkdir(parents=True, exist_ok=True)

            # Create JSON files with varying point counts
            for i in range(3):
                json_data = {
                    'format_version': '1.0',
                    'image': {'name': f'{i}.png', 'width': 128, 'height': 128},
                    'coordinates': [[10, 20]] * (i + 1),  # 1, 2, 3 points
                    'class': [1] * (i + 1)
                }
                with open(annotations_dir / f'{i}.json', 'w') as f:
                    json.dump(json_data, f)

            count = manager.get_annotation_count(0)
            assert count == 6  # 1 + 2 + 3
