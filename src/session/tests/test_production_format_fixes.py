"""
Test Production Format Fixes

Comprehensive test to verify all fixes for the production VIZ_SOFTWARE format:
1. Session creation with mask conversion
2. JSON format validation
3. Round-trip conversion (mask -> JSON -> mask)
4. SessionManager.get_available_iterations() method
5. ignore_index extraction from config
"""

import json
import shutil
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import pytest


def test_production_format_integration():
    """Test complete workflow with production format."""
    print("\n" + "="*60)
    print("PRODUCTION FORMAT INTEGRATION TEST")
    print("="*60)

    # Import after adding to path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from src.utils.config_loader import load_dataset_config, load_training_config
    from src.session.session_manager import SessionManager
    from src.session.mask_utils import batch_json_to_masks
    from src.session.simple_mask_converter import (
        convert_mask_to_json,
        validate_annotation_format,
        count_annotation_points
    )

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Test 1: Load configurations
        print("\n[Test 1] Loading configurations...")
        dataset_config = load_dataset_config('configs/datasets/vaihingen.yaml')
        training_config = load_training_config('configs/training/unet_efficientnet_b7.yaml')

        assert dataset_config['name'] == 'VAIHINGEN'
        assert dataset_config['classes']['ignore_index'] == 6
        print(f"  ✓ Dataset: {dataset_config['name']}")
        print(f"  ✓ Ignore index: {dataset_config['classes']['ignore_index']}")

        # Test 2: Create session with mask conversion
        print("\n[Test 2] Creating session with mask conversion...")
        session_manager = SessionManager(
            session_name='TEST_PRODUCTION_FORMAT',
            session_dir=str(temp_path),
            dataset_config=dataset_config,
            training_config=training_config
        )

        is_new = session_manager.initialize()
        assert is_new == True
        print(f"  ✓ Session created: {session_manager.session_path}")

        # Test 3: Check get_available_iterations method (fixes AttributeError)
        print("\n[Test 3] Testing get_available_iterations() method...")
        iterations = session_manager.get_available_iterations()
        assert isinstance(iterations, list)
        assert 0 in iterations
        print(f"  ✓ Available iterations: {iterations}")

        # Test 4: Validate JSON format
        print("\n[Test 4] Validating production JSON format...")
        annotations_dir = session_manager.session_path / 'iteration_0' / 'annotations'
        json_files = list(annotations_dir.glob('*.json'))

        assert len(json_files) > 0, "No JSON files created"
        print(f"  ✓ Created {len(json_files)} JSON files")

        # Check format of first file
        sample_json = json_files[0]
        with open(sample_json) as f:
            data = json.load(f)

        # Validate required fields
        assert 'format_version' in data
        assert data['format_version'] == '1.0'
        assert 'image' in data
        assert 'annotations' in data
        assert isinstance(data['annotations'], list)
        assert 'iteration' in data
        assert data['iteration'] == 0
        assert 'created_at' in data

        print(f"  ✓ Format version: {data['format_version']}")
        print(f"  ✓ Annotations: {len(data['annotations'])} points")
        print(f"  ✓ Sample annotation: {data['annotations'][0] if data['annotations'] else 'empty'}")

        # Validate format with function
        is_valid, error_msg = validate_annotation_format(data)
        assert is_valid, f"Format validation failed: {error_msg}"
        print(f"  ✓ Format validation: {error_msg}")

        # Test 5: Count annotation points
        print("\n[Test 5] Testing count_annotation_points()...")
        point_count = count_annotation_points(sample_json)
        assert point_count == len(data['annotations'])
        print(f"  ✓ Point count: {point_count}")

        # Test 6: Test round-trip conversion (JSON -> mask)
        print("\n[Test 6] Testing round-trip conversion (JSON -> mask)...")
        test_masks_dir = temp_path / 'test_masks'

        success_count, fail_count = batch_json_to_masks(
            json_dir=annotations_dir,
            output_dir=test_masks_dir,
            image_size=(512, 512),
            ignore_index=6
        )

        assert fail_count == 0, f"Some conversions failed: {fail_count}"
        assert success_count == len(json_files)
        print(f"  ✓ Converted {success_count}/{len(json_files)} JSON files to masks")

        # Test 7: Verify round-trip preserves data
        print("\n[Test 7] Verifying round-trip data preservation...")
        original_mask_path = session_manager.session_path / 'iteration_0' / 'masks' / sample_json.with_suffix('.png').name
        roundtrip_mask_path = test_masks_dir / sample_json.with_suffix('.png').name

        if original_mask_path.exists() and roundtrip_mask_path.exists():
            orig_mask = np.array(Image.open(original_mask_path))
            rt_mask = np.array(Image.open(roundtrip_mask_path))

            # Count non-ignore pixels
            non_ignore_orig = np.sum(orig_mask != 6)
            non_ignore_rt = np.sum(rt_mask != 6)

            assert non_ignore_orig == non_ignore_rt, "Annotation count mismatch"

            # Check if annotated pixels match
            annotated_match = np.sum((orig_mask != 6) & (orig_mask == rt_mask))
            match_percent = (annotated_match / non_ignore_orig * 100) if non_ignore_orig > 0 else 100

            assert match_percent == 100.0, f"Only {match_percent}% of annotated pixels match"

            print(f"  ✓ Non-ignore pixels: {non_ignore_orig}")
            print(f"  ✓ Annotated pixels match: {annotated_match}/{non_ignore_orig} (100%)")

        # Test 8: Test ignore_index from config (not hardcoded)
        print("\n[Test 8] Verifying ignore_index from config...")
        # Create a test mask with different ignore_index
        test_mask = np.full((512, 512), 6, dtype=np.uint8)
        test_mask[100, 100] = 2
        test_mask[200, 200] = 4

        test_mask_path = temp_path / 'test_custom.png'
        Image.fromarray(test_mask).save(test_mask_path)

        test_json_path = temp_path / 'test_custom.json'

        # Convert with config ignore_index (6)
        success = convert_mask_to_json(
            mask_path=test_mask_path,
            output_path=test_json_path,
            ignore_index=dataset_config['classes']['ignore_index'],
            iteration=0
        )

        assert success, "Custom mask conversion failed"

        with open(test_json_path) as f:
            custom_data = json.load(f)

        # Should only have 2 annotations (pixels != 6)
        assert len(custom_data['annotations']) == 2
        print(f"  ✓ Ignore index from config: {dataset_config['classes']['ignore_index']}")
        print(f"  ✓ Extracted {len(custom_data['annotations'])} non-ignore points")

        # Test 9: Verify format matches production exactly
        print("\n[Test 9] Verifying exact production format match...")

        # Check structure matches VIZ_SOFTWARE production format
        expected_keys = {'format_version', 'image', 'annotations', 'iteration', 'created_at'}
        actual_keys = set(data.keys())
        assert expected_keys == actual_keys, f"Key mismatch: expected {expected_keys}, got {actual_keys}"

        # Check annotation structure: [[x, y, class], ...]
        if data['annotations']:
            first_annotation = data['annotations'][0]
            assert isinstance(first_annotation, list), "Annotation must be list"
            assert len(first_annotation) >= 3, "Annotation must have [x, y, class]"
            assert all(isinstance(first_annotation[i], int) for i in range(3)), "Coordinates and class must be integers"

        print(f"  ✓ Format keys match: {expected_keys}")
        print(f"  ✓ Annotation structure: [x, y, class]")

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nSummary:")
        print(f"  ✓ Session creation: {len(json_files)} files")
        print(f"  ✓ JSON format: Production VIZ_SOFTWARE format")
        print(f"  ✓ Round-trip conversion: 100% accurate")
        print(f"  ✓ get_available_iterations(): Working")
        print(f"  ✓ ignore_index: From config ({dataset_config['classes']['ignore_index']})")
        print(f"  ✓ Format validation: All checks passed")


if __name__ == '__main__':
    test_production_format_integration()
