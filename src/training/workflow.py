"""
Complete training iteration workflow for active learning.

Handles the full training cycle: dataloaders, training, predictions,
metrics calculation, visualization, and next iteration setup.
"""
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import torch
from PIL import Image
from tqdm import tqdm
import segmentation_models_pytorch as smp
import imageio
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def cosine_1cycle_lr(epoch, num_epochs=100, warmup_epochs=10, peak_epoch=30,
                     warmup_target_lr=1e-4, peak_lr=1e-3, end_lr=1e-4):
    """1cycle-style schedule with linear warmup + cosine rise + cosine decay.

    Phase 1 (0..warmup_epochs): linear 0 → warmup_target_lr
    Phase 2 (warmup_epochs..peak_epoch): cosine rise warmup_target_lr → peak_lr
    Phase 3 (peak_epoch..num_epochs): cosine decay peak_lr → end_lr
    """
    if epoch < warmup_epochs:
        return (epoch + 1) / warmup_epochs * warmup_target_lr
    if epoch < peak_epoch:
        progress = (epoch - warmup_epochs) / max(peak_epoch - warmup_epochs, 1)
        return warmup_target_lr + 0.5 * (peak_lr - warmup_target_lr) * (1 - np.cos(np.pi * progress))
    progress = (epoch - peak_epoch) / max(num_epochs - peak_epoch, 1)
    return end_lr + 0.5 * (peak_lr - end_lr) * (1 + np.cos(np.pi * progress))


def evaluate_real_metrics(model, val_loader, val_loss_fn, device, num_classes, ignore_index):
    """Single val pass over the entire val set returning (val_loss, real_miou).

    Real mIoU = mean over per-class IoU, where each class IoU is computed from
    TP/FP/FN accumulated globally (matches metrics_history.csv computation).
    Use this for best-checkpoint selection so the per-epoch criterion matches
    the final reported metric — smp's batch-averaged miou diverges from the
    confusion-matrix mIoU under class imbalance.

    Binary segmentation (SMP convention: num_classes=1, single sigmoid-activated
    output channel) is detected by num_classes==1. Confusion matrix is still
    2x2 (background and foreground), and the returned scalar is foreground IoU
    only — matching the binary tasks' paper-table reporting convention.
    Multiclass tasks return mean IoU averaged across classes.
    """
    model.eval()
    loss_sum = 0.0
    sample_count = 0
    binary = num_classes == 1
    cm_size = 2 if binary else num_classes
    cm_total = np.zeros((cm_size, cm_size), dtype=np.int64)
    labels_list = list(range(cm_size))
    with torch.no_grad():
        for images, targets in val_loader:
            images = images.to(device)
            targets = targets.to(device)
            outputs = model(images)
            loss = val_loss_fn(outputs, targets)
            loss_sum += float(loss.item()) * images.size(0)
            sample_count += images.size(0)
            if binary:
                # Single-channel sigmoid-activated output: threshold at 0.5.
                if outputs.dim() == 4 and outputs.size(1) == 1:
                    probs = outputs.squeeze(1)
                else:
                    probs = outputs
                preds = (probs > 0.5).long().cpu().numpy().ravel()
            else:
                preds = outputs.argmax(dim=1).cpu().numpy().ravel()
            tgts = targets.cpu().numpy().ravel()
            valid = tgts != ignore_index
            cm_total += confusion_matrix(tgts[valid], preds[valid], labels=labels_list)
    val_loss_value = loss_sum / max(sample_count, 1)
    tp = np.diag(cm_total)
    fn = cm_total.sum(axis=1) - tp
    fp = cm_total.sum(axis=0) - tp
    iou_per_class = tp / (tp + fp + fn + 1e-8)
    if binary:
        return val_loss_value, float(iou_per_class[1])
    return val_loss_value, float(np.mean(iou_per_class))


class TrainEpochWithGradClip(smp.utils.train.TrainEpoch):
    """
    Custom TrainEpoch that adds gradient clipping for training stability.

    Gradient clipping prevents gradient explosion by limiting the total
    magnitude of gradients, which is important when using high penalty
    weights in confidence-based losses.
    """

    def __init__(self, model, loss, metrics, optimizer, device='cpu',
                 verbose=True, use_amp=False, scaler=None, max_grad_norm=5.0):
        super().__init__(model, loss, metrics, optimizer, device, verbose, use_amp, scaler)
        self.max_grad_norm = max_grad_norm

    def batch_update(self, x, y, batch_count=None):
        """Override batch_update to add gradient clipping."""
        self.optimizer.zero_grad()

        # Forward pass (with or without AMP)
        if self.use_amp:
            with torch.amp.autocast('cuda'):
                prediction = self.model.forward(x)
                loss = self.loss(prediction, y)
        else:
            prediction = self.model.forward(x)
            loss = self.loss(prediction, y)

        # Backward pass
        if self.use_amp:
            self.scaler.scale(loss).backward()
            # Gradient clipping with AMP
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss.backward()
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
            self.optimizer.step()

        return loss, prediction


class PredictionDataset(Dataset):
    """
    Dataset for generating predictions with same preprocessing as training.

    Uses imageio + float32 to match CustomDataset behavior in dataloader.py.
    Transform includes ToTensor and optional dataset-specific normalization.
    """
    def __init__(self, image_paths, transform):
        self.image_paths = image_paths
        self.transform = transform

    def __getitem__(self, index):
        # Load image using imageio (same as training)
        image = imageio.imread(str(self.image_paths[index]))
        image = np.asarray(image, dtype='float32')  # Keep [0, 255] range!

        # Apply transform (ToTensor + optional normalization from dataset config)
        if self.transform:
            image = self.transform(image)

        return image, self.image_paths[index].name

    def __len__(self):
        return len(self.image_paths)


def compute_penalty_schedule(epoch, max_epochs):
    """
    Compute linearly ramped penalty weights for confidence-based losses.

    Implements curriculum learning by starting with gentle penalties and
    gradually increasing to full penalties over the first 2/3 of training,
    then maintaining full penalties for the final 1/3.

    Args:
        epoch: Current epoch (0-indexed)
        max_epochs: Total number of epochs

    Returns:
        tuple: (uncertain_correct_penalty, uncertain_wrong_penalty, confident_wrong_penalty)
    """
    # Reach max penalties at 2/3 of training
    ramp_epochs = int(max_epochs * 2 / 3)

    # Compute progress (0.0 at start, 1.0 at 2/3 mark, stays 1.0 after)
    progress = min(epoch / max(ramp_epochs - 1, 1), 1.0)

    # Linear ramp from start to end values
    # Start: gentle penalties (early training, model is learning basics)
    # 2/3 mark: full penalties (enforce calibration for final 1/3)
    uncertain_correct = 1.0 + progress * 0.5   # 1.0 → 1.5
    uncertain_wrong = 5.0 + progress * 10.0     # 5.0 → 15.0
    confident_wrong = 15.0 + progress * 35.0    # 15.0 → 50.0

    return uncertain_correct, uncertain_wrong, confident_wrong


def run_training_iteration(
    session_path,
    dataset_config,
    training_config,
    model,
    device,
    train_loss,
    val_loss,
    metrics,
    optimizer,
    iteration='latest',
    visualize=True,
    use_lr_schedule=True,
    save_checkpoint_interval=None,
    lr_schedule_name='warmup_peak_decay',
    test_loader=None,
):
    """
    Run complete training iteration workflow.

    This function handles:
    1. Finding the iteration to train
    2. Creating dataloaders
    3. Loading previous model weights (if available)
    4. Training the model
    5. Generating predictions
    6. Calculating and saving metrics
    7. Visualizing results (optional)
    8. Creating next iteration

    Args:
        session_path: Path to session directory
        dataset_config: Dataset configuration dict
        training_config: Training configuration dict
        model: PyTorch model
        device: Device (cuda/cpu)
        train_loss: Training loss function
        val_loss: Validation loss function
        metrics: List of metric functions
        optimizer: Optimizer
        iteration: Iteration to train. Can be:
            - 'latest': Use latest iteration (default)
            - 'current': Same as 'latest'
            - int: Specific iteration number (e.g., 0, 1, 2)
        visualize: Whether to show visualization plots (default True)
        use_lr_schedule: Whether to use warmup-peak-decay LR schedule (default True).
            If False, uses constant learning rate from optimizer.

    Returns:
        dict: Training result with keys:
            - iteration: Iteration number trained
            - success: Overall success status
            - best_miou: Best mIoU achieved
            - pixel_accuracy: Pixel accuracy on validation set
            - train_loss: Final training loss
            - val_loss: Final validation loss
            - num_predictions: Number of predictions generated
            - next_iteration: Next iteration number created
            - message: Status message
    """
    print(f"{'='*60}")
    print(f"TRAINING ITERATION WORKFLOW")
    print(f"{'='*60}\n")

    session_path = Path(session_path)

    # ============================================================
    # STEP 1: Find Iteration to Train
    # ============================================================
    iteration_dirs = sorted([d for d in session_path.glob('iteration_*') if d.is_dir()])

    if not iteration_dirs:
        return {
            'iteration': None,
            'success': False,
            'best_miou': 0.0,
            'pixel_accuracy': 0.0,
            'train_loss': 0.0,
            'val_loss': 0.0,
            'num_predictions': 0,
            'next_iteration': None,
            'message': 'No iterations found in session'
        }

    iterations = [int(d.name.split('_')[1]) for d in iteration_dirs]

    # Determine which iteration to use
    if iteration == 'latest' or iteration == 'current':
        current_iter = max(iterations)
    elif isinstance(iteration, int):
        if iteration not in iterations:
            return {
                'iteration': iteration,
                'success': False,
                'best_miou': 0.0,
                'pixel_accuracy': 0.0,
                'train_loss': 0.0,
                'val_loss': 0.0,
                'num_predictions': 0,
                'next_iteration': None,
                'message': f'Iteration {iteration} does not exist. Available: {iterations}'
            }
        current_iter = iteration
    else:
        return {
            'iteration': None,
            'success': False,
            'best_miou': 0.0,
            'pixel_accuracy': 0.0,
            'train_loss': 0.0,
            'val_loss': 0.0,
            'num_predictions': 0,
            'next_iteration': None,
            'message': f'Invalid iteration parameter: {iteration}'
        }

    print(f"Training Iteration: {current_iter}")
    print(f"Session: {session_path}\n")

    iter_path = session_path / f'iteration_{current_iter}'
    masks_dir = iter_path / 'masks'
    models_dir = iter_path / 'models'
    predictions_dir = iter_path / 'predictions'

    # ============================================================
    # STEP 2: Prepare Data Loaders
    # ============================================================
    print(f"{'='*60}")
    print(f"STEP 1: Preparing Data Loaders")
    print(f"{'-'*60}\n")

    from src.training.dataloader import create_dataloaders

    train_loader, val_loader, train_images, base_transform, class_pixel_counts = create_dataloaders(
        dataset_config=dataset_config,
        training_config=training_config,
        masks_dir=masks_dir
    )

    # ============================================================
    # STEP 3: Load Previous Model Weights (if available)
    # ============================================================
    print(f"{'='*60}")
    print(f"STEP 2: Load Previous Model Weights")
    print(f"{'-'*60}\n")

    import os as _os
    _custom_warm = _os.environ.get("CURATED_WARM_START", "").strip()
    if _custom_warm and Path(_custom_warm).exists():
        print(f"Loading custom warm-start weights from {_custom_warm}...")
        model.load_state_dict(torch.load(_custom_warm))
        print(f"✓ Custom warm-start loaded\n")
    elif current_iter > 0:
        prev_model_path = session_path / f'iteration_{current_iter - 1}' / 'models' / 'best_model.pth'
        if prev_model_path.exists():
            print(f"Loading weights from iteration {current_iter - 1}...")
            model.load_state_dict(torch.load(prev_model_path))
            print(f"✓ Weights loaded from {prev_model_path}\n")
        else:
            print(f"⚠ No previous model found, starting from ImageNet weights\n")
    else:
        print(f"Iteration 0: Starting from ImageNet weights\n")

    # ============================================================
    # STEP 4: Train Model
    # ============================================================
    print(f"{'='*60}")
    print(f"STEP 3: Training Model")
    print(f"{'-'*60}\n")

    # Enable cuDNN benchmark for faster training (RTX 4090 optimization)
    torch.backends.cudnn.benchmark = True
    print(f"✓ cuDNN benchmark enabled (optimizing for fixed input size)")

    # Enable mixed precision training (AMP) for faster training
    use_amp = True
    scaler = torch.amp.GradScaler('cuda', enabled=use_amp)
    print(f"✓ Mixed precision (AMP) ENABLED (fp16 for speed, fp32 for stability)")
    print(f"✓ Gradient clipping enabled (max_norm=5.0) for training stability")
    print()

    # Create train and validation epochs (with AMP support + gradient clipping)
    train_epoch = TrainEpochWithGradClip(
        model,
        loss=train_loss,
        metrics=metrics,
        optimizer=optimizer,
        device=device,
        verbose=True,
        use_amp=use_amp,
        scaler=scaler,
        max_grad_norm=5.0  # Gradient clipping for training stability
    )

    # Training loop
    num_epochs = training_config['training']['num_epochs']
    best_miou = 0.0
    train_losses = []
    val_losses = []
    val_ious = []
    # Pull real-metric inputs once (used by evaluate_real_metrics each epoch).
    eval_num_classes = dataset_config['classes']['num_classes']
    eval_ignore_index = dataset_config['classes']['ignore_index']

    print(f"Training for {num_epochs} epochs...")

    if use_lr_schedule:
        print(f"Learning rate schedule (Warmup-Peak-Decay):")
        print(f"  Epochs 1-100: lr = 0.0001 (warmup)")
        print(f"  Epochs 101-200: lr = 0.001 (peak)")
        print(f"  Epochs 201-{num_epochs}: lr = 0.0001 (decay)")
    else:
        print(f"Learning rate: {optimizer.param_groups[0]['lr']} (constant)")

    # Check if using confidence-based loss with penalty scheduling
    if hasattr(train_loss, 'uncertain_correct_penalty'):
        print(f"\nPenalty schedule (Linear curriculum learning):")
        start_uc, start_uw, start_cw = compute_penalty_schedule(0, num_epochs)
        end_uc, end_uw, end_cw = compute_penalty_schedule(num_epochs - 1, num_epochs)
        print(f"  Start: uncertain_correct={start_uc:.1f}, uncertain_wrong={start_uw:.1f}, confident_wrong={start_cw:.1f}")
        print(f"  End:   uncertain_correct={end_uc:.1f}, uncertain_wrong={end_uw:.1f}, confident_wrong={end_cw:.1f}")
        print(f"  Confidence threshold: {train_loss.confidence_threshold}")

    print(f"\nDevice: {device}\n")

    for epoch in range(num_epochs):
        # Learning-rate schedule.
        if use_lr_schedule:
            if lr_schedule_name == 'cosine_1cycle':
                # 1cycle-style: linear warmup → cosine rise → cosine decay.
                lr = cosine_1cycle_lr(epoch, num_epochs=num_epochs)
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Cosine 1cycle: warmup 10ep to 1e-4, peak 1e-3 at ep 30, end 1e-4 at ep {num_epochs}")
            elif lr_schedule_name == 'warmstart_gentle':
                # Gentle fine-tuning for warm-started converged models:
                # 10 epochs at 1e-5 (refresh Adam moments) then 1e-4 until end.
                lr = 1e-5 if epoch < 10 else 1e-4
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-gentle: 1e-5 for epochs 1-10, then 1e-4 for epochs 11-{num_epochs}")
            elif lr_schedule_name == 'warmstart_gentle_30':
                # Extended warmup: 30 epochs at 1e-5 then 1e-4 until end.
                lr = 1e-5 if epoch < 30 else 1e-4
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-gentle-30: 1e-5 for epochs 1-30, then 1e-4 for epochs 31-{num_epochs}")
            elif lr_schedule_name == 'warmstart_gentle_50':
                # Long warmup: 50 epochs at 1e-5 then 1e-4 until end.
                lr = 1e-5 if epoch < 50 else 1e-4
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-gentle-50: 1e-5 for epochs 1-50, then 1e-4 for epochs 51-{num_epochs}")
            elif lr_schedule_name == 'warmstart_gentle_50_decay':
                # Long warmup with gentle polish: 50 epochs at 1e-5 then 1e-6 until end.
                # Replaces the destructive 1e-4 jump with a stable polish phase.
                lr = 1e-5 if epoch < 50 else 1e-6
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-gentle-50-decay: 1e-5 for epochs 1-50, then 1e-6 for epochs 51-{num_epochs}")
            elif lr_schedule_name == 'warmstart_gentle_30_decay':
                # Short warmup with gentle polish: 30 epochs at 1e-5 then 1e-6 until end.
                # Replaces the destructive 1e-4 jump with a stable polish phase.
                # Suited to warm-start fine-tuning where the source model is already
                # converged and last-epoch reporting is the deployment-realistic target
                # (no validation labels to pick the best-epoch checkpoint).
                lr = 1e-5 if epoch < 30 else 1e-6
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-gentle-30-decay: 1e-5 for epochs 1-30, then 1e-6 for epochs 31-{num_epochs}")
            elif lr_schedule_name == 'constant_1e4':
                # Constant 1e-4 throughout — no warmup, no peak, no decay.
                lr = 1e-4
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Constant LR 1e-4 for all {num_epochs} epochs")
            elif lr_schedule_name == 'constant_1e3':
                # Constant 1e-3 throughout — aggressive, no warmup, no decay.
                lr = 1e-3
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Constant LR 1e-3 for all {num_epochs} epochs")
            elif lr_schedule_name == 'warmstart_30_1e4_decay':
                # Mirror of warmstart_gentle_30_decay but one decade higher.
                # 30 epochs at 1e-4 (active exploration) then 1e-5 until end (polish).
                # Suited to BsB warm-start where final-epoch ≈ best-epoch is the
                # deployment-realistic target.
                lr = 1e-4 if epoch < 30 else 1e-5
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-30-1e4-decay: 1e-4 for epochs 1-30, then 1e-5 for epochs 31-{num_epochs}")
            elif lr_schedule_name == 'warmstart_50_1e4_decay':
                # Extended Phase 1: 50 epochs at 1e-4 (more exploration) then 1e-5.
                # Suited when warmstart_30_1e4_decay shows phase 2 drift away from peak.
                lr = 1e-4 if epoch < 50 else 1e-5
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Warmstart-50-1e4-decay: 1e-4 for epochs 1-50, then 1e-5 for epochs 51-{num_epochs}")
            elif lr_schedule_name == 'phase_50_1e3_then_1e4':
                # Two-phase: 50 epochs at 1e-3 (aggressive), then 1e-4 (refinement).
                lr = 1e-3 if epoch < 50 else 1e-4
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Phase schedule: 1e-3 for epochs 1-50, then 1e-4 for epochs 51-{num_epochs}")
            elif lr_schedule_name == 'phase_20_1e3_30_1e4_50_1e5':
                # Three-phase: 20@1e-3 (aggressive convergence) + 30@1e-4 (refine) + 50@1e-5 (polish).
                if epoch < 20:
                    lr = 1e-3
                elif epoch < 50:
                    lr = 1e-4
                else:
                    lr = 1e-5
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Phase 20+30+50: 1e-3 (ep1-20) → 1e-4 (ep21-50) → 1e-5 (ep51-{num_epochs})")
            elif lr_schedule_name == 'cosine_decay_1e4_to_1e5':
                # Cosine decay from 1e-4 to 1e-5 over all epochs — for warm-started fine-tune.
                import math as _math
                lr = 1e-5 + 0.5 * (1e-4 - 1e-5) * (1 + _math.cos(_math.pi * epoch / max(num_epochs, 1)))
                for pg in optimizer.param_groups:
                    pg['lr'] = lr
                if epoch == 0:
                    print(f"→ Cosine decay: 1e-4 → 1e-5 over {num_epochs} epochs")
            else:
                # Legacy warmup-peak-decay (1-100/101-200/201+).
                if epoch == 0:
                    for param_group in optimizer.param_groups:
                        param_group['lr'] = 0.0001
                    print(f"→ Learning rate set to 0.0001 (warmup: epochs 1-100)")
                elif epoch == 100:
                    for param_group in optimizer.param_groups:
                        param_group['lr'] = 0.001
                    print(f"→ Learning rate increased to 0.001 (peak: epochs 101-200)")
                elif epoch == 200:
                    for param_group in optimizer.param_groups:
                        param_group['lr'] = 0.0001
                    print(f"→ Learning rate reduced to 0.0001 (decay: epochs 201-{num_epochs})")

        current_lr = optimizer.param_groups[0]['lr']

        # Update penalty schedule for confidence-based losses (DWCCE, DWCDL)
        # Check if loss has penalty attributes
        if hasattr(train_loss, 'uncertain_correct_penalty'):
            uc, uw, cw = compute_penalty_schedule(epoch, num_epochs)
            train_loss.uncertain_correct_penalty = uc
            train_loss.uncertain_wrong_penalty = uw
            train_loss.confident_wrong_penalty = cw

            # Print penalty updates at key epochs
            if epoch == 0:
                print(f"→ Penalty schedule initialized (linear ramp over {num_epochs} epochs)")
                print(f"   Start: uncertain_correct={uc:.1f}, uncertain_wrong={uw:.1f}, confident_wrong={cw:.1f}")
            elif epoch == num_epochs - 1:
                print(f"→ Final penalties reached: uncertain_correct={uc:.1f}, uncertain_wrong={uw:.1f}, confident_wrong={cw:.1f}")

        print(f"Epoch {epoch + 1}/{num_epochs} (lr={current_lr})")

        # Train
        train_logs = train_epoch.run(train_loader)

        # Validate with the same TP/FP/FN-based mIoU used in metrics_history.csv
        # so best-checkpoint selection matches the reported metric.
        val_loss_value, real_miou = evaluate_real_metrics(
            model, val_loader, val_loss, device, eval_num_classes, eval_ignore_index,
        )

        # Track metrics
        train_loss_key = [k for k in train_logs.keys() if 'loss' in k.lower()][0]
        train_losses.append(train_logs[train_loss_key])
        val_losses.append(val_loss_value)
        val_ious.append(real_miou)

        # Optional test-set evaluation per epoch — written to a separate
        # epoch_metrics.csv so we can monitor val/test divergence.
        test_miou = None
        test_loss_value = None
        if test_loader is not None:
            test_loss_value, test_miou = evaluate_real_metrics(
                model, test_loader, val_loss, device, eval_num_classes, eval_ignore_index,
            )
        # Append to per-epoch trajectory CSV (always, regardless of best).
        epoch_csv = session_path / f"iteration_{current_iter}" / "epoch_metrics.csv"
        epoch_csv.parent.mkdir(parents=True, exist_ok=True)
        write_header = not epoch_csv.exists()
        with open(epoch_csv, "a") as ef:
            if write_header:
                ef.write("epoch,train_loss,val_loss,val_miou,test_loss,test_miou,lr\n")
            ef.write(
                f"{epoch + 1},{train_logs[train_loss_key]:.6f},"
                f"{val_loss_value:.6f},{real_miou:.6f},"
                f"{test_loss_value if test_loss_value is not None else ''},"
                f"{test_miou if test_miou is not None else ''},"
                f"{current_lr:.6e}\n"
            )

        # Save best model based on HIGHEST real validation mIoU
        if real_miou > best_miou:
            best_miou = real_miou
            models_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), models_dir / 'best_model.pth')
            test_str = f", Test mIoU: {test_miou:.4f}" if test_miou is not None else ""
            print(f"→ Best model saved! mIoU: {best_miou:.4f}, Val Loss: {val_loss_value:.4f}{test_str}")

        # Save periodic checkpoints (every save_checkpoint_interval epochs).
        # Useful for tracking plateau / overfit dynamics across the training run.
        if save_checkpoint_interval is not None and (epoch + 1) % save_checkpoint_interval == 0:
            models_dir.mkdir(parents=True, exist_ok=True)
            ckpt_path = models_dir / f'epoch_{epoch + 1:03d}.pth'
            torch.save(model.state_dict(), ckpt_path)
            print(f"→ Checkpoint saved: {ckpt_path.name} (val mIoU: {real_miou:.4f})")

        print()

    print(f"✓ Training complete!")
    print(f"✓ Best mIoU: {best_miou:.4f}\n")

    # Save the final-epoch model state before loading best-val for predictions.
    # This lets downstream analysis compare best-val vs last-epoch performance,
    # which addresses the "is a validation set required?" question empirically.
    models_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), models_dir / 'final_model.pth')
    print(f"→ Final-epoch model saved: final_model.pth (val mIoU at last epoch: {val_ious[-1]:.4f})\n")

    # Load best model for predictions
    model.load_state_dict(torch.load(models_dir / 'best_model.pth'))

    # ============================================================
    # STEP 5: Generate Predictions
    # ============================================================
    print(f"{'='*60}")
    print(f"STEP 4: Generating Predictions")
    print(f"{'-'*60}\n")

    predictions_dir.mkdir(parents=True, exist_ok=True)

    # Create prediction dataset using base preprocessing (NO augmentation!)
    # Uses imageio + float32 WITHOUT /255 normalization → [0, 255] range
    # IMPORTANT: Uses base_transform (no random flips/augmentation)
    pred_dataset = PredictionDataset(
        image_paths=train_images,
        transform=base_transform  # NO augmentation for predictions!
    )
    pred_loader = DataLoader(
        pred_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0
    )

    # Verify we're using the same images as training
    print(f"\n[Image Path Verification]")
    print(f"Training uses {len(train_images)} images from: {train_images[0].parent}")
    print(f"Prediction uses {len(pred_dataset.image_paths)} images from: {pred_dataset.image_paths[0].parent}")
    print(f"First training image: {train_images[0].name}")
    print(f"First prediction image: {pred_dataset.image_paths[0].name}")
    if train_images == pred_dataset.image_paths:
        print(f"✓ VERIFIED: Training and prediction use IDENTICAL image lists")
    else:
        print(f"✗ WARNING: Image lists differ!")
    print()

    model.eval()
    with torch.no_grad():
        for i, (images, img_names) in enumerate(tqdm(pred_loader, desc="Generating predictions")):
            images = images.to(device)

            # Debug: Verify preprocessing and filenames match (only first image)
            if i == 0:
                print(f"\n[Preprocessing Verification]")
                print(f"Prediction input range: [{images.min().item():.1f}, {images.max().item():.1f}]")
                print(f"Expected: [0.0, 255.0] (same as training)")

                # Cross-check with training dataloader
                train_sample, _ = train_loader.dataset[0]
                train_sample = train_sample.to(device)
                print(f"Training input range: [{train_sample.min().item():.1f}, {train_sample.max().item():.1f}]")

                # Verify tensors are identical
                pred_sample = images[0]
                if torch.allclose(pred_sample, train_sample, rtol=1e-5):
                    print(f"✓ VERIFIED: Preprocessing produces IDENTICAL tensors")
                else:
                    diff = (pred_sample - train_sample).abs().max().item()
                    print(f"✗ WARNING: Tensors differ by max {diff:.6f}")

                # Verify filename preservation
                original_path = train_images[0]
                predicted_name = img_names[0]
                if original_path.name == predicted_name:
                    print(f"✓ VERIFIED: Filename preserved: {original_path.name} → {predicted_name}")
                else:
                    print(f"✗ WARNING: Filename mismatch: {original_path.name} vs {predicted_name}")
                print()

            # Predict — auto-detect binary (single-channel) vs multiclass.
            prediction = model(images)
            if prediction.dim() == 4 and prediction.size(1) == 1:
                # Binary: sigmoid-activated, threshold at 0.5.
                prediction_mask = (prediction.squeeze(1) > 0.5).long().cpu().numpy()[0].astype(np.uint8)
            else:
                prediction_mask = prediction.argmax(dim=1).cpu().numpy()[0].astype(np.uint8)

            # Save prediction as PNG (annotation tool expects .png files)
            # Get stem (filename without extension) and always save as .png
            img_stem = Path(img_names[0]).stem
            pred_path = predictions_dir / f"{img_stem}.png"
            Image.fromarray(prediction_mask).save(pred_path)

    num_predictions = len(train_images)
    print(f"✓ Generated {num_predictions} predictions\n")

    # ============================================================
    # STEP 6: Calculate Metrics
    # ============================================================
    print(f"{'='*60}")
    print(f"STEP 5: Calculate Metrics")
    print(f"{'-'*60}\n")

    # Calculate detailed per-class metrics on validation set
    all_preds = []
    all_targets = []

    num_classes = dataset_config['classes']['num_classes']
    ignore_index = dataset_config['classes']['ignore_index']
    class_names = dataset_config['classes']['names']
    binary_task = num_classes == 1

    model.eval()
    with torch.no_grad():
        for images, targets in val_loader:
            images = images.to(device)
            outputs = model(images)
            if binary_task and outputs.dim() == 4 and outputs.size(1) == 1:
                preds = (outputs.squeeze(1) > 0.5).long().cpu().numpy()
            else:
                preds = outputs.argmax(dim=1).cpu().numpy()

            all_preds.extend(preds.flatten())
            all_targets.extend(targets.numpy().flatten())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    # Filter out ignore_index
    valid_mask = all_targets != ignore_index
    all_preds_filtered = all_preds[valid_mask]
    all_targets_filtered = all_targets[valid_mask]

    # Pixel accuracy
    pixel_accuracy = (all_preds_filtered == all_targets_filtered).mean()

    # Compute confusion matrix — binary tasks track 2 labels (bg, fg) even
    # though the model has a single output channel.
    cm_size = 2 if binary_task else num_classes
    cm_labels = list(range(cm_size))
    cm = confusion_matrix(all_targets_filtered, all_preds_filtered, labels=cm_labels)

    # Extract per-class TP, FP, FN
    tp = np.diag(cm)  # True Positives for each class
    fn = cm.sum(axis=1) - tp  # False Negatives
    fp = cm.sum(axis=0) - tp  # False Positives

    # Compute precision, recall, and F1-score for each class
    precision, recall, f1_score, _ = precision_recall_fscore_support(
        all_targets_filtered, all_preds_filtered, average=None, labels=cm_labels, zero_division=0
    )

    # Compute per-class IoU
    iou_per_class = tp / (tp + fp + fn + 1e-8)  # Avoid division by zero
    if binary_task:
        # Foreground IoU only — matches binary task paper-table convention.
        mean_iou = float(iou_per_class[1])
    else:
        mean_iou = np.mean(iou_per_class)

    # Print summary metrics
    print(f"Validation Metrics Summary:")
    print(f"  Mean IoU:        {mean_iou:.4f}")
    print(f"  Mean Precision:  {np.mean(precision):.4f}")
    print(f"  Mean Recall:     {np.mean(recall):.4f}")
    print(f"  Mean F1-Score:   {np.mean(f1_score):.4f}")
    print(f"  Pixel Accuracy:  {pixel_accuracy:.4f}")
    print(f"  Final Val Loss:  {val_losses[-1]:.4f}")
    print(f"  Final Train Loss: {train_losses[-1]:.4f}\n")

    # Print per-class metrics — for binary, the class_names list contains only
    # the foreground name; prepend an explicit background label for clarity.
    if binary_task:
        display_names = ['background', class_names[0]] if len(class_names) == 1 else class_names
    else:
        display_names = class_names
    print(f"Per-Class Metrics:")
    for i in range(cm_size):
        print(f"  Class {i} ({display_names[i]}): "
              f"Precision={precision[i]:.4f}, Recall={recall[i]:.4f}, "
              f"F1={f1_score[i]:.4f}, IoU={iou_per_class[i]:.4f}")
    print()

    # Save detailed metrics to CSV
    metrics_history_file = session_path / 'metrics_history.csv'

    # Build column names for CSV
    base_columns = ['iteration', 'miou', 'mean_precision', 'mean_recall', 'mean_f1',
                    'pixel_accuracy', 'train_loss', 'val_loss',
                    'total_tp', 'total_fp', 'total_fn',
                    'total_annotated_pixels']

    # Add per-class annotated pixel columns. Binary tracks both bg and fg.
    annotated_pixel_columns = [f'class_{i}_annotated_pixels' for i in range(cm_size)]

    per_class_columns = []
    for i in range(cm_size):
        per_class_columns.extend([
            f'class_{i}_tp', f'class_{i}_fp', f'class_{i}_fn',
            f'class_{i}_precision', f'class_{i}_recall',
            f'class_{i}_f1', f'class_{i}_iou'
        ])

    all_columns = base_columns + annotated_pixel_columns + per_class_columns

    if metrics_history_file.exists():
        metrics_df = pd.read_csv(metrics_history_file)
    else:
        metrics_df = pd.DataFrame(columns=all_columns)

    # Build new row
    new_row = {
        'iteration': current_iter,
        'miou': mean_iou,
        'mean_precision': np.mean(precision),
        'mean_recall': np.mean(recall),
        'mean_f1': np.mean(f1_score),
        'pixel_accuracy': pixel_accuracy,
        'train_loss': train_losses[-1],
        'val_loss': val_losses[-1],
        'total_tp': int(tp.sum()),
        'total_fp': int(fp.sum()),
        'total_fn': int(fn.sum()),
        'total_annotated_pixels': int(class_pixel_counts.sum())
    }

    # Add per-class annotated pixel counts. class_pixel_counts may have only
    # num_classes entries from the dataloader (binary: 1); pad to cm_size for
    # the wider per-class columns.
    for i in range(cm_size):
        if i < len(class_pixel_counts):
            new_row[f'class_{i}_annotated_pixels'] = int(class_pixel_counts[i])
        else:
            new_row[f'class_{i}_annotated_pixels'] = 0

    # Add per-class metrics — over the full cm_size (binary: 2 = bg + fg).
    for i in range(cm_size):
        new_row[f'class_{i}_tp'] = int(tp[i])
        new_row[f'class_{i}_fp'] = int(fp[i])
        new_row[f'class_{i}_fn'] = int(fn[i])
        new_row[f'class_{i}_precision'] = precision[i]
        new_row[f'class_{i}_recall'] = recall[i]
        new_row[f'class_{i}_f1'] = f1_score[i]
        new_row[f'class_{i}_iou'] = iou_per_class[i]

    metrics_df.loc[len(metrics_df)] = new_row
    metrics_df.to_csv(metrics_history_file, index=False)

    print(f"✓ Metrics saved to {metrics_history_file}\n")

    # ============================================================
    # STEP 7: Create Next Iteration
    # ============================================================
    print(f"\n{'='*60}")
    print(f"STEP 7: Create Next Iteration")
    print(f"{'-'*60}\n")

    next_iter = current_iter + 1
    next_iter_path = session_path / f'iteration_{next_iter}'

    # Create directory structure
    (next_iter_path / 'annotations').mkdir(parents=True, exist_ok=True)
    (next_iter_path / 'masks').mkdir(parents=True, exist_ok=True)
    (next_iter_path / 'models').mkdir(parents=True, exist_ok=True)
    (next_iter_path / 'predictions').mkdir(parents=True, exist_ok=True)

    print(f"✓ Created iteration_{next_iter} structure")

    # Copy annotations from current iteration to next
    current_annotations_dir = iter_path / 'annotations'
    next_annotations_dir = next_iter_path / 'annotations'

    annotation_files = list(current_annotations_dir.glob('*.json'))
    for json_file in tqdm(annotation_files, desc="Copying annotations"):
        shutil.copy(json_file, next_annotations_dir / json_file.name)

    print(f"✓ Copied {len(annotation_files)} annotations to iteration_{next_iter}\n")

    # ============================================================
    # Summary
    # ============================================================
    print(f"{'='*60}")
    print(f"ITERATION {current_iter} COMPLETE!")
    print(f"{'='*60}")
    print(f"\nResults:")
    print(f"  Mean IoU:        {mean_iou:.4f}")
    print(f"  Mean Precision:  {np.mean(precision):.4f}")
    print(f"  Mean Recall:     {np.mean(recall):.4f}")
    print(f"  Mean F1-Score:   {np.mean(f1_score):.4f}")
    print(f"  Pixel Accuracy:  {pixel_accuracy:.4f}")
    print(f"  Model saved:     {models_dir / 'best_model.pth'}")
    print(f"  Predictions:     {num_predictions} files")
    print(f"\nNext Steps:")
    print(f"  1. Run Cell 4 to annotate iteration {next_iter}")
    print(f"  2. Review predictions (overlay) to find uncertain areas")
    print(f"  3. Add/refine annotation points")
    print(f"  4. Run Cell 5 to train iteration {next_iter}")
    print(f"\nActive Learning Loop: Cell 4 → Cell 5 → Cell 4 → Cell 5...")
    print(f"{'='*60}")

    return {
        'iteration': current_iter,
        'success': True,
        'mean_iou': mean_iou,
        'mean_precision': np.mean(precision),
        'mean_recall': np.mean(recall),
        'mean_f1': np.mean(f1_score),
        'pixel_accuracy': pixel_accuracy,
        'train_loss': train_losses[-1],
        'val_loss': val_losses[-1],
        'num_predictions': num_predictions,
        'next_iteration': next_iter,
        'message': 'Training iteration completed successfully'
    }
