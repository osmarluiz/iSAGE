"""
Session management module for active learning workflow.

Handles creation and loading of session directories, iteration tracking,
and metrics history management.
"""
from pathlib import Path
import shutil
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import Image

from src.session.simple_mask_converter import convert_mask_to_json


def create_new_session(session_path, dataset_config):
    """
    Create a new active learning session.

    Creates the session directory structure, initializes iteration_0,
    converts sparse masks to JSON annotations and PNG masks, and
    creates the metrics history file.

    Args:
        session_path: Path to session directory (will be created)
        dataset_config: Dataset configuration dict

    Returns:
        dict: Session info with keys:
            - session_path: Path object
            - current_iteration: 0
            - status: 'created'
            - num_annotations: Number of annotation files
            - num_masks: Number of mask files
    """
    print("Creating new session...\n")

    session_path = Path(session_path)

    # Create iteration_0 structure
    iter_0_path = session_path / 'iteration_0'
    (iter_0_path / 'annotations').mkdir(parents=True, exist_ok=True)
    (iter_0_path / 'masks').mkdir(parents=True, exist_ok=True)
    (iter_0_path / 'models').mkdir(parents=True, exist_ok=True)
    (iter_0_path / 'predictions').mkdir(parents=True, exist_ok=True)

    print(f"✓ Created iteration_0 structure")

    annotations_dir = iter_0_path / 'annotations'
    masks_dir = iter_0_path / 'masks'

    # Check if we have initial sparse masks or starting from scratch
    sparse_masks_path_str = dataset_config['paths'].get('train_sparse_masks')

    if sparse_masks_path_str is not None:
        # Convert existing sparse masks to JSONs and PNGs
        sparse_masks_path = Path(sparse_masks_path_str)

        if not sparse_masks_path.exists():
            print(f"✗ Sparse masks not found: {sparse_masks_path}")
            raise FileNotFoundError(f"Sparse masks directory not found: {sparse_masks_path}")

        sparse_masks = sorted(list(sparse_masks_path.glob('*.png')))
        print(f"\nConverting {len(sparse_masks)} sparse masks to iteration_0...")

        # Convert each sparse mask to JSON and copy PNG
        for mask_file in tqdm(sparse_masks, desc="Converting masks"):
            # Convert PNG → JSON
            json_output = annotations_dir / mask_file.with_suffix('.json').name
            convert_mask_to_json(
                mask_path=mask_file,
                output_path=json_output,
                ignore_index=dataset_config['classes']['ignore_index'],
                iteration=0
            )

            # Copy PNG to masks directory
            shutil.copy(mask_file, masks_dir / mask_file.name)

        print(f"✓ Converted {len(sparse_masks)} masks to JSONs")
        print(f"✓ Copied {len(sparse_masks)} masks to PNGs")
        num_files = len(sparse_masks)
    else:
        # Starting from scratch - create empty annotations for each training image
        train_images_path = Path(dataset_config['paths']['train_images'])
        if not train_images_path.is_absolute():
            train_images_path = Path.cwd() / train_images_path

        # Support PNG, TIF, TIFF images
        train_images = sorted(list(train_images_path.glob('*.png')) + list(train_images_path.glob('*.tif')) + list(train_images_path.glob('*.tiff')))
        print(f"\nCreating empty annotations for {len(train_images)} images...")

        # Create empty JSON and mask for each training image
        ignore_index = dataset_config['classes']['ignore_index']
        img_width = dataset_config['image']['width']
        img_height = dataset_config['image']['height']

        for img_file in tqdm(train_images, desc="Creating empty annotations"):
            # Create empty JSON annotation
            json_output = annotations_dir / img_file.with_suffix('.json').name
            empty_annotation = {
                "image_name": img_file.stem,
                "iteration": 0,
                "annotations": []
            }
            with open(json_output, 'w') as f:
                json.dump(empty_annotation, f, indent=2)

            # Create empty mask (all ignore_index)
            mask_output = masks_dir / f"{img_file.stem}.png"
            empty_mask = np.full((img_height, img_width), ignore_index, dtype=np.uint8)
            Image.fromarray(empty_mask).save(mask_output)

        print(f"✓ Created {len(train_images)} empty annotations")
        print(f"✓ Created {len(train_images)} empty masks")
        num_files = len(train_images)

    # Create metrics history file
    metrics_history = pd.DataFrame(columns=['iteration', 'miou', 'pixel_accuracy', 'train_loss', 'val_loss'])
    metrics_history.to_csv(session_path / 'metrics_history.csv', index=False)

    print(f"\n✓ New session created: {session_path}")
    print(f"✓ Ready to annotate iteration 0")

    return {
        'session_path': session_path,
        'current_iteration': 0,
        'status': 'created',
        'num_annotations': num_files,
        'num_masks': num_files
    }


def load_existing_session(session_path):
    """
    Load an existing active learning session.

    Finds available iterations, determines latest iteration,
    checks status of files, and loads metrics history.

    Args:
        session_path: Path to existing session directory

    Returns:
        dict: Session info with keys:
            - session_path: Path object
            - current_iteration: Latest iteration number
            - available_iterations: List of available iteration numbers
            - status: 'loaded'
            - iteration_status: Dict with file counts and flags
            - metrics_history: DataFrame or None

    Raises:
        ValueError: If session has no iterations
    """
    print("Loading existing session...\n")

    session_path = Path(session_path)

    # Find available iterations
    iteration_dirs = sorted([d for d in session_path.glob('iteration_*') if d.is_dir()])

    if not iteration_dirs:
        print("✗ No iterations found in session")
        raise ValueError("Session exists but has no iterations")

    iterations = [int(d.name.split('_')[1]) for d in iteration_dirs]
    latest_iter = max(iterations)

    print(f"Available iterations: {iterations}")
    print(f"Latest iteration: {latest_iter}")

    # Get status of latest iteration
    latest_path = session_path / f'iteration_{latest_iter}'

    # Check files
    num_annotations = len(list((latest_path / 'annotations').glob('*.json'))) if (latest_path / 'annotations').exists() else 0
    num_masks = len(list((latest_path / 'masks').glob('*.png'))) if (latest_path / 'masks').exists() else 0
    num_predictions = len(list((latest_path / 'predictions').glob('*.png'))) if (latest_path / 'predictions').exists() else 0

    has_annotations = (latest_path / 'annotations').exists() and num_annotations > 0
    has_masks = (latest_path / 'masks').exists() and num_masks > 0
    has_model = (latest_path / 'models' / 'best_model.pth').exists()
    has_predictions = (latest_path / 'predictions').exists() and num_predictions > 0

    print(f"\nIteration {latest_iter} status:")
    print(f"  Annotations: {'✓' if has_annotations else '✗'} ({num_annotations} files)")
    print(f"  Masks:       {'✓' if has_masks else '✗'} ({num_masks} files)")
    print(f"  Model:       {'✓' if has_model else '✗'}")
    print(f"  Predictions: {'✓' if has_predictions else '✗'} ({num_predictions} files)")

    # Load metrics history if available
    metrics_file = session_path / 'metrics_history.csv'
    metrics_df = None

    if metrics_file.exists():
        metrics_df = pd.read_csv(metrics_file)
        print(f"\nMetrics history:")
        print(metrics_df.to_string(index=False))

    print(f"\n✓ Session loaded: {session_path}")

    return {
        'session_path': session_path,
        'current_iteration': latest_iter,
        'available_iterations': iterations,
        'status': 'loaded',
        'iteration_status': {
            'has_annotations': has_annotations,
            'has_masks': has_masks,
            'has_model': has_model,
            'has_predictions': has_predictions,
            'num_annotations': num_annotations,
            'num_masks': num_masks,
            'num_predictions': num_predictions
        },
        'metrics_history': metrics_df
    }


def get_or_create_session(session_path, dataset_config):
    """
    Get existing session or create new one if it doesn't exist.

    Convenience function that checks if session exists and calls
    either load_existing_session() or create_new_session().

    Args:
        session_path: Path to session directory
        dataset_config: Dataset configuration dict

    Returns:
        dict: Session info from either create_new_session() or load_existing_session()
    """
    session_path = Path(session_path)

    if session_path.exists():
        return load_existing_session(session_path)
    else:
        return create_new_session(session_path, dataset_config)
