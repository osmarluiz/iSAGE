"""
Iteration management utilities.

Handles iteration number resolution and session iteration discovery.
"""

from pathlib import Path
from typing import List, Union


def resolve_iteration(session_path: Path, iteration: Union[int, str]) -> int:
    """
    Converts 'latest' to actual iteration number or validates integer iteration.

    Args:
        session_path: Path to session directory
        iteration: Either 'latest' or an integer iteration number

    Returns:
        Validated iteration number

    Raises:
        ValueError: If iteration is invalid or doesn't exist
        TypeError: If iteration is not int or str
    """
    if isinstance(iteration, str):
        if iteration.lower() == 'latest':
            iterations = get_available_iterations(session_path)
            if not iterations:
                raise ValueError(f"No iterations found in session: {session_path}")
            return max(iterations)
        else:
            try:
                iteration = int(iteration)
            except ValueError:
                raise ValueError(f"Invalid iteration string: '{iteration}'. Must be 'latest' or an integer.")

    if not isinstance(iteration, int):
        raise TypeError(f"Iteration must be int or str, got {type(iteration).__name__}")

    if iteration < 0:
        raise ValueError(f"Iteration must be non-negative, got {iteration}")

    # Validate that iteration exists
    iteration_path = session_path / f"iteration_{iteration}"
    if not iteration_path.exists():
        raise ValueError(f"Iteration {iteration} does not exist at {iteration_path}")

    return iteration


def get_available_iterations(session_path: Path) -> List[int]:
    """
    Returns sorted list of iteration numbers found in session.

    Args:
        session_path: Path to session directory

    Returns:
        Sorted list of iteration numbers (e.g., [0, 1, 2])
    """
    if not session_path.exists():
        return []

    iterations = []
    for item in session_path.iterdir():
        if item.is_dir() and item.name.startswith('iteration_'):
            try:
                iter_num = int(item.name.split('_')[1])
                iterations.append(iter_num)
            except (ValueError, IndexError):
                # Skip folders that don't match iteration_N pattern
                continue

    return sorted(iterations)


def get_next_iteration_number(session_path: Path) -> int:
    """
    Returns the next iteration number (max + 1).

    Args:
        session_path: Path to session directory

    Returns:
        Next iteration number (0 if no iterations exist)
    """
    iterations = get_available_iterations(session_path)
    if not iterations:
        return 0
    return max(iterations) + 1


def validate_iteration_structure(iteration_path: Path) -> bool:
    """
    Validates that an iteration folder has the correct structure.

    Expected structure:
    - masks/
    - annotations/
    - models/
    - predictions/
    - metrics.json

    Args:
        iteration_path: Path to iteration_N folder

    Returns:
        True if structure is valid, False otherwise
    """
    if not iteration_path.exists() or not iteration_path.is_dir():
        return False

    required_folders = ['masks', 'annotations', 'models', 'predictions']
    for folder in required_folders:
        folder_path = iteration_path / folder
        if not folder_path.exists() or not folder_path.is_dir():
            return False

    return True
