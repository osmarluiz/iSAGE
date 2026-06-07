"""
Simple Annotation Canvas - Basic working implementation for demonstration

A simplified canvas component that can display images and handle basic annotations.
This is a minimal working version to demonstrate the modular concept.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleAnnotationCanvas(QLabel):
    """
    Simplified annotation canvas for demonstration.
    
    Provides basic image display and point annotation functionality
    without complex dependencies.
    """
    
    # Signals
    annotationAdded = pyqtSignal(float, float, int)  # x, y, class_id
    annotationChanged = pyqtSignal(dict)  # annotation_data
    imageLoaded = pyqtSignal(str)  # image_path
    
    def __init__(self, parent=None, name: str = "simple_canvas", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        self.initialized = False
        
        # Canvas state
        self._current_image: Optional[QPixmap] = None
        self._image_path: str = ""
        self._zoom_factor: float = 1.0
        self._annotations: List[Dict[str, Any]] = []
        self._current_class: int = 1
        
        # UI setup
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        
        # Styling
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #4a5568;
                border-radius: 8px;
                background-color: #2d3748;
                color: #e2e8f0;
            }
        """)
        
        # Initial state
        self.setText("🧩 Simple Shared Canvas\\n\\nReady for images and annotations")
        
        # Mouse tracking
        self.setMouseTracking(True)
        
        logger.info(f"SimpleAnnotationCanvas '{name}' v{version} created")
    
    def initialize(self, **kwargs) -> bool:
        """Initialize the canvas with configuration."""
        try:
            # Apply configuration
            if 'background_color' in kwargs:
                bg_color = kwargs['background_color']
                self.setStyleSheet(f"""
                    QLabel {{
                        border: 2px solid #4a5568;
                        border-radius: 8px;
                        background-color: {bg_color};
                        color: #e2e8f0;
                    }}
                """)
            
            if 'enable_optimized_rendering' in kwargs:
                # For now, just log this - we can add optimizations later
                logger.info(f"Optimized rendering: {kwargs['enable_optimized_rendering']}")
            
            if 'cache_layers' in kwargs:
                logger.info(f"Layer caching: {kwargs['cache_layers']}")
            
            self.initialized = True
            logger.info(f"SimpleAnnotationCanvas initialized with config: {kwargs}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize canvas: {e}")
            return False
    
    def load_image(self, image_path: str) -> bool:
        """Load an image into the canvas."""
        try:
            path = Path(image_path)
            if not path.exists():
                logger.error(f"Image file not found: {image_path}")
                return False
            
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                logger.error(f"Failed to load image: {image_path}")
                return False
            
            self._current_image = pixmap
            self._image_path = image_path
            self.setPixmap(pixmap)
            
            # Update display text to show image info
            self.setText("")  # Clear text when image is loaded
            
            self.imageLoaded.emit(image_path)
            logger.info(f"Image loaded: {path.name} ({pixmap.width()}x{pixmap.height()})")
            return True
            
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False
    
    def get_image(self) -> Optional[QPixmap]:
        """Get the current image."""
        return self._current_image
    
    def set_current_class(self, class_id: int):
        """Set the current annotation class."""
        self._current_class = class_id
        logger.info(f"Current annotation class set to: {class_id}")
    
    def mousePressEvent(self, event):
        """Handle mouse press events for annotation."""
        if event.button() == Qt.LeftButton and self._current_image:
            # Get click position relative to the widget
            pos = event.pos()
            
            # For now, just add the annotation at the click position
            # In a full implementation, we'd convert screen coords to image coords
            annotation = {
                'x': float(pos.x()),
                'y': float(pos.y()), 
                'class_id': self._current_class,
                'screen_pos': (pos.x(), pos.y())
            }
            
            self._annotations.append(annotation)
            
            # Emit signals
            self.annotationAdded.emit(pos.x(), pos.y(), self._current_class)
            self.annotationChanged.emit(annotation)
            
            logger.info(f"Annotation added at ({pos.x()}, {pos.y()}) class={self._current_class}")
            
            # Trigger repaint to show the annotation
            self.update()
    
    def paintEvent(self, event):
        """Custom paint event to draw annotations."""
        # First, paint the base image/text
        super().paintEvent(event)
        
        # Then draw annotations on top
        if self._annotations:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw each annotation as a colored circle
            colors = [QColor('#ef4444'), QColor('#10b981'), QColor('#3b82f6'), 
                     QColor('#f59e0b'), QColor('#8b5cf6'), QColor('#ec4899')]
            
            for i, annotation in enumerate(self._annotations):
                class_id = annotation['class_id']
                color = colors[class_id % len(colors)]
                
                painter.setPen(QPen(color, 3))
                painter.setBrush(QBrush(color))
                
                x, y = annotation['screen_pos']
                painter.drawEllipse(x - 5, y - 5, 10, 10)
                
                # Draw class label
                painter.setPen(QPen(QColor('#ffffff'), 1))
                painter.setFont(QFont('Arial', 8))
                painter.drawText(x + 8, y - 5, f"C{class_id}")
            
            painter.end()
    
    def clear_annotations(self):
        """Clear all annotations."""
        self._annotations.clear()
        self.update()
        logger.info("All annotations cleared")
    
    def get_annotations(self) -> List[Dict[str, Any]]:
        """Get current annotations."""
        return self._annotations.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get canvas statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'has_image': self._current_image is not None,
            'image_path': self._image_path,
            'annotation_count': len(self._annotations),
            'current_class': self._current_class,
            'zoom_factor': self._zoom_factor
        }