"""
Ground Truth Overlay - Displays dense ground truth masks

This module provides ground truth visualization with class-specific colors
as used in the ABILIUS system.
"""

from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from ..base_protocols import BaseComponent, OverlayType, OverlayData, QPixmap, QColor
from .base_overlay import BaseOverlay


class GroundTruthOverlay(BaseOverlay):
    """Overlay for displaying ground truth masks with class-specific colors."""
    
    def __init__(self, name: str = "ground_truth_overlay", version: str = "1.0.0"):
        super().__init__(name, OverlayType.GROUND_TRUTH, version)
        
        # Ground truth configuration
        self._class_colors: List[QColor] = [
            QColor(255, 0, 0),    # Red - Class 0
            QColor(0, 255, 0),    # Green - Class 1
            QColor(0, 0, 255),    # Blue - Class 2
            QColor(255, 255, 0),  # Yellow - Class 3
            QColor(255, 0, 255),  # Magenta - Class 4
            QColor(0, 255, 255),  # Cyan - Class 5
            QColor(255, 255, 255) # White - Class 6
        ]
        self._ignore_index: int = 255
        self._show_boundaries: bool = False
        self._boundary_color: QColor = QColor(255, 255, 255)
        self._boundary_width: int = 1
        self._class_names: List[str] = []
        
        # Visualization options
        self._show_class_labels: bool = False
        self._label_font_size: int = 12
        self._label_background: bool = True
        self._label_background_color: QColor = QColor(0, 0, 0, 128)
    
    def initialize(self, **kwargs) -> bool:
        """Initialize ground truth overlay."""
        self._ignore_index = kwargs.get('ignore_index', 255)
        self._show_boundaries = kwargs.get('show_boundaries', False)
        self._boundary_width = kwargs.get('boundary_width', 1)
        self._show_class_labels = kwargs.get('show_class_labels', False)
        self._label_font_size = kwargs.get('label_font_size', 12)
        
        # Set class colors if provided
        if 'class_colors' in kwargs:
            self._class_colors = kwargs['class_colors']
        
        # Set class names if provided
        if 'class_names' in kwargs:
            self._class_names = kwargs['class_names']
        
        return super().initialize(**kwargs)
    
    def set_ground_truth_data(self, mask: np.ndarray, class_names: Optional[List[str]] = None) -> bool:
        """Set ground truth mask data."""
        try:
            if mask.ndim != 2:
                self.emit_error(f"Ground truth mask must be 2D, got shape: {mask.shape}")
                return False
            
            # Set class names if provided
            if class_names:
                self._class_names = class_names
            
            # Process mask data
            processed_data = self._process_ground_truth_mask(mask)
            
            # Create overlay data
            overlay_data = OverlayData(
                overlay_type=OverlayType.GROUND_TRUTH,
                data=processed_data,
                opacity=self._opacity,
                color_map=None,
                visible=self._visible,
                metadata={
                    'mask_shape': mask.shape,
                    'num_classes': len(self._class_colors),
                    'ignore_index': self._ignore_index,
                    'class_names': self._class_names,
                    'show_boundaries': self._show_boundaries
                }
            )
            
            return self.set_overlay_data(overlay_data)
            
        except Exception as e:
            self.emit_error(f"Error setting ground truth data: {str(e)}")
            return False
    
    def set_class_colors(self, colors: List[QColor]) -> None:
        """Set class colors."""
        self._class_colors = colors
        self._cache_valid = False
        self.emit_state_changed({'class_colors_changed': True})
    
    def get_class_colors(self) -> List[QColor]:
        """Get class colors."""
        return self._class_colors.copy()
    
    def set_class_color(self, class_id: int, color: QColor) -> None:
        """Set color for specific class."""
        if 0 <= class_id < len(self._class_colors):
            self._class_colors[class_id] = color
            self._cache_valid = False
            self.emit_state_changed({'class_color_changed': class_id})
    
    def get_class_color(self, class_id: int) -> QColor:
        """Get color for specific class."""
        if 0 <= class_id < len(self._class_colors):
            return self._class_colors[class_id]
        return QColor(255, 255, 255)  # Default white
    
    def set_ignore_index(self, ignore_index: int) -> None:
        """Set ignore index."""
        self._ignore_index = ignore_index
        self._cache_valid = False
        self.emit_state_changed({'ignore_index': ignore_index})
    
    def get_ignore_index(self) -> int:
        """Get ignore index."""
        return self._ignore_index
    
    def set_show_boundaries(self, show: bool) -> None:
        """Enable/disable boundary visualization."""
        self._show_boundaries = show
        self._cache_valid = False
        self.emit_state_changed({'show_boundaries': show})
    
    def is_show_boundaries_enabled(self) -> bool:
        """Check if boundary visualization is enabled."""
        return self._show_boundaries
    
    def set_boundary_color(self, color: QColor) -> None:
        """Set boundary color."""
        self._boundary_color = color
        self._cache_valid = False
        self.emit_state_changed({'boundary_color_changed': True})
    
    def get_boundary_color(self) -> QColor:
        """Get boundary color."""
        return self._boundary_color
    
    def set_boundary_width(self, width: int) -> None:
        """Set boundary width."""
        self._boundary_width = max(1, width)
        self._cache_valid = False
        self.emit_state_changed({'boundary_width': width})
    
    def get_boundary_width(self) -> int:
        """Get boundary width."""
        return self._boundary_width
    
    def set_class_names(self, names: List[str]) -> None:
        """Set class names."""
        self._class_names = names
        self.emit_state_changed({'class_names_changed': True})
    
    def get_class_names(self) -> List[str]:
        """Get class names."""
        return self._class_names.copy()
    
    def set_show_class_labels(self, show: bool) -> None:
        """Enable/disable class label display."""
        self._show_class_labels = show
        self._cache_valid = False
        self.emit_state_changed({'show_class_labels': show})
    
    def is_show_class_labels_enabled(self) -> bool:
        """Check if class labels are shown."""
        return self._show_class_labels
    
    def set_label_font_size(self, size: int) -> None:
        """Set label font size."""
        self._label_font_size = max(8, min(24, size))
        self._cache_valid = False
        self.emit_state_changed({'label_font_size': size})
    
    def get_label_font_size(self) -> int:
        """Get label font size."""
        return self._label_font_size
    
    def get_class_statistics(self) -> Dict[int, Dict[str, Any]]:
        """Get class statistics from current mask."""
        if not self.has_data():
            return {}
        
        mask = self._overlay_data.data
        if mask.ndim != 2:
            return {}
        
        stats = {}
        unique_classes, counts = np.unique(mask, return_counts=True)
        
        total_pixels = mask.size
        
        for class_id, count in zip(unique_classes, counts):
            if class_id != self._ignore_index:
                stats[int(class_id)] = {
                    'pixel_count': int(count),
                    'percentage': float(count / total_pixels * 100),
                    'color': self.get_class_color(int(class_id)),
                    'name': self._class_names[int(class_id)] if int(class_id) < len(self._class_names) else f"Class {class_id}"
                }
        
        return stats
    
    def _render_overlay(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render ground truth overlay to pixmap."""
        if not self.has_data():
            return None
        
        try:
            # Get mask data
            mask = self._overlay_data.data
            
            # Create colored mask
            colored_mask = self._create_colored_mask(mask)
            
            # Add boundaries if enabled
            if self._show_boundaries:
                colored_mask = self._add_boundaries(colored_mask, mask)
            
            # Convert to pixmap
            pixmap = self._array_to_pixmap(colored_mask)
            
            # Add class labels if enabled
            if self._show_class_labels:
                pixmap = self._add_class_labels(pixmap, mask)
            
            # Resize to canvas size if needed
            if pixmap.size() != canvas_size:
                from PyQt5.QtCore import Qt
                pixmap = pixmap.scaled(
                    canvas_size[0], canvas_size[1],
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error rendering ground truth overlay: {str(e)}")
            return None
    
    def _process_ground_truth_mask(self, mask: np.ndarray) -> np.ndarray:
        """Process ground truth mask."""
        # Ensure mask is uint8
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        return mask
    
    def _create_colored_mask(self, mask: np.ndarray) -> np.ndarray:
        """Create colored mask from class indices."""
        height, width = mask.shape
        colored = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
        
        # Apply colors by class
        for class_id, color in enumerate(self._class_colors):
            class_mask = (mask == class_id) & (mask != self._ignore_index)
            if np.any(class_mask):
                colored[class_mask] = [color.red(), color.green(), color.blue(), int(255 * self._opacity)]
        
        # Handle ignore index (transparent)
        ignore_mask = mask == self._ignore_index
        colored[ignore_mask] = [0, 0, 0, 0]
        
        return colored
    
    def _add_boundaries(self, colored_mask: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Add class boundaries to colored mask."""
        try:
            from scipy.ndimage import generic_filter
            
            def boundary_filter(values):
                """Filter to detect boundaries."""
                center = values[len(values) // 2]
                return 1 if np.any(values != center) else 0
            
            # Create boundary mask
            boundary_mask = generic_filter(mask.astype(np.float32), boundary_filter, size=3)
            boundary_mask = boundary_mask.astype(bool)
            
            # Apply boundary color
            boundary_color = [
                self._boundary_color.red(),
                self._boundary_color.green(),
                self._boundary_color.blue(),
                255
            ]
            
            colored_mask[boundary_mask] = boundary_color
            
            return colored_mask
            
        except ImportError:
            self.emit_error("scipy is required for boundary detection")
            return colored_mask
        except Exception as e:
            self.emit_error(f"Error adding boundaries: {str(e)}")
            return colored_mask
    
    def _add_class_labels(self, pixmap: QPixmap, mask: np.ndarray) -> QPixmap:
        """Add class labels to pixmap."""
        try:
            from PyQt5.QtGui import QPainter, QFont, QPen, QBrush
            from PyQt5.QtCore import Qt
            
            # Create painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set font
            font = QFont("Arial", self._label_font_size)
            painter.setFont(font)
            
            # Get class statistics
            stats = self.get_class_statistics()
            
            # Draw labels for each class
            y_offset = 20
            for class_id, stat in stats.items():
                if stat['pixel_count'] > 0:
                    # Create label text
                    label = f"{stat['name']}: {stat['percentage']:.1f}%"
                    
                    # Set text color
                    text_color = QColor(255, 255, 255)
                    painter.setPen(QPen(text_color))
                    
                    # Draw background if enabled
                    if self._label_background:
                        text_rect = painter.fontMetrics().boundingRect(label)
                        text_rect.moveTopLeft(QPoint(10, y_offset - text_rect.height()))
                        painter.fillRect(text_rect, QBrush(self._label_background_color))
                    
                    # Draw text
                    painter.drawText(10, y_offset, label)
                    y_offset += self._label_font_size + 5
            
            painter.end()
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error adding class labels: {str(e)}")
            return pixmap
    
    def _array_to_pixmap(self, array: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap."""
        try:
            from PyQt5.QtGui import QImage
            
            if array.dtype != np.uint8:
                array = (array * 255).astype(np.uint8)
            
            height, width = array.shape[:2]
            
            if len(array.shape) == 3 and array.shape[2] == 4:
                # RGBA
                bytes_per_line = 4 * width
                q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            elif len(array.shape) == 3 and array.shape[2] == 3:
                # RGB
                bytes_per_line = 3 * width
                q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:
                # Grayscale
                bytes_per_line = width
                q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            
            return QPixmap.fromImage(q_image)
            
        except Exception as e:
            self.emit_error(f"Error converting array to pixmap: {str(e)}")
            return QPixmap()
    
    def export_colored_mask(self, output_path: str) -> bool:
        """Export colored mask to image file."""
        if not self.has_data():
            return False
        
        try:
            # Create colored mask
            mask = self._overlay_data.data
            colored_mask = self._create_colored_mask(mask)
            
            # Convert to pixmap
            pixmap = self._array_to_pixmap(colored_mask)
            
            # Save to file
            return pixmap.save(output_path)
            
        except Exception as e:
            self.emit_error(f"Error exporting colored mask: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ground truth overlay statistics."""
        stats = super().get_statistics()
        stats.update({
            'num_classes': len(self._class_colors),
            'ignore_index': self._ignore_index,
            'show_boundaries': self._show_boundaries,
            'boundary_width': self._boundary_width,
            'show_class_labels': self._show_class_labels,
            'label_font_size': self._label_font_size,
            'class_names': self._class_names,
            'class_statistics': self.get_class_statistics()
        })
        return stats