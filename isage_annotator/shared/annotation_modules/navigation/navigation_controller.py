"""
Navigation Controller - Coordinates navigation between components

This module provides centralized navigation control, coordinating between
image navigator, minimap, and main canvas for seamless navigation.
"""

from typing import Optional, Dict, Any, List, Tuple, Callable
from ..base_protocols import BaseComponent, QRect, QPoint, QSize, QPixmap
from .base_navigator import BaseNavigator
from .image_navigator import ImageNavigator
from .minimap import Minimap


class NavigationController(BaseNavigator):
    """Coordinates navigation between multiple navigation components."""
    
    # Navigation controller signals
    navigationStateChanged = pyqtSignal(dict)  # navigation_state
    imageNavigationChanged = pyqtSignal(str)  # image_path
    viewportNavigationChanged = pyqtSignal(object)  # QRect
    minimapNavigationChanged = pyqtSignal(object)  # QPoint
    
    def __init__(self, name: str = "navigation_controller", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Navigation components
        self._image_navigator: Optional[ImageNavigator] = None
        self._minimap: Optional[Minimap] = None
        self._main_canvas = None  # Will be set externally
        
        # Navigation state
        self._current_image_path: Optional[str] = None
        self._current_viewport: QRect = QRect()
        self._current_zoom_level: float = 1.0
        self._current_pan_offset: QPoint = QPoint()
        
        # Navigation settings
        self._sync_enabled: bool = True
        self._auto_fit_enabled: bool = True
        self._smooth_navigation: bool = True
        self._navigation_speed: float = 1.0
        
        # Navigation history
        self._navigation_history: List[Dict[str, Any]] = []
        self._history_index: int = -1
        self._max_history_size: int = 50
        
        # Callbacks
        self._image_changed_callback: Optional[Callable[[str], None]] = None
        self._viewport_changed_callback: Optional[Callable[[QRect], None]] = None
        
        # Performance settings
        self._update_throttle: bool = True
        self._batch_updates: bool = True
        self._update_delay: float = 0.05  # 50ms delay
        
        # State tracking
        self._updating: bool = False
        self._pending_updates: Dict[str, Any] = {}
    
    def initialize(self, **kwargs) -> bool:
        """Initialize navigation controller."""
        self._sync_enabled = kwargs.get('sync_enabled', True)
        self._auto_fit_enabled = kwargs.get('auto_fit_enabled', True)
        self._smooth_navigation = kwargs.get('smooth_navigation', True)
        self._navigation_speed = kwargs.get('navigation_speed', 1.0)
        self._max_history_size = kwargs.get('max_history_size', 50)
        self._update_throttle = kwargs.get('update_throttle', True)
        self._batch_updates = kwargs.get('batch_updates', True)
        self._update_delay = kwargs.get('update_delay', 0.05)
        
        return super().initialize(**kwargs)
    
    def set_image_navigator(self, navigator: ImageNavigator) -> None:
        """Set image navigator component."""
        try:
            # Disconnect previous navigator
            if self._image_navigator:
                self._disconnect_image_navigator()
            
            self._image_navigator = navigator
            
            # Connect signals
            if navigator:
                navigator.imageChanged.connect(self._on_image_changed)
                navigator.imageLoadFailed.connect(self._on_image_load_failed)
            
            self.emit_state_changed({'image_navigator_connected': navigator is not None})
            
        except Exception as e:
            self.emit_error(f"Error setting image navigator: {str(e)}")
    
    def set_minimap(self, minimap: Minimap) -> None:
        """Set minimap component."""
        try:
            # Disconnect previous minimap
            if self._minimap:
                self._disconnect_minimap()
            
            self._minimap = minimap
            
            # Connect signals
            if minimap:
                minimap.navigationRequested.connect(self._on_minimap_navigation_requested)
                minimap.viewportChanged.connect(self._on_minimap_viewport_changed)
            
            self.emit_state_changed({'minimap_connected': minimap is not None})
            
        except Exception as e:
            self.emit_error(f"Error setting minimap: {str(e)}")
    
    def set_main_canvas(self, canvas) -> None:
        """Set main canvas component."""
        try:
            self._main_canvas = canvas
            
            # Connect canvas signals if available
            if hasattr(canvas, 'zoomChanged'):
                canvas.zoomChanged.connect(self._on_canvas_zoom_changed)
            if hasattr(canvas, 'panChanged'):
                canvas.panChanged.connect(self._on_canvas_pan_changed)
            if hasattr(canvas, 'viewportChanged'):
                canvas.viewportChanged.connect(self._on_canvas_viewport_changed)
            
            self.emit_state_changed({'main_canvas_connected': canvas is not None})
            
        except Exception as e:
            self.emit_error(f"Error setting main canvas: {str(e)}")
    
    def navigate_to_image(self, image_path: str) -> bool:
        """Navigate to specific image."""
        try:
            if not self._image_navigator:
                self.emit_error("Image navigator not connected")
                return False
            
            # Navigate using image navigator
            success = self._image_navigator.navigate_to_file(image_path)
            
            if success:
                self._add_to_history('image_navigation', {'image_path': image_path})
            
            return success
            
        except Exception as e:
            self.emit_error(f"Error navigating to image: {str(e)}")
            return False
    
    def navigate_to_viewport(self, viewport_rect: QRect) -> bool:
        """Navigate to specific viewport."""
        try:
            if not self._main_canvas:
                self.emit_error("Main canvas not connected")
                return False
            
            # Update viewport
            self._current_viewport = viewport_rect
            
            # Apply to main canvas
            if hasattr(self._main_canvas, 'set_viewport'):
                self._main_canvas.set_viewport(viewport_rect)
            
            # Update minimap
            if self._minimap and self._sync_enabled:
                self._minimap.set_viewport(viewport_rect)
            
            self._add_to_history('viewport_navigation', {'viewport': viewport_rect})
            
            self.viewportNavigationChanged.emit(viewport_rect)
            self.emit_state_changed({'current_viewport': viewport_rect})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error navigating to viewport: {str(e)}")
            return False
    
    def navigate_to_point(self, point: QPoint) -> bool:
        """Navigate to specific point."""
        try:
            if not self._main_canvas:
                self.emit_error("Main canvas not connected")
                return False
            
            # Calculate viewport around point
            if hasattr(self._main_canvas, 'get_viewport_size'):
                viewport_size = self._main_canvas.get_viewport_size()
                viewport_rect = QRect(
                    point.x() - viewport_size.width() // 2,
                    point.y() - viewport_size.height() // 2,
                    viewport_size.width(),
                    viewport_size.height()
                )
                
                return self.navigate_to_viewport(viewport_rect)
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error navigating to point: {str(e)}")
            return False
    
    def navigate_next_image(self) -> bool:
        """Navigate to next image."""
        try:
            if not self._image_navigator:
                return False
            
            success = self._image_navigator.navigate_next()
            
            if success:
                self._add_to_history('next_image', {})
            
            return success
            
        except Exception as e:
            self.emit_error(f"Error navigating to next image: {str(e)}")
            return False
    
    def navigate_previous_image(self) -> bool:
        """Navigate to previous image."""
        try:
            if not self._image_navigator:
                return False
            
            success = self._image_navigator.navigate_previous()
            
            if success:
                self._add_to_history('previous_image', {})
            
            return success
            
        except Exception as e:
            self.emit_error(f"Error navigating to previous image: {str(e)}")
            return False
    
    def set_zoom_level(self, zoom_level: float) -> bool:
        """Set zoom level."""
        try:
            self._current_zoom_level = zoom_level
            
            # Apply to main canvas
            if self._main_canvas and hasattr(self._main_canvas, 'set_zoom_level'):
                self._main_canvas.set_zoom_level(zoom_level)
            
            # Update minimap
            if self._minimap and self._sync_enabled:
                self._minimap.set_zoom_level(zoom_level)
            
            self._add_to_history('zoom', {'zoom_level': zoom_level})
            
            self.emit_state_changed({'current_zoom_level': zoom_level})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting zoom level: {str(e)}")
            return False
    
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._current_zoom_level
    
    def set_pan_offset(self, offset: QPoint) -> bool:
        """Set pan offset."""
        try:
            self._current_pan_offset = offset
            
            # Apply to main canvas
            if self._main_canvas and hasattr(self._main_canvas, 'set_pan_offset'):
                self._main_canvas.set_pan_offset(offset)
            
            self._add_to_history('pan', {'pan_offset': offset})
            
            self.emit_state_changed({'current_pan_offset': offset})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting pan offset: {str(e)}")
            return False
    
    def get_pan_offset(self) -> QPoint:
        """Get current pan offset."""
        return self._current_pan_offset
    
    def fit_to_window(self) -> bool:
        """Fit image to window."""
        try:
            if not self._main_canvas:
                return False
            
            if hasattr(self._main_canvas, 'fit_to_window'):
                self._main_canvas.fit_to_window()
                self._add_to_history('fit_to_window', {})
                return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error fitting to window: {str(e)}")
            return False
    
    def reset_view(self) -> bool:
        """Reset view to default."""
        try:
            if not self._main_canvas:
                return False
            
            if hasattr(self._main_canvas, 'reset_view'):
                self._main_canvas.reset_view()
                self._add_to_history('reset_view', {})
                return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error resetting view: {str(e)}")
            return False
    
    def go_back(self) -> bool:
        """Go back in navigation history."""
        try:
            if self._history_index <= 0:
                return False
            
            self._history_index -= 1
            entry = self._navigation_history[self._history_index]
            
            return self._apply_history_entry(entry)
            
        except Exception as e:
            self.emit_error(f"Error going back: {str(e)}")
            return False
    
    def go_forward(self) -> bool:
        """Go forward in navigation history."""
        try:
            if self._history_index >= len(self._navigation_history) - 1:
                return False
            
            self._history_index += 1
            entry = self._navigation_history[self._history_index]
            
            return self._apply_history_entry(entry)
            
        except Exception as e:
            self.emit_error(f"Error going forward: {str(e)}")
            return False
    
    def can_go_back(self) -> bool:
        """Check if can go back."""
        return self._history_index > 0
    
    def can_go_forward(self) -> bool:
        """Check if can go forward."""
        return self._history_index < len(self._navigation_history) - 1
    
    def clear_history(self) -> None:
        """Clear navigation history."""
        self._navigation_history.clear()
        self._history_index = -1
        self.emit_state_changed({'history_cleared': True})
    
    def set_sync_enabled(self, enabled: bool) -> None:
        """Enable/disable component synchronization."""
        self._sync_enabled = enabled
        self.emit_state_changed({'sync_enabled': enabled})
    
    def is_sync_enabled(self) -> bool:
        """Check if synchronization is enabled."""
        return self._sync_enabled
    
    def set_auto_fit_enabled(self, enabled: bool) -> None:
        """Enable/disable auto fit."""
        self._auto_fit_enabled = enabled
        self.emit_state_changed({'auto_fit_enabled': enabled})
    
    def is_auto_fit_enabled(self) -> bool:
        """Check if auto fit is enabled."""
        return self._auto_fit_enabled
    
    def set_smooth_navigation(self, enabled: bool) -> None:
        """Enable/disable smooth navigation."""
        self._smooth_navigation = enabled
        self.emit_state_changed({'smooth_navigation': enabled})
    
    def is_smooth_navigation_enabled(self) -> bool:
        """Check if smooth navigation is enabled."""
        return self._smooth_navigation
    
    def set_navigation_speed(self, speed: float) -> None:
        """Set navigation speed."""
        self._navigation_speed = max(0.1, speed)
        self.emit_state_changed({'navigation_speed': speed})
    
    def get_navigation_speed(self) -> float:
        """Get navigation speed."""
        return self._navigation_speed
    
    def set_image_changed_callback(self, callback: Callable[[str], None]) -> None:
        """Set image changed callback."""
        self._image_changed_callback = callback
    
    def set_viewport_changed_callback(self, callback: Callable[[QRect], None]) -> None:
        """Set viewport changed callback."""
        self._viewport_changed_callback = callback
    
    def get_current_image_path(self) -> Optional[str]:
        """Get current image path."""
        return self._current_image_path
    
    def get_current_viewport(self) -> QRect:
        """Get current viewport."""
        return self._current_viewport
    
    def get_navigation_state(self) -> Dict[str, Any]:
        """Get complete navigation state."""
        return {
            'current_image_path': self._current_image_path,
            'current_viewport': self._current_viewport,
            'current_zoom_level': self._current_zoom_level,
            'current_pan_offset': self._current_pan_offset,
            'sync_enabled': self._sync_enabled,
            'auto_fit_enabled': self._auto_fit_enabled,
            'smooth_navigation': self._smooth_navigation,
            'navigation_speed': self._navigation_speed,
            'can_go_back': self.can_go_back(),
            'can_go_forward': self.can_go_forward(),
            'history_size': len(self._navigation_history),
            'history_index': self._history_index
        }
    
    def get_navigation_statistics(self) -> Dict[str, Any]:
        """Get navigation statistics."""
        return {
            'total_navigations': len(self._navigation_history),
            'current_history_position': self._history_index,
            'components_connected': {
                'image_navigator': self._image_navigator is not None,
                'minimap': self._minimap is not None,
                'main_canvas': self._main_canvas is not None
            },
            'sync_enabled': self._sync_enabled,
            'updating': self._updating,
            'pending_updates': len(self._pending_updates)
        }
    
    def _on_image_changed(self, image_path: str) -> None:
        """Handle image changed from image navigator."""
        try:
            self._current_image_path = image_path
            
            # Update minimap
            if self._minimap and self._sync_enabled:
                # Load image for minimap
                if hasattr(self._minimap, 'set_image'):
                    # Get image from main canvas or load separately
                    if self._main_canvas and hasattr(self._main_canvas, 'get_image'):
                        image = self._main_canvas.get_image()
                        if image:
                            self._minimap.set_image(image)
            
            # Auto fit if enabled
            if self._auto_fit_enabled:
                self.fit_to_window()
            
            # Call callback
            if self._image_changed_callback:
                self._image_changed_callback(image_path)
            
            self.imageNavigationChanged.emit(image_path)
            self.emit_state_changed({'current_image_path': image_path})
            
        except Exception as e:
            self.emit_error(f"Error handling image changed: {str(e)}")
    
    def _on_image_load_failed(self, error_message: str) -> None:
        """Handle image load failed from image navigator."""
        self.emit_error(f"Image load failed: {error_message}")
    
    def _on_minimap_navigation_requested(self, point: QPoint) -> None:
        """Handle navigation request from minimap."""
        try:
            self.navigate_to_point(point)
            self.minimapNavigationChanged.emit(point)
            
        except Exception as e:
            self.emit_error(f"Error handling minimap navigation: {str(e)}")
    
    def _on_minimap_viewport_changed(self, viewport: QRect) -> None:
        """Handle viewport changed from minimap."""
        try:
            if self._sync_enabled:
                self.navigate_to_viewport(viewport)
                
        except Exception as e:
            self.emit_error(f"Error handling minimap viewport change: {str(e)}")
    
    def _on_canvas_zoom_changed(self, zoom_level: float) -> None:
        """Handle zoom changed from main canvas."""
        try:
            self._current_zoom_level = zoom_level
            
            # Update minimap
            if self._minimap and self._sync_enabled:
                self._minimap.set_zoom_level(zoom_level)
            
            self.emit_state_changed({'current_zoom_level': zoom_level})
            
        except Exception as e:
            self.emit_error(f"Error handling canvas zoom change: {str(e)}")
    
    def _on_canvas_pan_changed(self, pan_offset: QPoint) -> None:
        """Handle pan changed from main canvas."""
        try:
            self._current_pan_offset = pan_offset
            self.emit_state_changed({'current_pan_offset': pan_offset})
            
        except Exception as e:
            self.emit_error(f"Error handling canvas pan change: {str(e)}")
    
    def _on_canvas_viewport_changed(self, viewport: QRect) -> None:
        """Handle viewport changed from main canvas."""
        try:
            self._current_viewport = viewport
            
            # Update minimap
            if self._minimap and self._sync_enabled:
                self._minimap.set_viewport(viewport)
            
            # Call callback
            if self._viewport_changed_callback:
                self._viewport_changed_callback(viewport)
            
            self.emit_state_changed({'current_viewport': viewport})
            
        except Exception as e:
            self.emit_error(f"Error handling canvas viewport change: {str(e)}")
    
    def _disconnect_image_navigator(self) -> None:
        """Disconnect image navigator signals."""
        try:
            if self._image_navigator:
                self._image_navigator.imageChanged.disconnect(self._on_image_changed)
                self._image_navigator.imageLoadFailed.disconnect(self._on_image_load_failed)
                
        except Exception as e:
            self.emit_error(f"Error disconnecting image navigator: {str(e)}")
    
    def _disconnect_minimap(self) -> None:
        """Disconnect minimap signals."""
        try:
            if self._minimap:
                self._minimap.navigationRequested.disconnect(self._on_minimap_navigation_requested)
                self._minimap.viewportChanged.disconnect(self._on_minimap_viewport_changed)
                
        except Exception as e:
            self.emit_error(f"Error disconnecting minimap: {str(e)}")
    
    def _add_to_history(self, action: str, data: Dict[str, Any]) -> None:
        """Add entry to navigation history."""
        try:
            import time
            
            entry = {
                'action': action,
                'data': data,
                'timestamp': time.time(),
                'image_path': self._current_image_path,
                'viewport': self._current_viewport,
                'zoom_level': self._current_zoom_level,
                'pan_offset': self._current_pan_offset
            }
            
            # Remove any entries after current index
            if self._history_index < len(self._navigation_history) - 1:
                self._navigation_history = self._navigation_history[:self._history_index + 1]
            
            # Add new entry
            self._navigation_history.append(entry)
            self._history_index += 1
            
            # Limit history size
            if len(self._navigation_history) > self._max_history_size:
                self._navigation_history.pop(0)
                self._history_index -= 1
            
            self.emit_state_changed({
                'history_size': len(self._navigation_history),
                'history_index': self._history_index
            })
            
        except Exception as e:
            self.emit_error(f"Error adding to history: {str(e)}")
    
    def _apply_history_entry(self, entry: Dict[str, Any]) -> bool:
        """Apply navigation history entry."""
        try:
            # Restore state
            if 'image_path' in entry and entry['image_path'] != self._current_image_path:
                self.navigate_to_image(entry['image_path'])
            
            if 'viewport' in entry:
                self.navigate_to_viewport(entry['viewport'])
            
            if 'zoom_level' in entry:
                self.set_zoom_level(entry['zoom_level'])
            
            if 'pan_offset' in entry:
                self.set_pan_offset(entry['pan_offset'])
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error applying history entry: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Disconnect components
            self._disconnect_image_navigator()
            self._disconnect_minimap()
            
            # Clear references
            self._image_navigator = None
            self._minimap = None
            self._main_canvas = None
            
            # Clear history
            self._navigation_history.clear()
            
        except Exception as e:
            self.emit_error(f"Error in cleanup: {str(e)}")
        
        super().cleanup()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get navigation controller statistics."""
        stats = super().get_statistics()
        stats.update({
            'sync_enabled': self._sync_enabled,
            'auto_fit_enabled': self._auto_fit_enabled,
            'smooth_navigation': self._smooth_navigation,
            'navigation_speed': self._navigation_speed,
            'max_history_size': self._max_history_size,
            'update_throttle': self._update_throttle,
            'batch_updates': self._batch_updates,
            'update_delay': self._update_delay,
            'navigation_state': self.get_navigation_state(),
            'navigation_statistics': self.get_navigation_statistics()
        })
        return stats