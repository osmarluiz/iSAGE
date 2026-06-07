"""
Enhanced Pixel Info Tooltip - Advanced pixel information tooltips with rich features

This enhanced version addresses potential issues and adds improvements:
- Better performance with caching and optimization
- Rich HTML formatting with customizable styles
- Support for multiple data layers and overlays
- Advanced statistics and analytics
- Improved accessibility features
- Better error handling and validation
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Callable, Union
from ..base_protocols import BaseComponent, QWidget, QPoint, QToolTip, QTimer, QLabel
from ..base_protocols import QVBoxLayout, QHBoxLayout, QFrame, QFont, QColor, QPalette
from ..base_protocols import pyqtSignal, QApplication
from functools import lru_cache
import time
import json
from collections import defaultdict, deque


class PixelInfoTooltip(BaseComponent):
    """Enhanced pixel information tooltip component with advanced features."""
    
    # Enhanced pixel info signals
    pixelInfoChanged = pyqtSignal(dict)  # pixel_info
    tooltipShown = pyqtSignal(QPoint)  # position
    tooltipHidden = pyqtSignal()
    dataLayerChanged = pyqtSignal(str)  # layer_name
    tooltipStyleChanged = pyqtSignal(str)  # style_name
    pixelHistoryUpdated = pyqtSignal(dict)  # history_data
    
    def __init__(self, name: str = "enhanced_pixel_info_tooltip", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Enhanced tooltip configuration
        self._enabled: bool = True
        self._show_coordinates: bool = True
        self._show_pixel_values: bool = True
        self._show_class_info: bool = True
        self._show_prediction_info: bool = True
        self._show_confidence_info: bool = True
        self._show_distance_info: bool = False
        self._show_statistics: bool = False
        self._show_metadata: bool = False
        self._show_history: bool = False
        
        # Advanced display settings
        self._decimal_places: int = 2
        self._coordinate_format: str = "({}, {})"
        self._value_format: str = "{:.{}f}"
        self._show_hex_values: bool = False
        self._show_rgb_values: bool = True
        self._show_hsv_values: bool = False
        self._show_channel_names: bool = True
        self._show_wavelengths: bool = False
        self._compact_mode: bool = False
        
        # Rich text and styling
        self._use_html_format: bool = True
        self._style_name: str = "default"
        self._custom_styles: Dict[str, Dict[str, str]] = {}
        self._color_scheme: str = "light"  # light, dark, auto
        self._font_family: str = "Arial"
        self._font_size: int = 10
        self._tooltip_theme: str = "modern"
        
        # Enhanced tooltip behavior
        self._show_delay: int = 300  # milliseconds
        self._hide_delay: int = 150  # milliseconds
        self._update_interval: int = 100  # milliseconds for dynamic updates
        self._follow_mouse: bool = True
        self._tooltip_offset: QPoint = QPoint(15, 15)
        self._max_width: int = 400
        self._max_height: int = 300
        self._auto_resize: bool = True
        
        # Multi-layer data support
        self._data_layers: Dict[str, Dict[str, Any]] = {}
        self._active_layers: List[str] = []
        self._layer_priorities: Dict[str, int] = {}
        self._layer_visibility: Dict[str, bool] = {}
        
        # Advanced canvas integration
        self._canvas = None
        self._image_data: Optional[np.ndarray] = None
        self._prediction_data: Optional[np.ndarray] = None
        self._ground_truth_data: Optional[np.ndarray] = None
        self._confidence_data: Optional[np.ndarray] = None
        self._class_names: List[str] = []
        self._channel_names: List[str] = []
        self._wavelengths: List[float] = []
        self._metadata: Dict[str, Any] = {}
        
        # Enhanced coordinate transformation
        self._scale_factor: float = 1.0
        self._image_offset: QPoint = QPoint(0, 0)
        self._rotation_angle: float = 0.0
        self._flip_horizontal: bool = False
        self._flip_vertical: bool = False
        
        # Performance optimization
        self._cache_enabled: bool = True
        self._cache_size: int = 100
        self._pixel_info_cache: Dict[str, Dict[str, Any]] = {}
        self._last_cache_cleanup: float = time.time()
        self._cache_cleanup_interval: float = 60.0  # seconds
        
        # Tooltip state and tracking
        self._current_position: Optional[QPoint] = None
        self._tooltip_visible: bool = False
        self._last_pixel_info: Dict[str, Any] = {}
        self._pixel_history: deque = deque(maxlen=50)
        self._hover_start_time: Optional[float] = None
        self._total_hover_time: float = 0.0
        
        # Enhanced timers
        self._show_timer: QTimer = QTimer()
        self._hide_timer: QTimer = QTimer()
        self._update_timer: QTimer = QTimer()
        self._cache_cleanup_timer: QTimer = QTimer()
        
        # Configure timers
        self._show_timer.setSingleShot(True)
        self._hide_timer.setSingleShot(True)
        self._update_timer.setSingleShot(False)
        self._cache_cleanup_timer.setSingleShot(False)
        
        # Connect timer signals
        self._show_timer.timeout.connect(self._show_tooltip)
        self._hide_timer.timeout.connect(self._hide_tooltip)
        self._update_timer.timeout.connect(self._update_tooltip_continuous)
        self._cache_cleanup_timer.timeout.connect(self._cleanup_cache)
        
        # Start cache cleanup timer
        self._cache_cleanup_timer.start(int(self._cache_cleanup_interval * 1000))
        
        # Custom info providers with priorities
        self._custom_info_providers: List[Tuple[Callable[[int, int], Dict[str, Any]], int]] = []
        self._info_filters: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        self._info_validators: List[Callable[[Dict[str, Any]], bool]] = []
        
        # Enhanced statistics
        self._tooltip_stats: Dict[str, Any] = {
            'tooltips_shown': 0,
            'tooltips_hidden': 0,
            'pixel_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_tooltip_duration': 0.0,
            'total_hover_time': 0.0,
            'most_queried_pixel': None,
            'query_frequency': defaultdict(int),
            'error_count': 0,
            'performance_metrics': {
                'avg_query_time': 0.0,
                'max_query_time': 0.0,
                'total_queries': 0
            }
        }
        
        # Accessibility features
        self._accessibility_enabled: bool = True
        self._screen_reader_support: bool = True
        self._high_contrast_mode: bool = False
        self._large_font_mode: bool = False
        self._keyboard_navigation: bool = True
        
        # Advanced features
        self._real_time_updates: bool = False
        self._interpolation_mode: str = "nearest"  # nearest, bilinear, bicubic
        self._subpixel_precision: bool = False
        self._show_neighborhood: bool = False
        self._neighborhood_size: int = 3
        
        # Initialize default styles and layers
        self._initialize_default_styles()
        self._initialize_default_layers()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced pixel info tooltip."""
        # Basic settings
        self._enabled = kwargs.get('enabled', True)
        self._show_coordinates = kwargs.get('show_coordinates', True)
        self._show_pixel_values = kwargs.get('show_pixel_values', True)
        self._show_class_info = kwargs.get('show_class_info', True)
        self._show_prediction_info = kwargs.get('show_prediction_info', True)
        self._show_confidence_info = kwargs.get('show_confidence_info', True)
        self._show_distance_info = kwargs.get('show_distance_info', False)
        self._show_statistics = kwargs.get('show_statistics', False)
        self._show_metadata = kwargs.get('show_metadata', False)
        self._show_history = kwargs.get('show_history', False)
        
        # Enhanced display settings
        self._decimal_places = kwargs.get('decimal_places', 2)
        self._coordinate_format = kwargs.get('coordinate_format', "({}, {})")
        self._value_format = kwargs.get('value_format', "{:.{}f}")
        self._show_hex_values = kwargs.get('show_hex_values', False)
        self._show_rgb_values = kwargs.get('show_rgb_values', True)
        self._show_hsv_values = kwargs.get('show_hsv_values', False)
        self._show_channel_names = kwargs.get('show_channel_names', True)
        self._show_wavelengths = kwargs.get('show_wavelengths', False)
        self._compact_mode = kwargs.get('compact_mode', False)
        
        # Rich text and styling
        self._use_html_format = kwargs.get('use_html_format', True)
        self._style_name = kwargs.get('style_name', 'default')
        self._color_scheme = kwargs.get('color_scheme', 'light')
        self._font_family = kwargs.get('font_family', 'Arial')
        self._font_size = kwargs.get('font_size', 10)
        self._tooltip_theme = kwargs.get('tooltip_theme', 'modern')
        
        # Behavior settings
        self._show_delay = kwargs.get('show_delay', 300)
        self._hide_delay = kwargs.get('hide_delay', 150)
        self._update_interval = kwargs.get('update_interval', 100)
        self._follow_mouse = kwargs.get('follow_mouse', True)
        self._tooltip_offset = kwargs.get('tooltip_offset', QPoint(15, 15))
        self._max_width = kwargs.get('max_width', 400)
        self._max_height = kwargs.get('max_height', 300)
        self._auto_resize = kwargs.get('auto_resize', True)
        
        # Performance settings
        self._cache_enabled = kwargs.get('cache_enabled', True)
        self._cache_size = kwargs.get('cache_size', 100)
        self._cache_cleanup_interval = kwargs.get('cache_cleanup_interval', 60.0)
        
        # Accessibility settings
        self._accessibility_enabled = kwargs.get('accessibility_enabled', True)
        self._screen_reader_support = kwargs.get('screen_reader_support', True)
        self._high_contrast_mode = kwargs.get('high_contrast_mode', False)
        self._large_font_mode = kwargs.get('large_font_mode', False)
        self._keyboard_navigation = kwargs.get('keyboard_navigation', True)
        
        # Advanced features
        self._real_time_updates = kwargs.get('real_time_updates', False)
        self._interpolation_mode = kwargs.get('interpolation_mode', 'nearest')
        self._subpixel_precision = kwargs.get('subpixel_precision', False)
        self._show_neighborhood = kwargs.get('show_neighborhood', False)
        self._neighborhood_size = kwargs.get('neighborhood_size', 3)
        
        # Configure timers with new intervals
        self._show_timer.setInterval(self._show_delay)
        self._hide_timer.setInterval(self._hide_delay)
        self._update_timer.setInterval(self._update_interval)
        
        # Start real-time updates if enabled
        if self._real_time_updates:
            self._update_timer.start()
        
        return super().initialize(**kwargs)
    
    def add_data_layer(self, layer_name: str, data: np.ndarray, 
                      layer_type: str = "image", priority: int = 0, 
                      visible: bool = True, **metadata) -> None:
        """Add a data layer for pixel information."""
        try:
            self._data_layers[layer_name] = {
                'data': data,
                'type': layer_type,
                'metadata': metadata,
                'timestamp': time.time()
            }
            
            self._layer_priorities[layer_name] = priority
            self._layer_visibility[layer_name] = visible
            
            if visible and layer_name not in self._active_layers:
                self._active_layers.append(layer_name)
                self._active_layers.sort(key=lambda x: self._layer_priorities.get(x, 0))
            
            # Clear cache when layers change
            if self._cache_enabled:
                self._pixel_info_cache.clear()
            
            self.dataLayerChanged.emit(layer_name)
            self.emit_state_changed({
                'data_layers_count': len(self._data_layers),
                'active_layers_count': len(self._active_layers)
            })
            
        except Exception as e:
            self.emit_error(f"Error adding data layer: {str(e)}")
    
    def remove_data_layer(self, layer_name: str) -> None:
        """Remove a data layer."""
        try:
            if layer_name in self._data_layers:
                del self._data_layers[layer_name]
                
                if layer_name in self._active_layers:
                    self._active_layers.remove(layer_name)
                
                if layer_name in self._layer_priorities:
                    del self._layer_priorities[layer_name]
                
                if layer_name in self._layer_visibility:
                    del self._layer_visibility[layer_name]
                
                # Clear cache
                if self._cache_enabled:
                    self._pixel_info_cache.clear()
                
                self.emit_state_changed({
                    'data_layers_count': len(self._data_layers),
                    'active_layers_count': len(self._active_layers)
                })
            
        except Exception as e:
            self.emit_error(f"Error removing data layer: {str(e)}")
    
    def set_layer_visibility(self, layer_name: str, visible: bool) -> None:
        """Set visibility of a data layer."""
        try:
            if layer_name in self._data_layers:
                self._layer_visibility[layer_name] = visible
                
                if visible and layer_name not in self._active_layers:
                    self._active_layers.append(layer_name)
                    self._active_layers.sort(key=lambda x: self._layer_priorities.get(x, 0))
                elif not visible and layer_name in self._active_layers:
                    self._active_layers.remove(layer_name)
                
                # Clear cache
                if self._cache_enabled:
                    self._pixel_info_cache.clear()
                
                self.emit_state_changed({'active_layers_count': len(self._active_layers)})
            
        except Exception as e:
            self.emit_error(f"Error setting layer visibility: {str(e)}")
    
    def set_tooltip_style(self, style_name: str) -> None:
        """Set the tooltip style."""
        try:
            if style_name in self._custom_styles or style_name in ['default', 'modern', 'minimal']:
                self._style_name = style_name
                self.tooltipStyleChanged.emit(style_name)
                self.emit_state_changed({'tooltip_style': style_name})
            else:
                self.emit_error(f"Unknown tooltip style: {style_name}")
            
        except Exception as e:
            self.emit_error(f"Error setting tooltip style: {str(e)}")
    
    def add_custom_style(self, style_name: str, style_config: Dict[str, str]) -> None:
        """Add a custom tooltip style."""
        try:
            self._custom_styles[style_name] = style_config
            self.emit_state_changed({'custom_styles_count': len(self._custom_styles)})
            
        except Exception as e:
            self.emit_error(f"Error adding custom style: {str(e)}")
    
    def set_accessibility_mode(self, enabled: bool) -> None:
        """Enable or disable accessibility features."""
        try:
            self._accessibility_enabled = enabled
            
            if enabled:
                self._large_font_mode = True
                self._high_contrast_mode = True
                self._font_size = max(12, self._font_size)
            
            self.emit_state_changed({'accessibility_enabled': enabled})
            
        except Exception as e:
            self.emit_error(f"Error setting accessibility mode: {str(e)}")
    
    def on_mouse_move(self, position: QPoint) -> None:
        """Handle mouse move event with enhanced tracking."""
        try:
            if not self._enabled:
                return
            
            # Update position
            self._current_position = position
            
            # Track hover time
            if self._hover_start_time is None:
                self._hover_start_time = time.time()
            
            # Stop hide timer if running
            if self._hide_timer.isActive():
                self._hide_timer.stop()
            
            # Handle tooltip display
            if not self._tooltip_visible:
                self._show_timer.start()
            elif self._real_time_updates:
                self._update_tooltip()
            
            # Track position for statistics
            self._track_position_statistics(position)
            
        except Exception as e:
            self.emit_error(f"Error handling mouse move: {str(e)}")
    
    def on_mouse_leave(self) -> None:
        """Handle mouse leave event with enhanced tracking."""
        try:
            # Update hover time statistics
            if self._hover_start_time is not None:
                hover_duration = time.time() - self._hover_start_time
                self._total_hover_time += hover_duration
                self._tooltip_stats['total_hover_time'] += hover_duration
                
                # Update average duration
                if self._tooltip_stats['tooltips_shown'] > 0:
                    self._tooltip_stats['avg_tooltip_duration'] = (
                        self._tooltip_stats['total_hover_time'] / self._tooltip_stats['tooltips_shown']
                    )
                
                self._hover_start_time = None
            
            # Stop show timer
            if self._show_timer.isActive():
                self._show_timer.stop()
            
            # Start hide timer
            if self._tooltip_visible:
                self._hide_timer.start()
            
        except Exception as e:
            self.emit_error(f"Error handling mouse leave: {str(e)}")
    
    def _show_tooltip(self) -> None:
        """Show the enhanced pixel info tooltip."""
        try:
            if not self._enabled or not self._current_position:
                return
            
            start_time = time.time()
            
            # Get enhanced pixel information
            pixel_info = self._get_enhanced_pixel_info(self._current_position)
            
            if pixel_info and pixel_info.get('valid_pixel', False):
                # Format tooltip text
                if self._use_html_format:
                    tooltip_text = self._format_html_tooltip(pixel_info)
                else:
                    tooltip_text = self._format_plain_tooltip(pixel_info)
                
                # Calculate tooltip position
                tooltip_pos = self._calculate_tooltip_position(self._current_position)
                
                # Show tooltip
                if self._canvas:
                    global_pos = self._canvas.mapToGlobal(tooltip_pos)
                    QToolTip.showText(global_pos, tooltip_text)
                
                # Update state
                self._tooltip_visible = True
                self._last_pixel_info = pixel_info
                self._tooltip_stats['tooltips_shown'] += 1
                
                # Add to history
                self._pixel_history.append({
                    'position': pixel_info['image_position'],
                    'info': pixel_info,
                    'timestamp': time.time()
                })
                
                # Update performance metrics
                query_time = time.time() - start_time
                self._update_performance_metrics(query_time)
                
                # Emit signals
                self.pixelInfoChanged.emit(pixel_info)
                self.tooltipShown.emit(self._current_position)
                
                if self._show_history:
                    self.pixelHistoryUpdated.emit({'history': list(self._pixel_history)})
            
        except Exception as e:
            self.emit_error(f"Error showing tooltip: {str(e)}")
            self._tooltip_stats['error_count'] += 1
    
    def _hide_tooltip(self) -> None:
        """Hide the enhanced pixel info tooltip."""
        try:
            if self._tooltip_visible:
                QToolTip.hideText()
                self._tooltip_visible = False
                self._tooltip_stats['tooltips_hidden'] += 1
                self.tooltipHidden.emit()
            
        except Exception as e:
            self.emit_error(f"Error hiding tooltip: {str(e)}")
    
    def _update_tooltip_continuous(self) -> None:
        """Update tooltip continuously for real-time updates."""
        try:
            if self._tooltip_visible and self._current_position and self._real_time_updates:
                self._update_tooltip()
            
        except Exception as e:
            self.emit_error(f"Error in continuous tooltip update: {str(e)}")
    
    def _get_enhanced_pixel_info(self, screen_pos: QPoint) -> Optional[Dict[str, Any]]:
        """Get enhanced pixel information at screen position."""
        try:
            # Convert screen position to image coordinates
            image_coords = self._screen_to_image_coords(screen_pos)
            
            # Generate cache key
            cache_key = self._generate_cache_key(screen_pos, image_coords)
            
            # Check cache
            if self._cache_enabled and cache_key in self._pixel_info_cache:
                self._tooltip_stats['cache_hits'] += 1
                return self._pixel_info_cache[cache_key]
            
            # Get pixel information
            pixel_info = self._compute_pixel_info(screen_pos, image_coords)
            
            # Cache result
            if self._cache_enabled:
                self._cache_pixel_info(cache_key, pixel_info)
                self._tooltip_stats['cache_misses'] += 1
            
            # Update statistics
            self._tooltip_stats['pixel_queries'] += 1
            
            return pixel_info
            
        except Exception as e:
            self.emit_error(f"Error getting enhanced pixel info: {str(e)}")
            return None
    
    def _compute_pixel_info(self, screen_pos: QPoint, image_coords: Tuple[float, float]) -> Dict[str, Any]:
        """Compute comprehensive pixel information."""
        try:
            image_x, image_y = image_coords
            
            pixel_info = {
                'screen_position': (screen_pos.x(), screen_pos.y()),
                'image_position': (image_x, image_y),
                'image_position_exact': image_coords,
                'valid_pixel': False,
                'timestamp': time.time()
            }
            
            # Check if coordinates are within any data layer bounds
            valid_layers = []
            for layer_name in self._active_layers:
                layer_data = self._data_layers[layer_name]
                data = layer_data['data']
                
                if self._is_within_bounds(image_x, image_y, data.shape):
                    valid_layers.append(layer_name)
            
            if valid_layers:
                pixel_info['valid_pixel'] = True
                pixel_info['valid_layers'] = valid_layers
                
                # Get information from each layer
                for layer_name in valid_layers:
                    layer_info = self._get_layer_pixel_info(layer_name, image_x, image_y)
                    if layer_info:
                        pixel_info[f'{layer_name}_info'] = layer_info
                
                # Get standard information
                if self._show_pixel_values:
                    pixel_info['pixel_values'] = self._get_enhanced_pixel_values(image_x, image_y)
                
                if self._show_class_info:
                    pixel_info['class_info'] = self._get_enhanced_class_info(image_x, image_y)
                
                if self._show_prediction_info:
                    pixel_info['prediction_info'] = self._get_enhanced_prediction_info(image_x, image_y)
                
                if self._show_confidence_info:
                    pixel_info['confidence_info'] = self._get_confidence_info(image_x, image_y)
                
                if self._show_distance_info:
                    pixel_info['distance_info'] = self._get_distance_info(image_x, image_y)
                
                if self._show_statistics:
                    pixel_info['statistics'] = self._get_pixel_statistics(image_x, image_y)
                
                if self._show_metadata:
                    pixel_info['metadata'] = self._get_pixel_metadata(image_x, image_y)
                
                if self._show_neighborhood:
                    pixel_info['neighborhood'] = self._get_neighborhood_info(image_x, image_y)
                
                # Get custom information
                pixel_info['custom_info'] = self._get_enhanced_custom_info(image_x, image_y)
                
                # Apply filters
                pixel_info = self._apply_info_filters(pixel_info)
                
                # Validate information
                if not self._validate_pixel_info(pixel_info):
                    pixel_info['valid_pixel'] = False
            
            return pixel_info
            
        except Exception as e:
            self.emit_error(f"Error computing pixel info: {str(e)}")
            return {'valid_pixel': False, 'error': str(e)}
    
    def _get_layer_pixel_info(self, layer_name: str, x: float, y: float) -> Dict[str, Any]:
        """Get pixel information from a specific data layer."""
        try:
            layer_data = self._data_layers[layer_name]
            data = layer_data['data']
            layer_type = layer_data['type']
            metadata = layer_data['metadata']
            
            # Get interpolated value if subpixel precision is enabled
            if self._subpixel_precision:
                value = self._get_interpolated_value(data, x, y)
            else:
                int_x, int_y = int(round(x)), int(round(y))
                if self._is_within_bounds(int_x, int_y, data.shape):
                    value = data[int_y, int_x]
                else:
                    return {}
            
            layer_info = {
                'value': value,
                'type': layer_type,
                'metadata': metadata,
                'shape': data.shape,
                'dtype': str(data.dtype)
            }
            
            # Add layer-specific processing
            if layer_type == 'image':
                layer_info.update(self._process_image_layer(value, data))
            elif layer_type == 'segmentation':
                layer_info.update(self._process_segmentation_layer(value, data))
            elif layer_type == 'probability':
                layer_info.update(self._process_probability_layer(value, data))
            
            return layer_info
            
        except Exception as e:
            self.emit_error(f"Error getting layer pixel info: {str(e)}")
            return {}
    
    def _get_interpolated_value(self, data: np.ndarray, x: float, y: float) -> Union[float, np.ndarray]:
        """Get interpolated value at non-integer coordinates."""
        try:
            from scipy.ndimage import map_coordinates
            
            if data.ndim == 2:
                coords = np.array([[y], [x]])
                if self._interpolation_mode == 'bilinear':
                    return map_coordinates(data, coords, order=1, mode='nearest')[0]
                elif self._interpolation_mode == 'bicubic':
                    return map_coordinates(data, coords, order=3, mode='nearest')[0]
                else:  # nearest
                    return data[int(round(y)), int(round(x))]
            else:
                # Multi-channel data
                result = np.zeros(data.shape[2])
                for i in range(data.shape[2]):
                    coords = np.array([[y], [x]])
                    if self._interpolation_mode == 'bilinear':
                        result[i] = map_coordinates(data[:, :, i], coords, order=1, mode='nearest')[0]
                    elif self._interpolation_mode == 'bicubic':
                        result[i] = map_coordinates(data[:, :, i], coords, order=3, mode='nearest')[0]
                    else:  # nearest
                        result[i] = data[int(round(y)), int(round(x)), i]
                return result
                
        except Exception as e:
            self.emit_error(f"Error getting interpolated value: {str(e)}")
            # Fallback to nearest neighbor
            return data[int(round(y)), int(round(x))]
    
    def _get_neighborhood_info(self, x: float, y: float) -> Dict[str, Any]:
        """Get neighborhood information around the pixel."""
        try:
            if self._image_data is None:
                return {}
            
            int_x, int_y = int(round(x)), int(round(y))
            half_size = self._neighborhood_size // 2
            
            # Extract neighborhood
            y_start = max(0, int_y - half_size)
            y_end = min(self._image_data.shape[0], int_y + half_size + 1)
            x_start = max(0, int_x - half_size)
            x_end = min(self._image_data.shape[1], int_x + half_size + 1)
            
            neighborhood = self._image_data[y_start:y_end, x_start:x_end]
            
            neighborhood_info = {
                'neighborhood': neighborhood,
                'size': neighborhood.shape,
                'center': (int_x - x_start, int_y - y_start),
                'statistics': {
                    'mean': float(np.mean(neighborhood)),
                    'std': float(np.std(neighborhood)),
                    'min': float(np.min(neighborhood)),
                    'max': float(np.max(neighborhood))
                }
            }
            
            return neighborhood_info
            
        except Exception as e:
            self.emit_error(f"Error getting neighborhood info: {str(e)}")
            return {}
    
    def _format_html_tooltip(self, pixel_info: Dict[str, Any]) -> str:
        """Format pixel information as HTML tooltip."""
        try:
            style = self._get_tooltip_style()
            
            html_parts = [
                f'<div style="{style["container"]}">',
                f'<div style="{style["header"]}">Pixel Information</div>'
            ]
            
            # Add coordinates
            if self._show_coordinates and 'image_position' in pixel_info:
                x, y = pixel_info['image_position']
                html_parts.append(
                    f'<div style="{style["section"]}"><b>Position:</b> ({x}, {y})</div>'
                )
            
            # Add pixel values
            if self._show_pixel_values and 'pixel_values' in pixel_info:
                html_parts.append(self._format_pixel_values_html(pixel_info['pixel_values'], style))
            
            # Add class information
            if self._show_class_info and 'class_info' in pixel_info:
                html_parts.append(self._format_class_info_html(pixel_info['class_info'], style))
            
            # Add prediction information
            if self._show_prediction_info and 'prediction_info' in pixel_info:
                html_parts.append(self._format_prediction_info_html(pixel_info['prediction_info'], style))
            
            # Add confidence information
            if self._show_confidence_info and 'confidence_info' in pixel_info:
                html_parts.append(self._format_confidence_info_html(pixel_info['confidence_info'], style))
            
            # Add layer information
            for layer_name in pixel_info.get('valid_layers', []):
                layer_info = pixel_info.get(f'{layer_name}_info', {})
                if layer_info:
                    html_parts.append(self._format_layer_info_html(layer_name, layer_info, style))
            
            # Add custom information
            if 'custom_info' in pixel_info and pixel_info['custom_info']:
                html_parts.append(self._format_custom_info_html(pixel_info['custom_info'], style))
            
            html_parts.append('</div>')
            
            return ''.join(html_parts)
            
        except Exception as e:
            self.emit_error(f"Error formatting HTML tooltip: {str(e)}")
            return f"<div>Error formatting tooltip: {str(e)}</div>"
    
    def _get_tooltip_style(self) -> Dict[str, str]:
        """Get tooltip style configuration."""
        try:
            if self._style_name in self._custom_styles:
                return self._custom_styles[self._style_name]
            
            # Default styles
            base_styles = {
                'container': f'font-family: {self._font_family}; font-size: {self._font_size}px; padding: 8px; max-width: {self._max_width}px;',
                'header': 'font-weight: bold; margin-bottom: 4px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 2px;',
                'section': 'margin: 2px 0; padding: 1px 0;',
                'value': 'color: #666; font-family: monospace;',
                'label': 'font-weight: bold; color: #333;',
                'separator': 'border-top: 1px solid #eee; margin: 4px 0;'
            }
            
            # Apply color scheme
            if self._color_scheme == 'dark' or (self._color_scheme == 'auto' and self._is_dark_theme()):
                base_styles.update({
                    'header': base_styles['header'].replace('#333', '#ccc').replace('#ccc', '#555'),
                    'value': base_styles['value'].replace('#666', '#aaa'),
                    'label': base_styles['label'].replace('#333', '#ccc'),
                    'separator': base_styles['separator'].replace('#eee', '#444')
                })
            
            # Apply accessibility modifications
            if self._accessibility_enabled:
                if self._high_contrast_mode:
                    base_styles['container'] += ' border: 2px solid #000; background: #fff;'
                if self._large_font_mode:
                    base_styles['container'] = base_styles['container'].replace(f'{self._font_size}px', f'{self._font_size + 2}px')
            
            return base_styles
            
        except Exception as e:
            self.emit_error(f"Error getting tooltip style: {str(e)}")
            return {'container': 'font-family: Arial; font-size: 10px;'}
    
    def _initialize_default_styles(self) -> None:
        """Initialize default tooltip styles."""
        try:
            self._custom_styles = {
                'modern': {
                    'container': 'font-family: Segoe UI, Arial; font-size: 11px; padding: 10px; border-radius: 6px; background: rgba(0,0,0,0.8); color: white;',
                    'header': 'font-weight: bold; margin-bottom: 6px; color: #ffd700; border-bottom: 1px solid #555; padding-bottom: 3px;',
                    'section': 'margin: 3px 0; padding: 2px 0;',
                    'value': 'color: #ccc; font-family: Consolas, monospace;',
                    'label': 'font-weight: bold; color: #ffd700;',
                    'separator': 'border-top: 1px solid #555; margin: 6px 0;'
                },
                'minimal': {
                    'container': 'font-family: Arial; font-size: 10px; padding: 6px; background: #f9f9f9; border: 1px solid #ddd;',
                    'header': 'font-weight: bold; margin-bottom: 4px; color: #333;',
                    'section': 'margin: 1px 0;',
                    'value': 'color: #666; font-family: monospace;',
                    'label': 'font-weight: normal; color: #333;',
                    'separator': 'margin: 3px 0;'
                }
            }
            
        except Exception as e:
            self.emit_error(f"Error initializing default styles: {str(e)}")
    
    def _initialize_default_layers(self) -> None:
        """Initialize default data layers."""
        try:
            # This will be populated when data is set
            pass
            
        except Exception as e:
            self.emit_error(f"Error initializing default layers: {str(e)}")
    
    def _is_within_bounds(self, x: float, y: float, shape: Tuple[int, ...]) -> bool:
        """Check if coordinates are within data bounds."""
        try:
            return (0 <= x < shape[1] and 0 <= y < shape[0])
        except:
            return False
    
    def _generate_cache_key(self, screen_pos: QPoint, image_coords: Tuple[float, float]) -> str:
        """Generate cache key for pixel information."""
        try:
            key_parts = [
                f"pos_{screen_pos.x()}_{screen_pos.y()}",
                f"img_{image_coords[0]:.3f}_{image_coords[1]:.3f}",
                f"scale_{self._scale_factor:.3f}",
                f"layers_{'-'.join(self._active_layers)}",
                f"time_{int(time.time() / 60)}"  # Cache valid for 1 minute
            ]
            return '_'.join(key_parts)
        except Exception as e:
            self.emit_error(f"Error generating cache key: {str(e)}")
            return "default_key"
    
    def _cache_pixel_info(self, cache_key: str, pixel_info: Dict[str, Any]) -> None:
        """Cache pixel information."""
        try:
            if len(self._pixel_info_cache) >= self._cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._pixel_info_cache))
                del self._pixel_info_cache[oldest_key]
            
            self._pixel_info_cache[cache_key] = pixel_info.copy()
            
        except Exception as e:
            self.emit_error(f"Error caching pixel info: {str(e)}")
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache entries."""
        try:
            current_time = time.time()
            
            # Remove entries older than cache timeout
            keys_to_remove = []
            for key in self._pixel_info_cache:
                # Extract timestamp from key
                try:
                    time_part = key.split('_time_')[1]
                    entry_time = int(time_part) * 60
                    if current_time - entry_time > self._cache_cleanup_interval:
                        keys_to_remove.append(key)
                except:
                    # If we can't parse the timestamp, remove the entry
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._pixel_info_cache[key]
            
            self._last_cache_cleanup = current_time
            
        except Exception as e:
            self.emit_error(f"Error cleaning up cache: {str(e)}")
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get enhanced tooltip statistics."""
        try:
            stats = super().get_statistics()
            stats.update({
                'enabled': self._enabled,
                'tooltip_visible': self._tooltip_visible,
                'data_layers': {
                    'total': len(self._data_layers),
                    'active': len(self._active_layers),
                    'visible': sum(1 for v in self._layer_visibility.values() if v)
                },
                'display_settings': {
                    'show_coordinates': self._show_coordinates,
                    'show_pixel_values': self._show_pixel_values,
                    'show_class_info': self._show_class_info,
                    'show_prediction_info': self._show_prediction_info,
                    'show_confidence_info': self._show_confidence_info,
                    'show_statistics': self._show_statistics,
                    'show_metadata': self._show_metadata,
                    'show_history': self._show_history,
                    'use_html_format': self._use_html_format,
                    'style_name': self._style_name,
                    'color_scheme': self._color_scheme,
                    'compact_mode': self._compact_mode
                },
                'performance': {
                    'cache_enabled': self._cache_enabled,
                    'cache_size': len(self._pixel_info_cache),
                    'cache_capacity': self._cache_size,
                    'cache_hit_rate': self._tooltip_stats['cache_hits'] / max(1, self._tooltip_stats['cache_hits'] + self._tooltip_stats['cache_misses']),
                    'real_time_updates': self._real_time_updates,
                    'interpolation_mode': self._interpolation_mode,
                    'subpixel_precision': self._subpixel_precision
                },
                'accessibility': {
                    'accessibility_enabled': self._accessibility_enabled,
                    'high_contrast_mode': self._high_contrast_mode,
                    'large_font_mode': self._large_font_mode,
                    'screen_reader_support': self._screen_reader_support
                },
                'usage_statistics': self._tooltip_stats,
                'history': {
                    'history_size': len(self._pixel_history),
                    'history_enabled': self._show_history
                }
            })
            return stats
            
        except Exception as e:
            self.emit_error(f"Error getting enhanced statistics: {str(e)}")
            return {}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop timers
            self._show_timer.stop()
            self._hide_timer.stop()
            self._update_timer.stop()
            self._cache_cleanup_timer.stop()
            
            # Clear caches
            self._pixel_info_cache.clear()
            self._pixel_history.clear()
            
            # Clear data layers
            self._data_layers.clear()
            
        except Exception as e:
            self.emit_error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor."""
        try:
            self.cleanup()
        except:
            pass