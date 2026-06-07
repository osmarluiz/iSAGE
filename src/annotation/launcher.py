"""
Annotation Tool Launcher

Launches the isage_annotator annotation tool for SIAL active learning workflow.
Uses subprocess to avoid event loop conflicts with Jupyter.
"""

import sys
import subprocess
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def launch_annotation_tool(
    session_path: Path,
    iteration: int,
    dataset_config: Dict[str, Any],
    wait: bool = True
) -> bool:
    """
    Launch the annotation tool for interactive point annotation.

    This launches the isage_annotator annotation widget as a subprocess,
    which avoids event loop conflicts with Jupyter notebooks.

    Args:
        session_path: Path to SIAL session (e.g., Sessions/VAIHINGEN_EXPERIMENT)
        iteration: Current iteration number
        dataset_config: Dataset configuration dictionary
        wait: If True, wait for annotation tool to close. If False, return immediately.

    Returns:
        True if annotation tool launched successfully, False otherwise

    Usage:
        from src.annotation import launch_annotation_tool

        success = launch_annotation_tool(
            session_path=Path('Sessions/VAIHINGEN_EXPERIMENT'),
            iteration=0,
            dataset_config=dataset_config
        )
    """
    try:
        session_path = Path(session_path)

        # Prepare session metadata for the annotation tool
        config_dir = session_path / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create/update dataset_metadata.json (widget needs this)
        # Always update to ensure it has all required fields (paths, classes, etc.)
        dataset_metadata_path = config_dir / 'dataset_metadata.json'
        if True:  # Always create/update
            # Extract class info from dataset_config
            classes = dataset_config['classes']
            class_info = {}

            for i, name in enumerate(classes['names']):
                # Generate colors for each class (matching dataset YAML config)
                colors = [
                    '#FFFFFF',  # White - impervious (RGB: 255, 255, 255)
                    '#0000FF',  # Blue - building (RGB: 0, 0, 255)
                    '#00FF00',  # Green - tree (RGB: 0, 255, 0)
                    '#FFFF00',  # Yellow - car (RGB: 255, 255, 0)
                    '#00FFFF',  # Cyan - low_veg (RGB: 0, 255, 255)
                    '#FF0000',  # Red - clutter (RGB: 255, 0, 0)
                ]
                color = colors[i] if i < len(colors) else f'#{i*40:02x}{i*30:02x}{i*50:02x}'

                class_info[str(i)] = {
                    'name': name,
                    'color': color
                }

            # Handle None values properly
            train_masks = dataset_config['paths'].get('train_dense_masks') or dataset_config['paths'].get('train_sparse_masks') or ''
            val_images = dataset_config['paths'].get('val_images') or ''
            val_masks = dataset_config['paths'].get('val_masks') or ''

            metadata = {
                'classes': {
                    'num_classes': classes['num_classes'],
                    'ignore_index': classes['ignore_index'],
                    'class_info': class_info
                },
                'image': {
                    'width': dataset_config['image']['width'],
                    'height': dataset_config['image']['height']
                },
                'paths': {
                    'train_images': dataset_config['paths']['train_images'],
                    'train_masks': train_masks,
                    'val_images': val_images,
                    'val_masks': val_masks
                }
            }

            with open(dataset_metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created dataset_metadata.json")

        # Find the annotation tool launcher script
        project_root = Path(__file__).parent.parent.parent
        launcher_script = project_root / 'tools' / 'launch_annotation_tool.py'

        if not launcher_script.exists():
            logger.error(f"Annotation tool launcher not found: {launcher_script}")
            return False

        # Prepare command
        cmd = [
            sys.executable,  # Use same Python interpreter
            str(launcher_script),
            '--session', str(session_path),
            '--iteration', str(iteration)
        ]

        logger.info(f"Launching annotation tool:")
        logger.info(f"  Session: {session_path}")
        logger.info(f"  Iteration: {iteration}")
        logger.info(f"  Command: {' '.join(cmd)}")

        # Launch as subprocess
        if wait:
            # Wait for tool to close (blocking)
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Annotation tool closed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                logger.error(f"Annotation tool exited with error code {result.returncode}")
                if result.stderr:
                    print(f"Error output:\n{result.stderr}")
                return False
        else:
            # Launch and return immediately (non-blocking)
            subprocess.Popen(cmd)
            logger.info("Annotation tool launched in background")
            return True

    except Exception as e:
        logger.error(f"Failed to launch annotation tool: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_annotation_workflow(session_path, dataset_config, iteration='latest', launch_tool=True):
    """
    Run the complete annotation workflow for an iteration.

    This is a high-level function that handles:
    1. Finding the specified iteration
    2. Showing current annotation/mask/prediction status
    3. Launching annotation tool (if enabled)
    4. Converting JSON annotations to PNG masks after tool closes

    Args:
        session_path: Path to session directory
        dataset_config: Dataset configuration dict
        iteration: Iteration to annotate. Can be:
            - 'latest': Use latest iteration (default)
            - 'current': Same as 'latest'
            - int: Specific iteration number (e.g., 0, 1, 2)
        launch_tool: Whether to launch annotation tool (default True)

    Returns:
        dict: Workflow result with keys:
            - iteration: Iteration number used
            - tool_launched: Whether tool was launched
            - success: Overall success status
            - num_annotations: Number of annotation files
            - num_masks: Number of mask files
            - message: Status message

    Usage:
        from src.annotation.launcher import run_annotation_workflow

        result = run_annotation_workflow(
            session_path=SESSION_PATH,
            dataset_config=dataset_config,
            iteration='latest',  # or 0, 1, 2, etc.
            launch_tool=True
        )
    """
    from src.session.mask_utils import batch_json_to_masks

    print(f"{'='*60}")
    print(f"ANNOTATION WORKFLOW")
    print(f"{'='*60}\n")

    session_path = Path(session_path)

    # Step 1: Find iteration to use
    iteration_dirs = sorted([d for d in session_path.glob('iteration_*') if d.is_dir()])

    if not iteration_dirs:
        return {
            'iteration': None,
            'tool_launched': False,
            'success': False,
            'num_annotations': 0,
            'num_masks': 0,
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
                'tool_launched': False,
                'success': False,
                'num_annotations': 0,
                'num_masks': 0,
                'message': f'Iteration {iteration} does not exist. Available: {iterations}'
            }
        current_iter = iteration
    else:
        return {
            'iteration': None,
            'tool_launched': False,
            'success': False,
            'num_annotations': 0,
            'num_masks': 0,
            'message': f'Invalid iteration parameter: {iteration}'
        }

    print(f"Iteration: {current_iter}")
    print(f"Session: {session_path}\n")

    # Step 2: Get paths and show status
    iter_path = session_path / f'iteration_{current_iter}'
    annotations_dir = iter_path / 'annotations'
    masks_dir = iter_path / 'masks'

    num_annotations = len(list(annotations_dir.glob('*.json'))) if annotations_dir.exists() else 0
    num_masks = len(list(masks_dir.glob('*.png'))) if masks_dir.exists() else 0

    print(f"Current status:")
    print(f"  Annotations: {num_annotations} files")
    print(f"  Masks:       {num_masks} files")

    # Check if predictions available from previous iteration
    if current_iter > 0:
        prev_predictions_dir = session_path / f'iteration_{current_iter - 1}' / 'predictions'
        if prev_predictions_dir.exists():
            num_predictions = len(list(prev_predictions_dir.glob('*.png')))
            print(f"  Predictions: {num_predictions} files (from iteration {current_iter - 1})")
            print(f"\n✓ Predictions available - will guide your annotations")
        else:
            print(f"\n⚠ No predictions from previous iteration")
    else:
        print(f"\nℹ Iteration 0: Starting with seed annotations")

    print(f"\n{'-'*60}")

    # Step 3: Launch annotation tool (if enabled)
    if not launch_tool:
        print("Annotation tool launch disabled (launch_tool=False)")
        print(f"Current annotations: {num_annotations} files")
        print(f"→ Set launch_tool=True to open annotation tool")

        return {
            'iteration': current_iter,
            'tool_launched': False,
            'success': True,
            'num_annotations': num_annotations,
            'num_masks': num_masks,
            'message': 'Tool launch disabled'
        }

    # Check if annotation tool is available
    annotator_path = Path('isage_annotator')

    if not annotator_path.exists():
        print(f"⚠ isage_annotator not found")
        print(f"\nAnnotation tool not available.")
        print(f"Using existing annotations: {num_annotations} files")

        return {
            'iteration': current_iter,
            'tool_launched': False,
            'success': True,
            'num_annotations': num_annotations,
            'num_masks': num_masks,
            'message': 'isage_annotator not found'
        }

    # Launch annotation tool
    print(f"LAUNCHING ANNOTATION TOOL...")
    print(f"{'-'*60}\n")

    success = launch_annotation_tool(
        session_path=session_path,
        iteration=current_iter,
        dataset_config=dataset_config,
        wait=True
    )

    if not success:
        print(f"\n✗ Annotation tool failed")

        return {
            'iteration': current_iter,
            'tool_launched': True,
            'success': False,
            'num_annotations': num_annotations,
            'num_masks': num_masks,
            'message': 'Annotation tool failed'
        }

    # Step 4: Convert JSONs → PNGs
    print(f"\n{'='*60}")
    print("✓ ANNOTATION TOOL CLOSED")
    print(f"{'='*60}\n")

    print("Converting annotations to masks...")

    success_count, fail_count = batch_json_to_masks(
        json_dir=annotations_dir,
        output_dir=masks_dir,
        image_size=(dataset_config['image']['width'], dataset_config['image']['height']),
        ignore_index=dataset_config['classes']['ignore_index']
    )

    print(f"\n✓ Converted {success_count} annotations to masks")
    if fail_count > 0:
        print(f"⚠ {fail_count} conversions failed")

    print(f"\n{'='*60}")
    print(f"ANNOTATION COMPLETE")
    print(f"{'='*60}")
    print(f"→ Run Cell 5 to train model")

    return {
        'iteration': current_iter,
        'tool_launched': True,
        'success': True,
        'num_annotations': success_count,
        'num_masks': success_count,
        'message': 'Annotation workflow completed successfully'
    }
