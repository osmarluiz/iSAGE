"""
Mask utilities for session management.

Handles PNG ↔ JSON conversions and validation for annotation masks.
Uses the canonical iSAGE session annotation format.
"""

import json
import shutil
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image

# Import simple converter using production format
from .simple_mask_converter import (
    convert_mask_to_json,
    json_to_mask as json_to_mask_simple,
    count_annotation_points as count_points_simple,
    validate_annotation_format
)


def initialize_iteration_masks(
    source_dir: Path,
    iteration_path: Path,
    image_info: dict,
    ignore_index: int
) -> Tuple[int, int]:
    """
    Copies PNG masks from source_dir to iteration_path/masks/,
    converts each to JSON in iteration_path/annotations/.

    Args:
        source_dir: Path to initial sparse masks (PNG)
        iteration_path: Path to iteration_0/
        image_info: Dict with 'width' and 'height'
        ignore_index: Value for background/ignore pixels

    Returns:
        Tuple of (num_processed, num_failed)
    """
    source_dir = Path(source_dir)
    iteration_path = Path(iteration_path)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    masks_dir = iteration_path / 'masks'
    annotations_dir = iteration_path / 'annotations'

    # Ensure directories exist
    masks_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    # Get all PNG files from source
    mask_files = list(source_dir.glob('*.png'))

    if not mask_files:
        return 0, 0

    num_processed = 0
    num_failed = 0

    for mask_file in mask_files:
        try:
            # Copy mask to iteration masks folder
            dest_mask = masks_dir / mask_file.name
            shutil.copy2(mask_file, dest_mask)

            # Convert to JSON using production format
            json_file = annotations_dir / mask_file.with_suffix('.json').name

            success = convert_mask_to_json(
                mask_path=dest_mask,
                output_path=json_file,
                ignore_index=ignore_index,
                iteration=0
            )

            if success:
                num_processed += 1
            else:
                num_failed += 1

        except Exception as e:
            print(f"Failed to process {mask_file.name}: {e}")
            num_failed += 1

    return num_processed, num_failed


def json_to_mask(
    json_path: Path,
    output_mask_path: Path,
    image_size: Tuple[int, int],
    ignore_index: int
) -> bool:
    """
    Converts production format JSON to PNG mask.

    Args:
        json_path: Path to JSON annotation file
        output_mask_path: Path to save PNG mask
        image_size: (width, height) tuple
        ignore_index: Value for background pixels

    Returns:
        True if successful, False otherwise
    """
    # Use simple converter with production format
    return json_to_mask_simple(
        json_path=Path(json_path),
        output_mask_path=Path(output_mask_path),
        image_size=image_size,
        ignore_index=ignore_index
    )


def batch_json_to_masks(
    json_dir: Path,
    output_dir: Path,
    image_size: Tuple[int, int],
    ignore_index: int
) -> Tuple[int, int]:
    """
    Converts all JSON files in json_dir to PNG masks.

    Args:
        json_dir: Directory containing JSON annotation files
        output_dir: Directory to save PNG masks
        image_size: (width, height) tuple
        ignore_index: Value for background pixels

    Returns:
        Tuple of (success_count, fail_count)
    """
    json_dir = Path(json_dir)
    output_dir = Path(output_dir)

    if not json_dir.exists():
        raise FileNotFoundError(f"JSON directory not found: {json_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(json_dir.glob('*.json'))

    if not json_files:
        return 0, 0

    success_count = 0
    fail_count = 0

    for json_file in json_files:
        # Output mask has same name as JSON, but .png extension
        output_mask = output_dir / json_file.with_suffix('.png').name

        success = json_to_mask(
            json_path=json_file,
            output_mask_path=output_mask,
            image_size=image_size,
            ignore_index=ignore_index
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count


def validate_mask_json_pair(mask_path: Path, json_path: Path) -> Tuple[bool, str]:
    """
    Validates that mask and JSON exist and are consistent.

    Args:
        mask_path: Path to PNG mask file
        json_path: Path to JSON annotation file

    Returns:
        Tuple of (is_valid, error_message)
    """
    mask_path = Path(mask_path)
    json_path = Path(json_path)

    # Check existence
    if not mask_path.exists():
        return False, f"Mask file not found: {mask_path}"

    if not json_path.exists():
        return False, f"JSON file not found: {json_path}"

    # Check that filenames match (except extension)
    if mask_path.stem != json_path.stem:
        return False, f"Filename mismatch: {mask_path.name} vs {json_path.name}"

    # Validate JSON format
    try:
        with open(json_path, 'r') as f:
            annotation_data = json.load(f)

        is_valid, error_msg = validate_annotation_format(annotation_data)
        if not is_valid:
            return False, f"Invalid JSON format: {error_msg}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON file: {e}"
    except Exception as e:
        return False, f"Error reading JSON: {e}"

    # Check mask can be loaded
    try:
        mask_image = Image.open(mask_path)
        mask_array = np.array(mask_image)

        # Verify it's a valid mask (single channel)
        if len(mask_array.shape) > 2:
            return False, f"Mask should be single channel, got shape {mask_array.shape}"

    except Exception as e:
        return False, f"Error loading mask: {e}"

    return True, "Valid"


def count_annotation_points(json_path: Path) -> int:
    """
    Counts the number of annotation points in production format JSON.

    Args:
        json_path: Path to JSON annotation file

    Returns:
        Number of annotation points, or 0 if error
    """
    # Use simple converter with production format
    return count_points_simple(Path(json_path))


def count_total_annotations(annotations_dir: Path) -> int:
    """
    Counts total annotation points across all JSON files in directory.

    Args:
        annotations_dir: Directory containing JSON files

    Returns:
        Total number of annotation points
    """
    annotations_dir = Path(annotations_dir)

    if not annotations_dir.exists():
        return 0

    total = 0
    for json_file in annotations_dir.glob('*.json'):
        total += count_annotation_points(json_file)

    return total
