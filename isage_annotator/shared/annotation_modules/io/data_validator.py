"""
Data Validator - Validates annotation data integrity and format

This module provides comprehensive data validation for annotation data,
ensuring consistency and detecting potential issues.
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from datetime import datetime
from ..base_protocols import BaseComponent, AnnotationPoint, AnnotationData, OverlayData
from .base_io import BaseIO


class ValidationError:
    """Represents a validation error."""
    
    def __init__(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message
        self.context = context or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp
        }


class DataValidator(BaseIO):
    """Validates annotation data integrity and format."""
    
    def __init__(self, name: str = "data_validator", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Validation configuration
        self._strict_mode: bool = False
        self._repair_mode: bool = True
        self._max_errors: int = 100
        self._error_threshold: float = 0.1  # 10% error rate threshold
        
        # Validation rules
        self._coordinate_bounds: Optional[Tuple[float, float, float, float]] = None  # (min_x, min_y, max_x, max_y)
        self._valid_class_ids: Optional[List[int]] = None
        self._confidence_range: Tuple[float, float] = (0.0, 1.0)
        self._timestamp_range: Optional[Tuple[float, float]] = None
        self._required_fields: List[str] = ['x', 'y', 'class_id']
        self._optional_fields: List[str] = ['confidence', 'timestamp', 'source']
        
        # Custom validators
        self._custom_validators: Dict[str, Callable] = {}
        
        # Validation statistics
        self._validation_count: int = 0
        self._error_count: int = 0
        self._repair_count: int = 0
        self._last_validation_time: float = 0.0
        
        # Error tracking
        self._recent_errors: List[ValidationError] = []
        self._error_summary: Dict[str, int] = {}
    
    def initialize(self, **kwargs) -> bool:
        """Initialize data validator."""
        self._strict_mode = kwargs.get('strict_mode', False)
        self._repair_mode = kwargs.get('repair_mode', True)
        self._max_errors = kwargs.get('max_errors', 100)
        self._error_threshold = kwargs.get('error_threshold', 0.1)
        
        # Set validation rules
        self._coordinate_bounds = kwargs.get('coordinate_bounds', None)
        self._valid_class_ids = kwargs.get('valid_class_ids', None)
        self._confidence_range = kwargs.get('confidence_range', (0.0, 1.0))
        self._timestamp_range = kwargs.get('timestamp_range', None)
        self._required_fields = kwargs.get('required_fields', ['x', 'y', 'class_id'])
        self._optional_fields = kwargs.get('optional_fields', ['confidence', 'timestamp', 'source'])
        
        return super().initialize(**kwargs)
    
    def validate_annotation_data(self, data: AnnotationData) -> Tuple[bool, List[ValidationError]]:
        """Validate complete annotation data."""
        try:
            start_time = time.time()
            errors = []
            
            # Validate basic structure
            structure_errors = self._validate_data_structure(data)
            errors.extend(structure_errors)
            
            # Validate points
            point_errors = self._validate_points(data.points)
            errors.extend(point_errors)
            
            # Validate metadata
            metadata_errors = self._validate_metadata(data)
            errors.extend(metadata_errors)
            
            # Run custom validators
            custom_errors = self._run_custom_validators(data)
            errors.extend(custom_errors)
            
            # Update statistics
            self._validation_count += 1
            self._error_count += len(errors)
            self._last_validation_time = time.time() - start_time
            
            # Update error tracking
            self._update_error_tracking(errors)
            
            # Check error threshold
            is_valid = self._check_error_threshold(errors, len(data.points))
            
            self.emit_state_changed({
                'validation_count': self._validation_count,
                'error_count': len(errors),
                'is_valid': is_valid,
                'last_validation_time': self._last_validation_time
            })
            
            return is_valid, errors
            
        except Exception as e:
            self.emit_error(f"Error validating annotation data: {str(e)}")
            return False, [ValidationError('system_error', str(e))]
    
    def validate_points(self, points: List[AnnotationPoint]) -> Tuple[bool, List[ValidationError]]:
        """Validate point annotations."""
        try:
            errors = self._validate_points(points)
            
            # Update statistics
            self._validation_count += 1
            self._error_count += len(errors)
            
            # Update error tracking
            self._update_error_tracking(errors)
            
            is_valid = self._check_error_threshold(errors, len(points))
            
            return is_valid, errors
            
        except Exception as e:
            self.emit_error(f"Error validating points: {str(e)}")
            return False, [ValidationError('system_error', str(e))]
    
    def validate_overlay_data(self, data: OverlayData) -> Tuple[bool, List[ValidationError]]:
        """Validate overlay data."""
        try:
            errors = []
            
            # Validate overlay structure
            if not hasattr(data, 'overlay_type'):
                errors.append(ValidationError('missing_field', 'Overlay type is missing'))
            
            if not hasattr(data, 'data') or data.data is None:
                errors.append(ValidationError('missing_field', 'Overlay data is missing'))
            
            # Validate opacity
            if hasattr(data, 'opacity'):
                if not (0.0 <= data.opacity <= 1.0):
                    errors.append(ValidationError('invalid_value', 
                                                f'Opacity must be between 0.0 and 1.0, got {data.opacity}'))
            
            # Validate data based on overlay type
            if hasattr(data, 'data') and data.data is not None:
                data_errors = self._validate_overlay_data_by_type(data)
                errors.extend(data_errors)
            
            is_valid = len(errors) == 0
            
            return is_valid, errors
            
        except Exception as e:
            self.emit_error(f"Error validating overlay data: {str(e)}")
            return False, [ValidationError('system_error', str(e))]
    
    def repair_annotation_data(self, data: AnnotationData) -> Tuple[AnnotationData, List[ValidationError]]:
        """Repair annotation data if possible."""
        if not self._repair_mode:
            return data, []
        
        try:
            repaired_data = data
            repair_errors = []
            
            # Repair points
            repaired_points, point_repair_errors = self._repair_points(data.points)
            repaired_data.points = repaired_points
            repair_errors.extend(point_repair_errors)
            
            # Repair metadata
            repaired_metadata, metadata_repair_errors = self._repair_metadata(data)
            repair_errors.extend(metadata_repair_errors)
            
            # Update repair statistics
            self._repair_count += len(repair_errors)
            
            self.emit_state_changed({
                'repair_count': self._repair_count,
                'repairs_applied': len(repair_errors)
            })
            
            return repaired_data, repair_errors
            
        except Exception as e:
            self.emit_error(f"Error repairing annotation data: {str(e)}")
            return data, [ValidationError('repair_error', str(e))]
    
    def add_custom_validator(self, name: str, validator_func: Callable) -> None:
        """Add custom validation function."""
        self._custom_validators[name] = validator_func
        self.emit_state_changed({'custom_validators': list(self._custom_validators.keys())})
    
    def remove_custom_validator(self, name: str) -> bool:
        """Remove custom validation function."""
        if name in self._custom_validators:
            del self._custom_validators[name]
            self.emit_state_changed({'custom_validators': list(self._custom_validators.keys())})
            return True
        return False
    
    def set_coordinate_bounds(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        """Set coordinate bounds for validation."""
        self._coordinate_bounds = (min_x, min_y, max_x, max_y)
        self.emit_state_changed({'coordinate_bounds': self._coordinate_bounds})
    
    def get_coordinate_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get coordinate bounds."""
        return self._coordinate_bounds
    
    def set_valid_class_ids(self, class_ids: List[int]) -> None:
        """Set valid class IDs."""
        self._valid_class_ids = class_ids
        self.emit_state_changed({'valid_class_ids': self._valid_class_ids})
    
    def get_valid_class_ids(self) -> Optional[List[int]]:
        """Get valid class IDs."""
        return self._valid_class_ids
    
    def set_confidence_range(self, min_confidence: float, max_confidence: float) -> None:
        """Set confidence range."""
        self._confidence_range = (min_confidence, max_confidence)
        self.emit_state_changed({'confidence_range': self._confidence_range})
    
    def get_confidence_range(self) -> Tuple[float, float]:
        """Get confidence range."""
        return self._confidence_range
    
    def set_strict_mode(self, enabled: bool) -> None:
        """Enable/disable strict mode."""
        self._strict_mode = enabled
        self.emit_state_changed({'strict_mode': enabled})
    
    def is_strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        return self._strict_mode
    
    def set_repair_mode(self, enabled: bool) -> None:
        """Enable/disable repair mode."""
        self._repair_mode = enabled
        self.emit_state_changed({'repair_mode': enabled})
    
    def is_repair_mode(self) -> bool:
        """Check if repair mode is enabled."""
        return self._repair_mode
    
    def set_error_threshold(self, threshold: float) -> None:
        """Set error threshold."""
        self._error_threshold = max(0.0, min(1.0, threshold))
        self.emit_state_changed({'error_threshold': self._error_threshold})
    
    def get_error_threshold(self) -> float:
        """Get error threshold."""
        return self._error_threshold
    
    def get_recent_errors(self, limit: int = 10) -> List[ValidationError]:
        """Get recent validation errors."""
        return self._recent_errors[-limit:]
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error summary by type."""
        return self._error_summary.copy()
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            'validation_count': self._validation_count,
            'error_count': self._error_count,
            'repair_count': self._repair_count,
            'last_validation_time': self._last_validation_time,
            'error_rate': self._error_count / max(1, self._validation_count),
            'recent_errors_count': len(self._recent_errors),
            'error_summary': self._error_summary.copy()
        }
    
    def clear_statistics(self) -> None:
        """Clear validation statistics."""
        self._validation_count = 0
        self._error_count = 0
        self._repair_count = 0
        self._last_validation_time = 0.0
        self._recent_errors.clear()
        self._error_summary.clear()
        self.emit_state_changed({'statistics_cleared': True})
    
    def _validate_data_structure(self, data: AnnotationData) -> List[ValidationError]:
        """Validate basic data structure."""
        errors = []
        
        # Check required attributes
        if not hasattr(data, 'points') or data.points is None:
            errors.append(ValidationError('missing_field', 'Points list is missing'))
        elif not isinstance(data.points, list):
            errors.append(ValidationError('invalid_type', 'Points must be a list'))
        
        if not hasattr(data, 'image_path'):
            if self._strict_mode:
                errors.append(ValidationError('missing_field', 'Image path is missing'))
        
        if not hasattr(data, 'image_size'):
            if self._strict_mode:
                errors.append(ValidationError('missing_field', 'Image size is missing'))
        elif data.image_size and len(data.image_size) != 2:
            errors.append(ValidationError('invalid_format', 'Image size must be a 2-tuple'))
        
        if not hasattr(data, 'class_names'):
            if self._strict_mode:
                errors.append(ValidationError('missing_field', 'Class names are missing'))
        elif data.class_names and not isinstance(data.class_names, list):
            errors.append(ValidationError('invalid_type', 'Class names must be a list'))
        
        return errors
    
    def _validate_points(self, points: List[AnnotationPoint]) -> List[ValidationError]:
        """Validate point annotations."""
        errors = []
        
        if not points:
            return errors
        
        for i, point in enumerate(points):
            # Validate point structure
            if not isinstance(point, AnnotationPoint):
                errors.append(ValidationError('invalid_type', 
                                            f'Point {i} is not an AnnotationPoint instance'))
                continue
            
            # Validate required fields
            for field in self._required_fields:
                if not hasattr(point, field):
                    errors.append(ValidationError('missing_field', 
                                                f'Point {i} missing required field: {field}'))
            
            # Validate coordinates
            if hasattr(point, 'x') and hasattr(point, 'y'):
                if not isinstance(point.x, (int, float)) or not isinstance(point.y, (int, float)):
                    errors.append(ValidationError('invalid_type', 
                                                f'Point {i} coordinates must be numeric'))
                elif self._coordinate_bounds:
                    min_x, min_y, max_x, max_y = self._coordinate_bounds
                    if not (min_x <= point.x <= max_x and min_y <= point.y <= max_y):
                        errors.append(ValidationError('out_of_bounds', 
                                                    f'Point {i} coordinates out of bounds: ({point.x}, {point.y})'))
            
            # Validate class ID
            if hasattr(point, 'class_id'):
                if not isinstance(point.class_id, int):
                    errors.append(ValidationError('invalid_type', 
                                                f'Point {i} class_id must be integer'))
                elif point.class_id < 0:
                    errors.append(ValidationError('invalid_value', 
                                                f'Point {i} class_id must be non-negative'))
                elif self._valid_class_ids and point.class_id not in self._valid_class_ids:
                    errors.append(ValidationError('invalid_value', 
                                                f'Point {i} class_id {point.class_id} not in valid classes'))
            
            # Validate confidence
            if hasattr(point, 'confidence'):
                if not isinstance(point.confidence, (int, float)):
                    errors.append(ValidationError('invalid_type', 
                                                f'Point {i} confidence must be numeric'))
                else:
                    min_conf, max_conf = self._confidence_range
                    if not (min_conf <= point.confidence <= max_conf):
                        errors.append(ValidationError('out_of_range', 
                                                    f'Point {i} confidence {point.confidence} out of range'))
            
            # Validate timestamp
            if hasattr(point, 'timestamp'):
                if not isinstance(point.timestamp, (int, float)):
                    errors.append(ValidationError('invalid_type', 
                                                f'Point {i} timestamp must be numeric'))
                elif self._timestamp_range:
                    min_time, max_time = self._timestamp_range
                    if not (min_time <= point.timestamp <= max_time):
                        errors.append(ValidationError('out_of_range', 
                                                    f'Point {i} timestamp out of range'))
            
            # Validate source
            if hasattr(point, 'source'):
                if not isinstance(point.source, str):
                    errors.append(ValidationError('invalid_type', 
                                                f'Point {i} source must be string'))
        
        return errors
    
    def _validate_metadata(self, data: AnnotationData) -> List[ValidationError]:
        """Validate metadata."""
        errors = []
        
        # Validate image path exists
        if hasattr(data, 'image_path') and data.image_path:
            if not os.path.exists(data.image_path):
                if self._strict_mode:
                    errors.append(ValidationError('file_not_found', 
                                                f'Image file not found: {data.image_path}'))
        
        # Validate image size consistency
        if hasattr(data, 'image_size') and data.image_size:
            width, height = data.image_size
            if width <= 0 or height <= 0:
                errors.append(ValidationError('invalid_value', 
                                            f'Image size must be positive: {data.image_size}'))
        
        # Validate class names consistency
        if hasattr(data, 'class_names') and data.class_names and hasattr(data, 'points'):
            max_class_id = max((p.class_id for p in data.points), default=-1)
            if max_class_id >= len(data.class_names):
                errors.append(ValidationError('inconsistent_data', 
                                            f'Class ID {max_class_id} exceeds class names length'))
        
        return errors
    
    def _validate_overlay_data_by_type(self, data: OverlayData) -> List[ValidationError]:
        """Validate overlay data based on type."""
        errors = []
        
        # Check if data is numpy array
        try:
            import numpy as np
            if isinstance(data.data, np.ndarray):
                # Validate array properties
                if data.data.size == 0:
                    errors.append(ValidationError('empty_data', 'Overlay data is empty'))
                
                # Validate dimensions based on overlay type
                if data.overlay_type.value == 'prediction':
                    if data.data.ndim not in [2, 3]:
                        errors.append(ValidationError('invalid_dimensions', 
                                                    f'Prediction overlay must be 2D or 3D, got {data.data.ndim}D'))
                elif data.overlay_type.value == 'ground_truth':
                    if data.data.ndim != 2:
                        errors.append(ValidationError('invalid_dimensions', 
                                                    f'Ground truth overlay must be 2D, got {data.data.ndim}D'))
                
        except ImportError:
            pass
        
        return errors
    
    def _repair_points(self, points: List[AnnotationPoint]) -> Tuple[List[AnnotationPoint], List[ValidationError]]:
        """Repair point annotations."""
        repaired_points = []
        repair_errors = []
        
        for i, point in enumerate(points):
            try:
                # Create copy for repair
                repaired_point = point
                
                # Repair coordinates
                if hasattr(point, 'x') and hasattr(point, 'y'):
                    if self._coordinate_bounds:
                        min_x, min_y, max_x, max_y = self._coordinate_bounds
                        if point.x < min_x or point.x > max_x or point.y < min_y or point.y > max_y:
                            # Clamp coordinates to bounds
                            repaired_point.x = max(min_x, min(max_x, point.x))
                            repaired_point.y = max(min_y, min(max_y, point.y))
                            repair_errors.append(ValidationError('coordinate_clamped', 
                                                               f'Point {i} coordinates clamped to bounds'))
                
                # Repair confidence
                if hasattr(point, 'confidence'):
                    min_conf, max_conf = self._confidence_range
                    if point.confidence < min_conf or point.confidence > max_conf:
                        repaired_point.confidence = max(min_conf, min(max_conf, point.confidence))
                        repair_errors.append(ValidationError('confidence_clamped', 
                                                           f'Point {i} confidence clamped to range'))
                
                # Repair class ID
                if hasattr(point, 'class_id'):
                    if point.class_id < 0:
                        repaired_point.class_id = 0
                        repair_errors.append(ValidationError('class_id_fixed', 
                                                           f'Point {i} class_id set to 0'))
                    elif self._valid_class_ids and point.class_id not in self._valid_class_ids:
                        repaired_point.class_id = self._valid_class_ids[0]
                        repair_errors.append(ValidationError('class_id_fixed', 
                                                           f'Point {i} class_id set to valid value'))
                
                # Add missing fields
                if not hasattr(repaired_point, 'confidence'):
                    repaired_point.confidence = 1.0
                    repair_errors.append(ValidationError('field_added', 
                                                       f'Point {i} confidence set to default'))
                
                if not hasattr(repaired_point, 'timestamp'):
                    repaired_point.timestamp = time.time()
                    repair_errors.append(ValidationError('field_added', 
                                                       f'Point {i} timestamp set to current time'))
                
                if not hasattr(repaired_point, 'source'):
                    repaired_point.source = 'repaired'
                    repair_errors.append(ValidationError('field_added', 
                                                       f'Point {i} source set to "repaired"'))
                
                repaired_points.append(repaired_point)
                
            except Exception as e:
                # Skip points that can't be repaired
                repair_errors.append(ValidationError('repair_failed', 
                                                   f'Point {i} could not be repaired: {str(e)}'))
        
        return repaired_points, repair_errors
    
    def _repair_metadata(self, data: AnnotationData) -> Tuple[Dict[str, Any], List[ValidationError]]:
        """Repair metadata."""
        repair_errors = []
        
        # Add missing image size
        if not hasattr(data, 'image_size') or not data.image_size:
            data.image_size = (1024, 1024)  # Default size
            repair_errors.append(ValidationError('field_added', 'Image size set to default'))
        
        # Add missing class names
        if not hasattr(data, 'class_names') or not data.class_names:
            if data.points:
                max_class_id = max((p.class_id for p in data.points), default=0)
                data.class_names = [f'Class {i}' for i in range(max_class_id + 1)]
                repair_errors.append(ValidationError('field_added', 'Class names generated'))
        
        # Add missing metadata
        if not hasattr(data, 'metadata') or not data.metadata:
            data.metadata = {}
            repair_errors.append(ValidationError('field_added', 'Metadata initialized'))
        
        return data.metadata, repair_errors
    
    def _run_custom_validators(self, data: AnnotationData) -> List[ValidationError]:
        """Run custom validation functions."""
        errors = []
        
        for name, validator_func in self._custom_validators.items():
            try:
                validator_errors = validator_func(data)
                if validator_errors:
                    errors.extend(validator_errors)
            except Exception as e:
                errors.append(ValidationError('custom_validator_error', 
                                            f'Custom validator {name} failed: {str(e)}'))
        
        return errors
    
    def _update_error_tracking(self, errors: List[ValidationError]) -> None:
        """Update error tracking."""
        # Add to recent errors
        self._recent_errors.extend(errors)
        
        # Limit recent errors
        if len(self._recent_errors) > self._max_errors:
            self._recent_errors = self._recent_errors[-self._max_errors:]
        
        # Update error summary
        for error in errors:
            self._error_summary[error.error_type] = self._error_summary.get(error.error_type, 0) + 1
    
    def _check_error_threshold(self, errors: List[ValidationError], total_items: int) -> bool:
        """Check if error rate is within threshold."""
        if total_items == 0:
            return len(errors) == 0
        
        error_rate = len(errors) / total_items
        return error_rate <= self._error_threshold
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data validator statistics."""
        stats = super().get_statistics()
        stats.update({
            'strict_mode': self._strict_mode,
            'repair_mode': self._repair_mode,
            'max_errors': self._max_errors,
            'error_threshold': self._error_threshold,
            'coordinate_bounds': self._coordinate_bounds,
            'valid_class_ids': self._valid_class_ids,
            'confidence_range': self._confidence_range,
            'timestamp_range': self._timestamp_range,
            'required_fields': self._required_fields,
            'optional_fields': self._optional_fields,
            'custom_validators': list(self._custom_validators.keys()),
            'validation_statistics': self.get_validation_statistics()
        })
        return stats