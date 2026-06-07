"""
Unit Tests for Simple Mask Converter

Tests the production format converter functions in isolation.
"""

import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.session.simple_mask_converter import (
    extract_sparse_points,
    convert_mask_to_json,
    json_to_mask,
    count_annotation_points,
    validate_annotation_format,
    load_annotation_json
)


def test_extract_sparse_points():
    """Test sparse point extraction from mask."""
    print("\n[Test] extract_sparse_points()")

    # Create test mask
    mask = np.full((10, 10), 255, dtype=np.uint8)  # All ignore
    mask[5, 5] = 0  # Class 0 at (5, 5)
    mask[3, 7] = 2  # Class 2 at (7, 3)
    mask[8, 2] = 1  # Class 1 at (2, 8)

    points = extract_sparse_points(mask, ignore_index=255)

    assert len(points) == 3, f"Expected 3 points, got {len(points)}"

    # Check point format: [x, y, class]
    for point in points:
        assert len(point) == 3, "Point must have 3 elements [x, y, class]"
        assert all(isinstance(p, int) for p in point), "All elements must be integers"

    print(f"  ✓ Extracted {len(points)} points")
    print(f"  ✓ Point format: {points[0]}")


def test_convert_mask_to_json():
    """Test mask to JSON conversion."""
    print("\n[Test] convert_mask_to_json()")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test mask
        mask = np.full((512, 512), 6, dtype=np.uint8)
        mask[100, 100] = 0
        mask[200, 200] = 1
        mask[300, 300] = 2

        mask_path = temp_path / 'test.png'
        Image.fromarray(mask).save(mask_path)

        # Convert to JSON
        json_path = temp_path / 'test.json'
        success = convert_mask_to_json(
            mask_path=mask_path,
            output_path=json_path,
            ignore_index=6,
            iteration=0
        )

        assert success, "Conversion failed"
        assert json_path.exists(), "JSON file not created"

        # Load and validate
        with open(json_path) as f:
            data = json.load(f)

        assert data['format_version'] == '1.0'
        assert data['image']['name'] == 'test.png'
        assert data['image']['width'] == 512
        assert data['image']['height'] == 512
        assert len(data['annotations']) == 3
        assert data['iteration'] == 0

        print(f"  ✓ Conversion successful")
        print(f"  ✓ Format: {data['format_version']}")
        print(f"  ✓ Annotations: {len(data['annotations'])}")


def test_json_to_mask():
    """Test JSON to mask conversion."""
    print("\n[Test] json_to_mask()")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test JSON
        json_data = {
            "format_version": "1.0",
            "image": {"name": "test.png", "width": 512, "height": 512},
            "annotations": [[100, 100, 0], [200, 200, 1], [300, 300, 2]],
            "iteration": 0,
            "created_at": "2025-01-01T00:00:00Z"
        }

        json_path = temp_path / 'test.json'
        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        # Convert to mask
        mask_path = temp_path / 'test.png'
        success = json_to_mask(
            json_path=json_path,
            output_mask_path=mask_path,
            image_size=(512, 512),
            ignore_index=6
        )

        assert success, "Conversion failed"
        assert mask_path.exists(), "Mask file not created"

        # Load and validate
        mask = np.array(Image.open(mask_path))

        assert mask.shape == (512, 512)
        assert mask[100, 100] == 0
        assert mask[200, 200] == 1
        assert mask[300, 300] == 2
        assert mask[0, 0] == 6  # Background should be ignore_index

        print(f"  ✓ Conversion successful")
        print(f"  ✓ Mask shape: {mask.shape}")
        print(f"  ✓ Annotations placed correctly")


def test_round_trip():
    """Test round-trip conversion: mask -> JSON -> mask."""
    print("\n[Test] Round-trip conversion")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create original mask
        original_mask = np.full((512, 512), 6, dtype=np.uint8)
        original_mask[100, 100] = 0
        original_mask[200, 200] = 1
        original_mask[300, 300] = 2
        original_mask[400, 400] = 3

        original_path = temp_path / 'original.png'
        Image.fromarray(original_mask).save(original_path)

        # Convert to JSON
        json_path = temp_path / 'test.json'
        convert_mask_to_json(
            mask_path=original_path,
            output_path=json_path,
            ignore_index=6,
            iteration=0
        )

        # Convert back to mask
        roundtrip_path = temp_path / 'roundtrip.png'
        json_to_mask(
            json_path=json_path,
            output_mask_path=roundtrip_path,
            image_size=(512, 512),
            ignore_index=6
        )

        # Compare
        roundtrip_mask = np.array(Image.open(roundtrip_path))

        # Check annotated pixels
        orig_annotated = original_mask != 6
        rt_annotated = roundtrip_mask != 6

        assert np.sum(orig_annotated) == np.sum(rt_annotated), "Annotation count mismatch"
        assert np.all(original_mask[orig_annotated] == roundtrip_mask[orig_annotated]), "Annotated pixels don't match"

        print(f"  ✓ Annotation count preserved: {np.sum(orig_annotated)}")
        print(f"  ✓ All annotated pixels match")


def test_validate_annotation_format():
    """Test format validation."""
    print("\n[Test] validate_annotation_format()")

    # Valid format
    valid_data = {
        "format_version": "1.0",
        "image": {"name": "test.png", "width": 512, "height": 512},
        "annotations": [[100, 100, 0]],
        "iteration": 0,
        "created_at": "2025-01-01T00:00:00Z"
    }

    is_valid, msg = validate_annotation_format(valid_data)
    assert is_valid, f"Valid data rejected: {msg}"
    print(f"  ✓ Valid format accepted: {msg}")

    # Invalid: missing format_version
    invalid_data = {
        "image": {"name": "test.png", "width": 512, "height": 512},
        "annotations": [[100, 100, 0]]
    }

    is_valid, msg = validate_annotation_format(invalid_data)
    assert not is_valid, "Invalid data accepted"
    print(f"  ✓ Invalid format rejected: {msg}")

    # Invalid: wrong annotation structure
    invalid_annotations = {
        "format_version": "1.0",
        "image": {"name": "test.png", "width": 512, "height": 512},
        "annotations": [[100, 100]],  # Missing class
        "iteration": 0
    }

    is_valid, msg = validate_annotation_format(invalid_annotations)
    assert not is_valid, "Invalid annotation accepted"
    print(f"  ✓ Invalid annotation rejected: {msg}")


def test_count_annotation_points():
    """Test point counting."""
    print("\n[Test] count_annotation_points()")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test JSON
        json_data = {
            "format_version": "1.0",
            "image": {"name": "test.png", "width": 512, "height": 512},
            "annotations": [[100, 100, 0], [200, 200, 1], [300, 300, 2]],
            "iteration": 0,
            "created_at": "2025-01-01T00:00:00Z"
        }

        json_path = temp_path / 'test.json'
        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        count = count_annotation_points(json_path)
        assert count == 3, f"Expected 3 points, got {count}"
        print(f"  ✓ Point count: {count}")


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("SIMPLE CONVERTER UNIT TESTS")
    print("="*60)

    test_extract_sparse_points()
    test_convert_mask_to_json()
    test_json_to_mask()
    test_round_trip()
    test_validate_annotation_format()
    test_count_annotation_points()

    print("\n" + "="*60)
    print("ALL UNIT TESTS PASSED ✓")
    print("="*60)


if __name__ == '__main__':
    run_all_tests()
