"""
Minimap Widget - Modular component for overview navigation

A completely self-contained minimap component that shows an overview
of the current image and allows navigation by clicking.
"""

from typing import Optional, Tuple, Protocol, List, Dict, Any
import logging
from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QImage, QMouseEvent

logger = logging.getLogger(__name__)


class MinimapProtocol(Protocol):
    """Protocol defining the minimap interface."""
    
    # Signals
    view_clicked: pyqtSignal  # Emits normalized coordinates (0-1)
    
    # Methods
    def set_image(self, image_path: str) -> bool: ...
    def update_view_rect(self, normalized_rect: QRectF) -> None: ...
    def set_config(self, config: dict) -> None: ...
    def get_size(self) -> Tuple[int, int]: ...
    def add_annotation_overlay(self, annotations: List[Dict]) -> None: ...
    def clear_annotation_overlay(self) -> None: ...


class MinimapWidget(QLabel):
    """
    Interactive minimap showing current view area.
    
    Features:
    - Shows scaled down version of full image
    - Displays current view rectangle
    - Click to navigate to that area
    - Configurable appearance
    
    This is a completely self-contained component that:
    - Manages its own state
    - Has no dependencies on other UI components
    - Communicates only through signals
    """
    
    # Signals
    view_clicked = pyqtSignal(float, float)  # Normalized x, y (0-1)
    
    def __init__(self, config: Optional[dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Configuration
        self._config = self._default_config()
        if config:
            self._config.update(config)
        
        # State
        self._image_pixmap: Optional[QPixmap] = None
        self._view_rect: QRectF = QRectF(0, 0, 1, 1)  # Normalized coordinates
        self._last_rendered_size: Optional[Tuple[int, int]] = None
        self._annotations: List[Dict] = []  # Annotation overlay data
        self._show_annotations: bool = True
        
        # Setup
        self._setup_ui()
        
    def _default_config(self) -> dict:
        """Default configuration for minimap."""
        return {
            'size': (180, 120),
            'style': {
                'background': '#374151',
                'border': '#6b7280',
                'border_width': 1,
                'border_radius': 4,
                'view_rect_color': '#3b82f6',
                'view_rect_border': '#60a5fa',
                'view_rect_width': 2,
                'view_rect_opacity': 0.3,
                'annotation_colors': ['#ef4444', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'],
                'annotation_size': 2,
                'annotation_opacity': 0.8
            },
            'behavior': {
                'click_to_navigate': True,
                'show_crosshair': False,
                'smooth_scaling': True
            }
        }
    
    def _setup_ui(self):
        """Setup the UI based on configuration."""
        # Set size
        width, height = self._config['size']
        self.setFixedSize(width, height)
        
        # Apply styling
        style = self._config['style']
        self.setStyleSheet(f"""
            QLabel {{
                background: {style['background']};
                border: {style['border_width']}px solid {style['border']};
                border-radius: {style['border_radius']}px;
            }}
        """)
        
        # Set initial state
        self.setText("Minimap")
        self.setAlignment(Qt.AlignCenter)
        
        # Enable mouse tracking if click navigation is enabled
        if self._config['behavior']['click_to_navigate']:
            self.setCursor(Qt.PointingHandCursor)
    
    # Public API (implements MinimapProtocol)
    
    def set_image(self, image_path: str) -> bool:
        """
        Set the image to display in the minimap.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if image loaded successfully, False otherwise
        """
        try:
            # Load image
            image = QImage(image_path)
            if image.isNull():
                return False
            
            # Scale to fit minimap while maintaining aspect ratio
            scaled = image.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation if self._config['behavior']['smooth_scaling'] else Qt.FastTransformation
            )
            
            # Convert to pixmap
            self._image_pixmap = QPixmap.fromImage(scaled)
            self._last_rendered_size = (image.width(), image.height())
            
            # Update display
            self._update_display()
            return True
            
        except Exception as e:
            print(f"Error loading minimap image: {e}")
            return False
    
    def update_view_rect(self, normalized_rect: QRectF) -> None:
        """
        Update the view rectangle overlay.
        
        Args:
            normalized_rect: Rectangle in normalized coordinates (0-1)
        """
        self._view_rect = normalized_rect
        self._update_display()
    
    def set_config(self, config: dict) -> None:
        """Update configuration and refresh display."""
        self._config.update(config)
        self._setup_ui()
        self._update_display()
    
    def get_size(self) -> Tuple[int, int]:
        """Get the current size of the minimap."""
        return (self.width(), self.height())
    
    def clear(self):
        """Clear the minimap display."""
        self._image_pixmap = None
        self._view_rect = QRectF(0, 0, 1, 1)
        self._annotations.clear()
        self.setText("Minimap")
        self.setPixmap(QPixmap())
    
    def add_annotation_overlay(self, annotations: List[Dict]) -> None:
        """
        Add annotation overlay to minimap.
        
        Args:
            annotations: List of annotation dictionaries with 'x', 'y', 'class_id'
        """
        self._annotations = annotations.copy()
        self._update_display()
        logger.debug(f"Added {len(annotations)} annotations to minimap overlay")
    
    def clear_annotation_overlay(self) -> None:
        """Clear annotation overlays."""
        self._annotations.clear()
        self._update_display()
        logger.debug("Cleared minimap annotation overlay")
    
    def set_annotation_visibility(self, visible: bool) -> None:
        """Toggle annotation overlay visibility."""
        self._show_annotations = visible
        self._update_display()
    
    # Internal methods
    
    def _update_display(self):
        """Update the minimap display with current image and view rect."""
        if not self._image_pixmap:
            return
        
        # Create a copy to draw on
        display_pixmap = QPixmap(self.size())
        display_pixmap.fill(Qt.transparent)
        
        painter = QPainter(display_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate image position to center it
        img_rect = self._image_pixmap.rect()
        x = (self.width() - img_rect.width()) // 2
        y = (self.height() - img_rect.height()) // 2
        
        # Draw the image
        painter.drawPixmap(x, y, self._image_pixmap)
        
        # Draw annotations if available and visible
        if self._show_annotations and self._annotations:
            self._draw_annotations(painter, x, y, img_rect.width(), img_rect.height())
        
        # Draw view rectangle if not showing full image
        if self._view_rect != QRectF(0, 0, 1, 1):
            self._draw_view_rect(painter, x, y, img_rect.width(), img_rect.height())
        
        painter.end()
        
        # Update display
        self.setPixmap(display_pixmap)
    
    def _draw_annotations(self, painter: QPainter, img_x: int, img_y: int, img_w: int, img_h: int):
        """Draw annotation overlays on the minimap."""
        style = self._config['style']
        annotation_size = style['annotation_size']
        colors = style['annotation_colors']
        
        # Get original image size for coordinate conversion
        if not self._last_rendered_size:
            return
        
        orig_w, orig_h = self._last_rendered_size
        
        for annotation in self._annotations:
            # Get annotation info
            x = annotation.get('x', 0)
            y = annotation.get('y', 0)
            class_id = annotation.get('class_id', 1)
            
            # Convert from original image coordinates to minimap coordinates
            norm_x = x / orig_w if orig_w > 0 else 0
            norm_y = y / orig_h if orig_h > 0 else 0
            
            # Convert to minimap pixel coordinates
            pixel_x = img_x + norm_x * img_w
            pixel_y = img_y + norm_y * img_h
            
            # Skip if outside minimap bounds
            if not (img_x <= pixel_x <= img_x + img_w and img_y <= pixel_y <= img_y + img_h):
                continue
            
            # Get color for class
            color = QColor(colors[(class_id - 1) % len(colors)])
            color.setAlphaF(style['annotation_opacity'])
            
            # Draw annotation point
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(
                int(pixel_x - annotation_size),
                int(pixel_y - annotation_size),
                annotation_size * 2,
                annotation_size * 2
            )
    
    def _draw_view_rect(self, painter: QPainter, img_x: int, img_y: int, img_w: int, img_h: int):
        """Draw the view rectangle overlay."""
        style = self._config['style']
        
        # Convert normalized rect to pixel coordinates
        rect = QRectF(
            img_x + self._view_rect.x() * img_w,
            img_y + self._view_rect.y() * img_h,
            self._view_rect.width() * img_w,
            self._view_rect.height() * img_h
        )
        
        # Draw semi-transparent fill
        color = QColor(style['view_rect_color'])
        color.setAlphaF(style['view_rect_opacity'])
        painter.fillRect(rect, color)
        
        # Draw border
        pen = QPen(QColor(style['view_rect_border']), style['view_rect_width'])
        painter.setPen(pen)
        painter.drawRect(rect)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks for navigation."""
        if not self._config['behavior']['click_to_navigate']:
            return
        
        if not self._image_pixmap or event.button() != Qt.LeftButton:
            return
        
        # Get click position
        pos = event.pos()
        
        # Calculate image bounds
        img_rect = self._image_pixmap.rect()
        img_x = (self.width() - img_rect.width()) // 2
        img_y = (self.height() - img_rect.height()) // 2
        
        # Check if click is within image bounds
        if (img_x <= pos.x() <= img_x + img_rect.width() and
            img_y <= pos.y() <= img_y + img_rect.height()):
            
            # Convert to normalized coordinates
            norm_x = (pos.x() - img_x) / img_rect.width()
            norm_y = (pos.y() - img_y) / img_rect.height()
            
            # Emit signal for navigation
            self.view_clicked.emit(norm_x, norm_y)
    
    def get_debug_info(self) -> dict:
        """Get debug information about the minimap state."""
        return {
            'has_image': self._image_pixmap is not None,
            'minimap_size': (self.width(), self.height()),
            'image_size': self._last_rendered_size or (0, 0),
            'view_rect': {
                'x': self._view_rect.x(),
                'y': self._view_rect.y(),
                'width': self._view_rect.width(),
                'height': self._view_rect.height()
            },
            'annotations': {
                'count': len(self._annotations),
                'visible': self._show_annotations
            },
            'config': self._config
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get minimap statistics."""
        return {
            'name': 'MinimapWidget',
            'version': '1.1.0',
            'has_image': self._image_pixmap is not None,
            'annotation_count': len(self._annotations),
            'annotations_visible': self._show_annotations,
            'size': self.get_size(),
            'image_size': self._last_rendered_size or (0, 0),
            'view_rect_normalized': {
                'x': self._view_rect.x(),
                'y': self._view_rect.y(),
                'width': self._view_rect.width(), 
                'height': self._view_rect.height()
            }
        }