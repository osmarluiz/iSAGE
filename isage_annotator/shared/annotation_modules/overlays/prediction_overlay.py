"""
Prediction Overlay - Displays model predictions with confidence mapping

This module provides prediction visualization with red-blue confidence mapping
as used in the ABILIUS system.
"""

from typing import Optional, Tuple, Dict, Any
import numpy as np
from ..base_protocols import BaseComponent, OverlayType, OverlayData, QPixmap, QColor
from .base_overlay import BaseOverlay


class PredictionOverlay(BaseOverlay):
    """Overlay for displaying model predictions with confidence mapping."""
    
    def __init__(self, name: str = "prediction_overlay", version: str = "1.0.0"):
        super().__init__(name, OverlayType.PREDICTION, version)
        
        # Prediction-specific configuration
        self._confidence_threshold: float = 0.5
        self._use_confidence_mapping: bool = True
        self._color_scheme: str = "red_blue"  # red_blue, heatmap, viridis
        self._show_uncertainty: bool = True
        self._uncertainty_threshold: float = 0.1
        
        # Color mapping
        self._color_maps = {
            'red_blue': self._create_red_blue_colormap(),
            'heatmap': self._create_heatmap_colormap(),
            'viridis': self._create_viridis_colormap()
        }
    
    def initialize(self, **kwargs) -> bool:
        """Initialize prediction overlay."""
        self._confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        self._use_confidence_mapping = kwargs.get('use_confidence_mapping', True)
        self._color_scheme = kwargs.get('color_scheme', 'red_blue')
        self._show_uncertainty = kwargs.get('show_uncertainty', True)
        self._uncertainty_threshold = kwargs.get('uncertainty_threshold', 0.1)
        
        return super().initialize(**kwargs)
    
    def set_prediction_data(self, predictions: np.ndarray, confidences: Optional[np.ndarray] = None) -> bool:
        """Set prediction data with optional confidence values."""
        try:
            if predictions.ndim == 2:
                # Single class predictions
                processed_data = self._process_single_class_predictions(predictions, confidences)
            elif predictions.ndim == 3:
                # Multi-class predictions (H, W, C)
                processed_data = self._process_multi_class_predictions(predictions)
            else:
                self.emit_error(f"Unsupported prediction shape: {predictions.shape}")
                return False
            
            # Create overlay data
            overlay_data = OverlayData(
                overlay_type=OverlayType.PREDICTION,
                data=processed_data,
                opacity=self._opacity,
                color_map=self._color_scheme,
                visible=self._visible,
                metadata={
                    'prediction_shape': predictions.shape,
                    'has_confidences': confidences is not None,
                    'confidence_threshold': self._confidence_threshold,
                    'color_scheme': self._color_scheme
                }
            )
            
            return self.set_overlay_data(overlay_data)
            
        except Exception as e:
            self.emit_error(f"Error setting prediction data: {str(e)}")
            return False
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set confidence threshold for display."""
        self._confidence_threshold = max(0.0, min(1.0, threshold))
        self._cache_valid = False
        self.emit_state_changed({'confidence_threshold': threshold})
    
    def get_confidence_threshold(self) -> float:
        """Get confidence threshold."""
        return self._confidence_threshold
    
    def set_use_confidence_mapping(self, use_mapping: bool) -> None:
        """Enable/disable confidence mapping."""
        self._use_confidence_mapping = use_mapping
        self._cache_valid = False
        self.emit_state_changed({'use_confidence_mapping': use_mapping})
    
    def is_confidence_mapping_enabled(self) -> bool:
        """Check if confidence mapping is enabled."""
        return self._use_confidence_mapping
    
    def set_color_scheme(self, scheme: str) -> None:
        """Set color scheme."""
        if scheme in self._color_maps:
            self._color_scheme = scheme
            self._cache_valid = False
            self.emit_state_changed({'color_scheme': scheme})
    
    def get_color_scheme(self) -> str:
        """Get current color scheme."""
        return self._color_scheme
    
    def set_show_uncertainty(self, show: bool) -> None:
        """Enable/disable uncertainty visualization."""
        self._show_uncertainty = show
        self._cache_valid = False
        self.emit_state_changed({'show_uncertainty': show})
    
    def is_show_uncertainty_enabled(self) -> bool:
        """Check if uncertainty visualization is enabled."""
        return self._show_uncertainty
    
    def set_uncertainty_threshold(self, threshold: float) -> None:
        """Set uncertainty threshold."""
        self._uncertainty_threshold = max(0.0, min(1.0, threshold))
        self._cache_valid = False
        self.emit_state_changed({'uncertainty_threshold': threshold})
    
    def get_uncertainty_threshold(self) -> float:
        """Get uncertainty threshold."""
        return self._uncertainty_threshold
    
    def get_available_color_schemes(self) -> list:
        """Get available color schemes."""
        return list(self._color_maps.keys())
    
    def _render_overlay(self, canvas_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Render prediction overlay to pixmap."""
        if not self.has_data():
            return None
        
        try:
            # Get prediction data
            data = self._overlay_data.data
            
            # Apply confidence mapping if enabled
            if self._use_confidence_mapping:
                colored_data = self._apply_confidence_mapping(data)
            else:
                colored_data = self._apply_class_mapping(data)
            
            # Convert to pixmap
            pixmap = self._array_to_pixmap(colored_data)
            
            # Resize to canvas size if needed
            if pixmap.size() != canvas_size:
                from PyQt5.QtCore import Qt
                pixmap = pixmap.scaled(
                    canvas_size[0], canvas_size[1],
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            return pixmap
            
        except Exception as e:
            self.emit_error(f"Error rendering prediction overlay: {str(e)}")
            return None
    
    def _process_single_class_predictions(self, predictions: np.ndarray, confidences: Optional[np.ndarray]) -> np.ndarray:
        """Process single class predictions."""
        if confidences is not None:
            # Use provided confidence values
            return np.stack([predictions, confidences], axis=-1)
        else:
            # Use predictions as confidence
            return np.stack([predictions, predictions], axis=-1)
    
    def _process_multi_class_predictions(self, predictions: np.ndarray) -> np.ndarray:
        """Process multi-class predictions."""
        # Get class with highest probability
        class_predictions = np.argmax(predictions, axis=-1)
        
        # Get confidence as max probability
        confidence_predictions = np.max(predictions, axis=-1)
        
        return np.stack([class_predictions, confidence_predictions], axis=-1)
    
    def _apply_confidence_mapping(self, data: np.ndarray) -> np.ndarray:
        """Apply confidence-based color mapping."""
        if data.shape[-1] < 2:
            return self._apply_class_mapping(data)
        
        # Get class and confidence
        class_data = data[:, :, 0]
        confidence_data = data[:, :, 1]
        
        # Get color map
        color_map = self._color_maps[self._color_scheme]
        
        # Apply threshold
        mask = confidence_data >= self._confidence_threshold
        
        # Create colored image
        colored = np.zeros((*data.shape[:2], 4), dtype=np.uint8)  # RGBA
        
        # Apply colors based on confidence
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if mask[i, j]:
                    confidence = confidence_data[i, j]
                    color = self._get_color_from_confidence(confidence, color_map)
                    colored[i, j] = color
                else:
                    # Transparent for low confidence
                    colored[i, j] = [0, 0, 0, 0]
        
        # Apply opacity
        colored[:, :, 3] = (colored[:, :, 3] * self._opacity).astype(np.uint8)
        
        return colored
    
    def _apply_class_mapping(self, data: np.ndarray) -> np.ndarray:
        """Apply class-based color mapping."""
        if data.ndim == 2:
            class_data = data
        else:
            class_data = data[:, :, 0]
        
        # Create colored image
        colored = np.zeros((*class_data.shape, 4), dtype=np.uint8)  # RGBA
        
        # Define class colors
        class_colors = [
            [255, 0, 0, 255],    # Red
            [0, 255, 0, 255],    # Green  
            [0, 0, 255, 255],    # Blue
            [255, 255, 0, 255],  # Yellow
            [255, 0, 255, 255],  # Magenta
            [0, 255, 255, 255],  # Cyan
            [255, 255, 255, 255] # White
        ]
        
        # Apply colors by class
        for class_id in range(len(class_colors)):
            mask = class_data == class_id
            colored[mask] = class_colors[class_id]
        
        # Apply opacity
        colored[:, :, 3] = (colored[:, :, 3] * self._opacity).astype(np.uint8)
        
        return colored
    
    def _get_color_from_confidence(self, confidence: float, color_map: np.ndarray) -> np.ndarray:
        """Get color from confidence value using color map."""
        # Map confidence to color map index
        index = int(confidence * (len(color_map) - 1))
        index = max(0, min(len(color_map) - 1, index))
        
        color = color_map[index].copy()
        color[3] = int(255 * self._opacity)  # Apply opacity
        
        return color
    
    def _create_red_blue_colormap(self) -> np.ndarray:
        """Create red-blue confidence colormap (ABILIUS style)."""
        # Create colormap from blue (low confidence) to red (high confidence)
        colormap = np.zeros((256, 4), dtype=np.uint8)
        
        for i in range(256):
            confidence = i / 255.0
            
            if confidence < 0.5:
                # Blue to purple
                red = int(255 * (confidence * 2))
                green = 0
                blue = 255
            else:
                # Purple to red
                red = 255
                green = 0
                blue = int(255 * (2 - confidence * 2))
            
            colormap[i] = [red, green, blue, 255]
        
        return colormap
    
    def _create_heatmap_colormap(self) -> np.ndarray:
        """Create heatmap colormap."""
        colormap = np.zeros((256, 4), dtype=np.uint8)
        
        for i in range(256):
            confidence = i / 255.0
            
            if confidence < 0.25:
                # Black to blue
                red = 0
                green = 0
                blue = int(255 * (confidence * 4))
            elif confidence < 0.5:
                # Blue to cyan
                red = 0
                green = int(255 * ((confidence - 0.25) * 4))
                blue = 255
            elif confidence < 0.75:
                # Cyan to yellow
                red = int(255 * ((confidence - 0.5) * 4))
                green = 255
                blue = int(255 * (1 - (confidence - 0.5) * 4))
            else:
                # Yellow to red
                red = 255
                green = int(255 * (1 - (confidence - 0.75) * 4))
                blue = 0
            
            colormap[i] = [red, green, blue, 255]
        
        return colormap
    
    def _create_viridis_colormap(self) -> np.ndarray:
        """Create viridis-style colormap."""
        # Simplified viridis colormap
        colormap = np.zeros((256, 4), dtype=np.uint8)
        
        # Viridis color points
        colors = [
            [68, 1, 84],      # Dark purple
            [59, 82, 139],    # Blue
            [33, 144, 140],   # Teal
            [93, 201, 99],    # Green
            [253, 231, 37]    # Yellow
        ]
        
        for i in range(256):
            t = i / 255.0
            
            # Interpolate between color points
            segment = t * (len(colors) - 1)
            idx = int(segment)
            frac = segment - idx
            
            if idx >= len(colors) - 1:
                color = colors[-1]
            else:
                color1 = colors[idx]
                color2 = colors[idx + 1]
                color = [
                    int(color1[0] * (1 - frac) + color2[0] * frac),
                    int(color1[1] * (1 - frac) + color2[1] * frac),
                    int(color1[2] * (1 - frac) + color2[2] * frac)
                ]
            
            colormap[i] = [color[0], color[1], color[2], 255]
        
        return colormap
    
    def _array_to_pixmap(self, array: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap."""
        try:
            from PyQt5.QtGui import QImage
            
            if array.dtype != np.uint8:
                # Convert to uint8
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get prediction overlay statistics."""
        stats = super().get_statistics()
        stats.update({
            'confidence_threshold': self._confidence_threshold,
            'use_confidence_mapping': self._use_confidence_mapping,
            'color_scheme': self._color_scheme,
            'show_uncertainty': self._show_uncertainty,
            'uncertainty_threshold': self._uncertainty_threshold,
            'available_color_schemes': self.get_available_color_schemes()
        })
        return stats