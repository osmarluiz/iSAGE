"""
Base I/O - Foundation for all I/O components

This module provides the base class for I/O components that handle
saving and loading annotations.
"""

from typing import List, Optional, Dict, Any
import json
import os
from pathlib import Path
from ..base_protocols import BaseComponent, IOProtocol, AnnotationData
from .file_locking import lock_file, atomic_write


class BaseIO(BaseComponent):
    """Base class for all I/O components."""
    
    # I/O-specific signals
    saveCompleted = pyqtSignal(str)  # filepath
    loadCompleted = pyqtSignal(str)  # filepath
    saveError = pyqtSignal(str, str)  # filepath, error
    loadError = pyqtSignal(str, str)  # filepath, error
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        self._supported_formats: List[str] = []
        self._default_format: str = "json"
        self._auto_backup: bool = True
        self._backup_count: int = 3
        self._use_file_locking: bool = True
    
    # IOProtocol implementation
    def save_annotations(self, annotations: AnnotationData, filepath: str) -> bool:
        """Save annotations to file with file locking."""
        try:
            if not self.validate_format(filepath):
                self.emit_error(f"Unsupported file format: {filepath}")
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Create backup if enabled
            if self._auto_backup and os.path.exists(filepath):
                self._create_backup(filepath)
            
            # Save annotations with file locking
            success = self._save_annotations_with_locking(annotations, filepath)
            
            if success:
                self.saveCompleted.emit(filepath)
                self.emit_state_changed({
                    'last_save_path': filepath,
                    'last_save_time': self._get_current_time()
                })
            else:
                self.saveError.emit(filepath, "Save operation failed")
            
            return success
            
        except Exception as e:
            error_msg = f"Error saving annotations: {str(e)}"
            self.emit_error(error_msg)
            self.saveError.emit(filepath, error_msg)
            return False
    
    def load_annotations(self, filepath: str) -> Optional[AnnotationData]:
        """Load annotations from file with file locking."""
        try:
            if not os.path.exists(filepath):
                self.emit_error(f"File not found: {filepath}")
                return None
            
            if not self.validate_format(filepath):
                self.emit_error(f"Unsupported file format: {filepath}")
                return None
            
            # Load annotations with file locking
            annotations = self._load_annotations_with_locking(filepath)
            
            if annotations:
                self.loadCompleted.emit(filepath)
                self.emit_state_changed({
                    'last_load_path': filepath,
                    'last_load_time': self._get_current_time()
                })
            else:
                self.loadError.emit(filepath, "Load operation failed")
            
            return annotations
            
        except Exception as e:
            error_msg = f"Error loading annotations: {str(e)}"
            self.emit_error(error_msg)
            self.loadError.emit(filepath, error_msg)
            return None
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return self._supported_formats.copy()
    
    def validate_format(self, filepath: str) -> bool:
        """Validate if file format is supported."""
        file_ext = Path(filepath).suffix.lower()
        return file_ext in self._supported_formats
    
    # I/O-specific methods
    def set_supported_formats(self, formats: List[str]) -> None:
        """Set supported file formats."""
        self._supported_formats = [fmt.lower() for fmt in formats]
        self.emit_state_changed({'supported_formats': self._supported_formats})
    
    def add_supported_format(self, format_ext: str) -> None:
        """Add a supported file format."""
        format_ext = format_ext.lower()
        if format_ext not in self._supported_formats:
            self._supported_formats.append(format_ext)
            self.emit_state_changed({'supported_formats': self._supported_formats})
    
    def set_default_format(self, format_ext: str) -> None:
        """Set default file format."""
        format_ext = format_ext.lower()
        if format_ext in self._supported_formats:
            self._default_format = format_ext
            self.emit_state_changed({'default_format': format_ext})
    
    def get_default_format(self) -> str:
        """Get default file format."""
        return self._default_format
    
    def set_auto_backup(self, enabled: bool) -> None:
        """Enable/disable automatic backup."""
        self._auto_backup = enabled
        self.emit_state_changed({'auto_backup': enabled})
    
    def is_auto_backup_enabled(self) -> bool:
        """Check if auto backup is enabled."""
        return self._auto_backup
    
    def set_backup_count(self, count: int) -> None:
        """Set number of backups to keep."""
        self._backup_count = max(0, count)
        self.emit_state_changed({'backup_count': count})
    
    def get_backup_count(self) -> int:
        """Get number of backups to keep."""
        return self._backup_count
    
    def set_file_locking(self, enabled: bool) -> None:
        """Enable/disable file locking."""
        self._use_file_locking = enabled
        self.emit_state_changed({'file_locking': enabled})
    
    def is_file_locking_enabled(self) -> bool:
        """Check if file locking is enabled."""
        return self._use_file_locking
    
    def _save_annotations_with_locking(self, annotations: AnnotationData, filepath: str) -> bool:
        """Save annotations with file locking."""
        if not self._use_file_locking:
            return self._save_annotations_impl(annotations, filepath)
            
        try:
            # Use atomic write for safe saving
            with atomic_write(filepath, mode='w', encoding='utf-8') as f:
                return self._save_annotations_to_file(annotations, f)
        except Exception as e:
            self.emit_error(f"Error in atomic write: {str(e)}")
            return False
    
    def _load_annotations_with_locking(self, filepath: str) -> Optional[AnnotationData]:
        """Load annotations with file locking."""
        if not self._use_file_locking:
            return self._load_annotations_impl(filepath)
            
        try:
            # Use file locking for safe reading
            with lock_file(filepath, mode='r', timeout=10) as f:
                return self._load_annotations_from_file(f)
        except Exception as e:
            self.emit_error(f"Error in file locking: {str(e)}")
            return None
    
    def _save_annotations_to_file(self, annotations: AnnotationData, file_handle) -> bool:
        """Save annotations to file handle. To be implemented by subclasses."""
        # Default implementation - convert to dict and save as JSON
        try:
            data = {
                'image_path': annotations.image_path,
                'image_size': annotations.image_size,
                'points': [
                    {
                        'x': point.x,
                        'y': point.y,
                        'class_id': point.class_id,
                        'confidence': getattr(point, 'confidence', 1.0),
                        'timestamp': getattr(point, 'timestamp', 0),
                        'source': getattr(point, 'source', 'manual')
                    }
                    for point in annotations.points
                ],
                'class_names': annotations.class_names,
                'metadata': annotations.metadata
            }
            
            json.dump(data, file_handle, indent=2)
            return True
            
        except Exception as e:
            self.emit_error(f"Error saving to file handle: {str(e)}")
            return False
    
    def _load_annotations_from_file(self, file_handle) -> Optional[AnnotationData]:
        """Load annotations from file handle. To be implemented by subclasses."""
        # Default implementation - load JSON
        try:
            data = json.load(file_handle)
            
            # Convert to AnnotationData (simplified)
            from ..base_protocols import AnnotationPoint
            
            points = []
            for point_data in data.get('points', []):
                point = AnnotationPoint(
                    x=point_data['x'],
                    y=point_data['y'],
                    class_id=point_data['class_id'],
                    confidence=point_data.get('confidence', 1.0),
                    timestamp=point_data.get('timestamp', 0),
                    source=point_data.get('source', 'manual')
                )
                points.append(point)
            
            return AnnotationData(
                image_path=data['image_path'],
                image_size=tuple(data['image_size']),
                points=points,
                class_names=data['class_names'],
                metadata=data.get('metadata', {})
            )
            
        except Exception as e:
            self.emit_error(f"Error loading from file handle: {str(e)}")
            return None
    
    def validate_annotations(self, annotations: AnnotationData) -> bool:
        """Validate annotation data."""
        try:
            # Basic validation
            if not isinstance(annotations.image_path, str):
                return False
            
            if not isinstance(annotations.image_size, (tuple, list)) or len(annotations.image_size) != 2:
                return False
            
            if not isinstance(annotations.points, list):
                return False
            
            if not isinstance(annotations.class_names, list):
                return False
            
            if not isinstance(annotations.metadata, dict):
                return False
            
            # Validate points
            for point in annotations.points:
                if not hasattr(point, 'x') or not hasattr(point, 'y'):
                    return False
                if not hasattr(point, 'class_id'):
                    return False
                if point.class_id < 0 or point.class_id >= len(annotations.class_names):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get I/O statistics."""
        return {
            'supported_formats': self._supported_formats,
            'default_format': self._default_format,
            'auto_backup': self._auto_backup,
            'backup_count': self._backup_count
        }
    
    # Helper methods
    def _create_backup(self, filepath: str) -> None:
        """Create backup of existing file."""
        try:
            path = Path(filepath)
            backup_dir = path.parent / f"{path.stem}_backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Find next backup number
            backup_files = list(backup_dir.glob(f"{path.stem}_*.{path.suffix[1:]}"))
            backup_numbers = []
            
            for backup_file in backup_files:
                try:
                    num = int(backup_file.stem.split('_')[-1])
                    backup_numbers.append(num)
                except ValueError:
                    continue
            
            next_num = max(backup_numbers, default=0) + 1
            backup_path = backup_dir / f"{path.stem}_{next_num:03d}{path.suffix}"
            
            # Copy file to backup
            import shutil
            shutil.copy2(filepath, backup_path)
            
            # Remove old backups
            if len(backup_numbers) >= self._backup_count:
                backup_numbers.sort()
                for old_num in backup_numbers[:-self._backup_count + 1]:
                    old_backup = backup_dir / f"{path.stem}_{old_num:03d}{path.suffix}"
                    if old_backup.exists():
                        old_backup.unlink()
            
        except Exception as e:
            self.emit_error(f"Failed to create backup: {str(e)}")
    
    def _get_current_time(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _ensure_directory_exists(self, filepath: str) -> None:
        """Ensure directory exists for filepath."""
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    # Abstract methods (to be implemented by subclasses)
    def _save_annotations_impl(self, annotations: AnnotationData, filepath: str) -> bool:
        """Save annotations implementation. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _save_annotations_impl")
    
    def _load_annotations_impl(self, filepath: str) -> Optional[AnnotationData]:
        """Load annotations implementation. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _load_annotations_impl")


# Re-export for convenience
IOProtocol = IOProtocol