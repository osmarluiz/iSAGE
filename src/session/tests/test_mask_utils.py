"""
Tests for mask_utils module.
"""

import pytest
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

from ..mask_utils import (
    json_to_mask,
    batch_json_to_masks,
    validate_mask_json_pair,
    count_annotation_points,
    count_total_annotations
)


class TestJsonToMask:
    """Test JSON to PNG mask conversion."""

    def test_json_to_mask_success(self):
        """Test successful JSON to mask conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a simple annotation JSON
            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [[5, 5], [7, 7]],
                'class': [1, 2]
            }

            json_path = tmpdir / 'test.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            output_mask = tmpdir / 'test_mask.png'

            # Convert
            success = json_to_mask(
                json_path=json_path,
                output_mask_path=output_mask,
                image_size=(10, 10),
                ignore_index=0
            )

            assert success
            assert output_mask.exists()

            # Verify mask content
            mask = np.array(Image.open(output_mask))
            assert mask.shape == (10, 10)

    def test_json_to_mask_nonexistent_file(self):
        """Test conversion with nonexistent JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            json_path = tmpdir / 'nonexistent.json'
            output_mask = tmpdir / 'output.png'

            success = json_to_mask(
                json_path=json_path,
                output_mask_path=output_mask,
                image_size=(10, 10),
                ignore_index=0
            )

            assert not success
            assert not output_mask.exists()


class TestBatchJsonToMasks:
    """Test batch JSON to mask conversion."""

    def test_batch_conversion(self):
        """Test batch conversion of multiple JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            json_dir = tmpdir / 'json'
            masks_dir = tmpdir / 'masks'
            json_dir.mkdir()

            # Create multiple JSON files
            for i in range(3):
                json_data = {
                    'format_version': '1.0',
                    'image': {'name': f'{i}.png', 'width': 10, 'height': 10},
                    'coordinates': [[5, 5]],
                    'class': [1]
                }

                with open(json_dir / f'{i}.json', 'w') as f:
                    json.dump(json_data, f)

            # Convert
            success_count, fail_count = batch_json_to_masks(
                json_dir=json_dir,
                output_dir=masks_dir,
                image_size=(10, 10),
                ignore_index=0
            )

            assert success_count == 3
            assert fail_count == 0
            assert (masks_dir / '0.png').exists()
            assert (masks_dir / '1.png').exists()
            assert (masks_dir / '2.png').exists()

    def test_batch_empty_directory(self):
        """Test batch conversion with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            json_dir = tmpdir / 'json'
            masks_dir = tmpdir / 'masks'
            json_dir.mkdir()

            success_count, fail_count = batch_json_to_masks(
                json_dir=json_dir,
                output_dir=masks_dir,
                image_size=(10, 10),
                ignore_index=0
            )

            assert success_count == 0
            assert fail_count == 0


class TestValidateMaskJsonPair:
    """Test mask and JSON pair validation."""

    def test_validate_valid_pair(self):
        """Test validation of valid mask/JSON pair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create mask
            mask = np.zeros((10, 10), dtype=np.uint8)
            mask_path = tmpdir / 'test.png'
            Image.fromarray(mask).save(mask_path)

            # Create JSON
            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [[5, 5]],
                'class': [1]
            }

            json_path = tmpdir / 'test.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            is_valid, error_msg = validate_mask_json_pair(mask_path, json_path)

            assert is_valid
            assert error_msg == "Valid"

    def test_validate_missing_mask(self):
        """Test validation with missing mask file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mask_path = tmpdir / 'nonexistent.png'

            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [[5, 5]],
                'class': [1]
            }

            json_path = tmpdir / 'test.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            is_valid, error_msg = validate_mask_json_pair(mask_path, json_path)

            assert not is_valid
            assert "Mask file not found" in error_msg

    def test_validate_missing_json(self):
        """Test validation with missing JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mask = np.zeros((10, 10), dtype=np.uint8)
            mask_path = tmpdir / 'test.png'
            Image.fromarray(mask).save(mask_path)

            json_path = tmpdir / 'nonexistent.json'

            is_valid, error_msg = validate_mask_json_pair(mask_path, json_path)

            assert not is_valid
            assert "JSON file not found" in error_msg

    def test_validate_filename_mismatch(self):
        """Test validation with mismatched filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mask = np.zeros((10, 10), dtype=np.uint8)
            mask_path = tmpdir / 'mask1.png'
            Image.fromarray(mask).save(mask_path)

            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [[5, 5]],
                'class': [1]
            }

            json_path = tmpdir / 'mask2.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            is_valid, error_msg = validate_mask_json_pair(mask_path, json_path)

            assert not is_valid
            assert "Filename mismatch" in error_msg


class TestCountAnnotationPoints:
    """Test annotation point counting."""

    def test_count_points(self):
        """Test counting annotation points in JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [[5, 5], [6, 6], [7, 7]],
                'class': [1, 1, 2]
            }

            json_path = tmpdir / 'test.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            count = count_annotation_points(json_path)
            assert count == 3

    def test_count_points_empty(self):
        """Test counting points in empty JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            json_data = {
                'format_version': '1.0',
                'image': {'name': 'test.png', 'width': 10, 'height': 10},
                'coordinates': [],
                'class': []
            }

            json_path = tmpdir / 'test.json'
            with open(json_path, 'w') as f:
                json.dump(json_data, f)

            count = count_annotation_points(json_path)
            assert count == 0

    def test_count_total_annotations(self):
        """Test counting total annotations across directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple JSON files
            for i in range(3):
                json_data = {
                    'format_version': '1.0',
                    'image': {'name': f'{i}.png', 'width': 10, 'height': 10},
                    'coordinates': [[5, 5]] * (i + 1),  # 1, 2, 3 points
                    'class': [1] * (i + 1)
                }

                with open(tmpdir / f'{i}.json', 'w') as f:
                    json.dump(json_data, f)

            total = count_total_annotations(tmpdir)
            assert total == 6  # 1 + 2 + 3
