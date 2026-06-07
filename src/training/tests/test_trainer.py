"""
Tests for trainer module.

These are integration-style tests that require PyTorch.
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np
import torch
from PIL import Image

from ..trainer import ActiveLearningTrainer
from ...session.session_manager import SessionManager


class TestActiveLearningTrainer:
    """Test ActiveLearningTrainer class."""

    @pytest.fixture
    def mock_session_with_data(self):
        """Create mock session with training data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create train images
            train_img_dir = tmpdir / 'train' / 'images'
            train_img_dir.mkdir(parents=True)

            for i in range(5):
                img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
                Image.fromarray(img).save(train_img_dir / f'{i}.png')

            # Create validation images and masks
            val_img_dir = tmpdir / 'val' / 'images'
            val_mask_dir = tmpdir / 'val' / 'masks'
            val_img_dir.mkdir(parents=True)
            val_mask_dir.mkdir(parents=True)

            for i in range(3):
                img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
                mask = np.random.randint(0, 3, (64, 64), dtype=np.uint8)

                Image.fromarray(img).save(val_img_dir / f'{i}.png')
                Image.fromarray(mask).save(val_mask_dir / f'{i}.png')

            # Create session structure
            session_dir = tmpdir / 'Sessions' / 'TEST_SESSION'
            iter0_masks = session_dir / 'iteration_0' / 'masks'
            iter0_masks.mkdir(parents=True)

            for i in range(5):
                mask = np.random.randint(0, 3, (64, 64), dtype=np.uint8)
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
                    'width': 64,
                    'height': 64,
                    'channels': 3
                }
            }

            training_config = {
                'name': 'TEST_TRAINING',
                'model': {
                    'architecture': 'Unet',
                    'encoder': 'resnet18',
                    'encoder_weights': 'imagenet',
                    'activation': 'softmax',
                    'in_channels': 3
                },
                'optimizer': {
                    'name': 'Adam',
                    'params': {
                        'lr': 0.001
                    }
                },
                'loss': {
                    'train': {
                        'name': 'CrossEntropyLoss',
                        'params': {}
                    },
                    'validation': {
                        'name': 'CrossEntropyLoss',
                        'params': {}
                    }
                },
                'training': {
                    'device': 'cpu',
                    'num_epochs': 2,
                    'batch_size': {'train': 2, 'val': 2},
                    'num_workers': 0
                }
            }

            # Create session manager
            session_manager = SessionManager(
                session_name='TEST_SESSION',
                session_dir=str(tmpdir / 'Sessions'),
                dataset_config=dataset_config,
                training_config=training_config
            )

            # Manually set session path
            session_manager.session_path = session_dir
            session_manager._initialized = True

            yield session_manager, dataset_config, training_config

    def test_trainer_initialization(self, mock_session_with_data):
        """Test that trainer initializes correctly."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        assert trainer.session_manager == session_manager
        assert trainer.dataset_config == dataset_config
        assert trainer.training_config == training_config
        assert trainer.device == torch.device('cpu')
        assert trainer.num_epochs == 2
        assert trainer.num_classes == 3
        assert trainer.ignore_index == 3
        assert trainer.model is None  # Not initialized yet
        assert trainer.best_val_loss == float('inf')

    def test_initialize_model(self, mock_session_with_data):
        """Test model initialization."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()

        assert trainer.model is not None
        assert trainer.optimizer is not None
        assert trainer.train_criterion is not None
        assert trainer.val_criterion is not None

    def test_create_dataloaders(self, mock_session_with_data):
        """Test dataloader creation."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        train_loader, val_loader = trainer._create_dataloaders(iteration=0)

        assert train_loader is not None
        assert val_loader is not None
        assert len(train_loader) > 0
        assert len(val_loader) > 0

    def test_train_epoch(self, mock_session_with_data):
        """Test single training epoch."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        train_loader, _ = trainer._create_dataloaders(iteration=0)

        metrics = trainer._train_epoch(train_loader, epoch=0)

        assert 'loss' in metrics
        assert isinstance(metrics['loss'], float)
        assert metrics['loss'] >= 0

    def test_validate_epoch(self, mock_session_with_data):
        """Test single validation epoch."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        _, val_loader = trainer._create_dataloaders(iteration=0)

        metrics = trainer._validate_epoch(val_loader, epoch=0)

        assert 'loss' in metrics
        assert 'miou' in metrics
        assert isinstance(metrics['loss'], float)
        assert isinstance(metrics['miou'], float)
        assert metrics['loss'] >= 0
        assert 0 <= metrics['miou'] <= 1

    def test_save_best_model(self, mock_session_with_data):
        """Test model saving."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        trainer._save_best_model(iteration=0)

        # Check that model file exists
        model_path = session_manager.get_iteration_path(0) / 'models' / 'best_model.pth'
        assert model_path.exists()

    def test_load_previous_model(self, mock_session_with_data):
        """Test loading previous model weights."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()

        # Save model for iteration 0
        trainer._save_best_model(iteration=0)

        # Create iteration 1
        iter1_path = session_manager.session_path / 'iteration_1'
        iter1_path.mkdir()

        # Initialize new trainer and load previous weights
        trainer2 = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer2._initialize_model()
        result = trainer2._load_previous_model(iteration=1)

        assert result is True

    def test_load_previous_model_nonexistent(self, mock_session_with_data):
        """Test loading previous model when it doesn't exist."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        result = trainer._load_previous_model(iteration=0)

        assert result is False

    def test_generate_predictions(self, mock_session_with_data):
        """Test prediction generation."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        train_loader, _ = trainer._create_dataloaders(iteration=0)

        trainer._generate_predictions(iteration=0, train_loader=train_loader)

        # Check that predictions were saved
        predictions_dir = session_manager.get_iteration_path(0) / 'predictions'
        assert predictions_dir.exists()

        prediction_files = list(predictions_dir.glob('*_pred.png'))
        assert len(prediction_files) > 0

    def test_calculate_final_metrics(self, mock_session_with_data):
        """Test final metrics calculation."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        trainer._initialize_model()
        _, val_loader = trainer._create_dataloaders(iteration=0)

        metrics = trainer._calculate_final_metrics(iteration=0, val_loader=val_loader)

        assert 'miou' in metrics
        assert 'per_class_iou' in metrics
        assert 'pixel_accuracy' in metrics
        assert 'per_class_accuracy' in metrics
        assert 'confusion_matrix' in metrics

        assert isinstance(metrics['miou'], float)
        assert isinstance(metrics['per_class_iou'], list)
        assert len(metrics['per_class_iou']) == 3

    def test_train_iteration_workflow(self, mock_session_with_data):
        """Test complete training iteration workflow."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        # Run complete training iteration
        metrics = trainer.train_iteration(
            iteration=0,
            use_previous_weights=False,
            create_next_iteration=True
        )

        # Check that metrics were returned
        assert 'train_loss' in metrics
        assert 'val_loss' in metrics
        assert 'miou' in metrics
        assert 'per_class_iou' in metrics
        assert 'pixel_accuracy' in metrics

        # Check that model was saved
        model_path = session_manager.get_iteration_path(0) / 'models' / 'best_model.pth'
        assert model_path.exists()

        # Check that predictions were generated
        predictions_dir = session_manager.get_iteration_path(0) / 'predictions'
        assert predictions_dir.exists()
        assert len(list(predictions_dir.glob('*_pred.png'))) > 0

        # Check that metrics were saved
        metrics_path = session_manager.get_iteration_path(0) / 'metrics.json'
        assert metrics_path.exists()

        # Check that next iteration was created
        next_iter_path = session_manager.get_iteration_path(1)
        assert next_iter_path.exists()

    def test_train_iteration_without_next(self, mock_session_with_data):
        """Test training iteration without creating next iteration."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        # Run training without creating next iteration
        metrics = trainer.train_iteration(
            iteration=0,
            use_previous_weights=False,
            create_next_iteration=False
        )

        # Check that next iteration was NOT created
        next_iter_path = session_manager.get_iteration_path(1)
        assert not next_iter_path.exists()

    def test_train_iteration_with_previous_weights(self, mock_session_with_data):
        """Test training iteration loading previous weights."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        # Train iteration 0
        trainer.train_iteration(
            iteration=0,
            use_previous_weights=False,
            create_next_iteration=True
        )

        # Create masks for iteration 1
        iter1_masks_dir = session_manager.get_iteration_path(1) / 'masks'
        iter1_masks_dir.mkdir(parents=True, exist_ok=True)

        for i in range(5):
            mask = np.random.randint(0, 3, (64, 64), dtype=np.uint8)
            Image.fromarray(mask).save(iter1_masks_dir / f'{i}.png')

        # Train iteration 1 with previous weights
        trainer2 = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        metrics = trainer2.train_iteration(
            iteration=1,
            use_previous_weights=True,
            create_next_iteration=False
        )

        # Should complete successfully
        assert 'miou' in metrics

    def test_train_iteration_resolve_latest(self, mock_session_with_data):
        """Test training iteration with 'latest' resolution."""
        session_manager, dataset_config, training_config = mock_session_with_data

        trainer = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        # Train iteration 0
        trainer.train_iteration(
            iteration=0,
            use_previous_weights=False,
            create_next_iteration=False
        )

        # Train 'latest' should train iteration 0
        trainer2 = ActiveLearningTrainer(
            session_manager=session_manager,
            dataset_config=dataset_config,
            training_config=training_config
        )

        metrics = trainer2.train_iteration(
            iteration='latest',
            use_previous_weights=False,
            create_next_iteration=False
        )

        assert 'miou' in metrics


class TestTrainerEdgeCases:
    """Test edge cases and error handling."""

    def test_trainer_with_missing_data(self):
        """Test trainer behavior with missing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            session_dir = tmpdir / 'Sessions' / 'TEST_SESSION'
            session_dir.mkdir(parents=True)

            dataset_config = {
                'paths': {
                    'train_images': str(tmpdir / 'nonexistent'),
                    'val_images': str(tmpdir / 'nonexistent'),
                    'val_masks': str(tmpdir / 'nonexistent')
                },
                'classes': {
                    'num_classes': 3,
                    'ignore_index': 3,
                    'names': ['class0', 'class1', 'class2']
                }
            }

            training_config = {
                'model': {
                    'architecture': 'Unet',
                    'encoder': 'resnet18',
                    'encoder_weights': 'imagenet',
                    'activation': 'softmax'
                },
                'optimizer': {'name': 'Adam', 'params': {'lr': 0.001}},
                'loss': {
                    'train': {'name': 'CrossEntropyLoss', 'params': {}},
                    'validation': {'name': 'CrossEntropyLoss', 'params': {}}
                },
                'training': {
                    'device': 'cpu',
                    'num_epochs': 1,
                    'batch_size': {'train': 2, 'val': 2},
                    'num_workers': 0
                }
            }

            session_manager = SessionManager(
                session_name='TEST_SESSION',
                session_dir=str(tmpdir / 'Sessions'),
                dataset_config=dataset_config,
                training_config=training_config
            )
            session_manager.session_path = session_dir
            session_manager._initialized = True

            trainer = ActiveLearningTrainer(
                session_manager=session_manager,
                dataset_config=dataset_config,
                training_config=training_config
            )

            # Should raise error when trying to create dataloaders
            with pytest.raises(Exception):
                trainer._create_dataloaders(iteration=0)
