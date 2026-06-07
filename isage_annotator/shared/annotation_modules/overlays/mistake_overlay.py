"""
Mistake Overlay - Displays prediction vs ground truth comparison

This module provides mistake analysis visualization comparing predictions
with ground truth as used in the ABILIUS system.
"""

from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from ..base_protocols import BaseComponent, OverlayType, OverlayData, QPixmap, QColor
from .base_overlay import BaseOverlay


class MistakeOverlay(BaseOverlay):
    """Overlay for displaying prediction vs ground truth comparison."""
    
    def __init__(self, name: str = "mistake_overlay", version: str = "1.0.0"):
        super().__init__(name, OverlayType.MISTAKE, version)
        
        # Mistake visualization configuration
        self._mistake_colors = {
            'correct': QColor(0, 255, 0, 128),        # Green - Correct predictions
            'false_positive': QColor(255, 0, 0, 128), # Red - False positives
            'false_negative': QColor(255, 255, 0, 128), # Yellow - False negatives
            'wrong_class': QColor(255, 0, 255, 128),  # Magenta - Wrong class
            'ignore': QColor(0, 0, 0, 0)             # Transparent - Ignore index
        }
        
        # Analysis configuration
        self._ignore_index: int = 255
        self._confidence_threshold: float = 0.5
        self._show_mistake_stats: bool = True
        self._highlight_confidence: bool = True
        self._min_region_size: int = 10  # Minimum region size for analysis
        
        # Cached analysis results
        self._mistake_analysis: Optional[Dict[str, Any]] = None
        self._per_class_analysis: Optional[Dict[int, Dict[str, Any]]] = None
    
    def initialize(self, **kwargs) -> bool:
        """Initialize mistake overlay."""
        self._ignore_index = kwargs.get('ignore_index', 255)
        self._confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        self._show_mistake_stats = kwargs.get('show_mistake_stats', True)
        self._highlight_confidence = kwargs.get('highlight_confidence', True)
        self._min_region_size = kwargs.get('min_region_size', 10)
        
        # Set custom colors if provided
        if 'mistake_colors' in kwargs:
            self._mistake_colors.update(kwargs['mistake_colors'])
        
        return super().initialize(**kwargs)
    
    def set_comparison_data(self, 
                           predictions: np.ndarray, 
                           ground_truth: np.ndarray,
                           confidences: Optional[np.ndarray] = None) -> bool:
        """Set prediction and ground truth data for comparison."""
        try:
            if predictions.shape != ground_truth.shape:
                self.emit_error(f"Predictions and ground truth must have same shape. "
                               f"Got {predictions.shape} vs {ground_truth.shape}")
                return False
            
            if predictions.ndim != 2:
                self.emit_error(f"Predictions and ground truth must be 2D. Got {predictions.ndim}D")
                return False
            
            # Process comparison data
            mistake_data = self._process_comparison_data(predictions, ground_truth, confidences)
            
            # Perform analysis
            self._perform_mistake_analysis(predictions, ground_truth, confidences)
            
            # Create overlay data
            overlay_data = OverlayData(
                overlay_type=OverlayType.MISTAKE,
                data=mistake_data,
                opacity=self._opacity,
                color_map=None,
                visible=self._visible,
                metadata={
                    'prediction_shape': predictions.shape,
                    'has_confidences': confidences is not None,
                    'confidence_threshold': self._confidence_threshold,
                    'ignore_index': self._ignore_index,
                    'mistake_analysis': self._mistake_analysis
                }
            )
            
            return self.set_overlay_data(overlay_data)
            
        except Exception as e:
            self.emit_error(f"Error setting comparison data: {str(e)}")
            return False
    
    def set_mistake_colors(self, colors: Dict[str, QColor]) -> None:
        """Set mistake visualization colors."""
        self._mistake_colors.update(colors)
        self._cache_valid = False
        self.emit_state_changed({'mistake_colors_changed': True})
    
    def get_mistake_colors(self) -> Dict[str, QColor]:
        """Get mistake visualization colors."""
        return self._mistake_colors.copy()
    
    def set_mistake_color(self, mistake_type: str, color: QColor) -> None:
        """Set color for specific mistake type."""
        if mistake_type in self._mistake_colors:
            self._mistake_colors[mistake_type] = color
            self._cache_valid = False
            self.emit_state_changed({'mistake_color_changed': mistake_type})
    
    def get_mistake_color(self, mistake_type: str) -> QColor:
        """Get color for specific mistake type."""
        return self._mistake_colors.get(mistake_type, QColor(255, 255, 255))
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set confidence threshold for analysis."""
        self._confidence_threshold = max(0.0, min(1.0, threshold))
        self._cache_valid = False
        self.emit_state_changed({'confidence_threshold': threshold})
    
    def get_confidence_threshold(self) -> float:
        """Get confidence threshold."""
        return self._confidence_threshold
    
    def set_show_mistake_stats(self, show: bool) -> None:
        """Enable/disable mistake statistics display."""
        self._show_mistake_stats = show
        self._cache_valid = False
        self.emit_state_changed({'show_mistake_stats': show})
    
    def is_show_mistake_stats_enabled(self) -> bool:
        """Check if mistake statistics are shown."""
        return self._show_mistake_stats
    
    def set_highlight_confidence(self, highlight: bool) -> None:
        """Enable/disable confidence highlighting."""
        self._highlight_confidence = highlight
        self._cache_valid = False
        self.emit_state_changed({'highlight_confidence': highlight})
    
    def is_highlight_confidence_enabled(self) -> bool:
        """Check if confidence highlighting is enabled."""
        return self._highlight_confidence
    
    def set_min_region_size(self, size: int) -> None:
        """Set minimum region size for analysis."""
        self._min_region_size = max(1, size)
        self._cache_valid = False
        self.emit_state_changed({'min_region_size': size})
    
    def get_min_region_size(self) -> int:
        """Get minimum region size."""
        return self._min_region_size
    
    def get_mistake_analysis(self) -> Optional[Dict[str, Any]]:
        """Get mistake analysis results."""
        return self._mistake_analysis
    
    def get_per_class_analysis(self) -> Optional[Dict[int, Dict[str, Any]]]:
        """Get per-class mistake analysis."""
        return self._per_class_analysis
    
    def _render_overlay(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render mistake overlay to pixmap."""
        if not self.has_data():
            return None
        
        try:
            # Get mistake data
            mistake_data = self._overlay_data.data
            
            # Create colored mistake visualization
            colored_mistakes = self._create_colored_mistakes(mistake_data)
            
            # Convert to pixmap
            pixmap = self._array_to_pixmap(colored_mistakes)
            
            # Add statistics if enabled
            if self._show_mistake_stats and self._mistake_analysis:
                pixmap = self._add_mistake_statistics(pixmap)
            
            # Resize to canvas size if needed
            if pixmap.size() != canvas_size:
                from PyQt5.QtCore import Qt
                pixmap = pixmap.scaled(
                    canvas_size[0], canvas_size[1],
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error rendering mistake overlay: {str(e)}")
            return None
    
    def _process_comparison_data(self, 
                                predictions: np.ndarray, 
                                ground_truth: np.ndarray,
                                confidences: Optional[np.ndarray]) -> np.ndarray:
        """Process comparison data to create mistake map."""
        height, width = predictions.shape
        mistake_map = np.zeros((height, width), dtype=np.uint8)
        
        # Create masks for different mistake types
        valid_mask = ground_truth != self._ignore_index
        
        # Correct predictions
        correct_mask = (predictions == ground_truth) & valid_mask
        mistake_map[correct_mask] = 1
        
        # False positives (predicted class when should be background/ignore)
        false_positive_mask = (predictions != ground_truth) & (ground_truth == 0) & valid_mask
        mistake_map[false_positive_mask] = 2
        
        # False negatives (predicted background when should be class)
        false_negative_mask = (predictions == 0) & (ground_truth != 0) & valid_mask
        mistake_map[false_negative_mask] = 3
        
        # Wrong class (predicted wrong class, neither is background)
        wrong_class_mask = (predictions != ground_truth) & (predictions != 0) & (ground_truth != 0) & valid_mask
        mistake_map[wrong_class_mask] = 4
        
        # Apply confidence filtering if available
        if confidences is not None and self._highlight_confidence:
            low_confidence_mask = confidences < self._confidence_threshold
            # Reduce intensity for low confidence predictions
            mistake_map[low_confidence_mask & (mistake_map > 0)] = mistake_map[low_confidence_mask & (mistake_map > 0)] + 4
        
        return mistake_map
    
    def _create_colored_mistakes(self, mistake_map: np.ndarray) -> np.ndarray:
        """Create colored mistake visualization."""
        height, width = mistake_map.shape
        colored = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
        
        # Color mapping
        color_mapping = {
            0: self._mistake_colors['ignore'],      # Ignore/background
            1: self._mistake_colors['correct'],     # Correct
            2: self._mistake_colors['false_positive'], # False positive
            3: self._mistake_colors['false_negative'], # False negative
            4: self._mistake_colors['wrong_class'],  # Wrong class
            5: self._mistake_colors['correct'],     # Correct (low confidence)
            6: self._mistake_colors['false_positive'], # False positive (low confidence)
            7: self._mistake_colors['false_negative'], # False negative (low confidence)
            8: self._mistake_colors['wrong_class']   # Wrong class (low confidence)
        }
        
        # Apply colors
        for mistake_type, color in color_mapping.items():
            mask = mistake_map == mistake_type
            if np.any(mask):
                alpha = color.alpha()
                
                # Reduce alpha for low confidence predictions
                if mistake_type > 4:
                    alpha = int(alpha * 0.5)
                
                colored[mask] = [color.red(), color.green(), color.blue(), alpha]
        
        return colored
    
    def _perform_mistake_analysis(self, 
                                 predictions: np.ndarray, 
                                 ground_truth: np.ndarray,
                                 confidences: Optional[np.ndarray]) -> None:
        """Perform comprehensive mistake analysis."""
        try:
            # Basic statistics
            valid_mask = ground_truth != self._ignore_index
            total_valid_pixels = np.sum(valid_mask)
            
            if total_valid_pixels == 0:
                self._mistake_analysis = None
                self._per_class_analysis = None
                return
            
            # Overall accuracy
            correct_predictions = np.sum((predictions == ground_truth) & valid_mask)
            overall_accuracy = correct_predictions / total_valid_pixels
            
            # Mistake type counts
            false_positives = np.sum((predictions != ground_truth) & (ground_truth == 0) & valid_mask)
            false_negatives = np.sum((predictions == 0) & (ground_truth != 0) & valid_mask)
            wrong_class = np.sum((predictions != ground_truth) & (predictions != 0) & (ground_truth != 0) & valid_mask)
            
            # Confidence analysis
            confidence_stats = {}
            if confidences is not None:
                valid_confidences = confidences[valid_mask]
                confidence_stats = {
                    'mean_confidence': float(np.mean(valid_confidences)),
                    'std_confidence': float(np.std(valid_confidences)),
                    'min_confidence': float(np.min(valid_confidences)),
                    'max_confidence': float(np.max(valid_confidences)),
                    'low_confidence_ratio': float(np.mean(valid_confidences < self._confidence_threshold))
                }
            
            # Store overall analysis
            self._mistake_analysis = {
                'overall_accuracy': float(overall_accuracy),
                'total_pixels': int(total_valid_pixels),
                'correct_predictions': int(correct_predictions),
                'false_positives': int(false_positives),
                'false_negatives': int(false_negatives),
                'wrong_class': int(wrong_class),
                'false_positive_rate': float(false_positives / total_valid_pixels),
                'false_negative_rate': float(false_negatives / total_valid_pixels),
                'wrong_class_rate': float(wrong_class / total_valid_pixels),
                'confidence_stats': confidence_stats
            }
            
            # Per-class analysis
            self._per_class_analysis = {}
            unique_classes = np.unique(ground_truth[valid_mask])
            
            for class_id in unique_classes:
                if class_id == self._ignore_index:
                    continue
                
                class_mask = (ground_truth == class_id) & valid_mask
                class_pixels = np.sum(class_mask)
                
                if class_pixels > 0:
                    class_correct = np.sum((predictions == class_id) & class_mask)
                    class_accuracy = class_correct / class_pixels
                    
                    # Class-specific mistakes
                    class_false_neg = np.sum((predictions != class_id) & class_mask)
                    class_false_pos = np.sum((predictions == class_id) & (ground_truth != class_id) & valid_mask)
                    
                    # Precision and recall
                    precision = class_correct / (class_correct + class_false_pos) if (class_correct + class_false_pos) > 0 else 0
                    recall = class_correct / (class_correct + class_false_neg) if (class_correct + class_false_neg) > 0 else 0
                    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                    
                    self._per_class_analysis[int(class_id)] = {
                        'accuracy': float(class_accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1_score': float(f1_score),
                        'total_pixels': int(class_pixels),
                        'correct_pixels': int(class_correct),
                        'false_positives': int(class_false_pos),
                        'false_negatives': int(class_false_neg)
                    }
            
        except Exception as e:
            self.emit_error(f"Error performing mistake analysis: {str(e)}")
            self._mistake_analysis = None
            self._per_class_analysis = None
    
    def _add_mistake_statistics(self, pixmap: QPixmap) -> QPixmap:
        """Add mistake statistics to pixmap."""
        try:
            from PyQt5.QtGui import QPainter, QFont, QPen, QBrush
            from PyQt5.QtCore import Qt, QRect
            
            if not self._mistake_analysis:
                return pixmap
            
            # Create painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set font
            font = QFont("Arial", 10)
            painter.setFont(font)
            
            # Background
            background_color = QColor(0, 0, 0, 180)
            text_color = QColor(255, 255, 255)
            
            # Create statistics text
            stats = self._mistake_analysis
            stat_lines = [
                f"Overall Accuracy: {stats['overall_accuracy']:.3f}",
                f"False Positive Rate: {stats['false_positive_rate']:.3f}",
                f"False Negative Rate: {stats['false_negative_rate']:.3f}",
                f"Wrong Class Rate: {stats['wrong_class_rate']:.3f}"
            ]
            
            # Add confidence statistics if available
            if stats['confidence_stats']:
                conf_stats = stats['confidence_stats']
                stat_lines.extend([
                    f"Mean Confidence: {conf_stats['mean_confidence']:.3f}",
                    f"Low Confidence: {conf_stats['low_confidence_ratio']:.3f}"
                ])
            
            # Calculate text dimensions
            font_metrics = painter.fontMetrics()
            line_height = font_metrics.height()
            max_width = max(font_metrics.width(line) for line in stat_lines)
            
            # Draw background
            stats_rect = QRect(10, 10, max_width + 20, len(stat_lines) * line_height + 20)
            painter.fillRect(stats_rect, QBrush(background_color))
            
            # Draw text
            painter.setPen(QPen(text_color))
            y_offset = 25
            for line in stat_lines:
                painter.drawText(20, y_offset, line)
                y_offset += line_height
            
            painter.end()
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error adding mistake statistics: {str(e)}")
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
            else:
                # Convert to RGBA
                rgba_array = np.zeros((height, width, 4), dtype=np.uint8)
                if len(array.shape) == 3:
                    rgba_array[:, :, :3] = array[:, :, :3]
                    rgba_array[:, :, 3] = 255
                else:
                    rgba_array[:, :, 0] = array
                    rgba_array[:, :, 1] = array
                    rgba_array[:, :, 2] = array
                    rgba_array[:, :, 3] = 255
                
                bytes_per_line = 4 * width
                q_image = QImage(rgba_array.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            
            return QPixmap.fromImage(q_image)
            
        except Exception as e:
            self.emit_error(f"Error converting array to pixmap: {str(e)}")
            return QPixmap()
    
    def export_mistake_analysis(self, output_path: str) -> bool:
        """Export mistake analysis to JSON file."""
        if not self._mistake_analysis:
            return False
        
        try:
            import json
            
            export_data = {
                'mistake_analysis': self._mistake_analysis,
                'per_class_analysis': self._per_class_analysis,
                'configuration': {
                    'confidence_threshold': self._confidence_threshold,
                    'ignore_index': self._ignore_index,
                    'min_region_size': self._min_region_size
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error exporting mistake analysis: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mistake overlay statistics."""
        stats = super().get_statistics()
        stats.update({
            'confidence_threshold': self._confidence_threshold,
            'ignore_index': self._ignore_index,
            'show_mistake_stats': self._show_mistake_stats,
            'highlight_confidence': self._highlight_confidence,
            'min_region_size': self._min_region_size,
            'mistake_analysis': self._mistake_analysis,
            'per_class_analysis': self._per_class_analysis,
            'mistake_colors': {k: v.name() for k, v in self._mistake_colors.items()}
        })
        return stats