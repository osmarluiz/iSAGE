"""
Pan Controller - Handles panning functionality for canvas

This module provides pan control with middle mouse drag support and bounds checking.
"""

from typing import Optional, Tuple
from ..base_protocols import BaseComponent, QPointF, pyqtSignal


class PanController(BaseComponent):
    """Controls panning functionality for canvas."""
    
    # Pan-specific signals
    panChanged = pyqtSignal(object)  # QPointF offset
    panStarted = pyqtSignal(object)  # QPointF start_pos
    panEnded = pyqtSignal(object)  # QPointF end_pos
    panReset = pyqtSignal()
    
    def __init__(self, name: str = "pan_controller", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Pan state
        self._pan_offset: QPointF = QPointF(0, 0)
        self._is_panning: bool = False
        self._pan_start_pos: QPointF = QPointF(0, 0)
        self._last_pan_pos: QPointF = QPointF(0, 0)
        
        # Pan configuration
        self._pan_button: int = 4  # Middle mouse button (Qt.MiddleButton)
        self._enable_pan_bounds: bool = True
        self._pan_bounds: Tuple[float, float, float, float] = (-1000, -1000, 1000, 1000)  # left, top, right, bottom
        self._pan_sensitivity: float = 1.0
        self._invert_pan: bool = False
        
        # Canvas and image info
        self._canvas_size: Tuple[int, int] = (800, 600)
        self._image_size: Tuple[int, int] = (0, 0)
        self._zoom_factor: float = 1.0
    
    def initialize(self, **kwargs) -> bool:
        """Initialize pan controller."""
        self._pan_button = kwargs.get('pan_button', 4)
        self._enable_pan_bounds = kwargs.get('enable_pan_bounds', True)
        self._pan_sensitivity = kwargs.get('pan_sensitivity', 1.0)
        self._invert_pan = kwargs.get('invert_pan', False)
        
        return super().initialize(**kwargs)
    
    def set_pan_offset(self, offset: QPointF) -> bool:
        """Set pan offset."""
        # Apply bounds if enabled
        if self._enable_pan_bounds:
            offset = self._clamp_to_bounds(offset)
        
        if offset != self._pan_offset:
            self._pan_offset = QPointF(offset)
            self.panChanged.emit(self._pan_offset)
            self.emit_state_changed({
                'pan_offset': (offset.x(), offset.y()),
                'pan_changed': True
            })
            return True
        
        return False
    
    def get_pan_offset(self) -> QPointF:
        """Get current pan offset."""
        return QPointF(self._pan_offset)
    
    def start_pan(self, start_pos: QPointF) -> bool:
        """Start panning operation."""
        if self._is_panning:
            return False
        
        self._is_panning = True
        self._pan_start_pos = QPointF(start_pos)
        self._last_pan_pos = QPointF(start_pos)
        
        self.panStarted.emit(start_pos)
        self.emit_state_changed({'is_panning': True})
        
        return True
    
    def update_pan(self, current_pos: QPointF) -> bool:
        """Update panning with current position."""
        if not self._is_panning:
            return False
        
        # Calculate delta
        delta_x = current_pos.x() - self._last_pan_pos.x()
        delta_y = current_pos.y() - self._last_pan_pos.y()
        
        # Apply sensitivity
        delta_x *= self._pan_sensitivity
        delta_y *= self._pan_sensitivity
        
        # Invert if enabled
        if self._invert_pan:
            delta_x = -delta_x
            delta_y = -delta_y
        
        # Update offset
        new_offset = QPointF(
            self._pan_offset.x() + delta_x,
            self._pan_offset.y() + delta_y
        )
        
        success = self.set_pan_offset(new_offset)
        
        # Update last position
        self._last_pan_pos = QPointF(current_pos)
        
        return success
    
    def end_pan(self, end_pos: QPointF) -> bool:
        """End panning operation."""
        if not self._is_panning:
            return False
        
        self._is_panning = False
        
        self.panEnded.emit(end_pos)
        self.emit_state_changed({'is_panning': False})
        
        return True
    
    def cancel_pan(self) -> bool:
        """Cancel current panning operation."""
        if not self._is_panning:
            return False
        
        self._is_panning = False
        self.emit_state_changed({'is_panning': False})
        
        return True
    
    def is_panning(self) -> bool:
        """Check if currently panning."""
        return self._is_panning
    
    def reset_pan(self) -> bool:
        """Reset pan to center."""
        if self.set_pan_offset(QPointF(0, 0)):
            self.panReset.emit()
            return True
        return False
    
    def handle_mouse_press(self, pos: QPointF, button: int) -> bool:
        """Handle mouse press for panning."""
        if button == self._pan_button:
            return self.start_pan(pos)
        return False
    
    def handle_mouse_move(self, pos: QPointF) -> bool:
        """Handle mouse move for panning."""
        if self._is_panning:
            return self.update_pan(pos)
        return False
    
    def handle_mouse_release(self, pos: QPointF, button: int) -> bool:
        """Handle mouse release for panning."""
        if button == self._pan_button and self._is_panning:
            return self.end_pan(pos)
        return False
    
    def set_pan_button(self, button: int) -> None:
        """Set pan button (Qt mouse button)."""
        self._pan_button = button
        self.emit_state_changed({'pan_button': button})
    
    def get_pan_button(self) -> int:
        """Get pan button."""
        return self._pan_button
    
    def set_pan_sensitivity(self, sensitivity: float) -> None:
        """Set pan sensitivity."""
        self._pan_sensitivity = max(0.1, min(5.0, sensitivity))
        self.emit_state_changed({'pan_sensitivity': sensitivity})
    
    def get_pan_sensitivity(self) -> float:
        """Get pan sensitivity."""
        return self._pan_sensitivity
    
    def set_invert_pan(self, invert: bool) -> None:
        """Set invert pan."""
        self._invert_pan = invert
        self.emit_state_changed({'invert_pan': invert})
    
    def is_pan_inverted(self) -> bool:
        """Check if pan is inverted."""
        return self._invert_pan
    
    def set_canvas_size(self, size: Tuple[int, int]) -> None:
        """Set canvas size for pan calculations."""
        self._canvas_size = size
        self._update_pan_bounds()
        self.emit_state_changed({'canvas_size': size})
    
    def get_canvas_size(self) -> Tuple[int, int]:
        """Get canvas size."""
        return self._canvas_size
    
    def set_image_size(self, size: Tuple[int, int]) -> None:
        """Set image size for pan calculations."""
        self._image_size = size
        self._update_pan_bounds()
        self.emit_state_changed({'image_size': size})
    
    def get_image_size(self) -> Tuple[int, int]:
        """Get image size."""
        return self._image_size
    
    def set_zoom_factor(self, factor: float) -> None:
        """Set zoom factor for pan calculations."""
        self._zoom_factor = factor
        self._update_pan_bounds()
        self.emit_state_changed({'zoom_factor': factor})
    
    def get_zoom_factor(self) -> float:
        """Get zoom factor."""
        return self._zoom_factor
    
    def set_enable_pan_bounds(self, enabled: bool) -> None:
        """Enable/disable pan bounds."""
        self._enable_pan_bounds = enabled
        if enabled:
            self._update_pan_bounds()
            # Re-clamp current offset
            self.set_pan_offset(self._pan_offset)
        self.emit_state_changed({'enable_pan_bounds': enabled})
    
    def is_pan_bounds_enabled(self) -> bool:
        """Check if pan bounds are enabled."""
        return self._enable_pan_bounds
    
    def set_pan_bounds(self, left: float, top: float, right: float, bottom: float) -> None:
        """Set manual pan bounds."""
        self._pan_bounds = (left, top, right, bottom)
        if self._enable_pan_bounds:
            self.set_pan_offset(self._pan_offset)  # Re-clamp
        self.emit_state_changed({'pan_bounds': self._pan_bounds})
    
    def get_pan_bounds(self) -> Tuple[float, float, float, float]:
        """Get current pan bounds."""
        return self._pan_bounds
    
    def center_on_point(self, point: QPointF) -> bool:
        """Center view on a specific point."""
        # Calculate offset to center the point
        canvas_center_x = self._canvas_size[0] / 2
        canvas_center_y = self._canvas_size[1] / 2
        
        offset_x = canvas_center_x - point.x()
        offset_y = canvas_center_y - point.y()
        
        return self.set_pan_offset(QPointF(offset_x, offset_y))
    
    def pan_to_show_point(self, point: QPointF, margin: float = 50) -> bool:
        """Pan to show a point if it's not visible."""
        # Check if point is already visible
        if self._is_point_visible(point, margin):
            return False
        
        # Calculate required pan to show point
        current_offset = self.get_pan_offset()
        
        # Transform point to screen coordinates
        screen_x = point.x() + current_offset.x()
        screen_y = point.y() + current_offset.y()
        
        new_offset_x = current_offset.x()
        new_offset_y = current_offset.y()
        
        # Adjust X if needed
        if screen_x < margin:
            new_offset_x = margin - point.x()
        elif screen_x > self._canvas_size[0] - margin:
            new_offset_x = self._canvas_size[0] - margin - point.x()
        
        # Adjust Y if needed
        if screen_y < margin:
            new_offset_y = margin - point.y()
        elif screen_y > self._canvas_size[1] - margin:
            new_offset_y = self._canvas_size[1] - margin - point.y()
        
        return self.set_pan_offset(QPointF(new_offset_x, new_offset_y))
    
    def get_pan_distance(self) -> float:
        """Get total pan distance from origin."""
        return (self._pan_offset.x() ** 2 + self._pan_offset.y() ** 2) ** 0.5
    
    def get_pan_delta_since_start(self) -> QPointF:
        """Get pan delta since start of current pan operation."""
        if not self._is_panning:
            return QPointF(0, 0)
        
        return QPointF(
            self._last_pan_pos.x() - self._pan_start_pos.x(),
            self._last_pan_pos.y() - self._pan_start_pos.y()
        )
    
    def get_statistics(self) -> dict:
        """Get pan controller statistics."""
        return {
            'pan_offset': (self._pan_offset.x(), self._pan_offset.y()),
            'is_panning': self._is_panning,
            'pan_button': self._pan_button,
            'pan_sensitivity': self._pan_sensitivity,
            'invert_pan': self._invert_pan,
            'enable_pan_bounds': self._enable_pan_bounds,
            'pan_bounds': self._pan_bounds,
            'canvas_size': self._canvas_size,
            'image_size': self._image_size,
            'zoom_factor': self._zoom_factor,
            'pan_distance': self.get_pan_distance(),
            'pan_delta_since_start': (
                self.get_pan_delta_since_start().x(),
                self.get_pan_delta_since_start().y()
            ) if self._is_panning else (0, 0)
        }
    
    # Helper methods
    def _update_pan_bounds(self) -> None:
        """Update pan bounds based on image and canvas size."""
        if not self._enable_pan_bounds or self._image_size[0] == 0 or self._image_size[1] == 0:
            return
        
        # Calculate bounds to keep image within canvas
        scaled_image_width = self._image_size[0] * self._zoom_factor
        scaled_image_height = self._image_size[1] * self._zoom_factor
        
        # Calculate maximum pan offsets
        max_offset_x = max(0, (scaled_image_width - self._canvas_size[0]) / 2)
        max_offset_y = max(0, (scaled_image_height - self._canvas_size[1]) / 2)
        
        # Set bounds
        self._pan_bounds = (
            -max_offset_x,  # left
            -max_offset_y,  # top
            max_offset_x,   # right
            max_offset_y    # bottom
        )
    
    def _clamp_to_bounds(self, offset: QPointF) -> QPointF:
        """Clamp offset to bounds."""
        if not self._enable_pan_bounds:
            return offset
        
        left, top, right, bottom = self._pan_bounds
        
        clamped_x = max(left, min(right, offset.x()))
        clamped_y = max(top, min(bottom, offset.y()))
        
        return QPointF(clamped_x, clamped_y)
    
    def _is_point_visible(self, point: QPointF, margin: float = 0) -> bool:
        """Check if point is visible in current view."""
        # Transform point to screen coordinates
        screen_x = point.x() + self._pan_offset.x()
        screen_y = point.y() + self._pan_offset.y()
        
        # Check if within canvas bounds with margin
        return (margin <= screen_x <= self._canvas_size[0] - margin and
                margin <= screen_y <= self._canvas_size[1] - margin)