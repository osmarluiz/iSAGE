"""
Active Learning Trainer for sparse semantic segmentation.

Handles model training, validation, prediction generation, and iteration management.
"""

import sys
from pathlib import Path
from typing import Dict, Union, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
from PIL import Image

# Add local segmentation_models_pytorch to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'segmentation_models_pytorch'))
import segmentation_models_pytorch as smp

from ..session.session_manager import SessionManager
from ..datasets import create_dataloaders
from ..utils.iteration_utils import resolve_iteration
from .metrics import calculate_metrics, format_metrics_for_display


class ActiveLearningTrainer:
    """
    Handles model training, validation, and prediction caching for active learning.

    Integrates with SessionManager for iteration management and file organization.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        dataset_config: dict,
        training_config: dict
    ):
        """
        Initialize trainer.

        Args:
            session_manager: SessionManager instance
            dataset_config: Dataset configuration dictionary
            training_config: Training configuration dictionary
        """
        self.session_manager = session_manager
        self.dataset_config = dataset_config
        self.training_config = training_config

        # Extract configuration
        self.device = torch.device(training_config['training']['device'])
        self.num_epochs = training_config['training']['num_epochs']
        self.num_classes = dataset_config['classes']['num_classes']
        self.ignore_index = dataset_config['classes']['ignore_index']
        self.class_names = dataset_config['classes']['names']

        # Model will be initialized in train_iteration
        self.model = None
        self.optimizer = None
        self.train_criterion = None
        self.val_criterion = None

        # Track best validation mIoU
        self.best_miou = 0.0

    def train_iteration(
        self,
        iteration: Union[int, str],
        use_previous_weights: bool = True,
        create_next_iteration: bool = True
    ) -> Dict:
        """
        Complete training workflow for one iteration.

        Steps:
        1. Resolve iteration number
        2. Load previous model if requested and available
        3. Create dataloaders from iteration masks
        4. Run training loop
        5. Save best model
        6. Generate predictions for training images
        7. Calculate final metrics
        8. Save metrics
        9. Create next iteration if requested

        Args:
            iteration: Iteration number or 'latest'
            use_previous_weights: Whether to load previous model weights
            create_next_iteration: Whether to create next iteration after training

        Returns:
            Dictionary with final metrics
        """
        # Resolve iteration
        iter_num = resolve_iteration(self.session_manager.session_path, iteration)
        print(f"\n{'='*60}")
        print(f"TRAINING ITERATION {iter_num}")
        print(f"{'='*60}\n")

        # Initialize model
        print("Initializing model...")
        self._initialize_model()

        # Load previous weights if requested
        if use_previous_weights and iter_num > 0:
            prev_model_path = self.session_manager.get_previous_model_path(iter_num)
            if prev_model_path is not None:
                print(f"Loading weights from iteration {iter_num - 1}...")
                self._load_previous_model(iter_num)
            else:
                print(f"No previous model found, training from scratch")
        else:
            print("Training from scratch")

        # Create dataloaders
        print("\nCreating dataloaders...")
        train_loader, val_loader = self._create_dataloaders(iter_num)
        has_validation = val_loader is not None

        if has_validation:
            print(f"Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")
        else:
            print(f"Train batches: {len(train_loader)}, No validation data")

        # Reset best mIoU
        self.best_miou = 0.0

        # Training loop
        print(f"\nStarting training for {self.num_epochs} epochs...")
        print("-" * 60)

        for epoch in range(self.num_epochs):
            # Train
            train_metrics = self._train_epoch(train_loader, epoch)

            if has_validation:
                # Validate
                val_metrics = self._validate_epoch(val_loader, epoch)

                # Print epoch summary with validation
                print(
                    f"Epoch {epoch+1}/{self.num_epochs} | "
                    f"Train Loss: {train_metrics['loss']:.4f} | "
                    f"Val Loss: {val_metrics['loss']:.4f} | "
                    f"Val mIoU: {val_metrics['miou']:.4f}"
                )

                # Save best model based on validation mIoU
                if val_metrics['miou'] > self.best_miou:
                    self.best_miou = val_metrics['miou']
                    self._save_best_model(iter_num)
                    print(f"  → Best model saved (mIoU: {self.best_miou:.4f})")
            else:
                # Print epoch summary without validation
                print(
                    f"Epoch {epoch+1}/{self.num_epochs} | "
                    f"Train Loss: {train_metrics['loss']:.4f}"
                )

        # Save final model when no validation data
        if not has_validation:
            self._save_best_model(iter_num)
            print(f"  → Final model saved (no validation data)")

        print("-" * 60)
        print("Training complete!\n")

        # Generate predictions
        print("Generating predictions for training images...")
        self._generate_predictions(iter_num, train_loader)
        print("Predictions saved\n")

        # Calculate final metrics on validation set (if available)
        if has_validation:
            print("Calculating final metrics...")
            final_metrics = self._calculate_final_metrics(iter_num, val_loader)

            # Format metrics
            print(format_metrics_for_display(final_metrics, self.class_names))

            # Save metrics with validation
            print("\nSaving metrics...")
            metrics_dict = {
                'train_loss': train_metrics['loss'],
                'val_loss': val_metrics['loss'],
                'miou': final_metrics['miou'],
                'per_class_iou': final_metrics['per_class_iou'],
                'pixel_accuracy': final_metrics['pixel_accuracy'],
                'per_class_accuracy': final_metrics['per_class_accuracy'],
                'num_epochs': self.num_epochs
            }
        else:
            # Save metrics without validation
            print("\nSaving metrics (no validation data)...")
            metrics_dict = {
                'train_loss': train_metrics['loss'],
                'val_loss': None,
                'miou': None,
                'per_class_iou': None,
                'pixel_accuracy': None,
                'per_class_accuracy': None,
                'num_epochs': self.num_epochs
            }

        self.session_manager.save_iteration_metrics(iter_num, metrics_dict)

        # Create next iteration
        if create_next_iteration:
            print(f"\nCreating iteration {iter_num + 1}...")
            next_iter = self.session_manager.create_next_iteration()
            print(f"Iteration {next_iter} ready for annotation\n")

        print(f"{'='*60}")
        print(f"ITERATION {iter_num} COMPLETE")
        print(f"{'='*60}\n")

        return metrics_dict

    def _initialize_model(self) -> None:
        """Initialize model, optimizer, and loss functions."""
        model_config = self.training_config['model']

        # Create model
        model_class = getattr(smp, model_config['architecture'])
        self.model = model_class(
            encoder_name=model_config['encoder'],
            encoder_weights=model_config.get('encoder_weights', 'imagenet'),
            classes=self.num_classes,
            activation=model_config.get('activation', 'softmax'),
            in_channels=model_config.get('in_channels', 3)
        )

        self.model = self.model.to(self.device)

        # Create optimizer
        optimizer_config = self.training_config['optimizer']
        optimizer_class = getattr(torch.optim, optimizer_config['name'])
        self.optimizer = optimizer_class(
            self.model.parameters(),
            **optimizer_config['params']
        )

        # Create loss functions
        train_loss_config = self.training_config['loss']['train']
        val_loss_config = self.training_config['loss']['validation']

        # Get loss class from smp.utils.losses
        train_loss_class = getattr(smp.utils.losses, train_loss_config['name'])
        val_loss_class = getattr(smp.utils.losses, val_loss_config['name'])

        # Set ignore_index for losses that support it
        train_loss_params = train_loss_config['params'].copy()
        if 'ignore_index' not in train_loss_params and train_loss_config['name'] != 'CrossEntropyLoss':
            train_loss_params['ignore_index'] = self.ignore_index

        self.train_criterion = train_loss_class(**train_loss_params)
        self.val_criterion = val_loss_class(**val_loss_config['params'])

    def _load_previous_model(self, iteration: int) -> bool:
        """
        Loads model from iteration_{N-1}/models/best_model.pth.

        Args:
            iteration: Current iteration number

        Returns:
            True if loaded successfully, False otherwise
        """
        prev_model_path = self.session_manager.get_previous_model_path(iteration)

        if prev_model_path is None or not prev_model_path.exists():
            return False

        try:
            checkpoint = torch.load(prev_model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)
            return True
        except Exception as e:
            print(f"Warning: Could not load previous model: {e}")
            return False

    def _create_dataloaders(self, iteration: int) -> Tuple[DataLoader, DataLoader]:
        """
        Creates train and validation dataloaders.

        Args:
            iteration: Iteration number

        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Get preprocessing function from encoder
        encoder_name = self.training_config['model']['encoder']
        encoder_weights = self.training_config['model'].get('encoder_weights', 'imagenet')

        preprocessing_fn = smp.encoders.get_preprocessing_fn(encoder_name, encoder_weights)

        return create_dataloaders(
            session_manager=self.session_manager,
            iteration=iteration,
            dataset_config=self.dataset_config,
            training_config=self.training_config,
            preprocessing_fn=preprocessing_fn
        )

    def _train_epoch(self, dataloader: DataLoader, epoch: int) -> Dict:
        """
        Runs one training epoch.

        Args:
            dataloader: Training dataloader
            epoch: Current epoch number

        Returns:
            Dictionary with training metrics
        """
        self.model.train()

        total_loss = 0.0
        num_batches = 0

        for images, masks in dataloader:
            images = images.to(self.device)
            masks = masks.to(self.device)

            # Forward pass
            self.optimizer.zero_grad()
            predictions = self.model(images)

            # Calculate loss
            loss = self.train_criterion(predictions, masks)

            # Backward pass
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0

        return {'loss': avg_loss}

    def _validate_epoch(self, dataloader: DataLoader, epoch: int) -> Dict:
        """
        Runs one validation epoch.

        Args:
            dataloader: Validation dataloader
            epoch: Current epoch number

        Returns:
            Dictionary with validation metrics
        """
        self.model.eval()

        total_loss = 0.0
        all_ious = []
        num_batches = 0

        with torch.no_grad():
            for images, masks in dataloader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                # Forward pass
                predictions = self.model(images)

                # Calculate loss
                loss = self.val_criterion(predictions, masks)
                total_loss += loss.item()

                # Calculate IoU
                pred_masks = torch.argmax(predictions, dim=1).cpu().numpy()
                true_masks = masks.cpu().numpy()

                batch_metrics = calculate_metrics(
                    true_masks,
                    pred_masks,
                    self.num_classes,
                    self.ignore_index
                )
                all_ious.append(batch_metrics['miou'])

                num_batches += 1

        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        avg_miou = np.mean(all_ious) if all_ious else 0.0

        return {
            'loss': avg_loss,
            'miou': avg_miou
        }

    def _save_best_model(self, iteration: int) -> None:
        """
        Saves model to iteration_N/models/best_model.pth.

        Args:
            iteration: Iteration number
        """
        iteration_path = self.session_manager.get_iteration_path(iteration)
        models_dir = iteration_path / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)

        model_path = models_dir / 'best_model.pth'
        torch.save(self.model.state_dict(), model_path)

    def _generate_predictions(self, iteration: int, train_loader: DataLoader) -> None:
        """
        Generates predictions for all training images.

        Saves predictions as PNG to iteration_N/predictions/.
        Naming: {image_name}_pred.png

        Args:
            iteration: Iteration number
            train_loader: Training dataloader
        """
        self.model.eval()

        iteration_path = self.session_manager.get_iteration_path(iteration)
        predictions_dir = iteration_path / 'predictions'
        predictions_dir.mkdir(parents=True, exist_ok=True)

        # Get training image paths
        train_image_dir = Path(self.dataset_config['paths']['train_images'])
        if not train_image_dir.is_absolute():
            train_image_dir = Path.cwd() / train_image_dir

        # Support PNG, TIF, TIFF images
        image_files = sorted(list(train_image_dir.glob('*.png')) + list(train_image_dir.glob('*.tif')) + list(train_image_dir.glob('*.tiff')))

        with torch.no_grad():
            for idx, (images, _) in enumerate(train_loader):
                images = images.to(self.device)

                # Forward pass
                predictions = self.model(images)
                pred_masks = torch.argmax(predictions, dim=1).cpu().numpy()

                # Save each prediction in batch
                for batch_idx in range(pred_masks.shape[0]):
                    global_idx = idx * train_loader.batch_size + batch_idx

                    if global_idx < len(image_files):
                        image_name = image_files[global_idx].stem
                        pred_path = predictions_dir / f'{image_name}_pred.png'

                        # Save as PNG
                        pred_mask = pred_masks[batch_idx].astype(np.uint8)
                        Image.fromarray(pred_mask).save(pred_path)

    def _calculate_final_metrics(self, iteration: int, val_loader: DataLoader) -> Dict:
        """
        Runs final evaluation on validation set.

        Args:
            iteration: Iteration number
            val_loader: Validation dataloader

        Returns:
            Dictionary with comprehensive metrics
        """
        self.model.eval()

        all_true_masks = []
        all_pred_masks = []

        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(self.device)

                # Forward pass
                predictions = self.model(images)
                pred_masks = torch.argmax(predictions, dim=1).cpu().numpy()
                true_masks = masks.numpy()

                all_true_masks.append(true_masks)
                all_pred_masks.append(pred_masks)

        # Concatenate all batches
        all_true_masks = np.concatenate(all_true_masks, axis=0)
        all_pred_masks = np.concatenate(all_pred_masks, axis=0)

        # Calculate metrics
        metrics = calculate_metrics(
            all_true_masks,
            all_pred_masks,
            self.num_classes,
            self.ignore_index
        )

        return metrics
