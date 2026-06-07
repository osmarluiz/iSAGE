"""
JSON Saver - Save annotation data to JSON files with validation

This module provides comprehensive JSON saving functionality with validation,
backup management, and atomic operations.
"""

import json
import os
import shutil
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from ..base_protocols import BaseComponent, AnnotationPoint, AnnotationData, OverlayData
from .base_io import BaseIO


class JsonSaver(BaseIO):
    """JSON annotation saver with validation and backup support."""
    
    def __init__(self, name: str = "json_saver", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Save configuration
        self._output_directory: Optional[str] = None
        self._backup_enabled: bool = True
        self._backup_count: int = 5
        self._compression_enabled: bool = False
        self._validation_enabled: bool = True
        self._atomic_save: bool = True
        
        # File naming
        self._filename_template: str = "{timestamp}_{session_id}.json"
        self._backup_template: str = "{basename}.backup_{index}.json"
        
        # Save statistics
        self._save_count: int = 0
        self._last_save_time: float = 0.0
        self._total_save_time: float = 0.0
        self._save_errors: List[str] = []
        
        # Validation settings
        self._strict_validation: bool = False
        self._schema_version: str = "1.0"
    
    def initialize(self, **kwargs) -> bool:
        """Initialize JSON saver."""
        self._output_directory = kwargs.get('output_directory', None)
        self._backup_enabled = kwargs.get('backup_enabled', True)
        self._backup_count = kwargs.get('backup_count', 5)
        self._compression_enabled = kwargs.get('compression_enabled', False)
        self._validation_enabled = kwargs.get('validation_enabled', True)
        self._atomic_save = kwargs.get('atomic_save', True)
        self._strict_validation = kwargs.get('strict_validation', False)
        
        # Set filename template if provided
        if 'filename_template' in kwargs:
            self._filename_template = kwargs['filename_template']
        
        return super().initialize(**kwargs)
    
    def save_annotation_data(self, 
                           data: AnnotationData, 
                           output_path: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save annotation data to JSON file."""
        try:
            start_time = time.time()
            
            # Determine output path
            if output_path is None:
                if self._output_directory is None:
                    self.emit_error("No output directory or path specified")
                    return False
                output_path = self._generate_filename(data)
            
            # Validate data if enabled
            if self._validation_enabled and not self._validate_annotation_data(data):
                self.emit_error("Annotation data validation failed")
                return False
            
            # Create backup if enabled
            if self._backup_enabled and os.path.exists(output_path):
                self._create_backup(output_path)
            
            # Prepare JSON data
            json_data = self._prepare_json_data(data, metadata)
            
            # Save with atomic operation if enabled
            if self._atomic_save:
                success = self._atomic_save_json(json_data, output_path)
            else:
                success = self._direct_save_json(json_data, output_path)
            
            # Update statistics
            save_time = time.time() - start_time
            self._save_count += 1
            self._last_save_time = save_time
            self._total_save_time += save_time
            
            if success:
                self.emit_state_changed({
                    'last_save_path': output_path,
                    'save_count': self._save_count,
                    'last_save_time': save_time
                })
                return True
            else:
                self._save_errors.append(f"Failed to save to {output_path}")
                return False
                
        except Exception as e:
            self.emit_error(f"Error saving annotation data: {str(e)}")
            self._save_errors.append(str(e))
            return False
    
    def save_points(self, 
                   points: List[AnnotationPoint], 
                   output_path: str,
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save point annotations to JSON file."""
        try:
            # Create annotation data from points
            annotation_data = AnnotationData(
                points=points,
                image_path="",
                image_size=(0, 0),
                class_names=[],
                metadata=metadata or {}
            )
            
            return self.save_annotation_data(annotation_data, output_path, metadata)
            
        except Exception as e:
            self.emit_error(f"Error saving points: {str(e)}")
            return False
    
    def save_overlay_data(self, 
                         overlay_data: OverlayData, 
                         output_path: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save overlay data to JSON file."""
        try:
            # Prepare overlay JSON data
            json_data = self._prepare_overlay_json(overlay_data, metadata)
            
            # Save with atomic operation if enabled
            if self._atomic_save:
                return self._atomic_save_json(json_data, output_path)
            else:
                return self._direct_save_json(json_data, output_path)
                
        except Exception as e:
            self.emit_error(f"Error saving overlay data: {str(e)}")
            return False
    
    def save_session_data(self, 
                         session_data: Dict[str, Any], 
                         output_path: str) -> bool:
        """Save session data to JSON file."""
        try:
            # Add session metadata
            session_data['saved_at'] = datetime.now().isoformat()
            session_data['schema_version'] = self._schema_version
            session_data['saver_version'] = self._version
            
            # Save with atomic operation if enabled
            if self._atomic_save:
                return self._atomic_save_json(session_data, output_path)
            else:
                return self._direct_save_json(session_data, output_path)
                
        except Exception as e:
            self.emit_error(f"Error saving session data: {str(e)}")
            return False
    
    def save_batch_data(self, 
                       batch_data: List[Dict[str, Any]], 
                       output_directory: str,
                       filename_prefix: str = "batch") -> List[str]:
        """Save batch data to multiple JSON files."""
        saved_files = []
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_directory, exist_ok=True)
            
            for i, data in enumerate(batch_data):
                filename = f"{filename_prefix}_{i:04d}.json"
                output_path = os.path.join(output_directory, filename)
                
                if self._atomic_save:
                    success = self._atomic_save_json(data, output_path)
                else:
                    success = self._direct_save_json(data, output_path)
                
                if success:
                    saved_files.append(output_path)
                else:
                    self.emit_error(f"Failed to save batch item {i} to {output_path}")
            
            return saved_files
            
        except Exception as e:
            self.emit_error(f"Error saving batch data: {str(e)}")
            return saved_files
    
    def set_output_directory(self, directory: str) -> bool:
        """Set output directory."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Verify write permissions
            test_file = os.path.join(directory, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            self._output_directory = directory
            self.emit_state_changed({'output_directory': directory})
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting output directory: {str(e)}")
            return False
    
    def get_output_directory(self) -> Optional[str]:
        """Get current output directory."""
        return self._output_directory
    
    def set_backup_enabled(self, enabled: bool) -> None:
        """Enable/disable backup creation."""
        self._backup_enabled = enabled
        self.emit_state_changed({'backup_enabled': enabled})
    
    def is_backup_enabled(self) -> bool:
        """Check if backup is enabled."""
        return self._backup_enabled
    
    def set_backup_count(self, count: int) -> None:
        """Set number of backups to keep."""
        self._backup_count = max(1, count)
        self.emit_state_changed({'backup_count': count})
    
    def get_backup_count(self) -> int:
        """Get backup count."""
        return self._backup_count
    
    def set_compression_enabled(self, enabled: bool) -> None:
        """Enable/disable compression."""
        self._compression_enabled = enabled
        self.emit_state_changed({'compression_enabled': enabled})
    
    def is_compression_enabled(self) -> bool:
        """Check if compression is enabled."""
        return self._compression_enabled
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """Enable/disable validation."""
        self._validation_enabled = enabled
        self.emit_state_changed({'validation_enabled': enabled})
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled."""
        return self._validation_enabled
    
    def set_atomic_save(self, enabled: bool) -> None:
        """Enable/disable atomic save."""
        self._atomic_save = enabled
        self.emit_state_changed({'atomic_save': enabled})
    
    def is_atomic_save_enabled(self) -> bool:
        """Check if atomic save is enabled."""
        return self._atomic_save
    
    def get_save_statistics(self) -> Dict[str, Any]:
        """Get save statistics."""
        return {
            'save_count': self._save_count,
            'last_save_time': self._last_save_time,
            'average_save_time': self._total_save_time / max(1, self._save_count),
            'total_save_time': self._total_save_time,
            'error_count': len(self._save_errors),
            'last_errors': self._save_errors[-5:] if self._save_errors else []
        }
    
    def clear_statistics(self) -> None:
        """Clear save statistics."""
        self._save_count = 0
        self._last_save_time = 0.0
        self._total_save_time = 0.0
        self._save_errors.clear()
        self.emit_state_changed({'statistics_cleared': True})
    
    def _generate_filename(self, data: AnnotationData) -> str:
        """Generate filename based on template."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = getattr(data, 'session_id', 'default')
        
        filename = self._filename_template.format(
            timestamp=timestamp,
            session_id=session_id
        )
        
        return os.path.join(self._output_directory, filename)
    
    def _validate_annotation_data(self, data: AnnotationData) -> bool:
        """Validate annotation data."""
        try:
            # Basic validation
            if not isinstance(data.points, list):
                self.emit_error("Points must be a list")
                return False
            
            # Validate each point
            for i, point in enumerate(data.points):
                if not isinstance(point, AnnotationPoint):
                    self.emit_error(f"Point {i} is not an AnnotationPoint")
                    return False
                
                if not (hasattr(point, 'x') and hasattr(point, 'y')):
                    self.emit_error(f"Point {i} missing x or y coordinate")
                    return False
                
                if not isinstance(point.class_id, int) or point.class_id < 0:
                    self.emit_error(f"Point {i} has invalid class_id")
                    return False
                
                if not (0.0 <= point.confidence <= 1.0):
                    self.emit_error(f"Point {i} has invalid confidence")
                    return False
            
            # Strict validation
            if self._strict_validation:
                if not data.image_path:
                    self.emit_error("Image path is required in strict mode")
                    return False
                
                if not data.image_size or len(data.image_size) != 2:
                    self.emit_error("Valid image size is required in strict mode")
                    return False
            
            return True
            
        except Exception as e:
            self.emit_error(f"Validation error: {str(e)}")
            return False
    
    def _prepare_json_data(self, data: AnnotationData, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare annotation data for JSON serialization."""
        json_data = {
            'schema_version': self._schema_version,
            'created_at': datetime.now().isoformat(),
            'saver_version': self._version,
            'annotation_data': {
                'points': [point.to_dict() for point in data.points],
                'image_path': data.image_path,
                'image_size': data.image_size,
                'class_names': data.class_names,
                'metadata': data.metadata
            }
        }
        
        if metadata:
            json_data['save_metadata'] = metadata
        
        return json_data
    
    def _prepare_overlay_json(self, overlay_data: OverlayData, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare overlay data for JSON serialization."""
        json_data = {
            'schema_version': self._schema_version,
            'created_at': datetime.now().isoformat(),
            'saver_version': self._version,
            'overlay_data': {
                'overlay_type': overlay_data.overlay_type.value,
                'data': self._serialize_overlay_data(overlay_data.data),
                'opacity': overlay_data.opacity,
                'color_map': overlay_data.color_map,
                'visible': overlay_data.visible,
                'metadata': overlay_data.metadata
            }
        }
        
        if metadata:
            json_data['save_metadata'] = metadata
        
        return json_data
    
    def _serialize_overlay_data(self, data: Any) -> Any:
        """Serialize overlay data for JSON."""
        try:
            import numpy as np
            
            if isinstance(data, np.ndarray):
                return {
                    'type': 'numpy_array',
                    'dtype': str(data.dtype),
                    'shape': data.shape,
                    'data': data.tolist()
                }
            else:
                return data
                
        except ImportError:
            return data
    
    def _create_backup(self, file_path: str) -> bool:
        """Create backup of existing file."""
        try:
            if not os.path.exists(file_path):
                return True
            
            # Find backup index
            backup_index = 0
            basename = os.path.splitext(os.path.basename(file_path))[0]
            directory = os.path.dirname(file_path)
            
            # Find next available backup index
            while backup_index < self._backup_count:
                backup_filename = self._backup_template.format(
                    basename=basename,
                    index=backup_index
                )
                backup_path = os.path.join(directory, backup_filename)
                
                if not os.path.exists(backup_path):
                    break
                backup_index += 1
            
            # If all backup slots are used, remove oldest
            if backup_index >= self._backup_count:
                backup_index = self._backup_count - 1
                
                # Shift backups
                for i in range(backup_index):
                    old_backup = os.path.join(directory, self._backup_template.format(
                        basename=basename, index=i
                    ))
                    new_backup = os.path.join(directory, self._backup_template.format(
                        basename=basename, index=i + 1
                    ))
                    
                    if os.path.exists(new_backup):
                        os.remove(old_backup)
                        os.rename(new_backup, old_backup)
            
            # Create backup
            backup_filename = self._backup_template.format(
                basename=basename,
                index=0
            )
            backup_path = os.path.join(directory, backup_filename)
            
            shutil.copy2(file_path, backup_path)
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating backup: {str(e)}")
            return False
    
    def _atomic_save_json(self, data: Dict[str, Any], output_path: str) -> bool:
        """Save JSON data with atomic operation."""
        try:
            # Create temporary file
            temp_path = output_path + ".tmp"
            
            # Write to temporary file
            with open(temp_path, 'w', encoding='utf-8') as f:
                if self._compression_enabled:
                    import gzip
                    with gzip.open(temp_path + '.gz', 'wt', encoding='utf-8') as gz_f:
                        json.dump(data, gz_f, indent=2, ensure_ascii=False)
                    temp_path = temp_path + '.gz'
                    output_path = output_path + '.gz'
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            if os.path.exists(output_path):
                if os.name == 'nt':  # Windows
                    os.remove(output_path)
                os.rename(temp_path, output_path)
            else:
                os.rename(temp_path, output_path)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            self.emit_error(f"Error in atomic save: {str(e)}")
            return False
    
    def _direct_save_json(self, data: Dict[str, Any], output_path: str) -> bool:
        """Save JSON data directly."""
        try:
            if self._compression_enabled:
                import gzip
                with gzip.open(output_path + '.gz', 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error in direct save: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get JSON saver statistics."""
        stats = super().get_statistics()
        stats.update({
            'output_directory': self._output_directory,
            'backup_enabled': self._backup_enabled,
            'backup_count': self._backup_count,
            'compression_enabled': self._compression_enabled,
            'validation_enabled': self._validation_enabled,
            'atomic_save': self._atomic_save,
            'filename_template': self._filename_template,
            'schema_version': self._schema_version,
            'save_statistics': self.get_save_statistics()
        })
        return stats