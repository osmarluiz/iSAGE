"""
Interactive Minimap Widget - Professional overview thumbnail with viewport navigation

This component provides the interactive minimap that appears in the status panel,
matching the functioning system exactly with viewport indication and click navigation.
"""

import logging
from typing import Optional, Tuple
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QImage, QColor

logger = logging.getLogger(__name__)


class InteractiveMinimap(QLabel):
    """
    Professional interactive minimap matching the functioning system exactly.
    
    Features:
    - Thumbnail overview of full image
    - Red viewport rectangle showing current view
    - Click navigation to different image areas
    - Real-time viewport updates with zoom/pan
    - Professional styling matching status panel
    - 180x120px size (3:2 aspect ratio)
    - Smooth scaling with aspect ratio preservation
    """
    
    # Signals
    viewChanged = pyqtSignal(int, int)  # pan_x, pan_y offsets
    navigationRequested = pyqtSignal(float, float)  # click_x, click_y in image coordinates
    
    def __init__(self, parent=None, name: str = "interactive_minimap", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # Minimap sizing - matches functioning system exactly
        self.setFixedSize(180, 120)  # Professional 3:2 aspect ratio
        self.setStyleSheet("""
            QLabel {
                background: #374151;
                border: 2px solid #4b5563;
                border-radius: 6px;
                color: #9ca3af;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        
        # State variables
        self.full_image = None  # Original full-resolution image
        self.canvas_widget_size = None  # Current canvas widget size
        self.canvas_zoom_factor = 1.0  # Current zoom factor
        self.canvas_pan_offset_x = 0  # Current pan offset X
        self.canvas_pan_offset_y = 0  # Current pan offset Y
        self.scaled_image_bounds = None  # Bounds of scaled image in minimap
        
        # Initial state
        self.setText("Mini-Map")
        self.setAlignment(Qt.AlignCenter)
        
        logger.info(f"InteractiveMinimap '{name}' v{version} initialized")
    
    def update_image(self, image):
        """Update the minimap with a new image."""
        # Handle both QPixmap and PIL Image
        if image is not None:
            if isinstance(image, QPixmap) and not image.isNull():
                self.full_image = image
                logger.debug(f"Minimap image updated: {image.width()}x{image.height()}")
                self.update_minimap()
            else:
                logger.warning(f"Minimap received non-QPixmap image: {type(image)}")
                self.full_image = None
                self.clear_minimap()
        else:
            self.full_image = None
            self.clear_minimap()
    
    def update_view(self, widget_size: QSize, zoom_factor: float, pan_offset_x: int, pan_offset_y: int):
        """Update the view rectangle based on canvas state."""
        self.canvas_widget_size = widget_size
        self.canvas_zoom_factor = zoom_factor
        self.canvas_pan_offset_x = pan_offset_x
        self.canvas_pan_offset_y = pan_offset_y
        
        logger.debug(f"Minimap view updated: zoom={zoom_factor:.2f}, pan=({pan_offset_x}, {pan_offset_y})")
        self.update_minimap()
    
    def update_minimap(self):
        """Redraw the minimap with current image and view rectangle."""
        if not self.full_image or self.full_image.isNull():
            self.clear_minimap()
            return
        
        # Create minimap pixmap
        minimap_size = self.size()
        pixmap = QPixmap(minimap_size)
        pixmap.fill(QColor(55, 65, 81))  # Match background color
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        try:
            # Scale image to fit minimap while preserving aspect ratio
            scaled_image = self.full_image.scaled(
                minimap_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # Center the scaled image in the minimap
            x_offset = (minimap_size.width() - scaled_image.width()) // 2
            y_offset = (minimap_size.height() - scaled_image.height()) // 2
            
            # Store scaled image bounds for click handling
            self.scaled_image_bounds = {
                'x': x_offset,
                'y': y_offset,
                'width': scaled_image.width(),
                'height': scaled_image.height()
            }
            
            # Draw the scaled image
            painter.drawPixmap(x_offset, y_offset, scaled_image)
            
            # Draw view rectangle if we have canvas state
            if (self.canvas_widget_size and 
                self.canvas_widget_size.isValid() and 
                scaled_image.size().isValid()):
                self.draw_view_rectangle(painter, scaled_image, x_offset, y_offset)
            
        except Exception as e:
            logger.error(f"Error updating minimap: {e}")
            painter.setPen(QPen(QColor(239, 68, 68), 1))
            painter.drawText(minimap_size.rect(), Qt.AlignCenter, "Error")
        
        finally:
            painter.end()
        
        self.setPixmap(pixmap)
    
    def draw_view_rectangle(self, painter: QPainter, scaled_image: QPixmap, img_x_offset: int, img_y_offset: int):
        """Draw the current view rectangle on the minimap."""
        try:
            # Calculate scale factors from original to minimap
            scale_x = scaled_image.width() / self.full_image.width()
            scale_y = scaled_image.height() / self.full_image.height()
            
            # Calculate visible area dimensions in original image coordinates
            canvas_width = self.canvas_widget_size.width()
            canvas_height = self.canvas_widget_size.height()
            
            # Account for zoom - higher zoom means smaller visible area
            visible_width = canvas_width / self.canvas_zoom_factor
            visible_height = canvas_height / self.canvas_zoom_factor
            
            # Calculate view rectangle position in original image coordinates
            # Center the view when no panning has occurred
            view_center_x = self.full_image.width() / 2
            view_center_y = self.full_image.height() / 2
            
            # Apply pan offsets (negative pan means view moved in that direction)
            view_x = view_center_x - visible_width / 2 - (self.canvas_pan_offset_x / self.canvas_zoom_factor)
            view_y = view_center_y - visible_height / 2 - (self.canvas_pan_offset_y / self.canvas_zoom_factor)
            
            # Convert to minimap coordinates
            minimap_rect_x = img_x_offset + view_x * scale_x
            minimap_rect_y = img_y_offset + view_y * scale_y
            minimap_rect_w = visible_width * scale_x
            minimap_rect_h = visible_height * scale_y
            
            # Clamp rectangle to image bounds
            minimap_rect_x = max(img_x_offset, min(minimap_rect_x, img_x_offset + scaled_image.width()))
            minimap_rect_y = max(img_y_offset, min(minimap_rect_y, img_y_offset + scaled_image.height()))
            minimap_rect_w = min(minimap_rect_w, img_x_offset + scaled_image.width() - minimap_rect_x)
            minimap_rect_h = min(minimap_rect_h, img_y_offset + scaled_image.height() - minimap_rect_y)
            
            # Draw view rectangle with professional styling
            painter.setPen(QPen(QColor(239, 68, 68), 2))  # Red border
            painter.setBrush(QBrush(Qt.transparent))  # Transparent fill
            painter.drawRect(
                int(minimap_rect_x), 
                int(minimap_rect_y), 
                int(minimap_rect_w), 
                int(minimap_rect_h)
            )
            
            # Optional: Add subtle inner highlight
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))  # Semi-transparent white
            painter.drawRect(
                int(minimap_rect_x + 1), 
                int(minimap_rect_y + 1), 
                int(minimap_rect_w - 2), 
                int(minimap_rect_h - 2)
            )
            
        except Exception as e:
            logger.error(f"Error drawing view rectangle: {e}")
    
    def clear_minimap(self):
        """Clear the minimap and show placeholder text."""
        self.clear()
        self.setText("Mini-Map")
        self.scaled_image_bounds = None
        logger.debug("Minimap cleared")
    
    def mousePressEvent(self, event):
        """Handle clicks on minimap for navigation."""
        if (not self.full_image or 
            not self.canvas_widget_size or 
            not self.scaled_image_bounds):
            return
        
        try:
            # Get click position
            click_x = event.x()
            click_y = event.y()
            
            # Check if click is within the scaled image bounds
            bounds = self.scaled_image_bounds
            if (click_x < bounds['x'] or click_x > bounds['x'] + bounds['width'] or
                click_y < bounds['y'] or click_y > bounds['y'] + bounds['height']):
                return  # Click outside image area
            
            # Convert click position to scaled image coordinates
            relative_x = click_x - bounds['x']
            relative_y = click_y - bounds['y']
            
            # Convert to original image coordinates
            scale_x = self.full_image.width() / bounds['width']
            scale_y = self.full_image.height() / bounds['height']
            
            orig_click_x = relative_x * scale_x
            orig_click_y = relative_y * scale_y
            
            # Calculate new pan offsets to center the view on the clicked point
            canvas_width = self.canvas_widget_size.width()
            canvas_height = self.canvas_widget_size.height()
            
            # Calculate visible area dimensions
            visible_width = canvas_width / self.canvas_zoom_factor
            visible_height = canvas_height / self.canvas_zoom_factor
            
            # Calculate desired view center (clicked point)
            desired_center_x = orig_click_x
            desired_center_y = orig_click_y
            
            # Calculate new pan offsets
            image_center_x = self.full_image.width() / 2
            image_center_y = self.full_image.height() / 2
            
            new_pan_x = -(desired_center_x - image_center_x) * self.canvas_zoom_factor
            new_pan_y = -(desired_center_y - image_center_y) * self.canvas_zoom_factor
            
            # Clamp pan offsets to prevent showing areas outside the image
            max_pan_x = max(0, (self.full_image.width() * self.canvas_zoom_factor - canvas_width) / 2)
            max_pan_y = max(0, (self.full_image.height() * self.canvas_zoom_factor - canvas_height) / 2)
            
            new_pan_x = max(-max_pan_x, min(max_pan_x, new_pan_x))
            new_pan_y = max(-max_pan_y, min(max_pan_y, new_pan_y))
            
            logger.info(f"Minimap navigation: click at ({orig_click_x:.0f}, {orig_click_y:.0f}) -> pan ({new_pan_x:.0f}, {new_pan_y:.0f})")
            
            # Emit navigation signal
            self.viewChanged.emit(int(new_pan_x), int(new_pan_y))
            self.navigationRequested.emit(orig_click_x, orig_click_y)
            
        except Exception as e:
            logger.error(f"Error handling minimap click: {e}")
    
    # Public API methods
    
    def set_image(self, image: QPixmap):
        """Set the image for the minimap."""
        self.update_image(image)
    
    def set_view_state(self, widget_size: QSize, zoom: float, pan_x: int, pan_y: int):
        """Set the current view state."""
        self.update_view(widget_size, zoom, pan_x, pan_y)
    
    def reset_view(self):
        """Reset minimap to show full image."""
        if self.full_image:
            self.canvas_zoom_factor = 1.0
            self.canvas_pan_offset_x = 0
            self.canvas_pan_offset_y = 0
            self.update_minimap()
    
    def get_minimap_size(self) -> QSize:
        """Get the fixed minimap size."""
        return QSize(180, 120)  # Professional 3:2 aspect ratio
    
    def has_image(self) -> bool:
        """Check if minimap has an image loaded."""
        return self.full_image is not None and not self.full_image.isNull()
    
    def get_view_info(self) -> dict:
        """Get current view information."""
        return {
            'zoom': self.canvas_zoom_factor,
            'pan_x': self.canvas_pan_offset_x,
            'pan_y': self.canvas_pan_offset_y,
            'has_image': self.has_image(),
            'canvas_size': self.canvas_widget_size.width() if self.canvas_widget_size else 0
        }
    
    def get_current_state(self) -> dict:
        """Get current minimap state."""
        return {
            'name': self.name,
            'version': self.version,
            'has_image': self.has_image(),
            'zoom_factor': self.canvas_zoom_factor,
            'pan_offset_x': self.canvas_pan_offset_x,
            'pan_offset_y': self.canvas_pan_offset_y,
            'image_size': {
                'width': self.full_image.width() if self.full_image else 0,
                'height': self.full_image.height() if self.full_image else 0
            },
            'canvas_size': {
                'width': self.canvas_widget_size.width() if self.canvas_widget_size else 0,
                'height': self.canvas_widget_size.height() if self.canvas_widget_size else 0
            }
        }
    
    def get_statistics(self) -> dict:
        """Get minimap statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'minimap_size': {'width': 180, 'height': 120},
            'has_image': self.has_image(),
            'zoom_factor': self.canvas_zoom_factor,
            'view_area_percent': {
                'width': (100.0 / self.canvas_zoom_factor) if self.canvas_zoom_factor > 0 else 100.0,
                'height': (100.0 / self.canvas_zoom_factor) if self.canvas_zoom_factor > 0 else 100.0
            },
            'interactive': True,
            'click_navigation_enabled': self.has_image()
        }