"""
Session Manager - Central session lifecycle management.

Handles session creation, iteration management, metrics tracking, and file organization.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
import pandas as pd

from ..utils.config_loader import save_config_to_yaml
from ..utils.iteration_utils import (
    resolve_iteration,
    get_available_iterations,
    get_next_iteration_number,
    validate_iteration_structure
)
from .mask_utils import (
    initialize_iteration_masks,
    batch_json_to_masks,
    count_total_annotations
)


class SessionManager:
    """
    Manages session lifecycle, iterations, and file organization.

    Handles:
    - Session creation and loading
    - Iteration management
    - Mask and annotation conversion
    - Metrics tracking
    - Configuration persistence
    """

    def __init__(
        self,
        session_name: str,
        session_dir: str,
        dataset_config: dict,
        training_config: dict
    ):
        """
        Initialize SessionManager.

        Args:
            session_name: Name of the session
            session_dir: Base directory for sessions
            dataset_config: Dataset configuration dictionary
            training_config: Training configuration dictionary
        """
        self.session_name = session_name
        self.session_dir = Path(session_dir)
        self.session_path = self.session_dir / session_name
        self.dataset_config = dataset_config
        self.training_config = training_config

        self._initialized = False

    def initialize(self) -> bool:
        """
        Creates session if new, loads if exists.

        Returns:
            True if new session created, False if existing session loaded
        """
        if self.session_path.exists():
            # Load existing session
            self._load_session()
            self._initialized = True
            return False
        else:
            # Create new session
            self._create_session()
            self._initialized = True
            return True

    def _create_session(self) -> None:
        """Creates new session with full directory structure."""
        # Create session directory
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Save config copies to session folder
        dataset_config_path = self.session_path / 'dataset_config.yaml'
        training_config_path = self.session_path / 'training_config.yaml'

        save_config_to_yaml(self.dataset_config, str(dataset_config_path))
        save_config_to_yaml(self.training_config, str(training_config_path))

        # Create session_info.json
        session_info = {
            'session_name': self.session_name,
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'current_iteration': 0,
            'dataset_name': self.dataset_config['name'],
            'model_name': self.training_config['name']
        }

        with open(self.session_path / 'session_info.json', 'w') as f:
            json.dump(session_info, f, indent=2)

        # Create metrics_history.csv with headers
        metrics_columns = [
            'iteration',
            'train_loss',
            'val_loss',
            'miou',
            'pixel_accuracy'
        ]

        # Add per-class IoU columns
        num_classes = self.dataset_config['classes']['num_classes']
        class_names = self.dataset_config['classes']['names']
        for i, class_name in enumerate(class_names):
            metrics_columns.append(f'{class_name}_iou')

        metrics_df = pd.DataFrame(columns=metrics_columns)
        metrics_df.to_csv(self.session_path / 'metrics_history.csv', index=False)

        # Create iteration_0 if train_sparse_masks exists
        if 'train_sparse_masks' in self.dataset_config['paths']:
            sparse_masks_path = self.dataset_config['paths']['train_sparse_masks']
            if sparse_masks_path is not None:
                self._create_iteration_0(sparse_masks_path)

    def _create_iteration_0(self, sparse_masks_path: str) -> None:
        """
        Creates iteration_0 with initial sparse masks.

        Args:
            sparse_masks_path: Path to initial sparse mask directory
        """
        iteration_path = self.session_path / 'iteration_0'

        # Create iteration folders
        (iteration_path / 'masks').mkdir(parents=True, exist_ok=True)
        (iteration_path / 'annotations').mkdir(parents=True, exist_ok=True)
        (iteration_path / 'models').mkdir(parents=True, exist_ok=True)
        (iteration_path / 'predictions').mkdir(parents=True, exist_ok=True)

        # Initialize masks from sparse masks (PNG → PNG + JSON)
        image_info = self.dataset_config['image']
        ignore_index = self.dataset_config['classes']['ignore_index']

        source_dir = Path(sparse_masks_path)
        if not source_dir.is_absolute():
            # Make relative paths absolute from project root
            source_dir = Path.cwd() / source_dir

        num_processed, num_failed = initialize_iteration_masks(
            source_dir=source_dir,
            iteration_path=iteration_path,
            image_info=image_info,
            ignore_index=ignore_index
        )

        print(f"Iteration 0 initialized: {num_processed} masks processed, {num_failed} failed")

    def _load_session(self) -> None:
        """Loads existing session metadata."""
        session_info_path = self.session_path / 'session_info.json'

        if not session_info_path.exists():
            raise FileNotFoundError(f"Session info not found: {session_info_path}")

        with open(session_info_path, 'r') as f:
            self.session_info = json.load(f)

    def get_current_iteration(self) -> int:
        """
        Returns highest iteration number in session.

        Returns:
            Current iteration number
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        iterations = get_available_iterations(self.session_path)
        if not iterations:
            return 0
        return max(iterations)

    def get_available_iterations(self) -> List[int]:
        """
        Returns list of all available iteration numbers in session.

        Returns:
            List of iteration numbers (e.g., [0, 1, 2])
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        return get_available_iterations(self.session_path)

    def create_next_iteration(self) -> int:
        """
        Creates iteration_N+1, copies JSON annotations from iteration_N.

        Returns:
            New iteration number
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        current_iter = self.get_current_iteration()
        next_iter = current_iter + 1

        next_iteration_path = self.session_path / f'iteration_{next_iter}'

        # Create iteration folders
        (next_iteration_path / 'masks').mkdir(parents=True, exist_ok=True)
        (next_iteration_path / 'annotations').mkdir(parents=True, exist_ok=True)
        (next_iteration_path / 'models').mkdir(parents=True, exist_ok=True)
        (next_iteration_path / 'predictions').mkdir(parents=True, exist_ok=True)

        # Copy all JSON files from previous iteration
        current_annotations_dir = self.session_path / f'iteration_{current_iter}' / 'annotations'
        next_annotations_dir = next_iteration_path / 'annotations'

        if current_annotations_dir.exists():
            for json_file in current_annotations_dir.glob('*.json'):
                shutil.copy2(json_file, next_annotations_dir / json_file.name)

        # Update session_info.json
        session_info_path = self.session_path / 'session_info.json'
        with open(session_info_path, 'r') as f:
            session_info = json.load(f)

        session_info['current_iteration'] = next_iter
        session_info['last_modified'] = datetime.now().isoformat()

        with open(session_info_path, 'w') as f:
            json.dump(session_info, f, indent=2)

        print(f"Created iteration {next_iter}")

        return next_iter

    def get_iteration_path(self, iteration: Union[int, str]) -> Path:
        """
        Resolves 'latest' or int to Path.

        Args:
            iteration: Iteration number or 'latest'

        Returns:
            Path to iteration directory
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        iter_num = resolve_iteration(self.session_path, iteration)
        return self.session_path / f'iteration_{iter_num}'

    def get_annotation_count(self, iteration: Union[int, str]) -> int:
        """
        Returns total number of annotated points across all JSON files.

        Args:
            iteration: Iteration number or 'latest'

        Returns:
            Total annotation count
        """
        iteration_path = self.get_iteration_path(iteration)
        annotations_dir = iteration_path / 'annotations'

        return count_total_annotations(annotations_dir)

    def save_iteration_metrics(self, iteration: int, metrics_dict: dict) -> None:
        """
        Saves metrics.json to iteration_N/ and appends row to metrics_history.csv.

        Args:
            iteration: Iteration number
            metrics_dict: Dictionary containing metrics
                         {train_loss, val_loss, miou, per_class_iou, pixel_accuracy, ...}
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        iteration_path = self.session_path / f'iteration_{iteration}'

        # Save to iteration_N/metrics.json
        metrics_path = iteration_path / 'metrics.json'
        with open(metrics_path, 'w') as f:
            json.dump(metrics_dict, f, indent=2)

        # Append to metrics_history.csv
        history_path = self.session_path / 'metrics_history.csv'

        # Prepare row data
        row_data = {
            'iteration': iteration,
            'train_loss': metrics_dict.get('train_loss', None),
            'val_loss': metrics_dict.get('val_loss', None),
            'miou': metrics_dict.get('miou', None),
            'pixel_accuracy': metrics_dict.get('pixel_accuracy', None)
        }

        # Add per-class IoU
        per_class_iou = metrics_dict.get('per_class_iou', [])
        class_names = self.dataset_config['classes']['names']

        for i, class_name in enumerate(class_names):
            if i < len(per_class_iou):
                row_data[f'{class_name}_iou'] = per_class_iou[i]
            else:
                row_data[f'{class_name}_iou'] = None

        # Append to CSV
        df = pd.read_csv(history_path)
        new_row = pd.DataFrame([row_data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(history_path, index=False)

        print(f"Metrics saved for iteration {iteration}")

    def load_metrics_history(self) -> pd.DataFrame:
        """
        Loads metrics_history.csv with all iterations.

        Returns:
            DataFrame with metrics history
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        history_path = self.session_path / 'metrics_history.csv'

        if not history_path.exists():
            raise FileNotFoundError(f"Metrics history not found: {history_path}")

        return pd.read_csv(history_path)

    def get_previous_model_path(self, iteration: int) -> Optional[Path]:
        """
        Returns path to iteration_{N-1}/models/best_model.pth.

        Args:
            iteration: Current iteration number

        Returns:
            Path to previous model, or None if iteration == 0 or model doesn't exist
        """
        if iteration == 0:
            return None

        previous_iter = iteration - 1
        model_path = self.session_path / f'iteration_{previous_iter}' / 'models' / 'best_model.pth'

        if model_path.exists():
            return model_path
        return None

    def get_prediction_paths(self, iteration: int) -> List[Path]:
        """
        Returns list of prediction PNG paths from iteration_N/predictions/.

        Args:
            iteration: Iteration number

        Returns:
            List of prediction file paths
        """
        iteration_path = self.session_path / f'iteration_{iteration}'
        predictions_dir = iteration_path / 'predictions'

        if not predictions_dir.exists():
            return []

        return sorted(predictions_dir.glob('*.png'))

    def convert_annotations_to_masks(self, iteration: Union[int, str]) -> Tuple[int, int]:
        """
        Converts all JSON annotations to PNG masks for given iteration.

        This is called after annotation to update masks from modified JSON files.

        Args:
            iteration: Iteration number or 'latest'

        Returns:
            Tuple of (success_count, fail_count)
        """
        iteration_path = self.get_iteration_path(iteration)
        annotations_dir = iteration_path / 'annotations'
        masks_dir = iteration_path / 'masks'

        image_info = self.dataset_config['image']
        image_size = (image_info['width'], image_info['height'])
        ignore_index = self.dataset_config['classes']['ignore_index']

        return batch_json_to_masks(
            json_dir=annotations_dir,
            output_dir=masks_dir,
            image_size=image_size,
            ignore_index=ignore_index
        )
