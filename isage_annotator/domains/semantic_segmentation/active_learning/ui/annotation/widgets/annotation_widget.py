"""
Working ABILIUS-Style Annotation Interface

A simplified but functional implementation of the ABILIUS annotation interface
that avoids the modular component import issues.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QComboBox, QSpinBox, QSlider, QCheckBox,
    QFrame, QSplitter, QStatusBar, QShortcut, QMessageBox,
    QGroupBox, QGridLayout, QSpacerItem, QSizePolicy,
    QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QScrollArea, QTabWidget, QButtonGroup, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QSize
from PyQt5.QtGui import QKeySequence, QFont, QPalette, QColor, QPixmap, QPainter, QPen, QBrush, QImage

# Import new modular navigation components  
from ...navigation.bottom_navigation_panel import BottomNavigationPanel
from ...navigation.top_navigation_module import TopNavigationModule

try:
    # Core annotation services - corrected import paths
    from ...sessions.annotation_manager import AnnotationManager
    from ...sessions.session_management import SessionManager
    from ...core.annotation_service import AnnotationService
    from ...core.active_learning_system import ActiveLearningSystem
    from ....data.image_loading import load_image
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Silently handle import errors - components will work in limited mode
    COMPONENTS_AVAILABLE = False
    # Dummy classes for type hints
    class SessionManager: pass
    class AnnotationManager: pass
    class ActiveLearningSystem: pass

logger = logging.getLogger(__name__)


class MinimapWidget(QLabel):
    """Interactive minimap showing current view area."""
    
    # Signal for navigation
    viewChanged = pyqtSignal(int, int)  # pan_x, pan_y offsets
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 120)
        self.setStyleSheet("""
            QLabel {
                background: #374151;
                border: 1px solid #6b7280;
                border-radius: 4px;
            }
        """)
        
        # Minimap state
        self.full_image = None
        self.canvas_widget_size = None
        self.canvas_zoom_factor = 1.0
        self.canvas_pan_offset_x = 0
        self.canvas_pan_offset_y = 0
        
        self.setText("Mini-Map")
        self.setAlignment(Qt.AlignCenter)
    
    def update_image(self, image):
        """Update the minimap with a new image."""
        self.full_image = image
        self.update_minimap()
    
    def update_view(self, widget_size, zoom_factor, pan_offset_x, pan_offset_y):
        """Update the view rectangle based on canvas state."""
        self.canvas_widget_size = widget_size
        self.canvas_zoom_factor = zoom_factor
        self.canvas_pan_offset_x = pan_offset_x
        self.canvas_pan_offset_y = pan_offset_y
        self.update_minimap()
    
    def update_minimap(self):
        """Redraw the minimap with view rectangle."""
        if not self.full_image:
            return
        
        # Create minimap pixmap
        minimap_size = self.size()
        pixmap = QPixmap(minimap_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Scale image to fit minimap
        scaled_image = self.full_image.scaled(
            minimap_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Center the scaled image
        x_offset = (minimap_size.width() - scaled_image.width()) // 2
        y_offset = (minimap_size.height() - scaled_image.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled_image)
        
        # Draw view rectangle if we have canvas state
        if self.canvas_widget_size and scaled_image.size().isValid():
            self.draw_view_rectangle(painter, scaled_image, x_offset, y_offset)
        
        painter.end()
        self.setPixmap(pixmap)
    
    def draw_view_rectangle(self, painter, scaled_image, img_x_offset, img_y_offset):
        """Draw the current view rectangle on the minimap."""
        # Calculate scale factors
        scale_x = scaled_image.width() / self.full_image.width()
        scale_y = scaled_image.height() / self.full_image.height()
        
        # Calculate visible area in original image coordinates
        canvas_width = self.canvas_widget_size.width()
        canvas_height = self.canvas_widget_size.height()
        
        # Account for zoom and pan
        visible_width = canvas_width / self.canvas_zoom_factor
        visible_height = canvas_height / self.canvas_zoom_factor
        
        # Calculate view rectangle position
        view_x = (-self.canvas_pan_offset_x / self.canvas_zoom_factor) + (self.full_image.width() - visible_width) / 2
        view_y = (-self.canvas_pan_offset_y / self.canvas_zoom_factor) + (self.full_image.height() - visible_height) / 2
        
        # Convert to minimap coordinates
        minimap_rect_x = img_x_offset + view_x * scale_x
        minimap_rect_y = img_y_offset + view_y * scale_y
        minimap_rect_w = visible_width * scale_x
        minimap_rect_h = visible_height * scale_y
        
        # Draw view rectangle
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QBrush(Qt.transparent))
        painter.drawRect(int(minimap_rect_x), int(minimap_rect_y), 
                        int(minimap_rect_w), int(minimap_rect_h))
    
    def mousePressEvent(self, event):
        """Handle clicks on minimap for navigation."""
        if not self.full_image or not self.canvas_widget_size:
            return
        
        # Calculate click position relative to scaled image
        minimap_size = self.size()
        scaled_size = self.full_image.size().scaled(minimap_size, Qt.KeepAspectRatio)
        
        x_offset = (minimap_size.width() - scaled_size.width()) // 2
        y_offset = (minimap_size.height() - scaled_size.height()) // 2
        
        click_x = event.x() - x_offset
        click_y = event.y() - y_offset
        
        if 0 <= click_x <= scaled_size.width() and 0 <= click_y <= scaled_size.height():
            # Convert to original image coordinates
            scale_x = self.full_image.width() / scaled_size.width()
            scale_y = self.full_image.height() / scaled_size.height()
            
            orig_click_x = click_x * scale_x
            orig_click_y = click_y * scale_y
            
            # Calculate new pan offsets to center this point
            canvas_center_x = self.canvas_widget_size.width() / 2
            canvas_center_y = self.canvas_widget_size.height() / 2
            
            new_pan_x = -(orig_click_x - self.full_image.width()/2) * self.canvas_zoom_factor
            new_pan_y = -(orig_click_y - self.full_image.height()/2) * self.canvas_zoom_factor
            
            self.viewChanged.emit(int(new_pan_x), int(new_pan_y))


class AnnotationHeaderBar(QFrame):
    """Standalone annotation window header - clean and focused."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)  # Single row header
        self.setFrameStyle(QFrame.StyledPanel)
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup simplified annotation header - single row only."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Title
        title_label = QLabel("🎯 Sparse Annotation Tool")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)
        
        # Spacer
        layout.addStretch()
        
        # Session info
        self.session_label = QLabel("Session: No Session")
        self.session_label.setStyleSheet("""
            font-size: 14px; 
            color: #94a3b8; 
            padding: 5px 10px; 
            border: 1px solid #374151; 
            border-radius: 4px; 
            background: #1f2937;
        """)
        layout.addWidget(self.session_label)
        
        # Iteration info
        self.iteration_label = QLabel("Iteration: 1")
        self.iteration_label.setStyleSheet("""
            font-size: 14px; 
            color: #10b981; 
            padding: 5px 10px; 
            border: 1px solid #065f46; 
            border-radius: 4px; 
            background: #064e3b;
        """)
        layout.addWidget(self.iteration_label)
    
    def apply_dark_theme(self):
        """Apply dark theme to header bar."""
        self.setStyleSheet("""
            QFrame {
                background: #374151;
                border-bottom: 1px solid #4b5563;
            }
        """)
    
    def update_session_info(self, session_id: str, session_data: Dict = None):
        """Update session information display."""
        self.session_label.setText(f"Session: {session_id}")
        if session_data:
            # Could add more session details here
            pass


# Dataset class configurations will be loaded dynamically
# Default fallback configuration (VAIHINGEN)
DEFAULT_CLASS_CONFIG = {
    "names": [
        "Impervious",
        "Building", 
        "Low vegetation",
        "Tree",
        "Car",
        "Clutter"
    ],
    "colors": [
        (255, 255, 255),    # 0: Impervious - White
        (0, 0, 255),        # 1: Building - Blue  
        (0, 255, 255),      # 2: Low vegetation - Cyan
        (0, 255, 0),        # 3: Tree - Green
        (255, 255, 0),      # 4: Car - Yellow
        (255, 0, 0),        # 5: Clutter - Red
    ],
    "ignore_index": 6
}

def generate_class_colors(num_classes):
    """Generate distinctive colors for classes."""
    import colorsys
    colors = []
    for i in range(num_classes):
        # Generate evenly spaced hues
        hue = i / num_classes
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        colors.append((int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
    return colors

def load_dataset_class_config(session_config=None):
    """Load class names and colors from dataset configuration or use defaults."""
    if session_config and hasattr(session_config, 'class_names') and session_config.class_names:
        # Load from session config
        names = session_config.class_names
        colors = getattr(session_config, 'class_colors', None)
        if colors and len(colors) == len(names):
            # Convert color format if needed
            colors = [(int(c[0]), int(c[1]), int(c[2])) for c in colors]
        else:
            # Generate colors if not provided
            colors = generate_class_colors(len(names))
        ignore_idx = getattr(session_config, 'ignore_index', len(names))
        
        return names, colors, ignore_idx
    else:
        # Use VAIHINGEN defaults
        return (DEFAULT_CLASS_CONFIG["names"], 
                DEFAULT_CLASS_CONFIG["colors"],
                DEFAULT_CLASS_CONFIG["ignore_index"])

# Initialize with defaults (will be updated when session loads)
CLASS_NAMES, CLASS_COLORS, IGNORE_INDEX = load_dataset_class_config()


class HeaderBar(QFrame):
    """ABILIUS-style header bar with session info and controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup header bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Title
        title_label = QLabel("🎯 Sparse Annotation Tool")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)
        
        # Spacer
        layout.addStretch()
        
        # Session info
        self.session_label = QLabel("Session: No Session")
        self.session_label.setStyleSheet("""
            font-size: 14px; 
            color: #94a3b8; 
            padding: 5px 10px; 
            border: 1px solid #374151; 
            border-radius: 4px;
        """)
        layout.addWidget(self.session_label)
        
        # Mode indicator
        self.mode_label = QLabel("Mode: Initial Annotation")
        self.mode_label.setStyleSheet("""
            font-size: 14px; 
            color: #10b981; 
            padding: 5px 10px; 
            border: 1px solid #065f46; 
            border-radius: 4px;
            background: #064e3b;
        """)
        layout.addWidget(self.mode_label)
        
        # Back button
        self.back_button = QPushButton("⬅ Back")
        self.back_button.setFixedHeight(30)
        self.back_button.setToolTip("Return to Mode Grid (Esc)")
        self.back_button.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: #ffffff;
                border: 1px solid #b91c1c;
                border-radius: 4px;
                font-size: 12px;
                padding: 5px 10px;
            }
            QPushButton:hover { background: #ef4444; }
        """)
        self.back_button.clicked.connect(self.request_exit)
        layout.addWidget(self.back_button)
        
        # Help button
        help_button = QPushButton("❓")
        help_button.setFixedSize(30, 30)
        help_button.setToolTip("Keyboard Shortcuts")
        help_button.setStyleSheet("""
            QPushButton {
                background: #374151;
                color: #ffffff;
                border: 1px solid #6b7280;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background: #4b5563; }
        """)
        help_button.clicked.connect(self.show_help)
        layout.addWidget(help_button)
    
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QFrame {
                background: #1f2937;
                border-bottom: 1px solid #374151;
            }
        """)
    
    def update_session_info(self, session_name: str):
        """Update session information display."""
        self.session_label.setText(f"Session: {session_name}")
        
    def update_mode(self, mode: str):
        """Update mode indicator."""
        self.mode_label.setText(f"Mode: {mode}")
    
    def request_exit(self):
        """Request to exit annotation mode."""
        if hasattr(self.parent(), 'modeExitRequested'):
            self.parent().modeExitRequested.emit()
    
    def show_help(self):
        """Show keyboard shortcuts help dialog."""
        help_text = """
        KEYBOARD SHORTCUTS:
        
        Navigation:
        • Q/E - Previous/Next image
        • R - Random image
        • G - Go to specific image
        
        Annotation:
        • 1-7 - Select class (1=Impervious, 2=Building, etc.)
        • Left Click - Add point (or drag existing point)
        • Right Click - Remove point
        • Mouse Wheel - Zoom in/out
        
        Zoom & View:
        • Ctrl++ - Zoom in
        • Ctrl+- - Zoom out
        • Ctrl+0 - Reset zoom to fit
        
        Control:
        • ESC - Return to Mode Grid
        
        Tips:
        • Drag points to move them
        • Use zoom controls or mouse wheel
        • Mini-map shows full image view
        """
        
        QMessageBox.information(self, "Keyboard Shortcuts", help_text.strip())


class SimpleAnnotationCanvas(QLabel):
    """Simplified annotation canvas with point annotation capabilities."""
    
    point_added = pyqtSignal(float, float, int)  # x, y, class_id
    point_removed = pyqtSignal(float, float)     # x, y
    point_moved = pyqtSignal(float, float, float, float)  # old_x, old_y, new_x, new_y
    mouse_coordinates = pyqtSignal(int, int)  # x, y coordinates for live tracking
    image_loaded = pyqtSignal()  # Emitted when new image is loaded
    view_changed = pyqtSignal()  # Emitted when zoom/pan changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background: #2d3748; border: 1px solid #4a5568;")
        self.setAlignment(Qt.AlignCenter)
        
        # Annotation state
        self.current_image = None
        self.image_path = None
        self.current_image_path = None
        self.original_image_array = None  # Store original numpy array for channel remapping
        self.annotations = []  # List of [x, y, class_id]
        self.current_class = 1
        self.point_size = 8
        self.highlighted_point_index = -1  # Track which point is highlighted
        self.space_pressed = False  # Track spacebar state for disabling point interaction
        
        # Display settings
        self.show_grid = False
        self.grid_size = 50
        self.show_pixel_info = False
        
        # Overlay settings
        self.show_gt_overlay = False
        self.show_prediction_overlay = False
        self.gt_overlay_opacity = 0.3
        self.prediction_overlay_opacity = 0.5
        
        # Overlay data (loaded when needed)
        self.gt_mask = None
        self.prediction_mask = None
        
        # RGB channel mapping (0=R, 1=G, 2=B for standard RGB)
        self.rgb_channel_mapping = [0, 1, 2]  # [R_source, G_source, B_source]
        
        # Drag state
        self.dragging = False
        self.drag_point_index = -1
        self.last_mouse_pos = None
        
        # Panning state
        self.panning = False
        self.pan_start_pos = None
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        # Track timestamps for points (for JSON efficiency)
        self.point_timestamps = []
        
        # Zoom state
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        
        # Enable mouse tracking and keyboard focus
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Allow keyboard focus
        
        # Request initial focus
        QTimer.singleShot(100, lambda: self.setFocus())
        
    def load_image(self, image_path: str):
        """Load and display an image."""
        try:
            logger.info(f"Loading image: {image_path}")
            self.image_path = image_path
            self.current_image_path = image_path
            
            # Clear existing overlay data when loading new image
            self.gt_mask = None
            self.prediction_mask = None
            
            # Check if file exists
            if not Path(image_path).exists():
                logger.error(f"Image file does not exist: {image_path}")
                return False
            
            # Load with PIL to handle various formats
            from PIL import Image
            pil_image = Image.open(image_path)
            
            # For debugging: print image info
            print(f"Original image mode: {pil_image.mode}, size: {pil_image.size}")
            
            # Convert to RGB if needed (this might lose channels for multi-channel images)
            if pil_image.mode != 'RGB':
                # Try to preserve multi-channel data if possible
                if pil_image.mode in ['L', 'P']:  # Grayscale or palette
                    pil_image = pil_image.convert('RGB')
                elif pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')  # Drop alpha
                else:
                    print(f"Converting from {pil_image.mode} to RGB")
                    pil_image = pil_image.convert('RGB')
            
            # Convert to QPixmap with channel remapping support
            import numpy as np
            from PyQt5.QtGui import QImage
            
            # Store original image array for channel remapping
            self.original_image_array = np.array(pil_image)
            
            # Apply current RGB channel mapping
            display_array = self.apply_rgb_channel_mapping(self.original_image_array)
            
            height, width, channel = display_array.shape
            bytes_per_line = 3 * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Store original pixmap and apply zoom
            self.original_pixmap = QPixmap.fromImage(q_image)
            self.apply_zoom()
            self.current_image = self.original_pixmap
            logger.info(f"Successfully loaded image: {Path(image_path).name}")
            
            # Reload overlays if they are currently enabled
            if self.show_gt_overlay:
                self.load_ground_truth_mask()
            if self.show_prediction_overlay:
                self.load_prediction_mask()
            
            # Update display
            self.update()
            
            # Emit signal for minimap update
            self.image_loaded.emit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.setText(f"Failed to load image: {e}")
            return False
    
    def show_empty_state(self, message: str):
        """Show empty state message."""
        self.clear()
        self.setText(f"📂 {message}\n\nPlease ensure your session has images in:\n{self.parent().session_path / 'data' / 'dataset' / 'train' / 'images' if hasattr(self.parent(), 'session_path') and self.parent().session_path else 'data/dataset/train/images'}")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 16px;
                background: #1e293b;
                border: 2px dashed #374151;
                border-radius: 8px;
                padding: 40px;
            }
        """)
    
    def load_annotations(self, annotations: List[List]):
        """Load annotations for current image."""
        self.annotations = annotations.copy() if annotations else []
        self.update()
    
    def set_current_class(self, class_id: int):
        """Set the current annotation class."""
        self.current_class = class_id
    
    def apply_zoom(self):
        """Apply current zoom factor to the image."""
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            # Calculate new size based on zoom factor
            original_size = self.original_pixmap.size()
            new_width = int(original_size.width() * self.zoom_factor)
            new_height = int(original_size.height() * self.zoom_factor)
            
            # Scale the image
            scaled_pixmap = self.original_pixmap.scaled(
                new_width, new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.setPixmap(scaled_pixmap)
            self.update()  # Force repaint with new positioning
            self.view_changed.emit()
    
    def zoom_in(self):
        """Zoom in on the image."""
        new_zoom = min(self.zoom_factor * 1.25, self.max_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
            return True
        return False
    
    def zoom_out(self):
        """Zoom out on the image."""
        new_zoom = max(self.zoom_factor / 1.25, self.min_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
            return True
        return False
    
    def reset_zoom(self):
        """Reset zoom to fit the widget."""
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            # Calculate zoom to fit widget
            widget_size = self.size()
            image_size = self.original_pixmap.size()
            
            scale_x = widget_size.width() / image_size.width()
            scale_y = widget_size.height() / image_size.height()
            self.zoom_factor = min(scale_x, scale_y)
            
            self.apply_zoom()
            return True
        return False
    
    def find_nearest_point(self, orig_x, orig_y, tolerance=5):
        """Find the nearest point to given coordinates within tolerance distance."""
        if not self.annotations:
            return -1
            
        min_dist = float('inf')
        nearest_idx = -1
        
        for i, (x, y, _) in enumerate(self.annotations):
            dist = ((x - orig_x) ** 2 + (y - orig_y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
        
        # Only return index if within tolerance
        return nearest_idx if nearest_idx >= 0 and min_dist < tolerance else -1
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for annotation."""
        # Ensure this widget has focus for keyboard events
        self.setFocus()
        
        if not self.current_image or not self.pixmap():
            return
            
        # Get click position relative to image
        pixmap = self.pixmap()
        widget_size = self.size()
        
        # Calculate image position within widget (including pan offsets)
        x_offset = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
        y_offset = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y
        
        # Check if click is within image bounds
        click_x = event.x() - x_offset
        click_y = event.y() - y_offset
        
        if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
            # Convert to original image coordinates
            scale_x = pixmap.width() / self.current_image.width() if self.current_image else 1
            scale_y = pixmap.height() / self.current_image.height() if self.current_image else 1
            
            orig_x = click_x / scale_x
            orig_y = click_y / scale_y
            
            # Handle different mouse buttons (only if spacebar not pressed)
            if event.button() == Qt.RightButton and not self.space_pressed:
                # Right click: Delete point if near one, otherwise do nothing
                nearest_idx = self.find_nearest_point(orig_x, orig_y)
                if nearest_idx >= 0:
                    removed_point = self.annotations.pop(nearest_idx)
                    self.point_removed.emit(removed_point[0], removed_point[1])
                    # Clear highlight since point was removed
                    self.highlighted_point_index = -1
                    self.update()
                return
                
            elif event.button() == Qt.MiddleButton:
                # Middle click: Always pan (regardless of spacebar state)
                self.panning = True
                self.pan_start_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            elif event.button() == Qt.LeftButton:
                if self.space_pressed:
                    # Spacebar held - disable point detection, always add new point at exact location
                    self.annotations.append([orig_x, orig_y, self.current_class])
                    self.point_added.emit(orig_x, orig_y, self.current_class)
                    self.update()
                else:
                    # Normal behavior - check for existing points to drag
                    nearest_idx = self.find_nearest_point(orig_x, orig_y)
                    
                    if nearest_idx >= 0:
                        # Start dragging existing point
                        self.dragging = True
                        self.drag_point_index = nearest_idx
                        self.last_mouse_pos = (orig_x, orig_y)
                        # Clear highlight during drag
                        self.highlighted_point_index = -1
                    else:
                        # Add new point
                        self.annotations.append([orig_x, orig_y, self.current_class])
                        self.point_added.emit(orig_x, orig_y, self.current_class)
                        self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points and coordinate tracking."""
        # Always emit coordinates for tracking and check for point highlighting
        if self.current_image:
            pixmap = self.pixmap()
            if pixmap:
                widget_size = self.size()
                x_offset = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
                y_offset = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y
                
                click_x = event.x() - x_offset
                click_y = event.y() - y_offset
                
                if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
                    # Convert to original image coordinates
                    scale_x = pixmap.width() / self.current_image.width()
                    scale_y = pixmap.height() / self.current_image.height()
                    
                    original_x = int(click_x / scale_x)
                    original_y = int(click_y / scale_y)
                    
                    # Emit coordinates for live tracking
                    self.mouse_coordinates.emit(original_x, original_y)
                    
                    # Show pixel info tooltip if enabled
                    if self.show_pixel_info:
                        self.show_pixel_tooltip(event, original_x, original_y)
                    
                    # Update point highlighting when not panning, dragging, or space pressed
                    if not self.panning and not self.dragging and not self.space_pressed:
                        # Find nearest point for highlighting
                        nearest_idx = self.find_nearest_point(original_x, original_y)
                        
                        # Update highlight if changed
                        if nearest_idx != self.highlighted_point_index:
                            self.highlighted_point_index = nearest_idx
                            self.update()  # Redraw to show/hide highlight
                    elif self.space_pressed and self.highlighted_point_index != -1:
                        # Clear highlight when spacebar is pressed
                        self.highlighted_point_index = -1
                        self.update()
                else:
                    # Mouse outside image bounds, clear highlight
                    if self.highlighted_point_index != -1:
                        self.highlighted_point_index = -1
                        self.update()
        
        # Handle panning
        if self.panning and self.pan_start_pos:
            delta = event.pos() - self.pan_start_pos
            self.pan_offset_x += delta.x()
            self.pan_offset_y += delta.y()
            self.pan_start_pos = event.pos()
            self.update()  # Trigger repaint with new offset
            self.view_changed.emit()  # Update minimap
            return
        
        # Handle dragging
        if not self.dragging or self.drag_point_index < 0 or not self.current_image:
            return
            
        # Get current mouse position relative to image
        pixmap = self.pixmap()
        widget_size = self.size()
        
        x_offset = (widget_size.width() - pixmap.width()) // 2
        y_offset = (widget_size.height() - pixmap.height()) // 2
        
        click_x = event.x() - x_offset
        click_y = event.y() - y_offset
        
        if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
            # Convert to original image coordinates
            scale_x = pixmap.width() / self.current_image.width() if self.current_image else 1
            scale_y = pixmap.height() / self.current_image.height() if self.current_image else 1
            
            new_x = click_x / scale_x
            new_y = click_y / scale_y
            
            # Update point position
            if self.drag_point_index < len(self.annotations):
                old_x, old_y = self.last_mouse_pos
                self.annotations[self.drag_point_index][0] = new_x
                self.annotations[self.drag_point_index][1] = new_y
                self.last_mouse_pos = (new_x, new_y)
                
                # Emit signal for drag
                self.point_moved.emit(old_x, old_y, new_x, new_y)
                self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to end dragging and panning."""
        if (event.button() == Qt.RightButton or event.button() == Qt.MiddleButton) and self.panning:
            self.panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
        elif event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.drag_point_index = -1
            self.last_mouse_pos = None
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        
        # Update zoom display if parent has a method for it
        if hasattr(self.parent(), 'update_zoom_display'):
            self.parent().update_zoom_display(self.zoom_factor)
    
    def paintEvent(self, event):
        """Custom paint event to draw image with pan offsets and annotations."""
        # Clear the widget with professional dark background
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2d3748"))  # Dark gray background matching theme
        
        # Draw the image at the correct position (with pan offsets)
        if self.pixmap():
            pixmap = self.pixmap()
            widget_size = self.size()
            
            # Calculate image position including pan offsets (ABILIUS-style)
            base_x = (widget_size.width() - pixmap.width()) // 2
            base_y = (widget_size.height() - pixmap.height()) // 2
            
            # Apply pan offsets to image position
            image_x = base_x + self.pan_offset_x
            image_y = base_y + self.pan_offset_y
            
            # Draw the image at the panned position
            painter.drawPixmap(image_x, image_y, pixmap)
            
            # Draw overlays if enabled (ground truth and predictions)
            if self.show_gt_overlay and self.gt_mask is not None:
                self.draw_overlay(painter, self.gt_mask, image_x, image_y, pixmap.width(), pixmap.height(), 
                                self.gt_overlay_opacity, "ground_truth")
            
            if self.show_prediction_overlay and self.prediction_mask is not None:
                self.draw_overlay(painter, self.prediction_mask, image_x, image_y, pixmap.width(), pixmap.height(), 
                                self.prediction_overlay_opacity, "prediction")
            
            # Draw grid overlay if enabled
            if self.show_grid:
                self.draw_grid(painter, image_x, image_y, pixmap.width(), pixmap.height())
            
            # Now draw annotations on top
            if self.annotations:
                painter.setRenderHint(QPainter.Antialiasing)

                # Use the same image positioning for annotations
                x_offset = image_x
                y_offset = image_y

                # Draw points
                for i, (x, y, class_id) in enumerate(self.annotations):
                    if 0 <= class_id < len(CLASS_COLORS):
                        color = CLASS_COLORS[class_id]

                        # Convert to widget coordinates
                        scale_x = pixmap.width() / self.current_image.width() if self.current_image else 1
                        scale_y = pixmap.height() / self.current_image.height() if self.current_image else 1

                        draw_x = x_offset + (x * scale_x)
                        draw_y = y_offset + (y * scale_y)

                        # Check if this point is highlighted
                        is_highlighted = (i == self.highlighted_point_index)

                        if is_highlighted:
                            # Draw highlighted point larger with white outer ring
                            highlight_size = self.point_size + 4
                            painter.setPen(QPen(QColor(255, 255, 255), 3))  # White highlight border
                            painter.setBrush(QBrush(QColor(*color)))
                            painter.drawEllipse(int(draw_x - highlight_size//2),
                                              int(draw_y - highlight_size//2),
                                              highlight_size, highlight_size)
                        else:
                            # Draw normal point
                            painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black border
                            painter.setBrush(QBrush(QColor(*color)))
                            painter.drawEllipse(int(draw_x - self.point_size//2),
                                              int(draw_y - self.point_size//2),
                                              self.point_size, self.point_size)
    
    def leaveEvent(self, event):
        """Clear point highlighting when mouse leaves widget."""
        if self.highlighted_point_index != -1:
            self.highlighted_point_index = -1
            self.update()
        super().leaveEvent(event)
    
    def draw_grid(self, painter, image_x, image_y, image_width, image_height):
        """Draw grid overlay on the image."""
        painter.setRenderHint(QPainter.Antialiasing, False)  # Crisp grid lines
        
        # Set grid line color and style
        grid_color = QColor(255, 255, 255, 100)  # Semi-transparent white
        painter.setPen(QPen(grid_color, 1, Qt.SolidLine))
        
        # Draw vertical lines
        for x in range(0, image_width + 1, self.grid_size):
            line_x = image_x + x
            painter.drawLine(line_x, image_y, line_x, image_y + image_height)
        
        # Draw horizontal lines  
        for y in range(0, image_height + 1, self.grid_size):
            line_y = image_y + y
            painter.drawLine(image_x, line_y, image_x + image_width, line_y)
    
    def set_grid_settings(self, enabled, size):
        """Update grid display settings."""
        self.show_grid = enabled
        self.grid_size = size
        self.update()  # Trigger repaint
    
    def set_point_size(self, size):
        """Update point size."""
        self.point_size = size
        self.update()  # Trigger repaint
    
    def draw_overlay(self, painter, mask, image_x, image_y, image_width, image_height, opacity, overlay_type):
        """Draw segmentation overlay (ground truth or prediction) on the image."""
        if mask is None:
            return
        
        try:
            # Create a QPixmap from the mask using class colors with proper alpha
            alpha_value = int(opacity * 255)  # Convert opacity (0.0-1.0) to alpha (0-255)
            overlay_pixmap = self.create_colored_mask_pixmap(mask, alpha_value)
            
            if overlay_pixmap.isNull():
                return
            
            # Scale overlay to match image size if needed
            if overlay_pixmap.size() != QSize(image_width, image_height):
                overlay_pixmap = overlay_pixmap.scaled(
                    image_width, image_height, 
                    Qt.IgnoreAspectRatio, 
                    Qt.SmoothTransformation
                )
            
            # Draw the colored overlay with full opacity since alpha is already in pixmap
            painter.drawPixmap(image_x, image_y, overlay_pixmap)
            
        except Exception as e:
            print(f"Error drawing {overlay_type} overlay: {str(e)}")
    
    def create_colored_mask_pixmap(self, mask, alpha=255):
        """Create a colored pixmap from a segmentation mask using class colors."""
        try:
            if mask is None:
                return QPixmap()
            
            # Convert mask to numpy array if it's not already
            if hasattr(mask, 'size'):
                # If it's a QPixmap, convert to numpy
                mask_array = self.qpixmap_to_numpy(mask)
            else:
                mask_array = mask
            
            # Create RGB image from mask using class colors
            height, width = mask_array.shape[:2]
            colored_mask = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
            
            # Apply class colors with specified alpha
            for class_id in range(len(CLASS_COLORS)):
                if class_id >= len(CLASS_COLORS):
                    continue
                    
                color = CLASS_COLORS[class_id]
                mask_pixels = (mask_array == class_id)
                
                if np.any(mask_pixels):
                    colored_mask[mask_pixels] = [color[0], color[1], color[2], alpha]
            
            # Convert numpy array to QPixmap
            return self.numpy_to_qpixmap(colored_mask)
            
        except Exception as e:
            print(f"Error creating colored mask pixmap: {str(e)}")
            return QPixmap()
    
    def qpixmap_to_numpy(self, pixmap):
        """Convert QPixmap to numpy array."""
        try:
            # Convert QPixmap to QImage
            qimg = pixmap.toImage()
            qimg = qimg.convertToFormat(QImage.Format_Grayscale8)
            
            # Convert to numpy array
            width = qimg.width()
            height = qimg.height()
            
            # Get the image data
            ptr = qimg.bits()
            ptr.setsize(height * width)
            arr = np.array(ptr, dtype=np.uint8).reshape((height, width))
            
            return arr
        except Exception as e:
            print(f"Error converting QPixmap to numpy: {str(e)}")
            return None
    
    def numpy_to_qpixmap(self, arr):
        """Convert numpy array to QPixmap."""
        try:
            if arr.ndim == 3 and arr.shape[2] == 4:  # RGBA
                height, width, channels = arr.shape
                bytes_per_line = 4 * width
                qimg = QImage(arr.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            elif arr.ndim == 3 and arr.shape[2] == 3:  # RGB
                height, width, channels = arr.shape
                bytes_per_line = 3 * width
                qimg = QImage(arr.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:
                # Grayscale
                height, width = arr.shape
                bytes_per_line = width
                qimg = QImage(arr.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Error converting numpy to QPixmap: {str(e)}")
            return QPixmap()
    
    def set_overlay_settings(self, overlay_type, opacity):
        """Update overlay display settings."""
        enabled = opacity > 0.0  # Interpret 0.0 opacity as disabled
        
        if overlay_type == "ground_truth":
            self.show_gt_overlay = enabled
            if enabled:
                self.gt_overlay_opacity = opacity
                
            # Load ground truth mask if enabled and not loaded
            if enabled and self.gt_mask is None:
                self.load_ground_truth_mask()
                
        elif overlay_type == "prediction":
            self.show_prediction_overlay = enabled
            if enabled:
                self.prediction_overlay_opacity = opacity
                
            # Load prediction mask if enabled and not loaded
            if enabled and self.prediction_mask is None:
                self.load_prediction_mask()
        
        self.update()  # Trigger repaint
    
    def set_rgb_channels(self, r_channel, g_channel, b_channel):
        """Set RGB channel mapping and regenerate image display."""
        print(f"RGB channel mapping changed: R={r_channel}, G={g_channel}, B={b_channel}")
        self.rgb_channel_mapping = [r_channel, g_channel, b_channel]
        
        # Regenerate image with new channel mapping if image is loaded
        if self.original_image_array is not None:
            print(f"Original image shape: {self.original_image_array.shape}")
            self.regenerate_image_with_channels()
        else:
            print("No original image array available for channel remapping")
    
    def apply_rgb_channel_mapping(self, image_array):
        """Apply RGB channel mapping to image array."""
        if image_array is None or len(image_array.shape) != 3:
            return image_array
        
        height, width, channels = image_array.shape
        
        # Handle cases where image might have fewer than 3 channels
        available_channels = min(channels, 3)
        
        # Create output array
        mapped_array = np.zeros((height, width, 3), dtype=image_array.dtype)
        
        # Map each RGB channel to the selected source channel
        for output_channel, source_channel in enumerate(self.rgb_channel_mapping):
            if source_channel < available_channels:
                mapped_array[:, :, output_channel] = image_array[:, :, source_channel]
            else:
                # If source channel doesn't exist, use channel 0 as fallback
                mapped_array[:, :, output_channel] = image_array[:, :, 0] if available_channels > 0 else 0
        
        return mapped_array
    
    def regenerate_image_with_channels(self):
        """Regenerate the displayed image with current channel mapping."""
        if self.original_image_array is None:
            return
        
        try:
            # Apply current RGB channel mapping
            display_array = self.apply_rgb_channel_mapping(self.original_image_array)
            print(f"Remapped array shape: {display_array.shape}, channel mapping: {self.rgb_channel_mapping}")
            
            # Convert to QPixmap
            height, width, channels = display_array.shape
            bytes_per_line = 3 * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Update pixmaps
            self.original_pixmap = QPixmap.fromImage(q_image)
            self.apply_zoom()
            self.current_image = self.original_pixmap
            
            # Update display
            self.update()
            
            # Emit signal for minimap update
            self.image_loaded.emit()
            
        except Exception as e:
            print(f"Error regenerating image with channel mapping: {str(e)}")
    
    def load_ground_truth_mask(self):
        """Load ground truth mask for current image."""
        if not self.current_image_path:
            return
        
        try:
            # Extract image name from current path
            image_name = Path(self.current_image_path).stem
            
            # Construct ground truth mask path
            # Assuming dataset structure: DATASETS/SESSION/v8/dataset/train/dense_masks/
            session_path = Path(self.current_image_path).parents[3]  # Go up from images to session root
            gt_mask_path = session_path / "data" / "dataset" / "train" / "masks" / f"{image_name}.png"
            
            if gt_mask_path.exists():
                # Load mask as grayscale
                gt_pixmap = QPixmap(str(gt_mask_path))
                if not gt_pixmap.isNull():
                    self.gt_mask = gt_pixmap
                    print(f"Loaded ground truth mask: {gt_mask_path}")
                else:
                    print(f"Failed to load ground truth mask: {gt_mask_path}")
            else:
                print(f"Ground truth mask not found: {gt_mask_path}")
                self.gt_mask = None
                
        except Exception as e:
            print(f"Error loading ground truth mask: {str(e)}")
            self.gt_mask = None
    
    def load_prediction_mask(self):
        """Load prediction mask for current image."""
        if not self.current_image_path:
            return
        
        try:
            # Extract image name from current path
            image_name = Path(self.current_image_path).stem
            
            # Construct prediction mask path
            # Assuming dataset structure: DATASETS/SESSION/v8/predictions/iteration_X/
            session_path = Path(self.current_image_path).parents[3]  # Go up from images to session root
            
            # Try to find the latest iteration
            predictions_path = session_path / "predictions"
            if predictions_path.exists():
                iteration_dirs = [d for d in predictions_path.iterdir() if d.is_dir() and d.name.startswith("iteration_")]
                if iteration_dirs:
                    # Get latest iteration
                    latest_iteration = max(iteration_dirs, key=lambda x: int(x.name.split("_")[1]))
                    prediction_mask_path = latest_iteration / f"{image_name}.png"
                    
                    if prediction_mask_path.exists():
                        # Load mask as grayscale
                        pred_pixmap = QPixmap(str(prediction_mask_path))
                        if not pred_pixmap.isNull():
                            self.prediction_mask = pred_pixmap
                            print(f"Loaded prediction mask: {prediction_mask_path}")
                        else:
                            print(f"Failed to load prediction mask: {prediction_mask_path}")
                    else:
                        print(f"Prediction mask not found: {prediction_mask_path}")
                        self.prediction_mask = None
                else:
                    print("No iteration directories found in predictions")
                    self.prediction_mask = None
            else:
                print(f"Predictions directory not found: {predictions_path}")
                self.prediction_mask = None
                
        except Exception as e:
            print(f"Error loading prediction mask: {str(e)}")
            self.prediction_mask = None
    
    def set_pixel_info_enabled(self, enabled):
        """Enable/disable pixel info display."""
        self.show_pixel_info = enabled
        if not enabled and hasattr(self, 'pixel_tooltip'):
            # Hide tooltip when disabled
            self.pixel_tooltip.hide()
    
    def show_pixel_tooltip(self, event, img_x, img_y):
        """Show pixel information tooltip."""
        if not self.current_image or not hasattr(self, 'current_image'):
            return
        
        # Create sophisticated tooltip if it doesn't exist (ABILIUS-style)
        if not hasattr(self, 'pixel_tooltip'):
            from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
            
            # Main tooltip container with shadow effect
            self.pixel_tooltip = QFrame(self)
            self.pixel_tooltip.setFrameStyle(QFrame.StyledPanel)
            self.pixel_tooltip.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 #2d3748, stop: 1 #1a202c);
                    border: 1px solid #4a5568;
                    border-radius: 8px;
                    padding: 0px;
                }
            """)
            
            # Layout for tooltip content
            tooltip_layout = QVBoxLayout(self.pixel_tooltip)
            tooltip_layout.setContentsMargins(12, 10, 12, 10)
            tooltip_layout.setSpacing(6)
            
            # Header with coordinates (prominent)
            self.coord_header = QLabel()
            self.coord_header.setStyleSheet("""
                color: #60a5fa;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 2px;
            """)
            tooltip_layout.addWidget(self.coord_header)
            
            # RGB Values section
            rgb_container = QFrame()
            rgb_layout = QVBoxLayout(rgb_container)
            rgb_layout.setContentsMargins(0, 0, 0, 0)
            rgb_layout.setSpacing(3)
            
            # RGB header
            rgb_header = QLabel("RGB Values")
            rgb_header.setStyleSheet("""
                color: #94a3b8;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            """)
            rgb_layout.addWidget(rgb_header)
            
            # Individual RGB values with color indicators
            self.rgb_values_layout = QHBoxLayout()
            self.rgb_values_layout.setSpacing(8)
            
            # R, G, B value displays
            self.r_display = self.create_color_value_display("R", "#ef4444")
            self.g_display = self.create_color_value_display("G", "#10b981") 
            self.b_display = self.create_color_value_display("B", "#3b82f6")
            
            self.rgb_values_layout.addWidget(self.r_display)
            self.rgb_values_layout.addWidget(self.g_display)
            self.rgb_values_layout.addWidget(self.b_display)
            
            rgb_layout.addLayout(self.rgb_values_layout)
            tooltip_layout.addWidget(rgb_container)
            
            # Additional info section (HSV, etc.)
            self.additional_info = QLabel()
            self.additional_info.setStyleSheet("""
                color: #6b7280;
                font-size: 10px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                margin-top: 2px;
            """)
            tooltip_layout.addWidget(self.additional_info)
            
            # Set minimum size for consistent appearance
            self.pixel_tooltip.setMinimumSize(180, 100)
            self.pixel_tooltip.hide()
    
    def create_color_value_display(self, channel_name, color):
        """Create a sophisticated color value display widget."""
        from PyQt5.QtWidgets import QFrame, QVBoxLayout
        
        container = QFrame()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Channel label (R, G, B)
        label = QLabel(channel_name)
        label.setStyleSheet(f"""
            color: {color};
            font-size: 10px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        """)
        label.setAlignment(Qt.AlignCenter)
        
        # Value display
        value_label = QLabel("0")
        value_label.setStyleSheet(f"""
            color: {color};
            font-size: 12px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            border: 1px solid {color};
            border-radius: 3px;
            padding: 2px 4px;
            background: rgba(0, 0, 0, 50);
        """)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setMinimumWidth(30)
        
        layout.addWidget(label)
        layout.addWidget(value_label)
        
        # Store reference to value label for updates
        setattr(container, 'value_label', value_label)
        
        return container
        
        # Get RGB values from current image
        try:
            # Convert QPixmap to QImage to read pixel data
            qimage = self.current_image.toImage()
            
            # Clamp coordinates to image bounds
            img_x = max(0, min(img_x, qimage.width() - 1))
            img_y = max(0, min(img_y, qimage.height() - 1))
            
            # Get pixel RGB values
            pixel = qimage.pixel(int(img_x), int(img_y))
            r = (pixel >> 16) & 255
            g = (pixel >> 8) & 255
            b = pixel & 255
            
            # Update sophisticated tooltip display
            # Update coordinate header
            self.coord_header.setText(f"Position: ({int(img_x)}, {int(img_y)})")
            
            # Update individual RGB value displays
            self.r_display.value_label.setText(str(r))
            self.g_display.value_label.setText(str(g))
            self.b_display.value_label.setText(str(b))
            
            # Calculate additional color information
            import colorsys
            
            # Convert RGB to HSV
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            h_deg = int(h * 360)
            s_pct = int(s * 100)
            v_pct = int(v * 100)
            
            # Calculate brightness and hex
            brightness = int((r + g + b) / 3)
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            
            # Update additional info
            additional_text = f"HSV: ({h_deg}°, {s_pct}%, {v_pct}%)\nHex: {hex_color}\nBrightness: {brightness}"
            self.additional_info.setText(additional_text)
            
            # Position tooltip near mouse cursor (ABILIUS-style with better positioning)
            cursor_pos = event.pos()  # Widget coordinates
            tooltip_x = cursor_pos.x() + 20  # Slightly more offset for sophistication
            tooltip_y = cursor_pos.y() - 15  # Slightly above cursor
            
            # Keep tooltip within widget bounds with padding
            widget_rect = self.rect()
            tooltip_size = self.pixel_tooltip.size()
            
            if tooltip_x + tooltip_size.width() > widget_rect.width() - 10:
                tooltip_x = cursor_pos.x() - tooltip_size.width() - 10
            if tooltip_y < 10:
                tooltip_y = cursor_pos.y() + 25  # Below cursor if above doesn't fit
            if tooltip_y + tooltip_size.height() > widget_rect.height() - 10:
                tooltip_y = widget_rect.height() - tooltip_size.height() - 10
                
            self.pixel_tooltip.move(tooltip_x, tooltip_y)
            self.pixel_tooltip.show()
            
        except Exception as e:
            # If pixel reading fails, show error state in sophisticated tooltip
            self.coord_header.setText(f"Position: ({int(img_x)}, {int(img_y)})")
            
            # Show N/A for RGB values with error styling
            self.r_display.value_label.setText("N/A")
            self.g_display.value_label.setText("N/A") 
            self.b_display.value_label.setText("N/A")
            
            # Show error in additional info
            self.additional_info.setText("Pixel data unavailable\nImage processing error")
            
            # Position tooltip (same sophisticated logic as above)
            cursor_pos = event.pos()
            tooltip_x = cursor_pos.x() + 20
            tooltip_y = cursor_pos.y() - 15
            
            widget_rect = self.rect()
            tooltip_size = self.pixel_tooltip.size()
            
            if tooltip_x + tooltip_size.width() > widget_rect.width() - 10:
                tooltip_x = cursor_pos.x() - tooltip_size.width() - 10
            if tooltip_y < 10:
                tooltip_y = cursor_pos.y() + 25
            if tooltip_y + tooltip_size.height() > widget_rect.height() - 10:
                tooltip_y = widget_rect.height() - tooltip_size.height() - 10
                
            self.pixel_tooltip.move(tooltip_x, tooltip_y)
            self.pixel_tooltip.show()
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            # Spacebar pressed - disable point interaction only
            self.space_pressed = True
            # Clear any existing highlight
            if self.highlighted_point_index != -1:
                self.highlighted_point_index = -1
                self.update()
            event.accept()
            return  # Prevent further propagation
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle keyboard release events."""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            # Spacebar released - re-enable point interaction
            self.space_pressed = False
            event.accept()
            return  # Prevent further propagation
        else:
            super().keyReleaseEvent(event)


class ControlPanel(QFrame):
    """Left control panel with all annotation controls."""
    
    image_changed = pyqtSignal(int)  # image_index
    class_changed = pyqtSignal(int)  # class_id
    point_size_changed = pyqtSignal(int)  # point_size
    grid_settings_changed = pyqtSignal(bool, int)  # enabled, size
    overlay_opacity_changed = pyqtSignal(str, float)  # overlay_type, opacity
    pixel_info_toggled = pyqtSignal(bool)  # enabled
    rgb_channels_changed = pyqtSignal(int, int, int)  # r_channel, g_channel, b_channel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(384)  # Increased by 20% for more space
        self.setFrameStyle(QFrame.StyledPanel)
        self.setup_ui()
        self.apply_dark_theme()
        
        # State
        self.current_image = 0
        self.total_images = 0
        
    def setup_ui(self):
        """Setup control panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Navigation removed from left panel - now uses floating overlay + top controls
        
        # Class Selection - Scrollable List with Search
        class_group = QGroupBox("🎨 Class Selection")
        class_layout = QVBoxLayout(class_group)
        class_layout.setSpacing(8)
        
        # Search box
        self.class_search = QLineEdit()
        self.class_search.setPlaceholderText("🔍 Search classes...")
        self.class_search.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #4a5568;
                border-radius: 4px;
                background: #1a202c;
                color: #e2e8f0;
            }
        """)
        self.class_search.textChanged.connect(self.filter_classes)
        class_layout.addWidget(self.class_search)
        
        # Scrollable list widget
        self.class_list = QListWidget()
        self.class_list.setMaximumHeight(220)  # Slightly taller for better visibility
        self.class_list.setStyleSheet("""
            QListWidget {
                background: #1a202c;
                border: 1px solid #4a5568;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #2d3748;
            }
            QListWidget::item:selected {
                background: #374151;
                border: 1px solid #60a5fa;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #2d3748;
                border-radius: 4px;
                background: #374151;
            }
        """)
        
        self.class_items = []
        self.current_class_id = 1  # Start with Building
        
        # Add all classes to list
        for i, (name, color) in enumerate(zip(CLASS_NAMES, CLASS_COLORS)):
            # Create custom widget for each item
            item_widget = QWidget()
            item_widget.setStyleSheet("background: transparent;")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(8)
            
            # Color indicator (circle) - larger and more prominent
            color_label = QLabel()
            r, g, b = color
            color_label.setFixedSize(20, 20)
            border_color = '#ffffff' if i == self.current_class_id else '#4a5568'
            color_label.setStyleSheet(f"""
                background-color: rgb({r}, {g}, {b});
                border-radius: 10px;
                border: 2px solid {border_color};
            """)
            
            # Class index (prominent)
            index_label = QLabel(f"{i}")
            index_label.setFixedWidth(25)
            index_label.setStyleSheet("""
                color: #94a3b8;
                font-size: 12px;
                font-weight: bold;
                font-family: monospace;
            """)
            index_label.setAlignment(Qt.AlignCenter)
            
            # Class name
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #e2e8f0; font-size: 13px;")
            name_label.setMinimumWidth(120)
            
            item_layout.addWidget(color_label)
            item_layout.addWidget(index_label)
            item_layout.addWidget(name_label)
            item_layout.addStretch()
            
            # Store references for later updates
            class_label = name_label  # For compatibility with existing code
            
            # Add to list
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(0, 36))  # Increased height for larger color indicator
            list_item.setData(Qt.UserRole, i)  # Store class ID
            self.class_list.addItem(list_item)
            self.class_list.setItemWidget(list_item, item_widget)
            
            self.class_items.append((list_item, item_widget, color_label, class_label))
        
        # Select initial class
        self.class_list.setCurrentRow(self.current_class_id)
        
        # Connect selection change
        self.class_list.itemClicked.connect(self.on_class_list_clicked)
        
        class_layout.addWidget(self.class_list)
        
        # Add Class button
        add_class_layout = QHBoxLayout()
        self.add_class_button = QPushButton("+ Add Class")
        self.add_class_button.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: white;
                border: 1px solid #047857;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #047857;
            }
        """)
        self.add_class_button.clicked.connect(self.add_new_class)
        add_class_layout.addWidget(self.add_class_button)
        add_class_layout.addStretch()
        class_layout.addLayout(add_class_layout)
        
        # Current class indicator
        self.class_indicator = QLabel("Current: Building")
        self.class_indicator.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px;")
        class_layout.addWidget(self.class_indicator)
        
        layout.addWidget(class_group)
        
        # Display Settings - Refined Icon-Based Categories
        display_group = QGroupBox("🎛️ Display Settings")
        display_layout = QVBoxLayout(display_group)
        display_layout.setSpacing(12)  # More space between categories
        
        # 📊 Visualization Aids Category
        viz_container, viz_layout = self.create_display_section("📊 Visualization Aids")
        
        # Point Size with professional styling
        point_row = QHBoxLayout()
        point_label = QLabel("Point Size")
        point_label.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 65px;")
        point_row.addWidget(point_label)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(4, 20)
        self.size_slider.setValue(8)
        self.size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -5px 0;
            }
        """)
        point_row.addWidget(self.size_slider, 1)
        
        self.size_label = QLabel("8px")
        self.size_label.setFixedWidth(40)
        self.size_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: monospace;")
        point_row.addWidget(self.size_label)
        
        # Connect size slider signal
        self.size_slider.valueChanged.connect(self.on_size_changed)
        
        # Grid with enhanced styling
        grid_row = QHBoxLayout()
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 45px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border: 1px solid #059669;
            }
        """)
        self.grid_checkbox.toggled.connect(self.toggle_grid)
        grid_row.addWidget(self.grid_checkbox)
        
        self.grid_size_slider = QSlider(Qt.Horizontal)
        self.grid_size_slider.setRange(10, 100)
        self.grid_size_slider.setValue(50)
        self.grid_size_slider.setEnabled(False)
        self.grid_size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #10b981;
                border: 1px solid #059669;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        grid_row.addWidget(self.grid_size_slider, 1)
        
        self.grid_size_label = QLabel("50px")
        self.grid_size_label.setFixedWidth(40)
        self.grid_size_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: monospace;")
        grid_row.addWidget(self.grid_size_label)
        
        # Connect grid size slider signal
        self.grid_size_slider.valueChanged.connect(self.on_grid_size_changed)
        
        # Pixel Info toggle
        pixel_info_row = QHBoxLayout()
        self.pixel_info_checkbox = QCheckBox("Pixel Info")
        self.pixel_info_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #f59e0b;
                border: 1px solid #d97706;
            }
        """)
        self.pixel_info_checkbox.setChecked(True)  # Enable by default like ABILIUS
        self.pixel_info_checkbox.toggled.connect(self.toggle_pixel_info)
        pixel_info_row.addWidget(self.pixel_info_checkbox)
        
        cursor_label = QLabel("Cursor tracking")
        cursor_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        pixel_info_row.addWidget(cursor_label)
        
        viz_layout.addLayout(point_row)
        viz_layout.addLayout(grid_row)
        viz_layout.addLayout(pixel_info_row)
        display_layout.addWidget(viz_container)
        
        # 🗺️ Data Layers Category  
        layers_container, layers_layout = self.create_display_section("🗺️ Data Layers")
        
        # Prediction Overlay
        pred_row = QHBoxLayout()
        self.prediction_checkbox = QCheckBox("Prediction")
        self.prediction_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 70px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #8b5cf6;
                border: 1px solid #7c3aed;
            }
        """)
        self.prediction_checkbox.toggled.connect(self.toggle_prediction_overlay)
        pred_row.addWidget(self.prediction_checkbox)
        
        self.pred_opacity_slider = QSlider(Qt.Horizontal)
        self.pred_opacity_slider.setRange(0, 100)
        self.pred_opacity_slider.setValue(50)
        self.pred_opacity_slider.setEnabled(False)
        self.pred_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8b5cf6;
                border: 1px solid #7c3aed;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        pred_row.addWidget(self.pred_opacity_slider, 1)
        
        self.pred_opacity_label = QLabel("50%")
        self.pred_opacity_label.setFixedWidth(40)
        self.pred_opacity_label.setStyleSheet("color: #8b5cf6; font-size: 11px; font-family: monospace;")
        pred_row.addWidget(self.pred_opacity_label)
        
        # Connect prediction opacity slider signal
        self.pred_opacity_slider.valueChanged.connect(self.on_pred_opacity_changed)
        
        # Ground Truth Overlay
        gt_row = QHBoxLayout()
        self.gt_checkbox = QCheckBox("Ground Truth")
        self.gt_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 70px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #f59e0b;
                border: 1px solid #d97706;
            }
        """)
        self.gt_checkbox.toggled.connect(self.toggle_gt_overlay)
        gt_row.addWidget(self.gt_checkbox)
        
        self.gt_opacity_slider = QSlider(Qt.Horizontal)
        self.gt_opacity_slider.setRange(0, 100)
        self.gt_opacity_slider.setValue(30)
        self.gt_opacity_slider.setEnabled(False)
        self.gt_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #f59e0b;
                border: 1px solid #d97706;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        gt_row.addWidget(self.gt_opacity_slider, 1)
        
        self.gt_opacity_label = QLabel("30%")
        self.gt_opacity_label.setFixedWidth(40)
        self.gt_opacity_label.setStyleSheet("color: #f59e0b; font-size: 11px; font-family: monospace;")
        gt_row.addWidget(self.gt_opacity_label)
        
        # Connect GT opacity slider signal
        self.gt_opacity_slider.valueChanged.connect(self.on_gt_opacity_changed)
        
        layers_layout.addLayout(pred_row)
        layers_layout.addLayout(gt_row)
        display_layout.addWidget(layers_container)
        
        # 🎨 Channel Mapping Category
        channels_container, channels_layout = self.create_display_section("🎨 Channel Mapping")
        
        # RGB Channel selector with compact design
        rgb_row = QHBoxLayout()
        rgb_label = QLabel("RGB →")
        rgb_label.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 45px;")
        rgb_row.addWidget(rgb_label)
        
        # R Channel
        self.r_channel_combo = QComboBox()
        self.r_channel_combo.addItems(["0", "1", "2"])
        self.r_channel_combo.setCurrentIndex(0)
        self.r_channel_combo.setFixedWidth(40)
        self.r_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #ef4444;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        # G Channel
        self.g_channel_combo = QComboBox()
        self.g_channel_combo.addItems(["0", "1", "2"])
        self.g_channel_combo.setCurrentIndex(1)
        self.g_channel_combo.setFixedWidth(40)
        self.g_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #10b981;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        # B Channel
        self.b_channel_combo = QComboBox()
        self.b_channel_combo.addItems(["0", "1", "2"])
        self.b_channel_combo.setCurrentIndex(2)
        self.b_channel_combo.setFixedWidth(40)
        self.b_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #3b82f6;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        rgb_row.addWidget(self.r_channel_combo)
        rgb_row.addWidget(self.g_channel_combo)
        rgb_row.addWidget(self.b_channel_combo)
        rgb_row.addStretch()
        
        # Reset button
        reset_btn = QPushButton("🔄")
        reset_btn.setFixedSize(24, 24)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background: #4b5563; }
        """)
        reset_btn.setToolTip("Reset to RGB → 012")
        reset_btn.clicked.connect(lambda: [
            self.r_channel_combo.setCurrentIndex(0),
            self.g_channel_combo.setCurrentIndex(1), 
            self.b_channel_combo.setCurrentIndex(2)
        ])
        rgb_row.addWidget(reset_btn)
        
        # Connect RGB channel change signals
        self.r_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        self.g_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        self.b_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        
        channels_layout.addLayout(rgb_row)
        display_layout.addWidget(channels_container)
        
        layout.addWidget(display_group)
        
        # Statistics Section
        stats_group = QGroupBox("📊 Statistics")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(8)
        
        # Point count statistics
        self.point_count_label = QLabel("Points: 0")
        self.point_count_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 12px;
            font-weight: bold;
        """)
        stats_layout.addWidget(self.point_count_label)
        
        self.total_points_label = QLabel("Total Session: 0")
        self.total_points_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
        """)
        stats_layout.addWidget(self.total_points_label)
        
        layout.addWidget(stats_group)
        
        # Initialize mistake tracking
        self.detected_mistakes = []  # List of image indices with detected mistakes
        self.current_mistake_index = -1  # Current position in mistakes list
    
    def create_display_section(self, title):
        """Create a professional display section with icon and title."""
        section_container = QFrame()
        section_container.setStyleSheet("""
            QFrame {
                background: rgba(55, 65, 81, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(8, 6, 8, 6)
        section_layout.setSpacing(8)
        
        # Section header
        header = QLabel(title)
        header.setStyleSheet("""
            color: #f3f4f6;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 0;
        """)
        section_layout.addWidget(header)
        
        return section_container, section_layout
        
        # Spacer
        layout.addStretch()
        
        # Navigation signals removed - handled by floating overlay + top navigation
        # Class buttons are connected in setup_ui
        self.size_slider.valueChanged.connect(self.on_size_changed)
        
        # Display settings connections
        self.grid_size_slider.valueChanged.connect(self.on_grid_size_changed)
        self.pred_opacity_slider.valueChanged.connect(self.on_pred_opacity_changed)
        self.gt_opacity_slider.valueChanged.connect(self.on_gt_opacity_changed)
        
        # RGB channel connections
        self.r_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        self.g_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        self.b_channel_combo.currentIndexChanged.connect(self.on_rgb_channel_changed)
        
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QFrame {
                background: #1f2937;
                border-right: 1px solid #374151;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #374151;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background: #374151;
                color: #ffffff;
                border: 1px solid #6b7280;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background: #4b5563; }
            QPushButton:pressed { background: #374151; }
            QLabel { color: #ffffff; }
            QComboBox {
                background: #374151;
                color: #ffffff;
                border: 1px solid #6b7280;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit {
                background: #374151;
                color: #ffffff;
                border: 1px solid #6b7280;
                border-radius: 4px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #6b7280;
                height: 8px;
                background: #374151;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #1e40af;
                width: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
        """)
        
    def set_image_info(self, current: int, total: int):
        """Update image navigation info."""
        # Navigation state now managed by external navigation modules
        self.current_image = current
        self.total_images = total
            
    def select_class(self, class_id):
        """Handle class selection."""
        # Update list selection
        self.class_list.setCurrentRow(class_id)
        
        # Update color indicators
        for i, (list_item, item_widget, color_label, class_label) in enumerate(self.class_items):
            r, g, b = CLASS_COLORS[i]
            border_color = '#ffffff' if i == class_id else '#4a5568'
            color_label.setStyleSheet(f"""
                background-color: rgb({r}, {g}, {b});
                border-radius: 8px;
                border: 2px solid {border_color};
            """)
        
        # Update current class
        self.current_class_id = class_id
        self.class_indicator.setText(f"Current: {CLASS_NAMES[class_id]}")
        color = CLASS_COLORS[class_id]
        self.class_indicator.setStyleSheet(f"""
            font-weight: bold; 
            color: rgb({color[0]}, {color[1]}, {color[2]});
            font-size: 12px;
        """)
        self.class_changed.emit(class_id)
    
    def on_class_list_clicked(self, item):
        """Handle class list item click."""
        class_id = item.data(Qt.UserRole)
        if class_id is not None:
            self.select_class(class_id)
    
    def filter_classes(self, search_text):
        """Filter class list based on search text."""
        search_text = search_text.lower()
        
        for i, (list_item, item_widget, color_label, class_label) in enumerate(self.class_items):
            class_name = CLASS_NAMES[i].lower()
            class_str = f"{i}: {class_name}"
            
            # Show/hide based on search match
            if search_text in class_str:
                list_item.setHidden(False)
            else:
                list_item.setHidden(True)
    
    def add_new_class(self):
        """Add a new class to the class list."""
        name, ok = QInputDialog.getText(self, "Add New Class", "Enter class name:")
        if ok and name.strip():
            name = name.strip()
            
            # Add to global configuration
            global CLASS_NAMES, CLASS_COLORS
            new_class_id = len(CLASS_NAMES)
            
            CLASS_NAMES.append(name)
            # Generate a new distinctive color using HSV spread
            import colorsys
            hue = (new_class_id * 0.618033988749895) % 1.0  # Golden ratio for good distribution
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            new_color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            CLASS_COLORS.append(new_color)
            
            # Add to UI list
            self.add_class_to_list(new_class_id, name, new_color)
            
            # Select the new class
            self.select_class(new_class_id)
            
            print(f"[INFO] Added new class {new_class_id}: {name}")
    
    def add_class_to_list(self, class_id, name, color):
        """Add a class to the UI list."""
        # Create custom widget for the item
        item_widget = QWidget()
        item_widget.setStyleSheet("background: transparent;")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 4, 8, 4)
        item_layout.setSpacing(8)
        
        # Color indicator (circle) - larger and more prominent
        color_label = QLabel()
        r, g, b = color
        color_label.setFixedSize(20, 20)
        color_label.setStyleSheet(f"""
            background-color: rgb({r}, {g}, {b});
            border-radius: 10px;
            border: 2px solid #4a5568;
        """)
        
        # Class index (prominent)
        index_label = QLabel(f"{class_id}")
        index_label.setFixedWidth(25)
        index_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 12px;
            font-weight: bold;
            font-family: monospace;
        """)
        index_label.setAlignment(Qt.AlignCenter)
        
        # Class name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        name_label.setMinimumWidth(120)
        
        item_layout.addWidget(color_label)
        item_layout.addWidget(index_label)
        item_layout.addWidget(name_label)
        item_layout.addStretch()
        
        # Store references for later updates
        class_label_widget = name_label  # For compatibility with existing code
        
        # Add to list
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 36))  # Increased height for larger color indicator
        list_item.setData(Qt.UserRole, class_id)
        self.class_list.addItem(list_item)
        self.class_list.setItemWidget(list_item, item_widget)
        
        self.class_items.append((list_item, item_widget, color_label, class_label_widget))
    
    def rebuild_class_list(self):
        """Rebuild the class list UI from current global configuration."""
        # Clear existing items
        self.class_list.clear()
        self.class_items.clear()
        
        # Recreate all class items
        for i, (name, color) in enumerate(zip(CLASS_NAMES, CLASS_COLORS)):
            self.add_class_to_list(i, name, color)
        
        # Reset selection to first class
        if CLASS_NAMES:
            self.select_class(0)
    
    def update_class_config(self, session_config):
        """Update class configuration when session loads."""
        global CLASS_NAMES, CLASS_COLORS, IGNORE_INDEX
        CLASS_NAMES, CLASS_COLORS, IGNORE_INDEX = load_dataset_class_config(session_config)
        
        # Rebuild UI list
        self.rebuild_class_list()
    
    def on_class_changed(self, index):
        """Handle class selection change (for backward compatibility)."""
        self.select_class(index)
        
    def on_size_changed(self, value):
        """Handle point size change."""
        self.size_label.setText(f"{value}px")
        # Update canvas point size (emit signal to parent)
        self.point_size_changed.emit(value)
        
    def on_grid_size_changed(self, value):
        """Handle grid size change."""
        self.grid_size_label.setText(f"{value}px")
        # Update grid if it's enabled
        if self.grid_checkbox.isChecked():
            self.grid_settings_changed.emit(True, value)
    
    def on_pred_opacity_changed(self, value):
        """Handle prediction overlay opacity change."""
        self.pred_opacity_label.setText(f"{value}%")
        # Update overlay opacity
        self.overlay_opacity_changed.emit("prediction", value / 100.0)
    
    def on_gt_opacity_changed(self, value):
        """Handle ground truth overlay opacity change."""
        self.gt_opacity_label.setText(f"{value}%")
        # Update overlay opacity  
        self.overlay_opacity_changed.emit("ground_truth", value / 100.0)
    
    def on_rgb_channel_changed(self):
        """Handle RGB channel mapping change."""
        r_ch = self.r_channel_combo.currentIndex()
        g_ch = self.g_channel_combo.currentIndex() 
        b_ch = self.b_channel_combo.currentIndex()
        self.rgb_channels_changed.emit(r_ch, g_ch, b_ch)
    
    def toggle_grid(self, enabled):
        """Toggle grid overlay."""
        self.grid_size_slider.setEnabled(enabled)
        grid_size = self.grid_size_slider.value()
        self.grid_settings_changed.emit(enabled, grid_size)
        
    def toggle_pixel_info(self, enabled):
        """Toggle pixel info display."""
        self.pixel_info_toggled.emit(enabled)
        # Also directly update the parent canvas if available
        if hasattr(self.parent(), 'canvas') and hasattr(self.parent().canvas, 'toggle_pixel_info_display'):
            self.parent().canvas.toggle_pixel_info_display(enabled)
    
    def toggle_prediction_overlay(self, enabled):
        """Toggle prediction overlay."""
        self.pred_opacity_slider.setEnabled(enabled)
        opacity = self.pred_opacity_slider.value() / 100.0 if enabled else 0.0
        self.overlay_opacity_changed.emit("prediction", opacity)
        
    def toggle_gt_overlay(self, enabled):
        """Toggle ground truth overlay."""
        self.gt_opacity_slider.setEnabled(enabled)
        opacity = self.gt_opacity_slider.value() / 100.0 if enabled else 0.0
        self.overlay_opacity_changed.emit("ground_truth", opacity)
        
    def update_statistics(self, current_points: int, total_points: int):
        """Update point count statistics."""
        self.point_count_label.setText(f"Points: {current_points}")
        self.total_points_label.setText(f"Total Session: {total_points}")
    
    def on_auto_detect_mistakes_changed(self, enabled):
        """Handle auto-detect mistakes toggle."""
        self.confidence_threshold.setEnabled(enabled)
        
        if enabled:
            print("[INFO] Auto-detect mistakes enabled")
            self.detect_model_mistakes()
        else:
            print("[INFO] Auto-detect mistakes disabled")
            self.detected_mistakes.clear()
            self.current_mistake_index = -1
            self.update_mistake_navigation()
    
    def on_confidence_threshold_changed(self, value):
        """Handle confidence threshold change."""
        self.confidence_label.setText(f"{value}%")
        
        # Re-detect mistakes with new threshold if auto-detect is enabled
        if self.auto_detect_mistakes.isChecked():
            self.detect_model_mistakes()
    
    def detect_model_mistakes(self):
        """Detect model mistakes based on prediction confidence."""
        if not hasattr(self, 'image_list') or not self.image_list:
            return
        
        confidence_threshold = self.confidence_threshold.value() / 100.0
        mistakes = []
        
        # For now, simulate mistake detection
        # In a real implementation, this would analyze prediction confidence maps
        import random
        random.seed(42)  # For reproducible results
        
        for i, image_path in enumerate(self.image_list):
            # Simulate confidence analysis (replace with actual model confidence analysis)
            simulated_confidence = random.uniform(0.3, 0.98)
            
            if simulated_confidence < confidence_threshold:
                mistakes.append(i)
        
        self.detected_mistakes = mistakes
        self.current_mistake_index = -1
        self.update_mistake_navigation()
        
        print(f"[INFO] Detected {len(mistakes)} potential mistakes with {confidence_threshold:.0%} confidence threshold")
    
    def update_mistake_navigation(self):
        """Update mistake navigation UI state."""
        has_mistakes = len(self.detected_mistakes) > 0
        
        self.prev_mistake_btn.setEnabled(has_mistakes)
        self.next_mistake_btn.setEnabled(has_mistakes)
        
        if has_mistakes:
            current_pos = self.current_mistake_index + 1 if self.current_mistake_index >= 0 else 0
            self.mistake_counter_label.setText(f"{current_pos}/{len(self.detected_mistakes)} mistakes")
        else:
            self.mistake_counter_label.setText("No mistakes")
    
    def go_to_previous_mistake(self):
        """Navigate to previous detected mistake."""
        if not self.detected_mistakes:
            return
        
        if self.current_mistake_index <= 0:
            # Wrap around to last mistake
            self.current_mistake_index = len(self.detected_mistakes) - 1
        else:
            self.current_mistake_index -= 1
        
        mistake_image_index = self.detected_mistakes[self.current_mistake_index]
        self.navigate_to_mistake(mistake_image_index)
    
    def go_to_next_mistake(self):
        """Navigate to next detected mistake."""
        if not self.detected_mistakes:
            return
        
        if self.current_mistake_index >= len(self.detected_mistakes) - 1:
            # Wrap around to first mistake
            self.current_mistake_index = 0
        else:
            self.current_mistake_index += 1
        
        mistake_image_index = self.detected_mistakes[self.current_mistake_index]
        self.navigate_to_mistake(mistake_image_index)
    
    def navigate_to_mistake(self, image_index):
        """Navigate to a specific image with detected mistakes."""
        if hasattr(self.parent(), 'load_image_by_index'):
            self.parent().load_image_by_index(image_index)
            print(f"[INFO] Navigated to mistake at image {image_index}")
        
        self.update_mistake_navigation()
    
    def mark_current_as_reviewed(self):
        """Mark current mistake as reviewed (remove from list)."""
        if self.current_mistake_index >= 0 and self.current_mistake_index < len(self.detected_mistakes):
            removed_index = self.detected_mistakes.pop(self.current_mistake_index)
            
            # Adjust current index
            if self.current_mistake_index >= len(self.detected_mistakes):
                self.current_mistake_index = len(self.detected_mistakes) - 1
            
            self.update_mistake_navigation()
            print(f"[INFO] Marked image {removed_index} as reviewed")


class StatusPanel(QFrame):
    """Right status panel with image and annotation info."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(384)  # Now matches left panel width
        self.setFrameStyle(QFrame.StyledPanel)
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup status panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Mini-Map
        minimap_group = QGroupBox("🗺️ Mini-Map")
        minimap_layout = QVBoxLayout(minimap_group)
        
        self.minimap_widget = MinimapWidget()
        minimap_layout.addWidget(self.minimap_widget)
        
        layout.addWidget(minimap_group)
        
        # Image Info
        image_group = QGroupBox("📸 Image Info")
        image_layout = QVBoxLayout(image_group)
        
        self.filename_label = QLabel("File: -")
        self.resolution_label = QLabel("Size: -")
        self.format_label = QLabel("Format: -")
        
        image_layout.addWidget(self.filename_label)
        image_layout.addWidget(self.resolution_label)
        image_layout.addWidget(self.format_label)
        
        layout.addWidget(image_group)
        
        # Annotation Info
        annot_group = QGroupBox("🎯 Annotations")
        annot_layout = QVBoxLayout(annot_group)
        
        self.points_label = QLabel("Points: 0")
        self.classes_label = QLabel("Classes: 0")
        
        annot_layout.addWidget(self.points_label)
        annot_layout.addWidget(self.classes_label)
        
        layout.addWidget(annot_group)
        
        # Session Progress
        progress_group = QGroupBox("📊 Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% (%v/%m)")
        progress_layout.addWidget(self.progress_bar)
        
        self.time_label = QLabel("Time: 00:00")
        progress_layout.addWidget(self.time_label)
        
        layout.addWidget(progress_group)
        
        # Spacer
        layout.addStretch()
        
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QFrame {
                background: #1f2937;
                border-left: 1px solid #374151;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #374151;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel { 
                color: #ffffff; 
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #374151;
                border-radius: 4px;
                background: #374151;
                color: #ffffff;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #3b82f6;
                border-radius: 3px;
            }
        """)
        
    def update_image_info(self, filename: str, width: int = 0, height: int = 0, format_str: str = ""):
        """Update image information display."""
        self.filename_label.setText(f"File: {Path(filename).name}")
        if width and height:
            self.resolution_label.setText(f"Size: {width}×{height}")
        if format_str:
            self.format_label.setText(f"Format: {format_str}")
            
    def update_annotation_info(self, point_count: int, class_count: int):
        """Update annotation information."""
        self.points_label.setText(f"Points: {point_count}")
        self.classes_label.setText(f"Classes: {class_count}")
        
    def update_progress(self, current: int, total: int):
        """Update session progress."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current + 1)


class FooterBar(QFrame):
    """Footer status bar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup footer bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.coords_label = QLabel("Coordinates: -")
        layout.addWidget(self.coords_label)
        
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QFrame {
                background: #1f2937;
                border-top: 1px solid #374151;
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
            }
        """)
        
    def update_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)
        
    def update_coordinates(self, x: int, y: int):
        """Update mouse coordinates."""
        self.coords_label.setText(f"Coordinates: ({x}, {y})")


class AnnotationWidget(QWidget):
    """
    Working ABILIUS-style annotation widget that provides a complete
    annotation interface without depending on problematic modular components.
    """
    
    # Required signals for integration with redesigned widget
    modeExitRequested = pyqtSignal()
    annotationChanged = pyqtSignal(str, dict)  # image_name, annotation_data
    sessionUpdated = pyqtSignal(dict)  # session_stats
    
    def __init__(self, session_manager=None, active_learning_system=None, parent=None):
        super().__init__(parent)
        
        # Core components
        self.session_manager = session_manager
        self.al_system = active_learning_system
        self.annotation_manager = None
        
        # State
        self.image_list = []
        self.current_image_index = 0
        self.current_annotations = []
        self.point_timestamps = []  # Track timestamps for efficient JSON saving
        self.session_path = None
        
        # Setup
        try:
            self.setup_ui()
            self.setup_connections()
            self.setup_keyboard_shortcuts()
            self.initialize_session()
            
            logger.info("Working ABILIUS annotation widget initialized")
            logger.info(f"Widget size: {self.size()}")
            logger.info(f"Widget visible: {self.isVisible()}")
            
            # Only log component visibility if they exist
            if hasattr(self, 'header'):
                logger.info(f"Header visible: {self.header.isVisible()}")
            if hasattr(self, 'footer'):
                logger.info(f"Footer visible: {self.footer.isVisible()}")
            if hasattr(self, 'canvas'):
                logger.info(f"Canvas visible: {self.canvas.isVisible()}")
            else:
                logger.warning("Canvas attribute not found after setup_ui!")
            
            # Open annotation mode in fullscreen (maximized)
            self.showMaximized()
                
        except Exception as e:
            logger.error(f"Error during widget initialization: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    def update_zoom_display(self, zoom_factor: float):
        """Update the zoom display in the controls bar."""
        if hasattr(self, 'zoom_label'):
            percentage = int(zoom_factor * 100)
            self.zoom_label.setText(f"{percentage}%")
        
    def setup_ui(self):
        """Setup the main UI layout."""
        logger.debug("Starting setup_ui...")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header bar (simplified for standalone annotation window)
        logger.debug("Creating annotation header...")
        self.header = AnnotationHeaderBar()  # Simpler header without breadcrumbs
        layout.addWidget(self.header)
        logger.debug("Annotation header created")
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left control panel
        self.control_panel = ControlPanel()
        main_splitter.addWidget(self.control_panel)
        
        # Central canvas area
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(5, 5, 5, 5)
        
        # Canvas controls bar
        controls_bar = QFrame()
        controls_bar.setFixedHeight(40)
        controls_bar.setStyleSheet("background: #374151; border: 1px solid #4b5563;")
        controls_layout = QHBoxLayout(controls_bar)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        self.zoom_out_btn = QPushButton("🔍−")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.setStyleSheet("""
            QPushButton {
                background: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background: #9ca3af; }
        """)
        # Connect zoom signal later after canvas is created
        zoom_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        zoom_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.setStyleSheet("""
            QPushButton {
                background: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background: #9ca3af; }
        """)
        # Connect zoom signal later after canvas is created
        zoom_layout.addWidget(self.zoom_in_btn)
        
        self.reset_zoom_btn = QPushButton("⚏ Fit")
        self.reset_zoom_btn.setFixedSize(50, 30)
        self.reset_zoom_btn.setStyleSheet("""
            QPushButton {
                background: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background: #9ca3af; }
        """)
        # Connect zoom signal later after canvas is created
        zoom_layout.addWidget(self.reset_zoom_btn)
        
        controls_layout.addLayout(zoom_layout)
        controls_layout.addStretch()
        
        # Image name instead of "No image loaded"
        self.canvas_info = QLabel("Image: 0.png")
        self.canvas_info.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        controls_layout.addWidget(self.canvas_info)
        
        # Add spacer
        controls_layout.addSpacing(20)
        
        # Add top navigation module (Go field) to controls bar
        self.top_nav = TopNavigationModule()
        controls_layout.addWidget(self.top_nav)
        
        canvas_layout.addWidget(controls_bar)
        
        # Annotation canvas
        logger.debug("Creating annotation canvas...")
        self.canvas = SimpleAnnotationCanvas()
        canvas_layout.addWidget(self.canvas)
        logger.debug("Canvas created successfully")
        
        # Navigation module will be added to canvas controls bar instead
        
        logger.debug("Top navigation module added successfully")
        
        # Now connect zoom button signals after canvas is created
        self.zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        self.zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        self.reset_zoom_btn.clicked.connect(self.canvas.reset_zoom)
        
        main_splitter.addWidget(canvas_widget)
        
        # Right status panel
        self.status_panel = StatusPanel()
        main_splitter.addWidget(self.status_panel)
        
        # Set splitter proportions - wider equal left and right panels
        main_splitter.setSizes([384, 552, 384])
        layout.addWidget(main_splitter)
        
        # Bottom navigation panel (full width like header bar)
        self.bottom_nav_panel = BottomNavigationPanel()
        layout.addWidget(self.bottom_nav_panel)
        
        # Footer bar
        self.footer = FooterBar()
        layout.addWidget(self.footer)
        
        # Apply global dark theme
        self.setStyleSheet("""
            QWidget {
                background: #111827;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
    
    def setup_connections(self):
        """Setup signal connections."""
        # Control panel connections  
        self.control_panel.class_changed.connect(self.canvas.set_current_class)
        self.control_panel.point_size_changed.connect(self.canvas.set_point_size)
        self.control_panel.grid_settings_changed.connect(self.canvas.set_grid_settings)
        self.control_panel.pixel_info_toggled.connect(self.canvas.set_pixel_info_enabled)
        self.control_panel.overlay_opacity_changed.connect(self.canvas.set_overlay_settings)
        self.control_panel.rgb_channels_changed.connect(self.canvas.set_rgb_channels)
        
        # Canvas connections
        self.canvas.point_added.connect(self.on_point_added)
        self.canvas.point_removed.connect(self.on_point_removed)
        self.canvas.point_moved.connect(self.on_point_moved)
        
        # Connect canvas mouse tracking for coordinates
        if hasattr(self.canvas, 'mouseMoveEvent'):
            # Enable mouse tracking for coordinates
            self.canvas.setMouseTracking(True)
        
        # Connect canvas signals to bottom navigation panel updates
        self.canvas.point_added.connect(self.update_action_display_added)
        self.canvas.point_removed.connect(self.update_action_display_removed)
        self.canvas.point_moved.connect(self.update_action_display_moved)
        
        # Connect mouse coordinates to bottom panel
        self.canvas.mouse_coordinates.connect(self.bottom_nav_panel.update_coordinates)
        
        # Connect minimap
        self.status_panel.minimap_widget.viewChanged.connect(self.on_minimap_navigation)
        
        # Connect canvas signals to update minimap
        self.canvas.image_loaded.connect(self.on_canvas_image_loaded)
        self.canvas.view_changed.connect(self.update_minimap_view)
        
        # Modular navigation connections - ultra minimal
        self.bottom_nav_panel.previousRequested.connect(self.previous_image)
        self.bottom_nav_panel.nextRequested.connect(self.next_image)
        self.top_nav.goToImageRequested.connect(self.load_image_by_index)
        
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Navigation shortcuts handled by bottom navigation panel
        
        # Class selection shortcuts
        for i in range(1, 8):  # 1-7 for classes
            if i <= len(CLASS_NAMES):
                QShortcut(QKeySequence(str(i)), self, 
                         lambda i=i-1: self.control_panel.select_class(i))
        
        # Exit shortcut
        QShortcut(QKeySequence("Escape"), self, self.request_exit)
        
        # Zoom shortcuts
        QShortcut(QKeySequence("Ctrl++"), self, self.canvas.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.canvas.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.canvas.reset_zoom)
                         
    def initialize_session(self):
        """Initialize the session and load images."""
        logger.info(f"Initializing session: session_manager={self.session_manager is not None}")
        
        if self.session_manager:
            try:
                # Get session path
                if not hasattr(self.session_manager, 'current_session_path') or not self.session_manager.current_session_path:
                    logger.error("Session manager has no current_session_path")
                    self.footer.update_status("No session path available")
                    return
                    
                self.session_path = Path(self.session_manager.current_session_path)
                session_name = self.session_path.name
                logger.info(f"Session path: {self.session_path}")
                
                if not self.session_path.exists():
                    logger.error(f"Session path does not exist: {self.session_path}")
                    self.footer.update_status(f"Session path not found: {self.session_path}")
                    return
                
                # Update header
                self.header.update_session_info(session_name)
                
                # Load image list
                self.load_image_list()
                
                # Load first image
                if self.image_list:
                    logger.info(f"Loading first image from {len(self.image_list)} total images")
                    self.load_image_by_index(0)
                    self.footer.update_status(f"Loaded session: {session_name} ({len(self.image_list)} images)")
                else:
                    logger.warning("No images found in session")
                    self.footer.update_status(f"Loaded session: {session_name} (no images found)")
                    # Show empty state in canvas
                    self.canvas.show_empty_state("No images available in this session")
                
            except Exception as e:
                logger.error(f"Failed to initialize session: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.footer.update_status(f"Session initialization failed: {e}")
        else:
            logger.warning("No session manager provided")
            self.footer.update_status("No session manager provided")
            # Show empty state for no session
            self.canvas.show_empty_state("No session loaded")
            self.header.update_session_info("No Session")
            
    def load_image_list(self):
        """Load the list of images from session."""
        if not self.session_path:
            logger.warning("No session path available for loading images")
            return
            
        images_dir = self.session_path / "data" / "dataset" / "train" / "images"
        logger.info(f"Looking for images in: {images_dir}")
        
        if not images_dir.exists():
            logger.warning(f"Images directory not found: {images_dir}")
            # Let's check what directories do exist
            if self.session_path.exists():
                logger.info(f"Session path exists. Contents: {list(self.session_path.iterdir())}")
                dataset_dir = self.session_path / "dataset"
                if dataset_dir.exists():
                    logger.info(f"Dataset dir exists. Contents: {list(dataset_dir.iterdir())}")
            return
            
        # Get all PNG files and sort numerically
        image_files = list(images_dir.glob("*.png"))
        
        # Sort by numeric value of filename (0.png, 1.png, ..., 10.png, etc.)
        def numeric_sort_key(path):
            try:
                return int(path.stem)
            except ValueError:
                return float('inf')  # Put non-numeric files at the end
                
        image_files.sort(key=numeric_sort_key)
        
        self.image_list = [str(f) for f in image_files]
        logger.info(f"Loaded {len(self.image_list)} images from {images_dir}")
        
        if self.image_list:
            logger.info(f"First 3 images: {[Path(p).name for p in self.image_list[:3]]}")
        else:
            logger.warning(f"No images found in {images_dir}")
            logger.info(f"Directory contents: {list(images_dir.iterdir()) if images_dir.exists() else 'Directory does not exist'}")
        
        # Update control panel
        if self.image_list:
            self.control_panel.set_image_info(0, len(self.image_list))
            self.status_panel.update_progress(0, len(self.image_list))
            
    def load_image_by_index(self, index: int):
        """Load image by index."""
        if not self.image_list or not (0 <= index < len(self.image_list)):
            return
            
        self.current_image_index = index
        image_path = self.image_list[index]
        
        # Load image in canvas
        success = self.canvas.load_image(image_path)
        if success:
            # Update UI
            self.control_panel.set_image_info(index, len(self.image_list))
            self.status_panel.update_progress(index, len(self.image_list))
            
            # Update modular navigation components
            self.bottom_nav_panel.update_navigation_state(index, len(self.image_list))
            self.top_nav.update_navigation_state(index, len(self.image_list), self.image_list)
            
            # Get image info
            filename = Path(image_path).name
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    format_str = img.format
                self.status_panel.update_image_info(filename, width, height, format_str)
            except:
                self.status_panel.update_image_info(filename)
                
            self.canvas_info.setText(f"Image: {filename}")
            
            # Load annotations for this image
            self.load_image_annotations(Path(image_path).stem)
            
            self.footer.update_status(f"Loaded image: {filename}")
            
    def load_image_annotations(self, image_stem: str):
        """Load annotations for a specific image."""
        if not self.session_path:
            return
            
        # Determine current iteration (default to 0)
        current_iteration = 0
        
        # Load annotations from JSON file in iterations format
        annotations_file = (self.session_path / "iterations" / f"iteration_{current_iteration}" /
                          "annotations" / "json" / f"{image_stem}.json")

        logger.info(f"Loading annotations from: {annotations_file}")
        annotations = []
        if annotations_file.exists():
            try:
                with open(annotations_file, 'r') as f:
                    data = json.load(f)

                # Use the iterations format: annotations are directly in data["annotations"]
                if "annotations" in data:
                    annotations = data["annotations"]
                    logger.info(f"Loaded {len(annotations)} annotation points: {annotations}")

                    # Create timestamps for existing points (iterations format doesn't store timestamps)
                    import datetime
                    self.point_timestamps = [datetime.datetime.now().isoformat() for _ in annotations]
                else:
                    logger.warning(f"No 'annotations' key found in {annotations_file}")

            except Exception as e:
                logger.error(f"Failed to load annotations from {annotations_file}: {e}")
        else:
            logger.warning(f"Annotation file does not exist: {annotations_file}")
        
        # Update canvas and UI - CRITICAL: Keep both in sync
        self.current_annotations = annotations.copy()
        self.canvas.load_annotations(annotations)
        logger.info(f"Updated canvas with {len(annotations)} annotations")
        
        # Ensure timestamps list matches annotations length
        while len(self.point_timestamps) < len(self.current_annotations):
            import datetime
            self.point_timestamps.append(datetime.datetime.now().isoformat())
        
        # Trim excess timestamps
        self.point_timestamps = self.point_timestamps[:len(self.current_annotations)]
        
        # Update statistics
        point_count = len(annotations)
        unique_classes = len(set(point[2] for point in annotations)) if annotations else 0
        self.status_panel.update_annotation_info(point_count, unique_classes)
        
        # Calculate total points in session
        total_points = self.calculate_total_session_points()
        self.control_panel.update_statistics(point_count, total_points)
        
    def calculate_total_session_points(self):
        """Calculate total points across all images in session."""
        if not self.session_path:
            return 0
            
        total = 0
        annotations_dir = self.session_path / "annotations" / "points" / "iteration_0"
        
        if annotations_dir.exists():
            for json_file in annotations_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    if "annotations" in data and "points" in data["annotations"]:
                        total += len(data["annotations"]["points"])
                except:
                    continue
                    
        return total
    
    def update_action_display_added(self, x: float, y: float, class_id: int):
        """Update bottom panel action display when point is added."""
        class_name = self.get_class_name(class_id)
        self.bottom_nav_panel.update_latest_action(f"Added point: {class_name}")
        
    def update_action_display_removed(self, x: float, y: float):
        """Update bottom panel action display when point is removed."""
        self.bottom_nav_panel.update_latest_action(f"Removed point")
        
    def update_action_display_moved(self, old_x: float, old_y: float, new_x: float, new_y: float):
        """Update bottom panel action display when point is moved."""
        self.bottom_nav_panel.update_latest_action(f"Moved point")
    
    def get_class_name(self, class_id: int) -> str:
        """Get class name from class ID."""
        class_names = {
            0: "class 0", 1: "class 1", 2: "class 2", 
            3: "class 3", 4: "class 4", 5: "class 5", 6: "class 6"
        }
        return class_names.get(class_id, f"class {class_id}")
    
    def on_canvas_image_loaded(self):
        """Handle canvas image loaded signal - update minimap."""
        if hasattr(self.canvas, 'current_image') and self.canvas.current_image:
            self.status_panel.minimap_widget.update_image(self.canvas.current_image)
            self.update_minimap_view()
    
    def on_minimap_navigation(self, pan_x: int, pan_y: int):
        """Handle navigation from minimap clicks - VIEW ONLY, no coordinate changes."""
        # CRITICAL: Only update view, never touch annotation coordinates
        self.canvas.pan_offset_x = pan_x
        self.canvas.pan_offset_y = pan_y
        # Only update visual display, don't affect any annotation data
        self.canvas.update()  # Just repaint, no coordinate changes
        self.update_minimap_view()
    
    def update_minimap_view(self):
        """Update minimap view rectangle."""
        if hasattr(self.status_panel, 'minimap_widget') and hasattr(self.canvas, 'current_image'):
            self.status_panel.minimap_widget.update_view(
                self.canvas.size(),
                self.canvas.zoom_factor,
                self.canvas.pan_offset_x,
                self.canvas.pan_offset_y
            )
        
    def on_point_added(self, x: float, y: float, class_id: int):
        """Handle point addition."""
        # Add to current annotations
        self.current_annotations.append([x, y, class_id])
        
        # Add timestamp for this point
        import datetime
        self.point_timestamps.append(datetime.datetime.now().isoformat())
        
        # Save to file
        self.save_current_annotations()
        
        # Update statistics
        point_count = len(self.current_annotations)
        unique_classes = len(set(point[2] for point in self.current_annotations))
        self.status_panel.update_annotation_info(point_count, unique_classes)
        
        total_points = self.calculate_total_session_points()
        self.control_panel.update_statistics(point_count, total_points)
        
        self.footer.update_status(f"Added point: class {class_id}")
        
        # Emit signals
        self.emit_annotation_changed({"action": "point_added", "x": x, "y": y, "class_id": class_id})
        self.emit_session_updated()
        
    def on_point_removed(self, x: float, y: float):
        """Handle point removal."""
        # CRITICAL: Sync main annotations with canvas annotations after removal
        old_count = len(self.current_annotations)
        self.current_annotations = self.canvas.annotations.copy()
        new_count = len(self.current_annotations)
        
        # Sync timestamps - remove timestamps for deleted points
        if new_count < old_count:
            # Keep only timestamps for remaining points (assuming last point was removed)
            self.point_timestamps = self.point_timestamps[:new_count]
        
        # Save to file
        self.save_current_annotations()
        
        # Update statistics
        point_count = len(self.current_annotations)
        unique_classes = len(set(point[2] for point in self.current_annotations)) if self.current_annotations else 0
        self.status_panel.update_annotation_info(point_count, unique_classes)
        
        total_points = self.calculate_total_session_points()
        self.control_panel.update_statistics(point_count, total_points)
        
        self.footer.update_status("Removed point")
        
        # Emit signals
        self.emit_annotation_changed({"action": "point_removed", "x": x, "y": y})
        self.emit_session_updated()
        
    def on_point_moved(self, old_x: float, old_y: float, new_x: float, new_y: float):
        """Handle point drag/move operations."""
        # CRITICAL: Sync main annotations with canvas annotations after move
        self.current_annotations = self.canvas.annotations.copy()
        
        # Save to file
        self.save_current_annotations()
        
        # Update statistics (no change in count, but update display)
        point_count = len(self.current_annotations)
        unique_classes = len(set(point[2] for point in self.current_annotations)) if self.current_annotations else 0
        self.status_panel.update_annotation_info(point_count, unique_classes)
        
        self.footer.update_status(f"Moved point from ({old_x:.0f}, {old_y:.0f}) to ({new_x:.0f}, {new_y:.0f})")
        
        # Emit signals
        self.emit_annotation_changed({
            "action": "point_moved", 
            "old_x": old_x, "old_y": old_y, 
            "new_x": new_x, "new_y": new_y
        })
        self.emit_session_updated()
        
    def request_exit(self):
        """Request to exit annotation mode and return to mode grid."""
        self.modeExitRequested.emit()
        
    def emit_annotation_changed(self, annotation_data: dict):
        """Emit annotation changed signal."""
        if self.current_image_index < len(self.image_list):
            image_path = Path(self.image_list[self.current_image_index])
            self.annotationChanged.emit(image_path.stem, annotation_data)
            
    def emit_session_updated(self):
        """Emit session updated signal with current statistics."""
        stats = {
            "total_images": len(self.image_list),
            "current_image": self.current_image_index + 1,
            "total_points": self.calculate_total_session_points(),
            "current_points": len(self.current_annotations)
        }
        self.sessionUpdated.emit(stats)
        
    def save_current_annotations(self):
        """Save current annotations to JSON file."""
        if not self.session_path or self.current_image_index >= len(self.image_list):
            return
            
        # Get current image info
        image_path = Path(self.image_list[self.current_image_index])
        image_stem = image_path.stem
        
        # Prepare annotations data
        import datetime
        
        annotations_data = {
            "version": "1.0",
            "image_name": image_stem,
            "format": "optimized_array",
            "annotations": {
                "points": self.current_annotations,
                "extended": {
                    "dense_gt": [point[2] for point in self.current_annotations],
                    "timestamp": self.point_timestamps.copy(),
                    "iteration_added": [0 for _ in self.current_annotations]
                }
            },
            "metadata": {
                "source": "abilius_annotation_tool",
                "created_at": datetime.datetime.now().isoformat(),
                "total_points": len(self.current_annotations),
                "has_dense_gt": True,
                "pixel_extraction": True,
                "ignore_index": 6
            }
        }
        
        # Save to file
        annotations_file = (self.session_path / "annotations" / "points" / 
                          "iteration_0" / f"{image_stem}.json")
        
        try:
            annotations_file.parent.mkdir(parents=True, exist_ok=True)
            with open(annotations_file, 'w') as f:
                json.dump(annotations_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save annotations to {annotations_file}: {e}")
            self.footer.update_status(f"Save failed: {e}")
    
    def verify_json_sync(self):
        """Verify that canvas and JSON are in sync - for debugging."""
        canvas_count = len(self.canvas.annotations)
        main_count = len(self.current_annotations)
        
        if canvas_count != main_count:
            logger.warning(f"SYNC ISSUE: Canvas has {canvas_count} points, main has {main_count}")
            return False
            
        # Check if content matches
        canvas_points = set(tuple(p) for p in self.canvas.annotations)
        main_points = set(tuple(p) for p in self.current_annotations)
        
        if canvas_points != main_points:
            logger.warning("SYNC ISSUE: Canvas and main annotations content differs")
            return False
            
        logger.info(f"✅ JSON sync verified: {canvas_count} points in sync")
        return True
            
    def previous_image(self):
        """Navigate to previous image with circular navigation."""
        if len(self.image_list) > 1:
            if self.current_image_index > 0:
                self.load_image_by_index(self.current_image_index - 1)
            else:
                # Wrap to last image (circular navigation)
                self.load_image_by_index(len(self.image_list) - 1)
            
    def next_image(self):
        """Navigate to next image with circular navigation."""
        if len(self.image_list) > 1:
            if self.current_image_index < len(self.image_list) - 1:
                self.load_image_by_index(self.current_image_index + 1)
            else:
                # Wrap to first image (circular navigation)
                self.load_image_by_index(0)
            
    def random_image(self):
        """Navigate to random image."""
        import random
        if self.image_list:
            random_idx = random.randint(0, len(self.image_list) - 1)
            self.load_image_by_index(random_idx)


# Backward compatibility alias
WorkingAbiliusAnnotateWidget = AnnotationWidget