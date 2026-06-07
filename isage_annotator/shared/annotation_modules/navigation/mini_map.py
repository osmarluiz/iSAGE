"""
Mini-map Navigation Component

Provides visual overview of large images with viewport indicators and navigation.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QPixmap, QImage, QMouseEvent
    )
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QWidget: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

import numpy as np
from typing import Optional, Tuple
from pathlib import Path


class MiniMapWidget(QWidget):
    """
    Mini-map widget showing overview of large images with viewport indicators.
    
    Features:
    - Thumbnail display of current image
    - Viewport rectangle showing current view
    - Click-to-navigate functionality
    - Zoom level indicators
    - Professional styling
    """
    
    # Signals
    navigate_requested = pyqtSignal(float, float)  # relative_x, relative_y (0-1)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 150)
        
        # Image and viewport state
        self.original_image = None
        self.thumbnail = None
        self.viewport_rect = QRect(0, 0, 100, 100)  # Viewport in thumbnail coordinates
        self.zoom_factor = 1.0
        
        # Styling
        self.setup_styling()
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
    def setup_styling(self):
        """Set up the mini-map styling."""
        self.setStyleSheet("""
            MiniMapWidget {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                border-radius: 8px;
            }
            MiniMapWidget:hover {
                border-color: #3b82f6;
            }
        """)
    
    def set_image(self, image: QImage):
        """Set the image to display in the mini-map."""
        if image is None:
            self.original_image = None
            self.thumbnail = None
            self.update()
            return
            
        self.original_image = image
        
        # Create thumbnail maintaining aspect ratio
        thumbnail_size = 140  # Leave 10px margin
        self.thumbnail = image.scaled(
            thumbnail_size, thumbnail_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Initialize viewport to full image
        self.viewport_rect = QRect(0, 0, self.thumbnail.width(), self.thumbnail.height())
        
        self.update()
    
    def update_viewport(self, viewport_x: float, viewport_y: float, 
                       viewport_width: float, viewport_height: float, zoom_factor: float):
        """
        Update the viewport rectangle.
        
        Args:
            viewport_x, viewport_y: Viewport center (0-1 relative to image)
            viewport_width, viewport_height: Viewport size (0-1 relative to image)
            zoom_factor: Current zoom level
        """
        if self.thumbnail is None:
            return
            
        self.zoom_factor = zoom_factor
        
        # Convert relative coordinates to thumbnail coordinates
        thumb_width = self.thumbnail.width()
        thumb_height = self.thumbnail.height()
        
        # Calculate viewport rectangle in thumbnail coordinates
        rect_width = thumb_width * viewport_width
        rect_height = thumb_height * viewport_height
        
        rect_x = (viewport_x * thumb_width) - (rect_width / 2)
        rect_y = (viewport_y * thumb_height) - (rect_height / 2)
        
        # Ensure rectangle stays within bounds
        rect_x = max(0, min(rect_x, thumb_width - rect_width))
        rect_y = max(0, min(rect_y, thumb_height - rect_height))
        
        self.viewport_rect = QRect(int(rect_x), int(rect_y), int(rect_width), int(rect_height))
        self.update()
    
    def paintEvent(self, event):
        """Paint the mini-map."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        if self.thumbnail is None:
            # Draw placeholder
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, "No Image")
            return
        
        # Calculate centered position for thumbnail
        thumb_x = (self.width() - self.thumbnail.width()) // 2
        thumb_y = (self.height() - self.thumbnail.height()) // 2
        
        # Draw thumbnail
        painter.drawImage(thumb_x, thumb_y, self.thumbnail)
        
        # Draw viewport rectangle
        viewport_rect = QRect(
            thumb_x + self.viewport_rect.x(),
            thumb_y + self.viewport_rect.y(),
            self.viewport_rect.width(),
            self.viewport_rect.height()
        )
        
        # Viewport outline
        painter.setPen(QPen(QColor(59, 130, 246), 2))  # Blue
        painter.setBrush(QBrush(QColor(59, 130, 246, 50)))  # Semi-transparent blue
        painter.drawRect(viewport_rect)
        
        # Draw zoom level indicator
        if self.zoom_factor > 1.0:
            zoom_text = f"{self.zoom_factor:.1f}x"
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(5, 15, zoom_text)
        
        # Draw navigation hint
        if self.rect().contains(self.mapFromGlobal(self.cursor().pos())):
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
            painter.drawText(5, self.height() - 5, "Click to navigate")
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks for navigation."""
        if event.button() == Qt.LeftButton and self.thumbnail is not None:
            # Calculate click position relative to thumbnail
            thumb_x = (self.width() - self.thumbnail.width()) // 2
            thumb_y = (self.height() - self.thumbnail.height()) // 2
            
            click_x = event.x() - thumb_x
            click_y = event.y() - thumb_y
            
            # Check if click is within thumbnail bounds
            if (0 <= click_x < self.thumbnail.width() and 
                0 <= click_y < self.thumbnail.height()):
                
                # Convert to relative coordinates (0-1)
                relative_x = click_x / self.thumbnail.width()
                relative_y = click_y / self.thumbnail.height()
                
                # Emit navigation signal
                self.navigate_requested.emit(relative_x, relative_y)
        
        super().mousePressEvent(event)
    
    def get_viewport_center(self) -> Tuple[float, float]:
        """Get the current viewport center as relative coordinates."""
        if self.thumbnail is None:
            return 0.5, 0.5
            
        center_x = (self.viewport_rect.x() + self.viewport_rect.width() / 2) / self.thumbnail.width()
        center_y = (self.viewport_rect.y() + self.viewport_rect.height() / 2) / self.thumbnail.height()
        
        return center_x, center_y


class MiniMapPanel(QWidget):
    """
    Complete mini-map panel with title and controls.
    
    Features:
    - Mini-map widget
    - Zoom level display
    - Navigation instructions
    - Professional styling
    """
    
    # Signals
    navigate_requested = pyqtSignal(float, float)  # relative_x, relative_y
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the mini-map panel UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("🗺️ Mini-Map")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 4px;
            }
        """)
        layout.addWidget(title_label)
        
        # Mini-map widget
        self.mini_map = MiniMapWidget()
        self.mini_map.navigate_requested.connect(self.navigate_requested.emit)
        layout.addWidget(self.mini_map)
        
        # Instructions
        instructions_label = QLabel("Click to navigate")
        instructions_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 10px;
                text-align: center;
                padding: 2px;
            }
        """)
        instructions_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions_label)
        
        self.setLayout(layout)
        
        # Panel styling
        self.setStyleSheet("""
            MiniMapPanel {
                background-color: #2d2d2d;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """)
    
    def set_image(self, image: QImage):
        """Set the image to display in the mini-map."""
        self.mini_map.set_image(image)
    
    def update_viewport(self, viewport_x: float, viewport_y: float, 
                       viewport_width: float, viewport_height: float, zoom_factor: float):
        """Update the viewport rectangle."""
        self.mini_map.update_viewport(viewport_x, viewport_y, viewport_width, viewport_height, zoom_factor)


def main():
    """Test the mini-map component."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Mini-Map Test")
    window.setGeometry(100, 100, 400, 300)
    
    # Create central widget
    central_widget = QWidget()
    layout = QHBoxLayout()
    
    # Create mini-map panel
    mini_map_panel = MiniMapPanel()
    layout.addWidget(mini_map_panel)
    
    # Connect signals
    mini_map_panel.navigate_requested.connect(
        lambda x, y: print(f"Navigate to: ({x:.2f}, {y:.2f})")
    )
    
    # Create test image
    test_image = QImage(800, 600, QImage.Format_RGB32)
    test_image.fill(QColor(100, 150, 200))
    mini_map_panel.set_image(test_image)
    
    # Simulate viewport update
    mini_map_panel.update_viewport(0.5, 0.5, 0.3, 0.3, 2.0)
    
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()