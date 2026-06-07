"""
Minimap - Overview navigation widget for large images

This module provides a minimap widget for navigating large images with
viewport visualization, click-to-navigate, and zoom indicators.
"""

import time
from typing import Optional, Tuple, Dict, Any, List
from ..base_protocols import BaseComponent, QWidget, QPixmap, QRect, QPoint, QSize, QColor, QPainter, QBrush, QPen
from .base_navigator import BaseNavigator


class Minimap(BaseNavigator, QWidget):
    """Minimap widget for image navigation."""
    
    # Minimap signals
    viewportChanged = pyqtSignal(object)  # QRect
    navigationRequested = pyqtSignal(object)  # QPoint
    minimapResized = pyqtSignal(object)  # QSize
    
    def __init__(self, name: str = "minimap", version: str = "1.0.0", parent=None):
        BaseNavigator.__init__(self, name, version)
        QWidget.__init__(self, parent)
        
        # Minimap configuration
        self._minimap_size: QSize = QSize(200, 200)
        self._border_width: int = 2
        self._border_color: QColor = QColor(128, 128, 128)
        self._background_color: QColor = QColor(240, 240, 240)
        
        # Viewport configuration
        self._viewport_color: QColor = QColor(255, 0, 0, 128)
        self._viewport_border_color: QColor = QColor(255, 0, 0)
        self._viewport_border_width: int = 2
        self._viewport_visible: bool = True
        
        # Image and viewport state
        self._full_image: Optional[QPixmap] = None
        self._minimap_image: Optional[QPixmap] = None
        self._image_rect: QRect = QRect()
        self._viewport_rect: QRect = QRect()
        self._scale_factor: float = 1.0
        
        # Navigation state
        self._dragging: bool = False
        self._drag_start_pos: QPoint = QPoint()
        self._drag_offset: QPoint = QPoint()
        
        # Interaction settings
        self._click_to_navigate: bool = True
        self._drag_to_navigate: bool = True
        self._show_zoom_level: bool = True
        self._show_coordinates: bool = False
        
        # Zoom indicators
        self._zoom_level: float = 1.0
        self._zoom_text_color: QColor = QColor(0, 0, 0)
        self._zoom_text_size: int = 12
        self._zoom_text_margin: int = 5
        
        # Performance settings
        self._update_throttle: float = 0.016  # 60 FPS
        self._last_update_time: float = 0.0
        self._pending_update: bool = False
        
        # Widget setup
        self.setFixedSize(self._minimap_size)
        self.setMouseTracking(True)
        
        # Style
        self.setStyleSheet("""
            Minimap {
                border: 2px solid #808080;
                background-color: #f0f0f0;
            }
        """)
    
    def initialize(self, **kwargs) -> bool:
        """Initialize minimap."""
        self._minimap_size = kwargs.get('minimap_size', QSize(200, 200))
        self._border_width = kwargs.get('border_width', 2)
        self._click_to_navigate = kwargs.get('click_to_navigate', True)
        self._drag_to_navigate = kwargs.get('drag_to_navigate', True)
        self._show_zoom_level = kwargs.get('show_zoom_level', True)
        self._show_coordinates = kwargs.get('show_coordinates', False)
        self._update_throttle = kwargs.get('update_throttle', 0.016)
        
        # Set colors if provided
        if 'viewport_color' in kwargs:
            self._viewport_color = kwargs['viewport_color']
        if 'border_color' in kwargs:
            self._border_color = kwargs['border_color']
        if 'background_color' in kwargs:
            self._background_color = kwargs['background_color']
        
        # Apply size
        self.setFixedSize(self._minimap_size)
        
        return super().initialize(**kwargs)
    
    def set_image(self, image: QPixmap) -> None:
        """Set the full image for minimap."""
        try:
            self._full_image = image
            
            if not image.isNull():
                # Calculate scale factor to fit image in minimap
                image_size = image.size()
                widget_size = self.size()
                
                # Account for border
                available_size = QSize(
                    widget_size.width() - 2 * self._border_width,
                    widget_size.height() - 2 * self._border_width
                )
                
                scale_x = available_size.width() / image_size.width()
                scale_y = available_size.height() / image_size.height()
                self._scale_factor = min(scale_x, scale_y)
                
                # Calculate image rect within minimap
                scaled_width = int(image_size.width() * self._scale_factor)
                scaled_height = int(image_size.height() * self._scale_factor)
                
                x = (widget_size.width() - scaled_width) // 2
                y = (widget_size.height() - scaled_height) // 2
                
                self._image_rect = QRect(x, y, scaled_width, scaled_height)
                
                # Create scaled minimap image
                self._minimap_image = image.scaled(
                    scaled_width, scaled_height,
                    aspectRatioMode=1,  # Qt.KeepAspectRatio
                    transformMode=1     # Qt.SmoothTransformation
                )
            else:
                self._minimap_image = None
                self._image_rect = QRect()
                self._scale_factor = 1.0
            
            self._schedule_update()
            
        except Exception as e:
            self.emit_error(f"Error setting image: {str(e)}")
    
    def set_viewport(self, viewport_rect: QRect) -> None:
        """Set the viewport rectangle in image coordinates."""
        try:
            if self._full_image is None or self._full_image.isNull():
                return
            
            # Convert viewport from image coordinates to minimap coordinates
            minimap_viewport = self._image_to_minimap_rect(viewport_rect)
            
            if minimap_viewport != self._viewport_rect:
                self._viewport_rect = minimap_viewport
                self._schedule_update()
                
        except Exception as e:
            self.emit_error(f"Error setting viewport: {str(e)}")
    
    def set_zoom_level(self, zoom_level: float) -> None:
        """Set zoom level for display."""
        self._zoom_level = zoom_level
        if self._show_zoom_level:
            self._schedule_update()
    
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_level
    
    def set_viewport_visible(self, visible: bool) -> None:
        """Set viewport visibility."""
        self._viewport_visible = visible
        self._schedule_update()
    
    def is_viewport_visible(self) -> bool:
        """Check if viewport is visible."""
        return self._viewport_visible
    
    def set_click_to_navigate(self, enabled: bool) -> None:
        """Enable/disable click to navigate."""
        self._click_to_navigate = enabled
        self.emit_state_changed({'click_to_navigate': enabled})
    
    def is_click_to_navigate_enabled(self) -> bool:
        """Check if click to navigate is enabled."""
        return self._click_to_navigate
    
    def set_drag_to_navigate(self, enabled: bool) -> None:
        """Enable/disable drag to navigate."""
        self._drag_to_navigate = enabled
        self.emit_state_changed({'drag_to_navigate': enabled})
    
    def is_drag_to_navigate_enabled(self) -> bool:
        """Check if drag to navigate is enabled."""
        return self._drag_to_navigate
    
    def set_show_zoom_level(self, show: bool) -> None:
        """Set whether to show zoom level."""
        self._show_zoom_level = show
        self._schedule_update()
    
    def is_show_zoom_level_enabled(self) -> bool:
        """Check if zoom level is shown."""
        return self._show_zoom_level
    
    def set_show_coordinates(self, show: bool) -> None:
        """Set whether to show coordinates."""
        self._show_coordinates = show
        self._schedule_update()
    
    def is_show_coordinates_enabled(self) -> bool:
        """Check if coordinates are shown."""
        return self._show_coordinates
    
    def set_viewport_color(self, color: QColor) -> None:
        """Set viewport color."""
        self._viewport_color = color
        self._schedule_update()
    
    def get_viewport_color(self) -> QColor:
        """Get viewport color."""
        return self._viewport_color
    
    def set_border_color(self, color: QColor) -> None:
        """Set border color."""
        self._border_color = color
        self._schedule_update()
    
    def get_border_color(self) -> QColor:
        """Get border color."""
        return self._border_color
    
    def set_background_color(self, color: QColor) -> None:
        """Set background color."""
        self._background_color = color
        self._schedule_update()
    
    def get_background_color(self) -> QColor:
        """Get background color."""
        return self._background_color
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if not self._click_to_navigate and not self._drag_to_navigate:
            return
        
        try:
            if event.button() == 1:  # Qt.LeftButton
                pos = event.pos()
                
                # Check if click is within image area
                if self._image_rect.contains(pos):
                    if self._click_to_navigate:
                        # Navigate to clicked position
                        self._navigate_to_position(pos)
                    
                    if self._drag_to_navigate:
                        # Start drag
                        self._dragging = True
                        self._drag_start_pos = pos
                        self._drag_offset = QPoint(
                            pos.x() - self._viewport_rect.center().x(),
                            pos.y() - self._viewport_rect.center().y()
                        )
                        
        except Exception as e:
            self.emit_error(f"Error in mouse press: {str(e)}")
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events."""
        if not self._dragging or not self._drag_to_navigate:
            return
        
        try:
            pos = event.pos()
            
            # Calculate new viewport center
            new_center = QPoint(
                pos.x() - self._drag_offset.x(),
                pos.y() - self._drag_offset.y()
            )
            
            # Navigate to new position
            self._navigate_to_position(new_center)
            
        except Exception as e:
            self.emit_error(f"Error in mouse move: {str(e)}")
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release events."""
        if event.button() == 1:  # Qt.LeftButton
            self._dragging = False
    
    def paintEvent(self, event) -> None:
        """Paint the minimap."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw background
            painter.fillRect(self.rect(), QBrush(self._background_color))
            
            # Draw border
            if self._border_width > 0:
                pen = QPen(self._border_color, self._border_width)
                painter.setPen(pen)
                painter.drawRect(self.rect())
            
            # Draw image
            if self._minimap_image and not self._minimap_image.isNull():
                painter.drawPixmap(self._image_rect, self._minimap_image)
            
            # Draw viewport
            if self._viewport_visible and not self._viewport_rect.isEmpty():
                self._draw_viewport(painter)
            
            # Draw zoom level
            if self._show_zoom_level:
                self._draw_zoom_level(painter)
            
            # Draw coordinates
            if self._show_coordinates:
                self._draw_coordinates(painter)
            
        except Exception as e:
            self.emit_error(f"Error in paint event: {str(e)}")
    
    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        try:
            new_size = event.size()
            self._minimap_size = new_size
            
            # Recreate minimap image with new size
            if self._full_image and not self._full_image.isNull():
                self.set_image(self._full_image)
            
            self.minimapResized.emit(new_size)
            
        except Exception as e:
            self.emit_error(f"Error in resize event: {str(e)}")
    
    def _navigate_to_position(self, pos: QPoint) -> None:
        """Navigate to position in minimap coordinates."""
        try:
            if self._full_image is None or self._full_image.isNull():
                return
            
            # Convert minimap coordinates to image coordinates
            image_pos = self._minimap_to_image_point(pos)
            
            # Emit navigation request
            self.navigationRequested.emit(image_pos)
            
        except Exception as e:
            self.emit_error(f"Error navigating to position: {str(e)}")
    
    def _draw_viewport(self, painter: QPainter) -> None:
        """Draw viewport rectangle."""
        try:
            # Draw filled rectangle
            brush = QBrush(self._viewport_color)
            painter.fillRect(self._viewport_rect, brush)
            
            # Draw border
            pen = QPen(self._viewport_border_color, self._viewport_border_width)
            painter.setPen(pen)
            painter.drawRect(self._viewport_rect)
            
        except Exception as e:
            self.emit_error(f"Error drawing viewport: {str(e)}")
    
    def _draw_zoom_level(self, painter: QPainter) -> None:
        """Draw zoom level text."""
        try:
            from PyQt5.QtGui import QFont
            from PyQt5.QtCore import Qt
            
            # Set font
            font = QFont("Arial", self._zoom_text_size)
            painter.setFont(font)
            
            # Set color
            pen = QPen(self._zoom_text_color)
            painter.setPen(pen)
            
            # Draw zoom text
            zoom_text = f"{self._zoom_level:.1f}x"
            text_rect = QRect(
                self._zoom_text_margin,
                self._zoom_text_margin,
                100,
                self._zoom_text_size + 4
            )
            
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop, zoom_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing zoom level: {str(e)}")
    
    def _draw_coordinates(self, painter: QPainter) -> None:
        """Draw coordinate information."""
        try:
            from PyQt5.QtGui import QFont
            from PyQt5.QtCore import Qt
            
            if self._viewport_rect.isEmpty():
                return
            
            # Set font
            font = QFont("Arial", self._zoom_text_size - 2)
            painter.setFont(font)
            
            # Set color
            pen = QPen(self._zoom_text_color)
            painter.setPen(pen)
            
            # Get viewport center in image coordinates
            viewport_center = self._minimap_to_image_point(self._viewport_rect.center())
            
            # Draw coordinate text
            coord_text = f"({viewport_center.x()}, {viewport_center.y()})"
            text_rect = QRect(
                self._zoom_text_margin,
                self.height() - self._zoom_text_size - self._zoom_text_margin - 4,
                150,
                self._zoom_text_size + 4
            )
            
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop, coord_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing coordinates: {str(e)}")
    
    def _image_to_minimap_rect(self, image_rect: QRect) -> QRect:
        """Convert rectangle from image coordinates to minimap coordinates."""
        try:
            if self._scale_factor == 0:
                return QRect()
            
            # Scale rectangle
            scaled_rect = QRect(
                int(image_rect.x() * self._scale_factor),
                int(image_rect.y() * self._scale_factor),
                int(image_rect.width() * self._scale_factor),
                int(image_rect.height() * self._scale_factor)
            )
            
            # Translate to minimap coordinates
            minimap_rect = QRect(
                scaled_rect.x() + self._image_rect.x(),
                scaled_rect.y() + self._image_rect.y(),
                scaled_rect.width(),
                scaled_rect.height()
            )
            
            return minimap_rect
            
        except Exception as e:
            self.emit_error(f"Error converting image to minimap rect: {str(e)}")
            return QRect()
    
    def _minimap_to_image_point(self, minimap_point: QPoint) -> QPoint:
        """Convert point from minimap coordinates to image coordinates."""
        try:
            if self._scale_factor == 0:
                return QPoint()
            
            # Translate from minimap coordinates
            translated_point = QPoint(
                minimap_point.x() - self._image_rect.x(),
                minimap_point.y() - self._image_rect.y()
            )
            
            # Scale to image coordinates
            image_point = QPoint(
                int(translated_point.x() / self._scale_factor),
                int(translated_point.y() / self._scale_factor)
            )
            
            return image_point
            
        except Exception as e:
            self.emit_error(f"Error converting minimap to image point: {str(e)}")
            return QPoint()
    
    def _schedule_update(self) -> None:
        """Schedule widget update with throttling."""
        try:
            current_time = time.time()
            
            if current_time - self._last_update_time >= self._update_throttle:
                self.update()
                self._last_update_time = current_time
                self._pending_update = False
            elif not self._pending_update:
                # Schedule delayed update
                self._pending_update = True
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(int(self._update_throttle * 1000), self._delayed_update)
                
        except Exception as e:
            self.emit_error(f"Error scheduling update: {str(e)}")
    
    def _delayed_update(self) -> None:
        """Perform delayed update."""
        try:
            if self._pending_update:
                self.update()
                self._last_update_time = time.time()
                self._pending_update = False
                
        except Exception as e:
            self.emit_error(f"Error in delayed update: {str(e)}")
    
    def get_minimap_info(self) -> Dict[str, Any]:
        """Get minimap information."""
        return {
            'minimap_size': (self._minimap_size.width(), self._minimap_size.height()),
            'scale_factor': self._scale_factor,
            'has_image': self._full_image is not None and not self._full_image.isNull(),
            'image_rect': (self._image_rect.x(), self._image_rect.y(), 
                          self._image_rect.width(), self._image_rect.height()),
            'viewport_rect': (self._viewport_rect.x(), self._viewport_rect.y(),
                             self._viewport_rect.width(), self._viewport_rect.height()),
            'viewport_visible': self._viewport_visible,
            'zoom_level': self._zoom_level,
            'dragging': self._dragging
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get minimap statistics."""
        stats = super().get_statistics()
        stats.update({
            'minimap_size': (self._minimap_size.width(), self._minimap_size.height()),
            'border_width': self._border_width,
            'viewport_visible': self._viewport_visible,
            'click_to_navigate': self._click_to_navigate,
            'drag_to_navigate': self._drag_to_navigate,
            'show_zoom_level': self._show_zoom_level,
            'show_coordinates': self._show_coordinates,
            'update_throttle': self._update_throttle,
            'scale_factor': self._scale_factor,
            'zoom_level': self._zoom_level,
            'minimap_info': self.get_minimap_info()
        })
        return stats