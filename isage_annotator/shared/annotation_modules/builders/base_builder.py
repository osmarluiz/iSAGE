"""
Base Builder - Foundation for all builders in the annotation system

This module provides the base class for all builders, defining common interfaces
and functionality for building annotation system components.
"""

from typing import Dict, Any, Optional, List, Callable, Protocol
from abc import ABC, abstractmethod
from ..base_protocols import BaseComponent


class BuilderProtocol(Protocol):
    """Protocol defining the builder interface."""
    
    def build(self) -> Optional[Any]:
        """Build the component."""
        ...
    
    def validate_configuration(self) -> bool:
        """Validate the current configuration."""
        ...
    
    def set_configuration(self, config: Dict[str, Any]) -> None:
        """Set the builder configuration."""
        ...
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get the current configuration."""
        ...

# Create a custom metaclass that combines ABC and QObject metaclasses
try:
    from PyQt5.QtCore import QObject
    
    class BuilderMeta(type(QObject), type(ABC)):
        pass
    
    class BaseBuilder(BaseComponent, ABC, metaclass=BuilderMeta):
        """Base class for all builders in the annotation system."""
except ImportError:
    # Fallback when PyQt5 is not available
    class BaseBuilder(BaseComponent, ABC):
        """Base class for all builders in the annotation system."""
        
        def __init__(self, name: str = "base_builder", version: str = "1.0.0"):
            super().__init__(name, version)
            
            # Builder state
            self._is_building: bool = False
            self._build_completed: bool = False
            self._build_errors: List[str] = []
            self._build_warnings: List[str] = []
            
            # Configuration
            self._configuration: Dict[str, Any] = {}
            self._validation_rules: List[Callable] = []
            
            # Build callbacks
            self._build_started_callbacks: List[Callable] = []
            self._build_progress_callbacks: List[Callable] = []
            self._build_completed_callbacks: List[Callable] = []
            self._build_error_callbacks: List[Callable] = []
    
        def initialize(self, **kwargs) -> bool:
            """Initialize the builder."""
            try:
                self._configuration.update(kwargs)
                
                # Initialize component state
                self._is_building = False
                self._build_completed = False
                self._build_errors.clear()
                self._build_warnings.clear()
                
                return super().initialize(**kwargs)
                
            except Exception as e:
                self.emit_error(f"Error initializing builder: {str(e)}")
                return False
        
        @abstractmethod
        def build(self) -> Optional[Any]:
            """Build the component. Must be implemented by subclasses."""
            pass
        
        def validate_configuration(self) -> bool:
            """Validate the current configuration."""
            try:
                self._build_errors.clear()
                self._build_warnings.clear()
                
                # Run validation rules
                for rule in self._validation_rules:
                    try:
                        rule(self._configuration)
                    except ValidationError as e:
                        self._build_errors.append(str(e))
                    except ValidationWarning as e:
                        self._build_warnings.append(str(e))
                    except Exception as e:
                        self._build_errors.append(f"Validation rule error: {str(e)}")
                
                return len(self._build_errors) == 0
                
            except Exception as e:
                self.emit_error(f"Error validating configuration: {str(e)}")
                return False
        
        def add_validation_rule(self, rule: Callable[[Dict[str, Any]], None]) -> None:
            """Add a validation rule for the configuration."""
            self._validation_rules.append(rule)
        
        def set_configuration(self, config: Dict[str, Any]) -> None:
            """Set the builder configuration."""
            self._configuration.update(config)
        
        def get_configuration(self) -> Dict[str, Any]:
            """Get the current configuration."""
            return self._configuration.copy()
        
        def get_build_errors(self) -> List[str]:
            """Get build errors."""
            return self._build_errors.copy()
        
        def get_build_warnings(self) -> List[str]:
            """Get build warnings."""
            return self._build_warnings.copy()
        
        def is_building(self) -> bool:
            """Check if currently building."""
            return self._is_building
        
        def is_build_completed(self) -> bool:
            """Check if build has completed."""
            return self._build_completed
        
        def add_build_started_callback(self, callback: Callable) -> None:
            """Add callback for build started event."""
            self._build_started_callbacks.append(callback)
        
        def add_build_progress_callback(self, callback: Callable[[int, str], None]) -> None:
            """Add callback for build progress event."""
            self._build_progress_callbacks.append(callback)
        
        def add_build_completed_callback(self, callback: Callable[[], None]) -> None:
            """Add callback for build completed event."""
            self._build_completed_callbacks.append(callback)
        
        def add_build_error_callback(self, callback: Callable[[str], None]) -> None:
            """Add callback for build error event."""
            self._build_error_callbacks.append(callback)
        
        def _emit_build_started(self) -> None:
            """Emit build started event."""
            self._is_building = True
            for callback in self._build_started_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.emit_error(f"Error in build started callback: {str(e)}")
        
        def _emit_build_progress(self, progress: int, message: str) -> None:
            """Emit build progress event."""
            for callback in self._build_progress_callbacks:
                try:
                    callback(progress, message)
                except Exception as e:
                    self.emit_error(f"Error in build progress callback: {str(e)}")
        
        def _emit_build_completed(self) -> None:
            """Emit build completed event."""
            self._is_building = False
            self._build_completed = True
            for callback in self._build_completed_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.emit_error(f"Error in build completed callback: {str(e)}")
        
        def _emit_build_error(self, error_message: str) -> None:
            """Emit build error event."""
            self._is_building = False
            self._build_errors.append(error_message)
            for callback in self._build_error_callbacks:
                try:
                    callback(error_message)
                except Exception as e:
                    self.emit_error(f"Error in build error callback: {str(e)}")
        
        def reset(self) -> None:
            """Reset the builder to initial state."""
            try:
                self._is_building = False
                self._build_completed = False
                self._build_errors.clear()
                self._build_warnings.clear()
                
                # Reset component state
                super().reset()
                
            except Exception as e:
                self.emit_error(f"Error resetting builder: {str(e)}")
        
        def get_statistics(self) -> Dict[str, Any]:
            """Get builder statistics."""
            stats = super().get_statistics()
            stats.update({
                'is_building': self._is_building,
                'build_completed': self._build_completed,
                'build_errors_count': len(self._build_errors),
                'build_warnings_count': len(self._build_warnings),
                'configuration_keys': list(self._configuration.keys()),
                'validation_rules_count': len(self._validation_rules),
                'build_callbacks_count': {
                    'started': len(self._build_started_callbacks),
                    'progress': len(self._build_progress_callbacks),
                    'completed': len(self._build_completed_callbacks),
                    'error': len(self._build_error_callbacks)
                }
            })
            return stats


class ValidationError(Exception):
        """Exception raised for configuration validation errors."""
        pass


class ValidationWarning(Exception):
        """Exception raised for configuration validation warnings."""
        pass


def create_validation_rule(rule_name: str, condition: Callable[[Any], bool], 
                              error_message: str, warning: bool = False) -> Callable:
        """Create a validation rule function."""
        def validation_rule(config: Dict[str, Any]) -> None:
            try:
                if not condition(config):
                    if warning:
                        raise ValidationWarning(f"{rule_name}: {error_message}")
                    else:
                        raise ValidationError(f"{rule_name}: {error_message}")
            except (ValidationError, ValidationWarning):
                raise
            except Exception as e:
                raise ValidationError(f"{rule_name}: Error evaluating condition - {str(e)}")
        
        return validation_rule


def create_required_key_rule(key: str, error_message: Optional[str] = None) -> Callable:
        """Create a validation rule for required configuration keys."""
        if error_message is None:
            error_message = f"Required configuration key '{key}' is missing"
        
        return create_validation_rule(
            rule_name=f"required_key_{key}",
            condition=lambda config: key in config,
            error_message=error_message
        )


def create_type_check_rule(key: str, expected_type: type, 
                              error_message: Optional[str] = None) -> Callable:
        """Create a validation rule for configuration value types."""
        if error_message is None:
            error_message = f"Configuration key '{key}' must be of type {expected_type.__name__}"
        
        return create_validation_rule(
            rule_name=f"type_check_{key}",
            condition=lambda config: key not in config or isinstance(config[key], expected_type),
            error_message=error_message
        )


def create_range_check_rule(key: str, min_value: Optional[float] = None, 
                               max_value: Optional[float] = None,
                               error_message: Optional[str] = None) -> Callable:
        """Create a validation rule for numeric range checks."""
        if error_message is None:
            range_desc = ""
            if min_value is not None and max_value is not None:
                range_desc = f"between {min_value} and {max_value}"
            elif min_value is not None:
                range_desc = f"at least {min_value}"
            elif max_value is not None:
                range_desc = f"at most {max_value}"
            error_message = f"Configuration key '{key}' must be {range_desc}"
        
        def check_range(config: Dict[str, Any]) -> bool:
            if key not in config:
                return True
            
            value = config[key]
            if not isinstance(value, (int, float)):
                return False
            
            if min_value is not None and value < min_value:
                return False
            
            if max_value is not None and value > max_value:
                return False
            
            return True
        
        return create_validation_rule(
            rule_name=f"range_check_{key}",
            condition=check_range,
            error_message=error_message
        )