"""
Base Protocols - Interface definitions for all annotation modules

This module defines the protocols (interfaces) that all annotation modules must follow.
This ensures consistent APIs and enables seamless module composition.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Handle PyQt5 imports gracefully
try:
    from PyQt5.QtCore import QObject, pyqtSignal, QPointF, QRectF
    from PyQt5.QtGui import QPixmap, QColor
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QPushButton, QLabel, QSlider, QSpinBox, QCheckBox, QComboBox, QGroupBox,
        QMainWindow, QSplitter
    )
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    # Create dummy classes for when PyQt5 is not available
    class QObject: pass
    class pyqtSignal: 
        def __init__(self, *args): pass
    class QPointF: pass
    class QRectF: pass
    class QPixmap: pass
    class QColor: pass
    class QWidget: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QGridLayout: pass
    class QPushButton: pass
    class QLabel: pass
    class QSlider: pass
    class QSpinBox: pass
    class QCheckBox: pass
    class QComboBox: pass
    class QGroupBox: pass
    class QMainWindow: pass
    class QSplitter: pass


# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class AnnotationPoint:
    """Represents a single annotation point."""
    x: float
    y: float
    class_id: int
    confidence: float = 1.0
    timestamp: Optional[str] = None
    source: str = "manual"  # "manual", "ai_suggested", "imported"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'class_id': self.class_id,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnnotationPoint':
        return cls(**data)


@dataclass
class AnnotationData:
    """Complete annotation data for an image."""
    image_path: str
    image_size: Tuple[int, int]  # (width, height)
    points: List[AnnotationPoint]
    class_names: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'image_path': self.image_path,
            'image_size': self.image_size,
            'points': [point.to_dict() for point in self.points],
            'class_names': self.class_names,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnnotationData':
        return cls(
            image_path=data['image_path'],
            image_size=tuple(data['image_size']),
            points=[AnnotationPoint.from_dict(p) for p in data['points']],
            class_names=data['class_names'],
            metadata=data['metadata']
        )


class OverlayType(Enum):
    """Types of overlays available."""
    PREDICTION = "prediction"
    GROUND_TRUTH = "ground_truth"
    MISTAKE = "mistake"
    GRID = "grid"
    UNCERTAINTY = "uncertainty"
    CUSTOM = "custom"


@dataclass
class OverlayData:
    """Data for an overlay."""
    overlay_type: OverlayType
    data: np.ndarray
    opacity: float = 0.5
    color_map: Optional[str] = None
    visible: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ==============================================================================
# Base Protocols
# ==============================================================================

class ComponentProtocol(Protocol):
    """Base protocol for all annotation components."""
    
    @property
    def name(self) -> str:
        """Component name for identification."""
        ...
    
    @property
    def version(self) -> str:
        """Component version."""
        ...
    
    def initialize(self, **kwargs) -> bool:
        """Initialize the component with configuration."""
        ...
    
    def cleanup(self) -> None:
        """Clean up resources when component is destroyed."""
        ...


class ToolProtocol(ComponentProtocol):
    """Protocol for annotation tools."""
    
    def handle_mouse_press(self, pos: QPointF, button: int) -> bool:
        """Handle mouse press events. Returns True if handled."""
        ...
    
    def handle_mouse_release(self, pos: QPointF, button: int) -> bool:
        """Handle mouse release events. Returns True if handled."""
        ...
    
    def handle_mouse_move(self, pos: QPointF) -> bool:
        """Handle mouse move events. Returns True if handled."""
        ...
    
    def handle_key_press(self, key: int) -> bool:
        """Handle key press events. Returns True if handled."""
        ...
    
    def get_annotations(self) -> List[AnnotationPoint]:
        """Get current annotations from this tool."""
        ...
    
    def set_annotations(self, annotations: List[AnnotationPoint]) -> None:
        """Set annotations for this tool."""
        ...
    
    def clear_annotations(self) -> None:
        """Clear all annotations from this tool."""
        ...


class CanvasProtocol(ComponentProtocol):
    """Protocol for canvas components."""
    
    def set_image(self, image: Union[np.ndarray, str, QPixmap]) -> bool:
        """Set the image to display."""
        ...
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get the current image."""
        ...
    
    def screen_to_image_coords(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to image coordinates."""
        ...
    
    def image_to_screen_coords(self, image_pos: QPointF) -> QPointF:
        """Convert image coordinates to screen coordinates."""
        ...
    
    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        ...
    
    def set_zoom_factor(self, factor: float) -> None:
        """Set zoom factor."""
        ...
    
    def get_pan_offset(self) -> QPointF:
        """Get current pan offset."""
        ...
    
    def set_pan_offset(self, offset: QPointF) -> None:
        """Set pan offset."""
        ...


class OverlayProtocol(ComponentProtocol):
    """Protocol for overlay components."""
    
    def set_overlay_data(self, data: OverlayData) -> bool:
        """Set overlay data."""
        ...
    
    def get_overlay_data(self) -> Optional[OverlayData]:
        """Get current overlay data."""
        ...
    
    def set_opacity(self, opacity: float) -> None:
        """Set overlay opacity (0.0 to 1.0)."""
        ...
    
    def get_opacity(self) -> float:
        """Get current opacity."""
        ...
    
    def set_visible(self, visible: bool) -> None:
        """Set overlay visibility."""
        ...
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        ...
    
    def render(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render overlay to pixmap."""
        ...


class IOProtocol(ComponentProtocol):
    """Protocol for I/O components."""
    
    def save_annotations(self, annotations: AnnotationData, filepath: str) -> bool:
        """Save annotations to file."""
        ...
    
    def load_annotations(self, filepath: str) -> Optional[AnnotationData]:
        """Load annotations from file."""
        ...
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        ...
    
    def validate_format(self, filepath: str) -> bool:
        """Validate if file format is supported."""
        ...


class NavigatorProtocol(ComponentProtocol):
    """Protocol for navigation components."""
    
    def set_image_list(self, image_paths: List[str]) -> None:
        """Set list of images to navigate."""
        ...
    
    def get_image_list(self) -> List[str]:
        """Get current image list."""
        ...
    
    def get_current_index(self) -> int:
        """Get current image index."""
        ...
    
    def set_current_index(self, index: int) -> bool:
        """Set current image index."""
        ...
    
    def next_image(self) -> bool:
        """Navigate to next image."""
        ...
    
    def previous_image(self) -> bool:
        """Navigate to previous image."""
        ...
    
    def get_current_image_path(self) -> Optional[str]:
        """Get current image path."""
        ...


class UIProtocol(ComponentProtocol):
    """Protocol for UI components."""
    
    def get_widget(self) -> QWidget:
        """Get the main widget for this UI component."""
        ...
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update UI state."""
        ...
    
    def get_state(self) -> Dict[str, Any]:
        """Get current UI state."""
        ...
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable UI component."""
        ...


class PerformanceProtocol(ComponentProtocol):
    """Protocol for performance components."""
    
    def optimize(self, operation: str, data: Any) -> Any:
        """Optimize a specific operation."""
        ...
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics."""
        ...
    
    def clear_cache(self) -> None:
        """Clear performance caches."""
        ...


# ==============================================================================
# Base Classes
# ==============================================================================

class BaseComponent(QObject):
    """Base class for all annotation components."""
    
    # Common signals
    stateChanged = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__()
        self._name = name
        self._version = version
        self._initialized = False
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    def initialize(self, **kwargs) -> bool:
        """Initialize the component."""
        self._initialized = True
        return True
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False
    
    def emit_state_changed(self, state: Dict[str, Any]) -> None:
        """Emit state changed signal."""
        self.stateChanged.emit(state)
    
    def emit_error(self, error: str) -> None:
        """Emit error signal."""
        self.errorOccurred.emit(error)


# ==============================================================================
# Module Registry
# ==============================================================================

class ModuleRegistry:
    """Registry for managing annotation modules."""
    
    def __init__(self):
        self._modules: Dict[str, Dict[str, type]] = {
            'tools': {},
            'canvas': {},
            'overlays': {},
            'io': {},
            'navigation': {},
            'ui': {},
            'performance': {}
        }
    
    def register_module(self, category: str, name: str, module_class: type) -> None:
        """Register a module in the registry."""
        if category not in self._modules:
            raise ValueError(f"Unknown category: {category}")
        
        self._modules[category][name] = module_class
    
    def get_module(self, category: str, name: str) -> Optional[type]:
        """Get a module class from the registry."""
        return self._modules.get(category, {}).get(name)
    
    def get_available_modules(self, category: str) -> List[str]:
        """Get list of available modules in a category."""
        return list(self._modules.get(category, {}).keys())
    
    def get_all_modules(self) -> Dict[str, List[str]]:
        """Get all available modules by category."""
        return {cat: list(modules.keys()) for cat, modules in self._modules.items()}


# Global registry instance
module_registry = ModuleRegistry()

# Export all important classes and functions
__all__ = [
    # PyQt5 imports (with fallbacks)
    'pyqtSignal', 'QObject', 'QPointF', 'QRectF', 'QPixmap', 'QColor',
    'QWidget', 'QVBoxLayout', 'QHBoxLayout', 'QGridLayout',
    'QPushButton', 'QLabel', 'QSlider', 'QSpinBox', 'QCheckBox', 'QComboBox', 'QGroupBox',
    'QMainWindow', 'QSplitter',
    
    # Data structures
    'AnnotationPoint', 'OverlayData', 'ComponentMetadata', 'ModuleConfig',
    
    # Enums
    'AnnotationMode', 'OverlayType', 'ComponentStatus', 'ComponentCategory',
    
    # Protocols
    'ComponentProtocol', 'ToolProtocol', 'CanvasProtocol', 'OverlayProtocol', 
    'NavigationProtocol', 'IOProtocol',
    
    # Base classes
    'BaseComponent',
    
    # Registry
    'ModuleRegistry', 'module_registry',
    
    # Constants
    'PYQT5_AVAILABLE'
]