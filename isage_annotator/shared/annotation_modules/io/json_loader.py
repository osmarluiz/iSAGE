"""
JSON Loader - Load annotation data from JSON files with validation

This module provides comprehensive JSON loading functionality with validation,
error recovery, and format migration support.
"""

import json
import os
import gzip
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from ..base_protocols import BaseComponent, AnnotationPoint, AnnotationData, OverlayData, OverlayType
from .base_io import BaseIO


class JsonLoader(BaseIO):
    """JSON annotation loader with validation and migration support."""
    
    def __init__(self, name: str = "json_loader", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Load configuration
        self._validation_enabled: bool = True
        self._migration_enabled: bool = True
        self._strict_validation: bool = False
        self._auto_repair: bool = True
        
        # Supported schema versions
        self._supported_versions: List[str] = ["1.0", "0.9", "0.8"]
        self._current_version: str = "1.0"
        
        # Load statistics
        self._load_count: int = 0
        self._last_load_time: float = 0.0
        self._total_load_time: float = 0.0
        self._load_errors: List[str] = []
        self._migration_count: int = 0
        self._repair_count: int = 0
        
        # Error recovery settings
        self._ignore_missing_fields: bool = True
        self._default_values: Dict[str, Any] = {
            'confidence': 1.0,
            'timestamp': 0.0,
            'source': 'unknown',
            'class_id': 0
        }
    
    def initialize(self, **kwargs) -> bool:
        """Initialize JSON loader."""
        self._validation_enabled = kwargs.get('validation_enabled', True)
        self._migration_enabled = kwargs.get('migration_enabled', True)
        self._strict_validation = kwargs.get('strict_validation', False)
        self._auto_repair = kwargs.get('auto_repair', True)
        self._ignore_missing_fields = kwargs.get('ignore_missing_fields', True)
        
        # Set default values if provided
        if 'default_values' in kwargs:
            self._default_values.update(kwargs['default_values'])
        
        return super().initialize(**kwargs)
    
    def load_annotation_data(self, file_path: str) -> Optional[AnnotationData]:
        """Load annotation data from JSON file."""
        try:
            import time
            start_time = time.time()
            
            # Check file existence
            if not os.path.exists(file_path):
                self.emit_error(f"File not found: {file_path}")
                return None
            
            # Load JSON data
            json_data = self._load_json_file(file_path)
            if json_data is None:
                return None
            
            # Validate and migrate if necessary
            if self._validation_enabled:
                json_data = self._validate_and_migrate(json_data)
                if json_data is None:
                    return None
            
            # Parse annotation data
            annotation_data = self._parse_annotation_data(json_data)
            
            # Update statistics
            load_time = time.time() - start_time
            self._load_count += 1
            self._last_load_time = load_time
            self._total_load_time += load_time
            
            if annotation_data:
                self.emit_state_changed({
                    'last_load_path': file_path,
                    'load_count': self._load_count,
                    'last_load_time': load_time
                })
            
            return annotation_data
            
        except Exception as e:
            self.emit_error(f"Error loading annotation data: {str(e)}")
            self._load_errors.append(str(e))
            return None
    
    def load_points(self, file_path: str) -> Optional[List[AnnotationPoint]]:
        """Load points from JSON file."""
        try:
            annotation_data = self.load_annotation_data(file_path)
            if annotation_data:
                return annotation_data.points
            return None
            
        except Exception as e:
            self.emit_error(f"Error loading points: {str(e)}")
            return None
    
    def load_overlay_data(self, file_path: str) -> Optional[OverlayData]:
        """Load overlay data from JSON file."""
        try:
            # Load JSON data
            json_data = self._load_json_file(file_path)
            if json_data is None:
                return None
            
            # Parse overlay data
            overlay_data = self._parse_overlay_data(json_data)
            return overlay_data
            
        except Exception as e:
            self.emit_error(f"Error loading overlay data: {str(e)}")
            return None
    
    def load_session_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load session data from JSON file."""
        try:
            json_data = self._load_json_file(file_path)
            if json_data is None:
                return None
            
            # Validate session data
            if 'session_data' in json_data:
                return json_data['session_data']
            else:
                return json_data
                
        except Exception as e:
            self.emit_error(f"Error loading session data: {str(e)}")
            return None
    
    def load_batch_data(self, directory: str, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """Load batch data from directory."""
        batch_data = []
        
        try:
            import glob
            
            # Find matching files
            search_pattern = os.path.join(directory, pattern)
            file_paths = glob.glob(search_pattern)
            
            for file_path in sorted(file_paths):
                json_data = self._load_json_file(file_path)
                if json_data is not None:
                    batch_data.append(json_data)
                else:
                    self.emit_error(f"Failed to load batch file: {file_path}")
            
            return batch_data
            
        except Exception as e:
            self.emit_error(f"Error loading batch data: {str(e)}")
            return batch_data
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """Validate JSON file without loading."""
        errors = []
        
        try:
            # Check file existence
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                return False, errors
            
            # Load JSON data
            json_data = self._load_json_file(file_path)
            if json_data is None:
                errors.append("Failed to parse JSON")
                return False, errors
            
            # Validate structure
            validation_errors = self._validate_json_structure(json_data)
            errors.extend(validation_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information without full loading."""
        try:
            # Load JSON data
            json_data = self._load_json_file(file_path)
            if json_data is None:
                return None
            
            # Extract metadata
            info = {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'schema_version': json_data.get('schema_version', 'unknown'),
                'created_at': json_data.get('created_at', 'unknown'),
                'saver_version': json_data.get('saver_version', 'unknown')
            }
            
            # Count points if available
            if 'annotation_data' in json_data and 'points' in json_data['annotation_data']:
                info['point_count'] = len(json_data['annotation_data']['points'])
            
            return info
            
        except Exception as e:
            self.emit_error(f"Error getting file info: {str(e)}")
            return None
    
    def list_files(self, directory: str, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """List annotation files in directory with metadata."""
        files = []
        
        try:
            import glob
            
            # Find matching files
            search_pattern = os.path.join(directory, pattern)
            file_paths = glob.glob(search_pattern)
            
            for file_path in sorted(file_paths):
                file_info = self.get_file_info(file_path)
                if file_info:
                    files.append(file_info)
            
            return files
            
        except Exception as e:
            self.emit_error(f"Error listing files: {str(e)}")
            return files
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """Enable/disable validation."""
        self._validation_enabled = enabled
        self.emit_state_changed({'validation_enabled': enabled})
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled."""
        return self._validation_enabled
    
    def set_migration_enabled(self, enabled: bool) -> None:
        """Enable/disable migration."""
        self._migration_enabled = enabled
        self.emit_state_changed({'migration_enabled': enabled})
    
    def is_migration_enabled(self) -> bool:
        """Check if migration is enabled."""
        return self._migration_enabled
    
    def set_auto_repair(self, enabled: bool) -> None:
        """Enable/disable auto repair."""
        self._auto_repair = enabled
        self.emit_state_changed({'auto_repair': enabled})
    
    def is_auto_repair_enabled(self) -> bool:
        """Check if auto repair is enabled."""
        return self._auto_repair
    
    def get_load_statistics(self) -> Dict[str, Any]:
        """Get load statistics."""
        return {
            'load_count': self._load_count,
            'last_load_time': self._last_load_time,
            'average_load_time': self._total_load_time / max(1, self._load_count),
            'total_load_time': self._total_load_time,
            'error_count': len(self._load_errors),
            'migration_count': self._migration_count,
            'repair_count': self._repair_count,
            'last_errors': self._load_errors[-5:] if self._load_errors else []
        }
    
    def clear_statistics(self) -> None:
        """Clear load statistics."""
        self._load_count = 0
        self._last_load_time = 0.0
        self._total_load_time = 0.0
        self._load_errors.clear()
        self._migration_count = 0
        self._repair_count = 0
        self.emit_state_changed({'statistics_cleared': True})
    
    def _load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load JSON file with compression support."""
        try:
            # Check if file is compressed
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
        except json.JSONDecodeError as e:
            self.emit_error(f"JSON decode error in {file_path}: {str(e)}")
            return None
        except Exception as e:
            self.emit_error(f"Error loading JSON file {file_path}: {str(e)}")
            return None
    
    def _validate_and_migrate(self, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and migrate JSON data."""
        try:
            # Check schema version
            schema_version = json_data.get('schema_version', '0.8')
            
            if schema_version not in self._supported_versions:
                if self._strict_validation:
                    self.emit_error(f"Unsupported schema version: {schema_version}")
                    return None
                else:
                    # Try to migrate anyway
                    schema_version = self._supported_versions[-1]
            
            # Migrate if necessary
            if self._migration_enabled and schema_version != self._current_version:
                json_data = self._migrate_schema(json_data, schema_version)
                if json_data is None:
                    return None
                self._migration_count += 1
            
            # Validate structure
            validation_errors = self._validate_json_structure(json_data)
            if validation_errors:
                if self._strict_validation:
                    self.emit_error(f"Validation errors: {validation_errors}")
                    return None
                elif self._auto_repair:
                    # Try to repair
                    json_data = self._repair_json_data(json_data, validation_errors)
                    if json_data is None:
                        return None
                    self._repair_count += 1
            
            return json_data
            
        except Exception as e:
            self.emit_error(f"Error in validation/migration: {str(e)}")
            return None
    
    def _migrate_schema(self, json_data: Dict[str, Any], from_version: str) -> Optional[Dict[str, Any]]:
        """Migrate schema from old version to current."""
        try:
            if from_version == '0.8':
                # Migrate from 0.8 to 0.9
                json_data = self._migrate_0_8_to_0_9(json_data)
                from_version = '0.9'
            
            if from_version == '0.9':
                # Migrate from 0.9 to 1.0
                json_data = self._migrate_0_9_to_1_0(json_data)
                from_version = '1.0'
            
            json_data['schema_version'] = self._current_version
            return json_data
            
        except Exception as e:
            self.emit_error(f"Error migrating schema: {str(e)}")
            return None
    
    def _migrate_0_8_to_0_9(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from schema version 0.8 to 0.9."""
        # Add missing fields
        if 'created_at' not in json_data:
            json_data['created_at'] = datetime.now().isoformat()
        
        # Update point structure
        if 'points' in json_data:
            for point in json_data['points']:
                if 'source' not in point:
                    point['source'] = 'legacy'
        
        return json_data
    
    def _migrate_0_9_to_1_0(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from schema version 0.9 to 1.0."""
        # Restructure data
        if 'annotation_data' not in json_data:
            annotation_data = {
                'points': json_data.get('points', []),
                'image_path': json_data.get('image_path', ''),
                'image_size': json_data.get('image_size', (0, 0)),
                'class_names': json_data.get('class_names', []),
                'metadata': json_data.get('metadata', {})
            }
            json_data['annotation_data'] = annotation_data
            
            # Remove old fields
            for old_field in ['points', 'image_path', 'image_size', 'class_names', 'metadata']:
                if old_field in json_data:
                    del json_data[old_field]
        
        return json_data
    
    def _validate_json_structure(self, json_data: Dict[str, Any]) -> List[str]:
        """Validate JSON structure."""
        errors = []
        
        # Check required fields
        if 'annotation_data' not in json_data:
            errors.append("Missing 'annotation_data' field")
            return errors
        
        annotation_data = json_data['annotation_data']
        
        if 'points' not in annotation_data:
            errors.append("Missing 'points' field in annotation_data")
        elif not isinstance(annotation_data['points'], list):
            errors.append("'points' must be a list")
        
        # Validate points
        if 'points' in annotation_data:
            for i, point in enumerate(annotation_data['points']):
                if not isinstance(point, dict):
                    errors.append(f"Point {i} is not a dictionary")
                    continue
                
                # Check required point fields
                required_fields = ['x', 'y', 'class_id']
                for field in required_fields:
                    if field not in point:
                        if not self._ignore_missing_fields:
                            errors.append(f"Point {i} missing required field: {field}")
                
                # STANDARDIZED: Validate array format [x, y, class_id] - no legacy dictionary support
                if not isinstance(point, list) or len(point) < 3:
                    errors.append(f"Point {i} must be array format [x, y, class_id]")
                    continue
                    
                # Validate array element types
                if not isinstance(point[0], (int, float)):
                    errors.append(f"Point {i} x coordinate (index 0) must be numeric")
                if not isinstance(point[1], (int, float)):
                    errors.append(f"Point {i} y coordinate (index 1) must be numeric") 
                if not isinstance(point[2], int):
                    errors.append(f"Point {i} class_id (index 2) must be integer")
        
        return errors
    
    def _repair_json_data(self, json_data: Dict[str, Any], errors: List[str]) -> Optional[Dict[str, Any]]:
        """Repair JSON data based on errors."""
        try:
            annotation_data = json_data.get('annotation_data', {})
            
            # Repair missing points list
            if 'points' not in annotation_data:
                annotation_data['points'] = []
            
            # Repair points
            repaired_points = []
            for i, point in enumerate(annotation_data.get('points', [])):
                if not isinstance(point, dict):
                    continue
                
                # Add missing fields with defaults
                for field, default_value in self._default_values.items():
                    if field not in point:
                        point[field] = default_value
                
                # STANDARDIZED: Normalize array format [x, y, class_id] - no dictionary conversion
                try:
                    if isinstance(point, list) and len(point) >= 3:
                        # Ensure correct types for array format
                        point[0] = int(round(float(point[0])))  # x coordinate (integer)
                        point[1] = int(round(float(point[1]))) # y coordinate (integer)
                        point[2] = int(point[2])                # class_id (integer)
                    else:
                        # Skip invalid format in modular system
                        continue
                    
                    repaired_points.append(point)
                    
                except (ValueError, TypeError):
                    # Skip invalid points
                    continue
            
            annotation_data['points'] = repaired_points
            json_data['annotation_data'] = annotation_data
            
            return json_data
            
        except Exception as e:
            self.emit_error(f"Error repairing JSON data: {str(e)}")
            return None
    
    def _parse_annotation_data(self, json_data: Dict[str, Any]) -> Optional[AnnotationData]:
        """Parse annotation data from JSON."""
        try:
            annotation_data = json_data['annotation_data']
            
            # Parse points
            points = []
            for point_data in annotation_data.get('points', []):
                point = AnnotationPoint(
                    x=float(point_data['x']),
                    y=float(point_data['y']),
                    class_id=int(point_data['class_id']),
                    confidence=float(point_data.get('confidence', 1.0)),
                    timestamp=float(point_data.get('timestamp', 0.0)),
                    source=point_data.get('source', 'unknown')
                )
                points.append(point)
            
            # Create annotation data
            result = AnnotationData(
                points=points,
                image_path=annotation_data.get('image_path', ''),
                image_size=tuple(annotation_data.get('image_size', (0, 0))),
                class_names=annotation_data.get('class_names', []),
                metadata=annotation_data.get('metadata', {})
            )
            
            return result
            
        except Exception as e:
            self.emit_error(f"Error parsing annotation data: {str(e)}")
            return None
    
    def _parse_overlay_data(self, json_data: Dict[str, Any]) -> Optional[OverlayData]:
        """Parse overlay data from JSON."""
        try:
            overlay_data = json_data['overlay_data']
            
            # Parse overlay type
            overlay_type = OverlayType(overlay_data['overlay_type'])
            
            # Parse data
            data = overlay_data['data']
            if isinstance(data, dict) and data.get('type') == 'numpy_array':
                # Deserialize numpy array
                data = self._deserialize_numpy_array(data)
            
            # Create overlay data
            result = OverlayData(
                overlay_type=overlay_type,
                data=data,
                opacity=float(overlay_data.get('opacity', 1.0)),
                color_map=overlay_data.get('color_map'),
                visible=bool(overlay_data.get('visible', True)),
                metadata=overlay_data.get('metadata', {})
            )
            
            return result
            
        except Exception as e:
            self.emit_error(f"Error parsing overlay data: {str(e)}")
            return None
    
    def _deserialize_numpy_array(self, data: Dict[str, Any]) -> Any:
        """Deserialize numpy array from JSON."""
        try:
            import numpy as np
            
            array_data = data['data']
            dtype = data['dtype']
            shape = data['shape']
            
            # Create numpy array
            array = np.array(array_data, dtype=dtype)
            array = array.reshape(shape)
            
            return array
            
        except ImportError:
            self.emit_error("NumPy is required for array deserialization")
            return data['data']
        except Exception as e:
            self.emit_error(f"Error deserializing numpy array: {str(e)}")
            return data['data']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get JSON loader statistics."""
        stats = super().get_statistics()
        stats.update({
            'validation_enabled': self._validation_enabled,
            'migration_enabled': self._migration_enabled,
            'strict_validation': self._strict_validation,
            'auto_repair': self._auto_repair,
            'supported_versions': self._supported_versions,
            'current_version': self._current_version,
            'ignore_missing_fields': self._ignore_missing_fields,
            'load_statistics': self.get_load_statistics()
        })
        return stats