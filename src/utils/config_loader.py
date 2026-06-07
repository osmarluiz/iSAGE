"""
Configuration loading and validation utilities.

Handles loading YAML configuration files for datasets and training parameters.
"""

from pathlib import Path
from typing import Tuple, Dict, Any
import yaml


def load_dataset_config(path: str) -> dict:
    """
    Load dataset configuration from YAML file.

    Args:
        path: Path to dataset config YAML file

    Returns:
        Dictionary with dataset configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValueError: If validation fails
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Dataset config not found: {path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    is_valid, error_msg = validate_dataset_config(config)
    if not is_valid:
        raise ValueError(f"Invalid dataset config: {error_msg}")

    return config


def load_training_config(path: str) -> dict:
    """
    Load training configuration from YAML file.

    Args:
        path: Path to training config YAML file

    Returns:
        Dictionary with training configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValueError: If validation fails
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Training config not found: {path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    is_valid, error_msg = validate_training_config(config)
    if not is_valid:
        raise ValueError(f"Invalid training config: {error_msg}")

    return config


def validate_dataset_config(config: dict) -> Tuple[bool, str]:
    """
    Validate dataset configuration structure and values.

    Args:
        config: Dataset configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Config must be a dictionary"

    # Required top-level keys
    required_keys = ['name', 'paths', 'classes', 'image']
    for key in required_keys:
        if key not in config:
            return False, f"Missing required key: {key}"

    # Validate paths
    if not isinstance(config['paths'], dict):
        return False, "paths must be a dictionary"

    # train_images is required and must have a value
    if 'train_images' not in config['paths']:
        return False, "Missing required path: train_images"
    if config['paths']['train_images'] is None:
        return False, "train_images path cannot be None"

    # These paths must be defined in config but can be None (for datasets without validation/GT)
    optional_paths = ['val_images', 'val_masks', 'train_dense_masks', 'train_sparse_masks']
    for path_key in optional_paths:
        if path_key not in config['paths']:
            return False, f"Missing path key: {path_key} (can be null but must be defined)"

    # Validate classes
    if not isinstance(config['classes'], dict):
        return False, "classes must be a dictionary"

    required_class_keys = ['num_classes', 'ignore_index', 'names', 'colors']
    for key in required_class_keys:
        if key not in config['classes']:
            return False, f"Missing required classes key: {key}"

    num_classes = config['classes']['num_classes']
    if not isinstance(num_classes, int) or num_classes <= 0:
        return False, "num_classes must be a positive integer"

    class_names = config['classes']['names']
    if not isinstance(class_names, list):
        return False, "class names must be a list"

    if len(class_names) != num_classes:
        return False, f"Number of class names ({len(class_names)}) must match num_classes ({num_classes})"

    class_colors = config['classes']['colors']
    if not isinstance(class_colors, list):
        return False, "class colors must be a list"

    if len(class_colors) != num_classes:
        return False, f"Number of colors ({len(class_colors)}) must match num_classes ({num_classes})"

    # Validate each color is RGB
    for i, color in enumerate(class_colors):
        if not isinstance(color, list) or len(color) != 3:
            return False, f"Color {i} must be [R, G, B] list"
        if not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            return False, f"Color {i} values must be integers 0-255"

    # Validate image specs
    if not isinstance(config['image'], dict):
        return False, "image must be a dictionary"

    required_image_keys = ['width', 'height', 'channels']
    for key in required_image_keys:
        if key not in config['image']:
            return False, f"Missing required image key: {key}"
        if not isinstance(config['image'][key], int) or config['image'][key] <= 0:
            return False, f"image.{key} must be a positive integer"

    return True, ""


def validate_training_config(config: dict) -> Tuple[bool, str]:
    """
    Validate training configuration structure and values.

    Args:
        config: Training configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Config must be a dictionary"

    # Required top-level keys
    required_keys = ['name', 'model', 'training', 'loss', 'optimizer']
    for key in required_keys:
        if key not in config:
            return False, f"Missing required key: {key}"

    # Validate model
    if not isinstance(config['model'], dict):
        return False, "model must be a dictionary"

    required_model_keys = ['architecture', 'encoder', 'activation']
    for key in required_model_keys:
        if key not in config['model']:
            return False, f"Missing required model key: {key}"

    # Validate training
    if not isinstance(config['training'], dict):
        return False, "training must be a dictionary"

    required_training_keys = ['learning_rate', 'batch_size', 'num_epochs', 'device']
    for key in required_training_keys:
        if key not in config['training']:
            return False, f"Missing required training key: {key}"

    if not isinstance(config['training']['batch_size'], dict):
        return False, "batch_size must be a dictionary with train and val keys"

    if 'train' not in config['training']['batch_size']:
        return False, "Missing batch_size.train"
    if 'val' not in config['training']['batch_size']:
        return False, "Missing batch_size.val"

    train_bs = config['training']['batch_size']['train']
    val_bs = config['training']['batch_size']['val']

    if not isinstance(train_bs, int) or train_bs <= 0:
        return False, "batch_size.train must be a positive integer"
    if not isinstance(val_bs, int) or val_bs <= 0:
        return False, "batch_size.val must be a positive integer"

    lr = config['training']['learning_rate']
    if not isinstance(lr, (int, float)) or lr <= 0:
        return False, "learning_rate must be a positive number"

    epochs = config['training']['num_epochs']
    if not isinstance(epochs, int) or epochs <= 0:
        return False, "num_epochs must be a positive integer"

    # Validate loss
    if not isinstance(config['loss'], dict):
        return False, "loss must be a dictionary"

    if 'train' not in config['loss']:
        return False, "Missing loss.train"
    if 'validation' not in config['loss']:
        return False, "Missing loss.validation"

    for loss_type in ['train', 'validation']:
        loss_cfg = config['loss'][loss_type]
        if not isinstance(loss_cfg, dict):
            return False, f"loss.{loss_type} must be a dictionary"
        if 'name' not in loss_cfg:
            return False, f"Missing loss.{loss_type}.name"
        if 'params' not in loss_cfg:
            return False, f"Missing loss.{loss_type}.params"

    # Validate optimizer
    if not isinstance(config['optimizer'], dict):
        return False, "optimizer must be a dictionary"

    if 'name' not in config['optimizer']:
        return False, "Missing optimizer.name"
    if 'params' not in config['optimizer']:
        return False, "Missing optimizer.params"

    return True, ""


def save_config_to_yaml(config: dict, path: str) -> None:
    """
    Save configuration dictionary to YAML file.

    Args:
        config: Configuration dictionary to save
        path: Output path for YAML file
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
