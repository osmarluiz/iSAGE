"""
Tests for iteration_utils module.
"""

import pytest
import tempfile
from pathlib import Path
from ..iteration_utils import (
    resolve_iteration,
    get_available_iterations,
    get_next_iteration_number,
    validate_iteration_structure
)


class TestGetAvailableIterations:
    """Test getting available iteration numbers."""

    def test_empty_session(self):
        """Test that empty session returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            iterations = get_available_iterations(session_path)
            assert iterations == []

    def test_single_iteration(self):
        """Test session with single iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()

            iterations = get_available_iterations(session_path)
            assert iterations == [0]

    def test_multiple_iterations(self):
        """Test session with multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_2').mkdir()
            (session_path / 'iteration_1').mkdir()

            iterations = get_available_iterations(session_path)
            assert iterations == [0, 1, 2]  # Should be sorted

    def test_ignores_non_iteration_folders(self):
        """Test that non-iteration folders are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_1').mkdir()
            (session_path / 'other_folder').mkdir()
            (session_path / 'iteration_abc').mkdir()

            iterations = get_available_iterations(session_path)
            assert iterations == [0, 1]

    def test_nonexistent_session_path(self):
        """Test that nonexistent path returns empty list."""
        iterations = get_available_iterations(Path('/nonexistent/path'))
        assert iterations == []


class TestResolveIteration:
    """Test iteration number resolution."""

    def test_resolve_integer_iteration(self):
        """Test resolving valid integer iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_1').mkdir()

            result = resolve_iteration(session_path, 0)
            assert result == 0

            result = resolve_iteration(session_path, 1)
            assert result == 1

    def test_resolve_latest(self):
        """Test resolving 'latest' to max iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_1').mkdir()
            (session_path / 'iteration_2').mkdir()

            result = resolve_iteration(session_path, 'latest')
            assert result == 2

    def test_resolve_latest_case_insensitive(self):
        """Test that 'LATEST' works too."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_1').mkdir()

            result = resolve_iteration(session_path, 'LATEST')
            assert result == 1

    def test_resolve_string_integer(self):
        """Test resolving string representation of integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()

            result = resolve_iteration(session_path, '0')
            assert result == 0

    def test_resolve_nonexistent_iteration(self):
        """Test that nonexistent iteration raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()

            with pytest.raises(ValueError, match="does not exist"):
                resolve_iteration(session_path, 5)

    def test_resolve_negative_iteration(self):
        """Test that negative iteration raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            with pytest.raises(ValueError, match="non-negative"):
                resolve_iteration(session_path, -1)

    def test_resolve_invalid_string(self):
        """Test that invalid string raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            with pytest.raises(ValueError, match="Invalid iteration string"):
                resolve_iteration(session_path, 'invalid')

    def test_resolve_invalid_type(self):
        """Test that invalid type raises TypeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            with pytest.raises(TypeError):
                resolve_iteration(session_path, 1.5)

    def test_resolve_latest_no_iterations(self):
        """Test that 'latest' with no iterations raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            with pytest.raises(ValueError, match="No iterations found"):
                resolve_iteration(session_path, 'latest')


class TestGetNextIterationNumber:
    """Test getting next iteration number."""

    def test_next_iteration_empty_session(self):
        """Test that empty session returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            next_iter = get_next_iteration_number(session_path)
            assert next_iter == 0

    def test_next_iteration_with_existing(self):
        """Test that next iteration is max + 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_1').mkdir()

            next_iter = get_next_iteration_number(session_path)
            assert next_iter == 2

    def test_next_iteration_with_gaps(self):
        """Test that gaps in iteration numbers don't affect next number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            (session_path / 'iteration_0').mkdir()
            (session_path / 'iteration_5').mkdir()

            next_iter = get_next_iteration_number(session_path)
            assert next_iter == 6


class TestValidateIterationStructure:
    """Test iteration folder structure validation."""

    def test_validate_complete_structure(self):
        """Test that complete structure passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iter_path = Path(tmpdir) / 'iteration_0'
            iter_path.mkdir()
            (iter_path / 'masks').mkdir()
            (iter_path / 'annotations').mkdir()
            (iter_path / 'models').mkdir()
            (iter_path / 'predictions').mkdir()

            assert validate_iteration_structure(iter_path) is True

    def test_validate_missing_folder(self):
        """Test that missing folder fails validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iter_path = Path(tmpdir) / 'iteration_0'
            iter_path.mkdir()
            (iter_path / 'masks').mkdir()
            (iter_path / 'annotations').mkdir()
            # Missing 'models' and 'predictions'

            assert validate_iteration_structure(iter_path) is False

    def test_validate_nonexistent_path(self):
        """Test that nonexistent path fails validation."""
        assert validate_iteration_structure(Path('/nonexistent/iteration_0')) is False

    def test_validate_file_instead_of_folder(self):
        """Test that file instead of folder fails validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            iter_path = Path(tmpdir) / 'iteration_0'
            iter_path.mkdir()
            (iter_path / 'masks').mkdir()
            (iter_path / 'annotations').mkdir()
            (iter_path / 'models').mkdir()
            # Create 'predictions' as file instead of folder
            (iter_path / 'predictions').touch()

            assert validate_iteration_structure(iter_path) is False
