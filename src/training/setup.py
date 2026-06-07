"""
Training setup module for creating model, losses, metrics, and optimizer.
"""
import torch
import torch.nn as _nn
import segmentation_models_pytorch as smp


class _BinaryValLoss(_nn.Module):
    """Per-pixel binary cross-entropy for sigmoid-probability model outputs.

    Used as validation loss when num_classes == 1 so the printed val_loss is
    interpretable in BCE units (matches the training loss family). Skips
    pixels where target == ignore_index. Casts to fp32 internally so AMP
    fp16 saturation doesn't drive log(0) → -inf.
    """

    __name__ = "binary_val_loss"

    def __init__(self, ignore_index=2, eps=1e-7):
        super().__init__()
        self.ignore_index = ignore_index
        self.eps = eps

    def forward(self, y_pr, y_gt):
        if y_pr.dim() == 4 and y_pr.size(1) == 1:
            y_pr = y_pr.squeeze(1)
        # Cast to fp32 for numerical stability under AMP (fp16 sigmoid can
        # saturate to exactly 0 or 1, and eps below 1e-7 rounds to zero in fp16).
        y_pr = y_pr.float().clamp(min=self.eps, max=1.0 - self.eps)
        valid = (y_gt != self.ignore_index).float()
        y_gt_clamped = y_gt.clone()
        y_gt_clamped[y_gt == self.ignore_index] = 0
        y_gt_f = y_gt_clamped.float()
        per_pixel = -(y_gt_f * torch.log(y_pr) + (1 - y_gt_f) * torch.log(1 - y_pr))
        return (per_pixel * valid).sum() / (valid.sum() + 1e-8)


def create_model(dataset_config, training_config):
    """Create segmentation model from configurations.

    Dispatches on training_config['model']['architecture'] to one of the SMP
    classes. Default is Unet for backward compatibility.
    """
    arch = training_config['model'].get('architecture', 'Unet')
    encoder = training_config['model']['encoder']
    encoder_weights = training_config['model'].get('encoder_weights', 'imagenet')
    activation = training_config['model'].get('activation', 'softmax')
    in_channels = dataset_config['image']['channels']
    num_classes = dataset_config['classes']['num_classes']

    arch_map = {
        'Unet': smp.Unet,
        'UnetPlusPlus': smp.UnetPlusPlus,
        'FPN': smp.FPN,
        'PSPNet': smp.PSPNet,
        'DeepLabV3': smp.DeepLabV3,
        'DeepLabV3Plus': smp.DeepLabV3Plus,
        'Linknet': smp.Linknet,
        'MAnet': smp.MAnet,
        'PAN': smp.PAN,
        'Segformer': smp.Segformer,
        'UPerNet': smp.UPerNet,
    }
    if arch not in arch_map:
        raise ValueError(f"Unsupported architecture '{arch}'. Choices: {sorted(arch_map.keys())}")

    cls = arch_map[arch]
    model = cls(
        encoder_name=encoder,
        encoder_weights=encoder_weights,
        classes=num_classes,
        activation=activation,
        in_channels=in_channels,
    )
    return model


def create_losses(dataset_config, training_config):
    """
    Create training and validation loss functions from configuration.

    Supports:
    - DWCCEMulticlass: CrossEntropy + confidence penalties + curriculum learning
    - DWCDLMulticlass: Dice Loss + confidence weighting (legacy)

    Args:
        dataset_config: Dataset configuration dict
        training_config: Training configuration dict

    Returns:
        train_loss: Loss function for training
        val_loss: Loss function for validation
    """
    loss_config = training_config.get('loss', {})
    train_config = loss_config.get('train', {})
    loss_name = train_config.get('name', 'DWCCEMulticlass')
    loss_params = train_config.get('params', {}).copy()

    # Add ignore_index from dataset config
    loss_params['ignore_index'] = dataset_config['classes']['ignore_index']

    # Create training loss based on config
    if loss_name == 'DWCCEMulticlass':
        train_loss = smp.utils.losses.DWCCEMulticlass(
            eps=loss_params.get('eps', 1e-7),
            confidence_threshold=loss_params.get('confidence_threshold', 0.95),
            uncertain_correct_penalty=loss_params.get('uncertain_correct_penalty', 1.0),
            uncertain_wrong_penalty=loss_params.get('uncertain_wrong_penalty', 5.0),
            confident_wrong_penalty=loss_params.get('confident_wrong_penalty', 15.0),
            activation=loss_params.get('activation', None),
            ignore_index=loss_params['ignore_index']
        )
    elif loss_name == 'DWCDLMulticlass':
        train_loss = smp.utils.losses.DWCDLMulticlass(
            eps=loss_params.get('eps', 1.0),
            confidence_threshold=loss_params.get('confidence_threshold', 0.8),
            uncertain_correct_penalty=loss_params.get('uncertain_correct_penalty', 2.0),
            uncertain_wrong_penalty=loss_params.get('uncertain_wrong_penalty', 4.0),
            confident_wrong_penalty=loss_params.get('confident_wrong_penalty', 10.0),
            activation=loss_params.get('activation', 'softmax'),
            ignore_index=loss_params['ignore_index']
        )
    elif loss_name == 'EWDLMulticlass':
        train_loss = smp.utils.losses.EWDLMulticlass(
            eps=loss_params.get('eps', 1.0),
            wrong_penalty=loss_params.get('wrong_penalty', 5.0),
            activation=loss_params.get('activation', None),
            ignore_index=loss_params['ignore_index']
        )
    elif loss_name == 'EWCEMulticlass':
        train_loss = smp.utils.losses.EWCEMulticlass(
            wrong_penalty=loss_params.get('wrong_penalty', 5.0),
            activation=loss_params.get('activation', None),
            ignore_index=loss_params['ignore_index'],
            eps=loss_params.get('eps', 1e-10),
        )
    elif loss_name == 'EWBCE':
        train_loss = smp.utils.losses.EWBCE(
            wrong_penalty=loss_params.get('wrong_penalty', 5.0),
            activation=loss_params.get('activation', None),
            ignore_index=loss_params['ignore_index'],
            eps=loss_params.get('eps', 1e-10),
        )
    elif loss_name == 'CrossEntropyLoss':
        # Plain CE — used for dense supervision baselines.
        # Optionally load class weights from DATASETS/CITYSCAPES_TOP5/class_weights.txt
        # (one float per line, total = num_classes). Set USE_CLASS_WEIGHTS=1 to enable.
        import os as _os, torch as _torch
        from pathlib import Path as _Path
        ce_kwargs = {'ignore_index': loss_params['ignore_index']}
        if _os.environ.get('USE_CLASS_WEIGHTS', '0') == '1':
            wp = _Path(__file__).resolve().parent.parent.parent / 'DATASETS/CITYSCAPES_TOP5/class_weights.txt'
            if wp.exists():
                vals = [float(x) for x in wp.read_text().split()]
                weight = _torch.tensor(vals, dtype=_torch.float32)
                ce_kwargs['weight'] = weight
                print(f"  Loaded class weights from {wp}: {vals}")
            else:
                print(f"  USE_CLASS_WEIGHTS=1 but no file at {wp}, falling back to no weights")
        train_loss = smp.utils.losses.CrossEntropyLoss(**ce_kwargs)
    elif loss_name == 'BCELoss':
        # Plain per-pixel BCE on sigmoid probs — for binary dense baselines.
        train_loss = _BinaryValLoss(ignore_index=loss_params['ignore_index'])
    elif loss_name == 'DiceLoss':
        # Plain Dice loss for dense segmentation — robust to class imbalance.
        train_loss = smp.utils.losses.DiceLoss(
            eps=loss_params.get('eps', 1.0),
            activation=loss_params.get('activation', None),
            ignore_channels=None,
        )
    elif loss_name == 'FocalLoss':
        # Focal Loss for multiclass: down-weights well-classified pixels.
        train_loss = smp.utils.losses.FocalLoss(
            gamma=loss_params.get('gamma', 2.0),
            ignore_index=loss_params['ignore_index'],
        )
    elif loss_name == 'EWDLBinary':
        train_loss = smp.utils.losses.EWDLBinary(
            eps=loss_params.get('eps', 1.0),
            wrong_penalty=loss_params.get('wrong_penalty', 5.0),
            activation=loss_params.get('activation', None),
            ignore_index=loss_params['ignore_index'],
        )
    else:
        raise ValueError(f"Unknown loss function: {loss_name}")

    # Validation loss: CrossEntropyLoss for multiclass, BCELoss-on-probs for binary.
    if dataset_config['classes']['num_classes'] == 1:
        # Model outputs sigmoid probs; use plain BCE on probs (not BCEWithLogitsLoss).
        val_loss = _BinaryValLoss(ignore_index=dataset_config['classes']['ignore_index'])
    else:
        val_loss = smp.utils.losses.CrossEntropyLoss(
            ignore_index=dataset_config['classes']['ignore_index']
        )

    return train_loss, val_loss


def create_metrics():
    """
    Create evaluation metrics.

    Returns:
        metrics: List of metric functions
    """
    metrics = [smp.utils.metrics.mIoU()]
    return metrics


def create_optimizer(model, training_config):
    """
    Create optimizer from configuration.

    Args:
        model: PyTorch model
        training_config: Training configuration dict

    Returns:
        optimizer: Configured optimizer
    """
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=training_config['optimizer']['params']['lr']
    )

    return optimizer


def setup_training(dataset_config, training_config):
    """
    Complete training setup from configurations.

    Creates model, losses, metrics, and optimizer in one call.

    Args:
        dataset_config: Dataset configuration dict
        training_config: Training configuration dict

    Returns:
        model: Initialized model on correct device
        device: Device (cuda/cpu)
        train_loss: Training loss function
        val_loss: Validation loss function
        metrics: List of metrics
        optimizer: Configured optimizer
    """
    print("Setting up training components...")

    # Create model
    model = create_model(dataset_config, training_config)
    print(f"✓ Model: {training_config['model']['architecture']} + {training_config['model']['encoder']}")

    # Move to device
    device = training_config['training']['device']
    model = model.to(device)
    print(f"✓ Device: {device}")

    # Create losses
    train_loss, val_loss = create_losses(dataset_config, training_config)
    # Move losses to device (so any internal weight tensors / buffers go to GPU)
    try:
        train_loss = train_loss.to(device)
        val_loss = val_loss.to(device)
    except Exception:
        pass
    train_loss_name = type(train_loss).__name__
    val_loss_name = type(val_loss).__name__
    train_params = training_config.get('loss', {}).get('train', {}).get('params', {})
    if train_params:
        params_str = ', '.join(f"{k}={v}" for k, v in train_params.items() if k != 'ignore_index')
        print(f"✓ Train Loss: {train_loss_name}({params_str})")
    else:
        print(f"✓ Train Loss: {train_loss_name}")
    print(f"✓ Val Loss: {val_loss_name}")

    # Create metrics
    metrics = create_metrics()
    print(f"✓ Metrics: mIoU")

    # Create optimizer
    optimizer = create_optimizer(model, training_config)
    print(f"✓ Optimizer: Adam (lr={training_config['optimizer']['params']['lr']})")

    print("✓ Training setup complete\n")

    return model, device, train_loss, val_loss, metrics, optimizer
