"""
Prediction Confidence Display System

Provides sophisticated visualization of model prediction confidence.
Supports heatmaps, uncertainty indicators, and interactive exploration.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
        QCheckBox, QComboBox, QSpinBox, QFrame
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QPixmap, QImage, 
        QLinearGradient, QRadialGradient, QConicalGradient
    )
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QWidget: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import colorsys


class ConfidenceVisualizationMode(Enum):
    """Confidence visualization modes."""
    HEATMAP = "heatmap"
    CONTOURS = "contours"
    TRANSPARENCY = "transparency"
    OVERLAYS = "overlays"
    UNCERTAINTY_BARS = "uncertainty_bars"
    CONFIDENCE_DOTS = "confidence_dots"


class ColorScheme(Enum):
    """Color schemes for confidence visualization."""
    VIRIDIS = "viridis"
    PLASMA = "plasma"
    INFERNO = "inferno"
    MAGMA = "magma"
    COOLWARM = "coolwarm"
    RED_BLUE = "red_blue"
    GREEN_RED = "green_red"
    RAINBOW = "rainbow"


@dataclass
class ConfidenceSettings:
    """Settings for confidence visualization."""
    visualization_mode: ConfidenceVisualizationMode = ConfidenceVisualizationMode.HEATMAP
    color_scheme: ColorScheme = ColorScheme.VIRIDIS
    opacity: float = 0.7
    threshold_min: float = 0.0
    threshold_max: float = 1.0
    show_uncertainty: bool = True
    show_statistics: bool = True
    smooth_visualization: bool = True
    contour_levels: int = 10
    dot_size: int = 3
    bar_width: int = 20


class ColorSchemeGenerator:
    """Generate color schemes for confidence visualization."""
    
    @staticmethod
    def viridis(value: float) -> QColor:
        """Generate viridis colormap color."""
        # Simplified viridis approximation
        r = max(0, min(1, 0.267004 + value * (0.993248 - 0.267004)))
        g = max(0, min(1, 0.004874 + value * (0.906157 - 0.004874)))
        b = max(0, min(1, 0.329415 + value * (0.143936 - 0.329415)))
        
        return QColor(int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def plasma(value: float) -> QColor:
        """Generate plasma colormap color."""
        r = max(0, min(1, 0.050383 + value * (0.940015 - 0.050383)))
        g = max(0, min(1, 0.029803 + value * (0.975158 - 0.029803)))
        b = max(0, min(1, 0.527975 + value * (0.131326 - 0.527975)))
        
        return QColor(int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def coolwarm(value: float) -> QColor:
        """Generate cool-warm colormap color."""
        if value < 0.5:
            # Cool (blue) side
            intensity = value * 2
            r = int(59 + intensity * (255 - 59))
            g = int(76 + intensity * (255 - 76))
            b = 255
        else:
            # Warm (red) side
            intensity = (value - 0.5) * 2
            r = 255
            g = int(255 - intensity * (255 - 76))
            b = int(255 - intensity * 255)
        
        return QColor(r, g, b)
    
    @staticmethod
    def red_blue(value: float) -> QColor:
        """Generate red-blue colormap color."""
        if value < 0.5:
            # Blue to white
            intensity = value * 2
            r = int(intensity * 255)
            g = int(intensity * 255)
            b = 255
        else:
            # White to red
            intensity = (value - 0.5) * 2
            r = 255
            g = int(255 - intensity * 255)
            b = int(255 - intensity * 255)
        
        return QColor(r, g, b)
    
    @staticmethod
    def rainbow(value: float) -> QColor:
        """Generate rainbow colormap color."""
        hue = value * 300  # 0 to 300 degrees (avoid full circle)
        r, g, b = colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)
        return QColor(int(r * 255), int(g * 255), int(b * 255))
    
    @classmethod
    def get_color(cls, scheme: ColorScheme, value: float) -> QColor:
        """Get color for value using specified scheme."""
        value = max(0.0, min(1.0, value))  # Clamp to [0, 1]
        
        if scheme == ColorScheme.VIRIDIS:
            return cls.viridis(value)
        elif scheme == ColorScheme.PLASMA:
            return cls.plasma(value)
        elif scheme == ColorScheme.COOLWARM:
            return cls.coolwarm(value)
        elif scheme == ColorScheme.RED_BLUE:
            return cls.red_blue(value)
        elif scheme == ColorScheme.RAINBOW:
            return cls.rainbow(value)
        else:
            # Default to viridis
            return cls.viridis(value)


class ConfidenceAnalyzer:
    """Analyze prediction confidence data."""
    
    @staticmethod
    def calculate_statistics(confidence_map: np.ndarray) -> Dict[str, float]:
        """Calculate confidence statistics."""
        if confidence_map.size == 0:
            return {}
        
        flat_conf = confidence_map.flatten()
        
        return {
            "mean": float(np.mean(flat_conf)),
            "std": float(np.std(flat_conf)),
            "min": float(np.min(flat_conf)),
            "max": float(np.max(flat_conf)),
            "median": float(np.median(flat_conf)),
            "q25": float(np.percentile(flat_conf, 25)),
            "q75": float(np.percentile(flat_conf, 75)),
            "low_confidence_ratio": float(np.sum(flat_conf < 0.5) / flat_conf.size),
            "high_confidence_ratio": float(np.sum(flat_conf > 0.8) / flat_conf.size)
        }
    
    @staticmethod
    def find_uncertain_regions(confidence_map: np.ndarray, 
                             threshold: float = 0.5) -> List[Tuple[int, int, float]]:
        """Find regions with low confidence."""
        uncertain_points = []
        
        h, w = confidence_map.shape
        for y in range(h):
            for x in range(w):
                if confidence_map[y, x] < threshold:
                    uncertain_points.append((x, y, confidence_map[y, x]))
        
        return uncertain_points
    
    @staticmethod
    def calculate_uncertainty_entropy(probabilities: np.ndarray) -> np.ndarray:
        """Calculate uncertainty using entropy."""
        # probabilities should be shape (H, W, num_classes)
        if len(probabilities.shape) != 3:
            return np.zeros(probabilities.shape[:2])
        
        # Calculate entropy
        epsilon = 1e-8  # Avoid log(0)
        log_probs = np.log(probabilities + epsilon)
        entropy = -np.sum(probabilities * log_probs, axis=2)
        
        # Normalize to [0, 1]
        max_entropy = np.log(probabilities.shape[2])
        normalized_entropy = entropy / max_entropy
        
        return normalized_entropy


class ConfidenceVisualizer:
    """
    Visualize prediction confidence using various methods.
    
    Features:
    - Multiple visualization modes
    - Customizable color schemes
    - Real-time confidence analysis
    - Uncertainty highlighting
    - Statistical overlays
    """
    
    def __init__(self, settings: ConfidenceSettings = None):
        self.settings = settings or ConfidenceSettings()
        self.color_generator = ColorSchemeGenerator()
        self.analyzer = ConfidenceAnalyzer()
        self._cached_visualization = None
        self._cache_valid = False
        
    def set_settings(self, settings: ConfidenceSettings):
        """Update visualization settings."""
        self.settings = settings
        self._invalidate_cache()
    
    def _invalidate_cache(self):
        """Invalidate cached visualizations."""
        self._cache_valid = False
        self._cached_visualization = None
    
    def create_heatmap(self, confidence_map: np.ndarray) -> QImage:
        """Create confidence heatmap visualization."""
        if confidence_map.size == 0:
            return QImage()
        
        h, w = confidence_map.shape
        
        # Apply thresholds
        filtered_conf = np.clip(confidence_map, self.settings.threshold_min, self.settings.threshold_max)
        
        # Normalize to [0, 1]
        if self.settings.threshold_max > self.settings.threshold_min:
            normalized = (filtered_conf - self.settings.threshold_min) / (self.settings.threshold_max - self.settings.threshold_min)
        else:
            normalized = filtered_conf
        
        # Create QImage
        image = QImage(w, h, QImage.Format_ARGB32)
        
        for y in range(h):
            for x in range(w):
                confidence = normalized[y, x]
                color = self.color_generator.get_color(self.settings.color_scheme, confidence)
                color.setAlpha(int(255 * self.settings.opacity))
                image.setPixelColor(x, y, color)
        
        return image
    
    def create_contour_visualization(self, confidence_map: np.ndarray) -> List[Tuple[List[QPoint], float]]:
        """Create contour lines for confidence visualization."""
        contours = []
        
        if confidence_map.size == 0:
            return contours
        
        h, w = confidence_map.shape
        levels = np.linspace(self.settings.threshold_min, self.settings.threshold_max, self.settings.contour_levels)
        
        # Simple contour extraction (this is a simplified version)
        for level in levels:
            points = []
            for y in range(1, h-1):
                for x in range(1, w-1):
                    # Check if this point crosses the contour level
                    current = confidence_map[y, x]
                    neighbors = [
                        confidence_map[y-1, x], confidence_map[y+1, x],
                        confidence_map[y, x-1], confidence_map[y, x+1]
                    ]
                    
                    # Simple crossing detection
                    if any((current >= level > neighbor) or (current <= level < neighbor) for neighbor in neighbors):
                        points.append(QPoint(x, y))
            
            if points:
                contours.append((points, level))
        
        return contours
    
    def create_uncertainty_overlay(self, confidence_map: np.ndarray) -> List[Tuple[QPoint, float]]:
        """Create uncertainty overlay points."""
        uncertain_regions = self.analyzer.find_uncertain_regions(
            confidence_map, threshold=0.5
        )
        
        overlay_points = []
        for x, y, confidence in uncertain_regions:
            overlay_points.append((QPoint(x, y), confidence))
        
        return overlay_points
    
    def paint_confidence_visualization(self, painter: QPainter, confidence_map: np.ndarray, 
                                     target_rect: QRect = None):
        """Paint confidence visualization on the given painter."""
        if not PYQT5_AVAILABLE or confidence_map.size == 0:
            return
        
        painter.save()
        
        if self.settings.visualization_mode == ConfidenceVisualizationMode.HEATMAP:
            self._paint_heatmap(painter, confidence_map, target_rect)
        elif self.settings.visualization_mode == ConfidenceVisualizationMode.CONTOURS:
            self._paint_contours(painter, confidence_map, target_rect)
        elif self.settings.visualization_mode == ConfidenceVisualizationMode.TRANSPARENCY:
            self._paint_transparency_overlay(painter, confidence_map, target_rect)
        elif self.settings.visualization_mode == ConfidenceVisualizationMode.OVERLAYS:
            self._paint_uncertainty_overlays(painter, confidence_map, target_rect)
        elif self.settings.visualization_mode == ConfidenceVisualizationMode.CONFIDENCE_DOTS:
            self._paint_confidence_dots(painter, confidence_map, target_rect)
        
        painter.restore()
    
    def _paint_heatmap(self, painter: QPainter, confidence_map: np.ndarray, target_rect: QRect):
        """Paint heatmap visualization."""
        heatmap_image = self.create_heatmap(confidence_map)
        if not heatmap_image.isNull():
            if target_rect:
                painter.drawImage(target_rect, heatmap_image)
            else:
                painter.drawImage(0, 0, heatmap_image)
    
    def _paint_contours(self, painter: QPainter, confidence_map: np.ndarray, target_rect: QRect):
        """Paint contour visualization."""
        contours = self.create_contour_visualization(confidence_map)
        
        for points, level in contours:
            # Color based on confidence level
            normalized_level = (level - self.settings.threshold_min) / max(0.001, self.settings.threshold_max - self.settings.threshold_min)
            color = self.color_generator.get_color(self.settings.color_scheme, normalized_level)
            color.setAlpha(int(255 * self.settings.opacity))
            
            pen = QPen(color, 2)
            painter.setPen(pen)
            
            # Draw contour lines
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
    
    def _paint_transparency_overlay(self, painter: QPainter, confidence_map: np.ndarray, target_rect: QRect):
        """Paint transparency-based confidence overlay."""
        h, w = confidence_map.shape
        
        # Create overlay with varying transparency
        for y in range(0, h, 2):  # Sample every 2nd pixel for performance
            for x in range(0, w, 2):
                confidence = confidence_map[y, x]
                
                if self.settings.threshold_min <= confidence <= self.settings.threshold_max:
                    alpha = int(255 * confidence * self.settings.opacity)
                    color = QColor(255, 255, 255, alpha)  # White overlay with varying alpha
                    
                    painter.fillRect(x, y, 2, 2, color)
    
    def _paint_uncertainty_overlays(self, painter: QPainter, confidence_map: np.ndarray, target_rect: QRect):
        """Paint uncertainty overlay indicators."""
        uncertain_points = self.create_uncertainty_overlay(confidence_map)
        
        for point, confidence in uncertain_points:
            # Color intensity based on uncertainty (lower confidence = more intense)
            intensity = 1.0 - confidence
            color = QColor(255, int(255 * (1 - intensity)), 0, int(200 * intensity))  # Orange to red
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(), 1))
            painter.drawEllipse(point, 3, 3)
    
    def _paint_confidence_dots(self, painter: QPainter, confidence_map: np.ndarray, target_rect: QRect):
        """Paint confidence as colored dots."""
        h, w = confidence_map.shape
        dot_size = self.settings.dot_size
        spacing = max(dot_size * 2, 8)  # Minimum spacing between dots
        
        for y in range(0, h, spacing):
            for x in range(0, w, spacing):
                confidence = confidence_map[y, x]
                
                if self.settings.threshold_min <= confidence <= self.settings.threshold_max:
                    # Normalize confidence for color mapping
                    normalized = (confidence - self.settings.threshold_min) / max(0.001, self.settings.threshold_max - self.settings.threshold_min)
                    color = self.color_generator.get_color(self.settings.color_scheme, normalized)
                    color.setAlpha(int(255 * self.settings.opacity))
                    
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color.darker(), 1))
                    painter.drawEllipse(QPoint(x, y), dot_size, dot_size)
    
    def get_confidence_statistics(self, confidence_map: np.ndarray) -> Dict[str, Any]:
        """Get comprehensive confidence statistics."""
        if confidence_map.size == 0:
            return {}
        
        basic_stats = self.analyzer.calculate_statistics(confidence_map)
        
        # Add visualization-specific information
        visualization_info = {
            "visualization_mode": self.settings.visualization_mode.value,
            "color_scheme": self.settings.color_scheme.value,
            "threshold_range": [self.settings.threshold_min, self.settings.threshold_max],
            "opacity": self.settings.opacity
        }
        
        return {**basic_stats, **visualization_info}


class ConfidenceControlWidget(QWidget):
    """
    Control widget for confidence visualization settings.
    
    Features:
    - Visualization mode selection
    - Color scheme selection
    - Threshold controls
    - Opacity adjustment
    - Real-time preview
    """
    
    settings_changed = pyqtSignal(ConfidenceSettings)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = ConfidenceSettings()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the control UI."""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Visualization mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        for mode in ConfidenceVisualizationMode:
            self.mode_combo.addItem(mode.value.title(), mode)
        mode_layout.addWidget(self.mode_combo)
        
        layout.addLayout(mode_layout)
        
        # Color scheme
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Colors:"))
        
        self.color_combo = QComboBox()
        for scheme in ColorScheme:
            self.color_combo.addItem(scheme.value.title(), scheme)
        color_layout.addWidget(self.color_combo)
        
        layout.addLayout(color_layout)
        
        # Opacity control
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.settings.opacity * 100))
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel(f"{self.settings.opacity:.1f}")
        opacity_layout.addWidget(self.opacity_label)
        
        layout.addLayout(opacity_layout)
        
        # Threshold controls
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(QLabel("Confidence Thresholds:"))
        
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Min:"))
        self.min_slider = QSlider(Qt.Horizontal)
        self.min_slider.setRange(0, 100)
        self.min_slider.setValue(int(self.settings.threshold_min * 100))
        min_layout.addWidget(self.min_slider)
        
        self.min_label = QLabel(f"{self.settings.threshold_min:.2f}")
        min_layout.addWidget(self.min_label)
        
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max:"))
        self.max_slider = QSlider(Qt.Horizontal)
        self.max_slider.setRange(0, 100)
        self.max_slider.setValue(int(self.settings.threshold_max * 100))
        max_layout.addWidget(self.max_slider)
        
        self.max_label = QLabel(f"{self.settings.threshold_max:.2f}")
        max_layout.addWidget(self.max_label)
        
        threshold_layout.addLayout(min_layout)
        threshold_layout.addLayout(max_layout)
        layout.addLayout(threshold_layout)
        
        # Options
        self.uncertainty_checkbox = QCheckBox("Show Uncertainty Regions")
        self.uncertainty_checkbox.setChecked(self.settings.show_uncertainty)
        layout.addWidget(self.uncertainty_checkbox)
        
        self.statistics_checkbox = QCheckBox("Show Statistics")
        self.statistics_checkbox.setChecked(self.settings.show_statistics)
        layout.addWidget(self.statistics_checkbox)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to update handlers."""
        self.mode_combo.currentIndexChanged.connect(self._update_settings)
        self.color_combo.currentIndexChanged.connect(self._update_settings)
        self.opacity_slider.valueChanged.connect(self._update_opacity)
        self.min_slider.valueChanged.connect(self._update_min_threshold)
        self.max_slider.valueChanged.connect(self._update_max_threshold)
        self.uncertainty_checkbox.toggled.connect(self._update_settings)
        self.statistics_checkbox.toggled.connect(self._update_settings)
    
    def _update_opacity(self, value):
        """Update opacity setting."""
        self.settings.opacity = value / 100.0
        self.opacity_label.setText(f"{self.settings.opacity:.1f}")
        self._update_settings()
    
    def _update_min_threshold(self, value):
        """Update minimum threshold."""
        self.settings.threshold_min = value / 100.0
        self.min_label.setText(f"{self.settings.threshold_min:.2f}")
        
        # Ensure min <= max
        if self.settings.threshold_min > self.settings.threshold_max:
            self.settings.threshold_max = self.settings.threshold_min
            self.max_slider.setValue(value)
            self.max_label.setText(f"{self.settings.threshold_max:.2f}")
        
        self._update_settings()
    
    def _update_max_threshold(self, value):
        """Update maximum threshold."""
        self.settings.threshold_max = value / 100.0
        self.max_label.setText(f"{self.settings.threshold_max:.2f}")
        
        # Ensure min <= max
        if self.settings.threshold_max < self.settings.threshold_min:
            self.settings.threshold_min = self.settings.threshold_max
            self.min_slider.setValue(value)
            self.min_label.setText(f"{self.settings.threshold_min:.2f}")
        
        self._update_settings()
    
    def _update_settings(self):
        """Update settings from UI controls."""
        self.settings.visualization_mode = self.mode_combo.currentData()
        self.settings.color_scheme = self.color_combo.currentData()
        self.settings.show_uncertainty = self.uncertainty_checkbox.isChecked()
        self.settings.show_statistics = self.statistics_checkbox.isChecked()
        
        self.settings_changed.emit(self.settings)


def main():
    """Test the confidence display system."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Confidence Display Test")
    window.setGeometry(100, 100, 1000, 600)
    
    # Central widget
    central_widget = QWidget()
    layout = QHBoxLayout()
    
    # Control widget
    control_widget = ConfidenceControlWidget()
    layout.addWidget(control_widget)
    
    # Visualization display
    class ConfidenceDisplayWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.visualizer = ConfidenceVisualizer()
            self.confidence_map = self._generate_test_data()
            self.setMinimumSize(400, 400)
        
        def _generate_test_data(self):
            # Generate test confidence map
            h, w = 200, 200
            x, y = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
            
            # Create interesting confidence pattern
            confidence = 0.5 + 0.3 * np.sin(4 * np.pi * x) * np.cos(4 * np.pi * y)
            confidence += 0.2 * np.random.random((h, w))  # Add noise
            confidence = np.clip(confidence, 0, 1)
            
            return confidence
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            
            # Paint confidence visualization
            self.visualizer.paint_confidence_visualization(
                painter, self.confidence_map, self.rect()
            )
        
        def update_settings(self, settings):
            self.visualizer.set_settings(settings)
            self.update()
    
    display_widget = ConfidenceDisplayWidget()
    layout.addWidget(display_widget)
    
    # Connect control to display
    control_widget.settings_changed.connect(display_widget.update_settings)
    
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    
    window.show()
    
    # Print confidence statistics
    stats = display_widget.visualizer.get_confidence_statistics(display_widget.confidence_map)
    print(f"Confidence statistics: {stats}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()