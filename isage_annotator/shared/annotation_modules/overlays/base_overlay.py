"""
Base Overlay - Foundation for all overlay components

This module provides the base class for overlay components that handle
visual overlays like predictions, ground truth, etc.
"""

from typing import Optional, Tuple, Dict, Any
import numpy as np
from ..base_protocols import BaseComponent, OverlayProtocol, OverlayData, OverlayType, QPixmap


class BaseOverlay(BaseComponent):
    """Base class for all overlay components."""
    
    # Overlay-specific signals
    overlayChanged = pyqtSignal(object)  # OverlayData
    opacityChanged = pyqtSignal(float)
    visibilityChanged = pyqtSignal(bool)
    
    def __init__(self, name: str, overlay_type: OverlayType, version: str = "1.0.0"):
        super().__init__(name, version)
        
        self._overlay_type = overlay_type
        self._overlay_data: Optional[OverlayData] = None
        self._opacity: float = 0.5
        self._visible: bool = True
        self._cached_pixmap: Optional[QPixmap] = None
        self._cache_valid: bool = False
    
    # OverlayProtocol implementation
    def set_overlay_data(self, data: OverlayData) -> bool:
        """Set overlay data."""
        try:
            if data.overlay_type != self._overlay_type:
                self.emit_error(f"Overlay type mismatch: expected {self._overlay_type}, got {data.overlay_type}")
                return False
            
            self._overlay_data = data
            self._opacity = data.opacity
            self._visible = data.visible
            self._cache_valid = False
            
            self.overlayChanged.emit(data)
            self.emit_state_changed({
                'data_loaded': True,
                'data_shape': data.data.shape if data.data is not None else None,
                'opacity': self._opacity,
                'visible': self._visible
            })
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting overlay data: {str(e)}")
            return False
    
    def get_overlay_data(self) -> Optional[OverlayData]:
        """Get current overlay data."""
        return self._overlay_data
    
    def set_opacity(self, opacity: float) -> None:
        """Set overlay opacity (0.0 to 1.0)."""
        opacity = max(0.0, min(1.0, opacity))
        if opacity != self._opacity:
            self._opacity = opacity
            if self._overlay_data:
                self._overlay_data.opacity = opacity
            self._cache_valid = False
            
            self.opacityChanged.emit(opacity)
            self.emit_state_changed({'opacity': opacity})
    
    def get_opacity(self) -> float:
        """Get current opacity."""
        return self._opacity
    
    def set_visible(self, visible: bool) -> None:
        """Set overlay visibility."""
        if visible != self._visible:
            self._visible = visible
            if self._overlay_data:
                self._overlay_data.visible = visible
            
            self.visibilityChanged.emit(visible)
            self.emit_state_changed({'visible': visible})
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self._visible
    
    def render(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render overlay to pixmap."""
        if not self._visible or self._overlay_data is None:
            return None
        
        # Use cached pixmap if valid
        if self._cache_valid and self._cached_pixmap is not None:
            return self._cached_pixmap
        
        try:
            # Render overlay
            pixmap = self._render_overlay(canvas_size)
            
            # Cache the result
            self._cached_pixmap = pixmap
            self._cache_valid = True
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error rendering overlay: {str(e)}")
            return None
    
    # Overlay-specific methods
    def get_overlay_type(self) -> OverlayType:
        """Get overlay type."""
        return self._overlay_type
    
    def has_data(self) -> bool:
        """Check if overlay has data."""
        return self._overlay_data is not None and self._overlay_data.data is not None
    
    def get_data_shape(self) -> Optional[Tuple[int, ...]]:
        """Get data shape."""
        if self._overlay_data and self._overlay_data.data is not None:
            return self._overlay_data.data.shape
        return None
    
    def clear_data(self) -> None:
        """Clear overlay data."""
        self._overlay_data = None
        self._cache_valid = False
        self._cached_pixmap = None
        
        self.overlayChanged.emit(None)
        self.emit_state_changed({'data_loaded': False})
    
    def invalidate_cache(self) -> None:
        """Invalidate render cache."""
        self._cache_valid = False
        self._cached_pixmap = None
    
    def set_color_map(self, color_map: str) -> None:
        """Set color map for overlay."""
        if self._overlay_data:
            self._overlay_data.color_map = color_map
            self._cache_valid = False
            self.emit_state_changed({'color_map': color_map})
    
    def get_color_map(self) -> Optional[str]:
        """Get current color map."""
        return self._overlay_data.color_map if self._overlay_data else None
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set overlay metadata."""
        if self._overlay_data:
            self._overlay_data.metadata = metadata
            self.emit_state_changed({'metadata': metadata})
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get overlay metadata."""
        return self._overlay_data.metadata if self._overlay_data else {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overlay statistics."""
        stats = {
            'overlay_type': self._overlay_type.value,
            'has_data': self.has_data(),
            'data_shape': self.get_data_shape(),
            'opacity': self._opacity,
            'visible': self._visible,
            'color_map': self.get_color_map(),
            'cache_valid': self._cache_valid
        }
        
        if self.has_data():
            data = self._overlay_data.data
            stats.update({
                'data_min': float(np.min(data)),
                'data_max': float(np.max(data)),
                'data_mean': float(np.mean(data)),
                'data_std': float(np.std(data)),
                'data_dtype': str(data.dtype)
            })
        
        return stats
    
    # Abstract methods (to be implemented by subclasses)
    def _render_overlay(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render overlay to pixmap. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _render_overlay")
    
    def _apply_color_map(self, data: np.ndarray, color_map: str) -> np.ndarray:
        """Apply color map to data. Override in subclasses."""
        # Basic implementation - just return data as is
        return data
    
    def _resize_data(self, data: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """Resize data to target size. Override in subclasses."""
        # Basic implementation using nearest neighbor
        try:
            from scipy.ndimage import zoom
            
            height, width = data.shape[:2]
            target_height, target_width = target_size
            
            zoom_y = target_height / height
            zoom_x = target_width / width
            
            if len(data.shape) == 2:
                return zoom(data, (zoom_y, zoom_x), order=0)
            else:
                return zoom(data, (zoom_y, zoom_x, 1), order=0)
                
        except ImportError:
            # Fallback without scipy
            self.emit_error("scipy not available for image resizing")
            return data
        except Exception as e:
            self.emit_error(f"Error resizing data: {str(e)}")
            return data


# Re-export for convenience
OverlayProtocol = OverlayProtocol