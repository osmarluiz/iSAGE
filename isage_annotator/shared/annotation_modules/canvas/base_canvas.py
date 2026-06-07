"""
Base Canvas - Foundation for all canvas components

This module provides the base class for canvas components that handle
image display and coordinate conversion.
"""

from typing import Optional, Tuple, Union, Dict, Any
import numpy as np

# Handle PyQt5 imports gracefully
try:
    from PyQt5.QtCore import pyqtSignal, QPointF
    from PyQt5.QtGui import QPixmap
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class pyqtSignal: 
        def __init__(self, *args): pass
    class QPointF: pass
    class QPixmap: pass

from ..base_protocols import BaseComponent, CanvasProtocol


class BaseCanvas(BaseComponent):
    """Base class for all canvas components."""
    
    # Canvas-specific signals
    imageChanged = pyqtSignal(str)  # image path
    zoomChanged = pyqtSignal(float)  # zoom factor
    panChanged = pyqtSignal(object)  # QPointF offset
    coordinatesChanged = pyqtSignal(object)  # QPointF image coordinates
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Image data
        self._image: Optional[np.ndarray] = None
        self._image_path: Optional[str] = None
        self._image_size: Tuple[int, int] = (0, 0)  # (width, height)
        
        # View state
        self._zoom_factor: float = 1.0
        self._pan_offset: QPointF = QPointF(0, 0)
        self._fit_to_window: bool = True
        
        # Canvas properties
        self._canvas_size: Tuple[int, int] = (800, 600)  # (width, height)
        self._background_color: str = "#2b2b2b"
    
    # CanvasProtocol implementation
    def set_image(self, image: Union[np.ndarray, str, QPixmap]) -> bool:
        """Set the image to display."""
        try:
            if isinstance(image, str):
                # Load from file path
                self._image_path = image
                self._image = self._load_image_from_path(image)
            elif isinstance(image, np.ndarray):
                self._image = image.copy()
                self._image_path = None
            elif isinstance(image, QPixmap):
                self._image = self._pixmap_to_array(image)
                self._image_path = None
            else:
                self.emit_error(f"Unsupported image type: {type(image)}")
                return False
            
            if self._image is not None:
                self._image_size = (self._image.shape[1], self._image.shape[0])  # (width, height)
                self.imageChanged.emit(self._image_path or "")
                self.emit_state_changed({
                    'image_loaded': True,
                    'image_size': self._image_size,
                    'image_path': self._image_path
                })
                return True
            else:
                self.emit_error("Failed to load image")
                return False
                
        except Exception as e:
            self.emit_error(f"Error setting image: {str(e)}")
            return False
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get the current image."""
        return self._image.copy() if self._image is not None else None
    
    def screen_to_image_coords(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to image coordinates."""
        if self._image is None:
            return QPointF(0, 0)
        
        # Account for canvas centering
        canvas_center_x = self._canvas_size[0] / 2
        canvas_center_y = self._canvas_size[1] / 2
        
        # Account for pan offset
        adjusted_x = screen_pos.x() - canvas_center_x - self._pan_offset.x()
        adjusted_y = screen_pos.y() - canvas_center_y - self._pan_offset.y()
        
        # Convert to image coordinates
        image_x = adjusted_x / self._zoom_factor + self._image_size[0] / 2
        image_y = adjusted_y / self._zoom_factor + self._image_size[1] / 2
        
        return QPointF(image_x, image_y)
    
    def image_to_screen_coords(self, image_pos: QPointF) -> QPointF:
        """Convert image coordinates to screen coordinates."""
        if self._image is None:
            return QPointF(0, 0)
        
        # Convert from image coordinates
        adjusted_x = (image_pos.x() - self._image_size[0] / 2) * self._zoom_factor
        adjusted_y = (image_pos.y() - self._image_size[1] / 2) * self._zoom_factor
        
        # Account for canvas centering and pan offset
        canvas_center_x = self._canvas_size[0] / 2
        canvas_center_y = self._canvas_size[1] / 2
        
        screen_x = adjusted_x + canvas_center_x + self._pan_offset.x()
        screen_y = adjusted_y + canvas_center_y + self._pan_offset.y()
        
        return QPointF(screen_x, screen_y)
    
    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._zoom_factor
    
    def set_zoom_factor(self, factor: float) -> None:
        """Set zoom factor."""
        factor = max(0.1, min(10.0, factor))  # Clamp between 0.1x and 10x
        if factor != self._zoom_factor:
            self._zoom_factor = factor
            self._fit_to_window = False
            self.zoomChanged.emit(factor)
            self.emit_state_changed({'zoom_factor': factor, 'fit_to_window': False})
    
    def get_pan_offset(self) -> QPointF:
        """Get current pan offset."""
        return QPointF(self._pan_offset)
    
    def set_pan_offset(self, offset: QPointF) -> None:
        """Set pan offset."""
        self._pan_offset = QPointF(offset)
        self.panChanged.emit(self._pan_offset)
        self.emit_state_changed({'pan_offset': (offset.x(), offset.y())})
    
    # Canvas-specific methods
    def set_canvas_size(self, size: Tuple[int, int]) -> None:
        """Set canvas size."""
        self._canvas_size = size
        self.emit_state_changed({'canvas_size': size})
    
    def get_canvas_size(self) -> Tuple[int, int]:
        """Get canvas size."""
        return self._canvas_size
    
    def get_image_size(self) -> Tuple[int, int]:
        """Get image size."""
        return self._image_size
    
    def get_image_path(self) -> Optional[str]:
        """Get current image path."""
        return self._image_path
    
    def zoom_in(self, factor: float = 1.2) -> None:
        """Zoom in by factor."""
        self.set_zoom_factor(self._zoom_factor * factor)
    
    def zoom_out(self, factor: float = 1.2) -> None:
        """Zoom out by factor."""
        self.set_zoom_factor(self._zoom_factor / factor)
    
    def fit_to_window(self) -> None:
        """Fit image to window."""
        if self._image is None:
            return
        
        # Calculate zoom factor to fit image in canvas
        zoom_x = self._canvas_size[0] / self._image_size[0]
        zoom_y = self._canvas_size[1] / self._image_size[1]
        zoom_factor = min(zoom_x, zoom_y)
        
        self._zoom_factor = zoom_factor
        self._pan_offset = QPointF(0, 0)
        self._fit_to_window = True
        
        self.zoomChanged.emit(zoom_factor)
        self.panChanged.emit(self._pan_offset)
        self.emit_state_changed({
            'zoom_factor': zoom_factor,
            'pan_offset': (0, 0),
            'fit_to_window': True
        })
    
    def reset_view(self) -> None:
        """Reset view to default state."""
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self._fit_to_window = True
        
        self.zoomChanged.emit(1.0)
        self.panChanged.emit(self._pan_offset)
        self.emit_state_changed({
            'zoom_factor': 1.0,
            'pan_offset': (0, 0),
            'fit_to_window': True
        })
    
    def is_fit_to_window(self) -> bool:
        """Check if fit to window mode is enabled."""
        return self._fit_to_window
    
    def set_background_color(self, color: str) -> None:
        """Set background color."""
        self._background_color = color
        self.emit_state_changed({'background_color': color})
    
    def get_background_color(self) -> str:
        """Get background color."""
        return self._background_color
    
    def get_viewport_bounds(self) -> Tuple[QPointF, QPointF]:
        """Get viewport bounds in image coordinates."""
        if self._image is None:
            return QPointF(0, 0), QPointF(0, 0)
        
        # Get canvas corners in image coordinates
        top_left = self.screen_to_image_coords(QPointF(0, 0))
        bottom_right = self.screen_to_image_coords(QPointF(self._canvas_size[0], self._canvas_size[1]))
        
        return top_left, bottom_right
    
    def is_point_visible(self, image_pos: QPointF) -> bool:
        """Check if a point in image coordinates is visible in viewport."""
        top_left, bottom_right = self.get_viewport_bounds()
        
        return (top_left.x() <= image_pos.x() <= bottom_right.x() and
                top_left.y() <= image_pos.y() <= bottom_right.y())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get canvas statistics."""
        return {
            'image_loaded': self._image is not None,
            'image_size': self._image_size,
            'image_path': self._image_path,
            'zoom_factor': self._zoom_factor,
            'pan_offset': (self._pan_offset.x(), self._pan_offset.y()),
            'canvas_size': self._canvas_size,
            'fit_to_window': self._fit_to_window,
            'background_color': self._background_color
        }
    
    # Helper methods (to be implemented by subclasses)
    def _load_image_from_path(self, path: str) -> Optional[np.ndarray]:
        """Load image from file path. Override in subclasses."""
        # Basic implementation using imageio
        try:
            import imageio
            image = imageio.imread(path)
            if len(image.shape) == 2:
                # Convert grayscale to RGB
                image = np.stack([image] * 3, axis=-1)
            return image
        except Exception as e:
            self.emit_error(f"Failed to load image from {path}: {str(e)}")
            return None
    
    def _pixmap_to_array(self, pixmap: QPixmap) -> Optional[np.ndarray]:
        """Convert QPixmap to numpy array. Override in subclasses."""
        # Basic implementation
        try:
            from PyQt5.QtGui import QImage
            image = pixmap.toImage()
            width = image.width()
            height = image.height()
            
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(height, width, 4)  # RGBA
            return arr[:, :, :3]  # Return only RGB
        except Exception as e:
            self.emit_error(f"Failed to convert pixmap to array: {str(e)}")
            return None


# Re-export for convenience
CanvasProtocol = CanvasProtocol