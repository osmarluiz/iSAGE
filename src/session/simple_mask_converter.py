"""
Simple Mask to JSON Converter - Production Format

Creates the canonical iSAGE session annotation format.
This is the unified format that the annotation tool expects.

Format:
{
  "format_version": "1.0",
  "image": {"name": "...", "width": ..., "height": ...},
  "annotations": [[x, y, class], [x, y, class], ...],
  "iteration": 0,
  "created_at": "2025-09-24T17:30:01.894508Z"
}
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np
from PIL import Image


def extract_sparse_points(mask_array: np.ndarray, ignore_index: int) -> List[List[int]]:
    """
    Extract sparse annotation points from mask array.

    Args:
        mask_array: 2D numpy array with class labels
        ignore_index: Value to ignore (background/void)

    Returns:
        List of [x, y, class] points
    """
    # Find all non-ignore pixels
    valid_mask = mask_array != ignore_index
    y_coords, x_coords = np.where(valid_mask)

    # Get class values
    class_values = mask_array[valid_mask]

    # Create point list [[x, y, class], ...]
    points = [[int(x), int(y), int(c)] for x, y, c in zip(x_coords, y_coords, class_values)]

    return points


def convert_mask_to_json(
    mask_path: Path,
    output_path: Path,
    ignore_index: int = 255,
    iteration: int = 0
) -> bool:
    """
    Convert PNG mask to production JSON format.

    Args:
        mask_path: Path to PNG mask file
        output_path: Path to save JSON file
        ignore_index: Value for background/ignore pixels (default: 255)
        iteration: Iteration number (default: 0)

    Returns:
        True if successful, False otherwise
    """
    try:
        mask_path = Path(mask_path)
        output_path = Path(output_path)

        # Load mask
        mask_image = Image.open(mask_path)
        mask_array = np.array(mask_image)

        # Convert to 2D if needed
        if len(mask_array.shape) == 3:
            if mask_array.shape[2] == 1:
                mask_array = mask_array.squeeze(2)
            else:
                # Multi-channel - take first channel
                mask_array = mask_array[:, :, 0]

        # Extract sparse points
        annotations = extract_sparse_points(mask_array, ignore_index)

        # Create production format JSON
        annotation_data = {
            "format_version": "1.0",
            "image": {
                "name": mask_path.name,
                "width": int(mask_array.shape[1]),
                "height": int(mask_array.shape[0])
            },
            "annotations": annotations,
            "iteration": iteration,
            "created_at": datetime.now().isoformat() + "Z"
        }

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with compact formatting for annotations array
        _write_compact_json(annotation_data, output_path)

        return True

    except Exception as e:
        print(f"Error converting {mask_path} to JSON: {e}")
        return False


def _write_compact_json(data: dict, file_path: Path) -> None:
    """
    Write JSON with compact formatting for annotations array.

    Writes the annotations array on single lines to make files more readable
    and match the production format.
    """
    # Separate annotations from rest of data
    annotations = data.pop('annotations', [])

    # Write main structure with indentation
    json_str = json.dumps(data, indent=2)

    # Remove closing brace
    json_str = json_str.rstrip('\n}')

    # Add annotations array with compact formatting
    json_str += ',\n  "annotations": [\n'

    for i, annotation in enumerate(annotations):
        comma = ',' if i < len(annotations) - 1 else ''
        json_str += f'    {json.dumps(annotation)}{comma}\n'

    json_str += '  ]\n}'

    # Write to file
    with open(file_path, 'w') as f:
        f.write(json_str)


def load_annotation_json(json_path: Path) -> Optional[dict]:
    """
    Load production format JSON annotation.

    Args:
        json_path: Path to JSON file

    Returns:
        Annotation data dict or None if error
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Validate production format
        if 'format_version' not in data:
            print(f"Warning: {json_path} missing format_version")

        if 'annotations' not in data:
            print(f"Error: {json_path} missing annotations array")
            return None

        return data

    except Exception as e:
        print(f"Error loading {json_path}: {e}")
        return None


def count_annotation_points(json_path: Path) -> int:
    """
    Count annotation points in production format JSON.

    Args:
        json_path: Path to JSON file

    Returns:
        Number of annotation points, or 0 if error
    """
    data = load_annotation_json(json_path)
    if data and 'annotations' in data:
        return len(data['annotations'])
    return 0


def json_to_mask(
    json_path: Path,
    output_mask_path: Path,
    image_size: Tuple[int, int],
    ignore_index: int
) -> bool:
    """
    Convert production format JSON to PNG mask.

    Args:
        json_path: Path to JSON annotation file
        output_mask_path: Path to save PNG mask
        image_size: (width, height) tuple
        ignore_index: Value for background pixels

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load JSON
        data = load_annotation_json(json_path)
        if data is None:
            return False

        # Get image dimensions
        width, height = image_size

        # Create mask filled with ignore_index
        mask = np.full((height, width), ignore_index, dtype=np.uint8)

        # Get annotations array
        annotations = data.get('annotations', [])

        # Place point annotations
        for annotation in annotations:
            if len(annotation) >= 3:
                x = int(annotation[0])
                y = int(annotation[1])
                class_id = int(annotation[2])

                # Ensure coordinates are within bounds
                if 0 <= x < width and 0 <= y < height:
                    mask[y, x] = class_id

        # Ensure output directory exists
        output_mask_path.parent.mkdir(parents=True, exist_ok=True)

        # Save mask as PNG
        mask_image = Image.fromarray(mask.astype(np.uint8))
        mask_image.save(output_mask_path)

        return True

    except Exception as e:
        print(f"Error converting {json_path} to mask: {e}")
        return False


def validate_annotation_format(data: dict) -> Tuple[bool, str]:
    """
    Validate production format annotation data.

    Args:
        data: Annotation data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check format version
    if 'format_version' not in data:
        return False, "Missing format_version"

    if data['format_version'] != "1.0":
        return False, f"Unsupported format_version: {data['format_version']}"

    # Check image info
    if 'image' not in data:
        return False, "Missing image info"

    image_info = data['image']
    required_image_fields = ['name', 'width', 'height']
    for field in required_image_fields:
        if field not in image_info:
            return False, f"Missing image.{field}"

    # Check annotations array
    if 'annotations' not in data:
        return False, "Missing annotations array"

    annotations = data['annotations']
    if not isinstance(annotations, list):
        return False, "annotations must be a list"

    # Validate each annotation
    for i, annotation in enumerate(annotations):
        if not isinstance(annotation, list):
            return False, f"Annotation {i} must be a list [x, y, class]"

        if len(annotation) < 3:
            return False, f"Annotation {i} must have at least 3 elements [x, y, class]"

        x, y, class_id = annotation[0], annotation[1], annotation[2]

        if not isinstance(x, (int, float)):
            return False, f"Annotation {i} x coordinate must be numeric"

        if not isinstance(y, (int, float)):
            return False, f"Annotation {i} y coordinate must be numeric"

        if not isinstance(class_id, int):
            return False, f"Annotation {i} class_id must be integer"

    return True, "Valid"
