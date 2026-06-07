"""
Mistake Highlighting Overlay System

Provides visual highlighting of prediction errors and annotation mistakes.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import QWidget
    from PyQt5.QtCore import Qt, QRect, QPoint
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPolygon
    )
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QWidget: pass

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MistakeType(Enum):
    """Types of mistakes that can be highlighted."""
    PREDICTION_ERROR = "prediction_error"
    ANNOTATION_INCONSISTENCY = "annotation_inconsistency"
    UNCERTAIN_PREDICTION = "uncertain_prediction"
    MISSING_ANNOTATION = "missing_annotation"


@dataclass
class MistakeHighlight:
    """Individual mistake highlight information."""
    x: int
    y: int
    mistake_type: MistakeType
    confidence: float
    predicted_class: int
    ground_truth_class: int
    description: str
    severity: float  # 0.0 to 1.0


class MistakeHighlighter:
    """
    Mistake highlighting system for annotation overlays.
    
    Features:
    - Multiple mistake types with different visual styles
    - Confidence-based highlighting intensity
    - Customizable color schemes
    - Performance-optimized rendering
    """
    
    def __init__(self):
        # Color schemes for different mistake types
        self.color_schemes = {
            MistakeType.PREDICTION_ERROR: {
                'color': QColor(255, 0, 0),      # Red
                'border': QColor(255, 100, 100), # Light red
                'alpha': 180
            },
            MistakeType.ANNOTATION_INCONSISTENCY: {
                'color': QColor(255, 165, 0),    # Orange
                'border': QColor(255, 200, 100), # Light orange
                'alpha': 160
            },
            MistakeType.UNCERTAIN_PREDICTION: {
                'color': QColor(255, 255, 0),    # Yellow
                'border': QColor(255, 255, 150), # Light yellow
                'alpha': 140
            },
            MistakeType.MISSING_ANNOTATION: {
                'color': QColor(255, 0, 255),    # Magenta
                'border': QColor(255, 150, 255), # Light magenta
                'alpha': 120
            }
        }
        
        # Highlight settings
        self.highlight_radius = 8
        self.border_width = 2
        self.animation_enabled = True
        self.show_confidence = True
        
        # State
        self.highlights = []
        self.enabled = True
        self.opacity = 0.7
        
    def add_highlight(self, highlight: MistakeHighlight):
        """Add a mistake highlight."""
        self.highlights.append(highlight)
    
    def clear_highlights(self):
        """Clear all highlights."""
        self.highlights.clear()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable highlighting."""
        self.enabled = enabled
    
    def set_opacity(self, opacity: float):
        """Set highlight opacity (0.0 to 1.0)."""
        self.opacity = max(0.0, min(1.0, opacity))
    
    def analyze_predictions(self, predictions: np.ndarray, ground_truth: np.ndarray, 
                          confidence_threshold: float = 0.5) -> List[MistakeHighlight]:
        """
        Analyze predictions vs ground truth to identify mistakes.
        
        Args:
            predictions: Predicted class map (H, W)
            ground_truth: Ground truth class map (H, W)
            confidence_threshold: Minimum confidence for highlighting
            
        Returns:
            List of mistake highlights
        """
        highlights = []
        
        if predictions.shape != ground_truth.shape:
            return highlights
        
        # Find prediction errors
        error_mask = predictions != ground_truth
        error_positions = np.where(error_mask)
        
        for y, x in zip(error_positions[0], error_positions[1]):
            pred_class = predictions[y, x]
            gt_class = ground_truth[y, x]
            
            # Skip ignore index
            if gt_class == 255:
                continue
            
            # Calculate confidence based on local consistency
            confidence = self._calculate_local_confidence(predictions, x, y)
            
            if confidence >= confidence_threshold:
                highlight = MistakeHighlight(
                    x=int(x),
                    y=int(y),
                    mistake_type=MistakeType.PREDICTION_ERROR,
                    confidence=confidence,
                    predicted_class=int(pred_class),
                    ground_truth_class=int(gt_class),
                    description=f"Predicted: {pred_class}, GT: {gt_class}",
                    severity=confidence
                )
                highlights.append(highlight)
        
        return highlights
    
    def analyze_annotation_consistency(self, annotations: List[Dict[str, Any]], 
                                     predictions: np.ndarray) -> List[MistakeHighlight]:
        """
        Analyze annotation consistency with predictions.
        
        Args:
            annotations: List of point annotations
            predictions: Predicted class map (H, W)
            
        Returns:
            List of inconsistency highlights
        """
        highlights = []
        
        for ann in annotations:
            x = ann.get('x', 0)
            y = ann.get('y', 0)
            gt_class = ann.get('class_id', 0)
            
            # Check bounds
            if (0 <= x < predictions.shape[1] and 
                0 <= y < predictions.shape[0]):
                
                pred_class = predictions[y, x]
                
                if pred_class != gt_class:
                    # Calculate local confidence
                    confidence = self._calculate_local_confidence(predictions, x, y)
                    
                    highlight = MistakeHighlight(
                        x=x,
                        y=y,
                        mistake_type=MistakeType.ANNOTATION_INCONSISTENCY,
                        confidence=confidence,
                        predicted_class=int(pred_class),
                        ground_truth_class=int(gt_class),
                        description=f"Annotation: {gt_class}, Prediction: {pred_class}",
                        severity=confidence
                    )
                    highlights.append(highlight)
        
        return highlights
    
    def _calculate_local_confidence(self, predictions: np.ndarray, x: int, y: int, 
                                  window_size: int = 5) -> float:
        """
        Calculate local confidence based on prediction consistency.
        
        Args:
            predictions: Predicted class map
            x, y: Center coordinates
            window_size: Size of local window
            
        Returns:
            Confidence value (0.0 to 1.0)
        """
        try:
            # Extract local window
            half_window = window_size // 2
            y_start = max(0, y - half_window)
            y_end = min(predictions.shape[0], y + half_window + 1)
            x_start = max(0, x - half_window)
            x_end = min(predictions.shape[1], x + half_window + 1)
            
            local_window = predictions[y_start:y_end, x_start:x_end]
            center_class = predictions[y, x]
            
            # Calculate consistency
            matching_pixels = np.sum(local_window == center_class)
            total_pixels = local_window.size
            
            return matching_pixels / total_pixels
            
        except Exception:
            return 0.5
    
    def paint_highlights(self, painter: QPainter, scale_factor: float = 1.0):
        """
        Paint all highlights on the given painter.
        
        Args:
            painter: QPainter instance
            scale_factor: Scaling factor for coordinates
        """
        if not self.enabled or not self.highlights:
            return
        
        painter.save()
        
        # Set antialiasing for smooth circles
        painter.setRenderHint(QPainter.Antialiasing)
        
        for highlight in self.highlights:
            self._paint_single_highlight(painter, highlight, scale_factor)
        
        painter.restore()
    
    def _paint_single_highlight(self, painter: QPainter, highlight: MistakeHighlight, 
                               scale_factor: float):
        """Paint a single highlight."""
        # Get color scheme
        scheme = self.color_schemes.get(highlight.mistake_type)
        if not scheme:
            return
        
        # Scale coordinates
        x = highlight.x * scale_factor
        y = highlight.y * scale_factor
        radius = self.highlight_radius * scale_factor
        
        # Adjust alpha based on confidence and opacity
        alpha = int(scheme['alpha'] * highlight.confidence * self.opacity)
        
        # Create colors with adjusted alpha
        fill_color = QColor(scheme['color'])
        fill_color.setAlpha(alpha)
        
        border_color = QColor(scheme['border'])
        border_color.setAlpha(min(255, alpha + 50))
        
        # Draw highlight circle
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(border_color, self.border_width))
        painter.drawEllipse(QPoint(int(x), int(y)), int(radius), int(radius))
        
        # Draw severity indicator (small inner circle)
        if highlight.severity > 0.7:
            inner_radius = radius * 0.3
            inner_color = QColor(255, 255, 255, alpha)
            painter.setBrush(QBrush(inner_color))
            painter.setPen(QPen(inner_color, 1))
            painter.drawEllipse(QPoint(int(x), int(y)), int(inner_radius), int(inner_radius))
    
    def get_highlight_at_position(self, x: int, y: int, 
                                 tolerance: int = 10) -> Optional[MistakeHighlight]:
        """
        Get highlight at the given position.
        
        Args:
            x, y: Position coordinates
            tolerance: Distance tolerance
            
        Returns:
            MistakeHighlight if found, None otherwise
        """
        for highlight in self.highlights:
            dx = highlight.x - x
            dy = highlight.y - y
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance <= tolerance:
                return highlight
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current highlights."""
        if not self.highlights:
            return {}
        
        stats = {
            'total_highlights': len(self.highlights),
            'by_type': {},
            'average_confidence': 0.0,
            'high_severity_count': 0
        }
        
        # Count by type
        for highlight in self.highlights:
            mistake_type = highlight.mistake_type.value
            stats['by_type'][mistake_type] = stats['by_type'].get(mistake_type, 0) + 1
        
        # Calculate average confidence
        total_confidence = sum(h.confidence for h in self.highlights)
        stats['average_confidence'] = total_confidence / len(self.highlights)
        
        # Count high severity
        stats['high_severity_count'] = sum(1 for h in self.highlights if h.severity > 0.7)
        
        return stats


class MistakeHighlightOverlay(QWidget):
    """
    Widget overlay for displaying mistake highlights.
    
    Features:
    - Transparent overlay widget
    - Handles mouse events for highlight interaction
    - Tooltip display for highlight information
    - Integration with annotation canvas
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = MistakeHighlighter()
        self.scale_factor = 1.0
        
        # Enable mouse tracking for tooltips
        self.setMouseTracking(True)
        
        # Make widget transparent
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")
    
    def set_highlights(self, highlights: List[MistakeHighlight]):
        """Set the highlights to display."""
        self.highlighter.clear_highlights()
        for highlight in highlights:
            self.highlighter.add_highlight(highlight)
        self.update()
    
    def set_scale_factor(self, scale_factor: float):
        """Set the scaling factor for coordinates."""
        self.scale_factor = scale_factor
        self.update()
    
    def paintEvent(self, event):
        """Paint the highlights."""
        painter = QPainter(self)
        self.highlighter.paint_highlights(painter, self.scale_factor)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for tooltips."""
        # Convert to image coordinates
        image_x = int(event.x() / self.scale_factor)
        image_y = int(event.y() / self.scale_factor)
        
        # Find highlight at position
        highlight = self.highlighter.get_highlight_at_position(image_x, image_y)
        
        if highlight:
            # Show tooltip
            tooltip_text = (
                f"Type: {highlight.mistake_type.value}\n"
                f"Confidence: {highlight.confidence:.2f}\n"
                f"Severity: {highlight.severity:.2f}\n"
                f"{highlight.description}"
            )
            self.setToolTip(tooltip_text)
        else:
            self.setToolTip("")
        
        super().mouseMoveEvent(event)


def main():
    """Test the mistake highlighter component."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Mistake Highlighter Test")
    window.setGeometry(100, 100, 600, 400)
    
    # Create overlay widget
    overlay = MistakeHighlightOverlay()
    
    # Create test highlights
    test_highlights = [
        MistakeHighlight(
            x=100, y=100, mistake_type=MistakeType.PREDICTION_ERROR,
            confidence=0.8, predicted_class=1, ground_truth_class=0,
            description="Prediction error", severity=0.8
        ),
        MistakeHighlight(
            x=200, y=150, mistake_type=MistakeType.ANNOTATION_INCONSISTENCY,
            confidence=0.6, predicted_class=2, ground_truth_class=1,
            description="Annotation inconsistency", severity=0.6
        ),
        MistakeHighlight(
            x=300, y=200, mistake_type=MistakeType.UNCERTAIN_PREDICTION,
            confidence=0.4, predicted_class=0, ground_truth_class=0,
            description="Uncertain prediction", severity=0.4
        )
    ]
    
    overlay.set_highlights(test_highlights)
    overlay.set_scale_factor(2.0)
    
    window.setCentralWidget(overlay)
    window.show()
    
    # Print statistics
    stats = overlay.highlighter.get_statistics()
    print(f"Mistake statistics: {stats}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()