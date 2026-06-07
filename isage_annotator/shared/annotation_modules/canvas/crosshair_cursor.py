"""
Enhanced Crosshair Cursor - Improved crosshair with better performance and features

This enhanced version addresses potential issues and adds improvements:
- Better performance with optimized drawing
- Smart color adaptation based on background
- Enhanced visual feedback
- Better integration with annotation tools
"""

import numpy as np
from typing import Optional, Tuple, List
from ..base_protocols import BaseComponent, QPainter, QColor, QPen, QPoint, QRect
from ..base_protocols import pyqtSignal, QTimer


class CrosshairCursor(BaseComponent):
    """Enhanced crosshair cursor with improved performance and features."""
    
    # Crosshair cursor signals
    crosshairToggled = pyqtSignal(bool)  # enabled
    crosshairColorChanged = pyqtSignal(object)  # QColor
    crosshairStyleChanged = pyqtSignal(str)  # style
    crosshairMoved = pyqtSignal(object)  # QPoint
    
    def __init__(self, name: str = "enhanced_crosshair_cursor", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Enhanced crosshair configuration
        self._enabled: bool = True
        self._mouse_position: Optional[QPoint] = None
        self._last_mouse_position: Optional[QPoint] = None
        self._crosshair_color: QColor = QColor(255, 255, 255, 180)
        self._crosshair_style: str = "full"  # full, center, dot, cross, adaptive
        
        # Enhanced appearance options
        self._line_width: int = 1
        self._line_style: int = 2  # Qt.DashLine
        self._center_gap: int = 10
        self._center_size: int = 20
        self._dot_size: int = 4
        self._cross_arm_length: int = 8
        
        # Smart color adaptation
        self._adaptive_color: bool = True
        self._background_sampling: bool = True
        self._background_sample_radius: int = 5
        self._color_contrast_threshold: float = 0.3
        self._auto_invert_color: bool = True
        
        # Dynamic appearance
        self._fade_with_zoom: bool = True
        self._scale_with_zoom: bool = False
        self._min_opacity: float = 0.3
        self._max_opacity: float = 0.9
        self._zoom_scale_factor: float = 1.0
        
        # Canvas integration
        self._canvas = None
        self._canvas_rect: Optional[QRect] = None
        self._scale_factor: float = 1.0
        self._image_data: Optional[np.ndarray] = None
        
        # Performance optimization
        self._draw_full_lines: bool = True
        self._clip_to_canvas: bool = True
        self._smooth_lines: bool = True
        self._use_fast_drawing: bool = True
        self._redraw_on_move: bool = True
        
        # Enhanced animation
        self._animate_enabled: bool = False
        self._pulse_enabled: bool = False
        self._pulse_phase: float = 0.0
        self._pulse_speed: float = 0.1
        self._breathe_enabled: bool = False
        self._breathe_amplitude: float = 0.2
        self._breathe_frequency: float = 0.05
        
        # Interaction feedback
        self._show_coordinates: bool = False
        self._coordinate_format: str = "({}, {})"
        self._coordinate_offset: QPoint = QPoint(10, -10)
        self._highlight_on_tool_active: bool = True
        self._tool_active_color: QColor = QColor(255, 255, 0, 200)
        
        # Precision aids
        self._show_rulers: bool = False
        self._ruler_length: int = 50
        self._ruler_marks: int = 5
        self._magnetic_snap: bool = False
        self._snap_targets: List[QPoint] = []
        self._snap_radius: int = 10
        
        # Animation timer
        self._animation_timer: Optional[QTimer] = None
        self._animation_frame: int = 0
        self._animation_fps: int = 30
        
        # Tool integration
        self._current_tool: Optional[str] = None
        self._tool_specific_styles: dict = {
            'point_tool': {'style': 'cross', 'color': QColor(255, 255, 255, 200)},
            'polygon_tool': {'style': 'full', 'color': QColor(0, 255, 255, 180)},
            'brush_tool': {'style': 'center', 'color': QColor(255, 0, 255, 160)}
        }
        
        # Performance metrics
        self._draw_calls: int = 0
        self._last_draw_time: float = 0.0
        self._average_draw_time: float = 0.0
    
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced crosshair cursor."""
        self._enabled = kwargs.get('enabled', True)
        self._crosshair_color = kwargs.get('crosshair_color', QColor(255, 255, 255, 180))
        self._crosshair_style = kwargs.get('crosshair_style', 'full')
        self._line_width = kwargs.get('line_width', 1)
        self._line_style = kwargs.get('line_style', 2)
        self._center_gap = kwargs.get('center_gap', 10)
        self._center_size = kwargs.get('center_size', 20)
        self._dot_size = kwargs.get('dot_size', 4)
        self._cross_arm_length = kwargs.get('cross_arm_length', 8)
        self._adaptive_color = kwargs.get('adaptive_color', True)
        self._background_sampling = kwargs.get('background_sampling', True)
        self._background_sample_radius = kwargs.get('background_sample_radius', 5)
        self._color_contrast_threshold = kwargs.get('color_contrast_threshold', 0.3)
        self._auto_invert_color = kwargs.get('auto_invert_color', True)
        self._fade_with_zoom = kwargs.get('fade_with_zoom', True)
        self._scale_with_zoom = kwargs.get('scale_with_zoom', False)
        self._min_opacity = kwargs.get('min_opacity', 0.3)
        self._max_opacity = kwargs.get('max_opacity', 0.9)
        self._draw_full_lines = kwargs.get('draw_full_lines', True)
        self._clip_to_canvas = kwargs.get('clip_to_canvas', True)
        self._smooth_lines = kwargs.get('smooth_lines', True)
        self._use_fast_drawing = kwargs.get('use_fast_drawing', True)
        self._redraw_on_move = kwargs.get('redraw_on_move', True)
        self._animate_enabled = kwargs.get('animate_enabled', False)
        self._pulse_enabled = kwargs.get('pulse_enabled', False)
        self._pulse_speed = kwargs.get('pulse_speed', 0.1)
        self._breathe_enabled = kwargs.get('breathe_enabled', False)
        self._breathe_amplitude = kwargs.get('breathe_amplitude', 0.2)
        self._breathe_frequency = kwargs.get('breathe_frequency', 0.05)
        self._show_coordinates = kwargs.get('show_coordinates', False)
        self._coordinate_format = kwargs.get('coordinate_format', "({}, {})")
        self._coordinate_offset = kwargs.get('coordinate_offset', QPoint(10, -10))
        self._highlight_on_tool_active = kwargs.get('highlight_on_tool_active', True)
        self._tool_active_color = kwargs.get('tool_active_color', QColor(255, 255, 0, 200))
        self._show_rulers = kwargs.get('show_rulers', False)
        self._ruler_length = kwargs.get('ruler_length', 50)
        self._ruler_marks = kwargs.get('ruler_marks', 5)
        self._magnetic_snap = kwargs.get('magnetic_snap', False)
        self._snap_radius = kwargs.get('snap_radius', 10)
        self._animation_fps = kwargs.get('animation_fps', 30)
        
        # Set tool-specific styles
        if 'tool_specific_styles' in kwargs:
            self._tool_specific_styles.update(kwargs['tool_specific_styles'])
        
        # Initialize animation timer
        if self._animate_enabled:
            self._setup_animation_timer()
        
        return super().initialize(**kwargs)
    
    def set_canvas(self, canvas) -> None:
        """Set the canvas widget."""
        self._canvas = canvas
        if canvas:
            self._canvas_rect = canvas.rect()
    
    def set_image_data(self, image_data: np.ndarray) -> None:
        """Set image data for background color sampling."""
        self._image_data = image_data
        self.emit_state_changed({'image_data_set': True})
    
    def set_current_tool(self, tool_name: str) -> None:
        """Set current annotation tool for adaptive styling."""
        if self._current_tool != tool_name:
            self._current_tool = tool_name
            
            # Apply tool-specific styling
            if tool_name in self._tool_specific_styles:
                style_config = self._tool_specific_styles[tool_name]
                if 'style' in style_config:
                    self._crosshair_style = style_config['style']
                if 'color' in style_config:
                    self._crosshair_color = style_config['color']
            
            self.emit_state_changed({'current_tool': tool_name})
            
            # Request canvas repaint
            if self._canvas and self._enabled:
                self._canvas.update()
    
    def set_mouse_position(self, position: QPoint) -> None:
        """Update mouse position with enhanced features."""
        if self._mouse_position != position:
            self._last_mouse_position = self._mouse_position
            self._mouse_position = position
            
            # Apply magnetic snapping if enabled
            if self._magnetic_snap:
                snapped_pos = self._apply_magnetic_snap(position)
                if snapped_pos != position:
                    self._mouse_position = snapped_pos
            
            # Emit movement signal
            self.crosshairMoved.emit(self._mouse_position)
            
            # Request canvas repaint if enabled
            if self._canvas and self._enabled and self._redraw_on_move:
                self._canvas.update()
    
    def add_snap_target(self, target: QPoint) -> None:
        """Add a magnetic snap target."""
        self._snap_targets.append(target)
        self.emit_state_changed({'snap_targets_count': len(self._snap_targets)})
    
    def remove_snap_target(self, target: QPoint) -> None:
        """Remove a magnetic snap target."""
        if target in self._snap_targets:
            self._snap_targets.remove(target)
            self.emit_state_changed({'snap_targets_count': len(self._snap_targets)})
    
    def clear_snap_targets(self) -> None:
        """Clear all magnetic snap targets."""
        self._snap_targets.clear()
        self.emit_state_changed({'snap_targets_count': 0})
    
    def draw_crosshair(self, painter: QPainter) -> None:
        """Draw enhanced crosshair cursor."""
        try:
            if not self._enabled or not self._mouse_position or not self._canvas_rect:
                return
            
            import time
            start_time = time.time()
            
            # Calculate crosshair color with smart adaptation
            crosshair_color = self._calculate_adaptive_color()
            if crosshair_color.alpha() == 0:
                return
            
            # Set up painter
            if self._smooth_lines:
                painter.setRenderHint(QPainter.Antialiasing, True)
            
            # Calculate effective sizes
            effective_line_width = self._line_width
            effective_center_gap = self._center_gap
            effective_center_size = self._center_size
            
            if self._scale_with_zoom:
                scale = self._zoom_scale_factor
                effective_line_width = max(1, int(self._line_width * scale))
                effective_center_gap = int(self._center_gap * scale)
                effective_center_size = int(self._center_size * scale)
            
            # Set pen
            pen = QPen(crosshair_color)
            pen.setWidth(effective_line_width)
            pen.setStyle(self._line_style)
            painter.setPen(pen)
            
            # Draw crosshair based on style
            if self._crosshair_style == 'full':
                self._draw_full_crosshair(painter)
            elif self._crosshair_style == 'center':
                self._draw_center_crosshair(painter, effective_center_gap, effective_center_size)
            elif self._crosshair_style == 'dot':
                self._draw_dot_crosshair(painter)
            elif self._crosshair_style == 'cross':
                self._draw_cross_crosshair(painter)
            elif self._crosshair_style == 'adaptive':
                self._draw_adaptive_crosshair(painter)
            
            # Draw additional features
            if self._show_rulers:
                self._draw_rulers(painter)
            
            if self._show_coordinates:
                self._draw_coordinates(painter)
            
            # Draw snap targets
            if self._magnetic_snap and self._snap_targets:
                self._draw_snap_targets(painter)
            
            # Update performance metrics
            self._draw_calls += 1
            self._last_draw_time = time.time() - start_time
            self._average_draw_time = (self._average_draw_time * 0.9 + self._last_draw_time * 0.1)
            
        except Exception as e:
            self.emit_error(f"Error drawing enhanced crosshair: {str(e)}")
    
    def _calculate_adaptive_color(self) -> QColor:
        """Calculate adaptive crosshair color based on background."""
        try:
            base_color = QColor(self._crosshair_color)
            
            # Apply tool-specific color if active
            if (self._highlight_on_tool_active and self._current_tool and 
                self._current_tool in self._tool_specific_styles):
                style_config = self._tool_specific_styles[self._current_tool]
                if 'color' in style_config:
                    base_color = style_config['color']
            
            # Calculate opacity based on zoom
            opacity = self._calculate_zoom_opacity()
            
            # Apply animation effects
            if self._pulse_enabled:
                pulse_factor = 0.5 + 0.5 * abs(self._pulse_phase)
                opacity *= pulse_factor
            
            if self._breathe_enabled:
                breathe_factor = 1.0 + self._breathe_amplitude * np.sin(self._animation_frame * self._breathe_frequency)
                opacity *= breathe_factor
            
            # Sample background color for contrast
            if self._adaptive_color and self._background_sampling:
                background_color = self._sample_background_color()
                if background_color:
                    # Calculate contrast and adjust color if needed
                    contrast = self._calculate_contrast_ratio(base_color, background_color)
                    if contrast < self._color_contrast_threshold and self._auto_invert_color:
                        # Invert color for better contrast
                        base_color = QColor(255 - base_color.red(), 255 - base_color.green(), 
                                          255 - base_color.blue(), base_color.alpha())
            
            # Set final alpha
            base_color.setAlpha(int(opacity * 255))
            
            return base_color
            
        except Exception as e:
            self.emit_error(f"Error calculating adaptive color: {str(e)}")
            return QColor(255, 255, 255, 180)
    
    def _calculate_zoom_opacity(self) -> float:
        """Calculate opacity based on zoom level."""
        try:
            if not self._fade_with_zoom:
                return self._max_opacity
            
            # Calculate opacity based on scale factor
            if self._scale_factor < 0.5:
                return self._min_opacity
            elif self._scale_factor > 2.0:
                return self._max_opacity
            else:
                # Linear interpolation
                return self._min_opacity + (self._max_opacity - self._min_opacity) * (self._scale_factor - 0.5) / 1.5
                
        except Exception as e:
            self.emit_error(f"Error calculating zoom opacity: {str(e)}")
            return self._max_opacity
    
    def _sample_background_color(self) -> Optional[QColor]:
        """Sample background color around cursor position."""
        try:
            if not self._image_data or not self._mouse_position:
                return None
            
            # Convert screen position to image coordinates
            image_x = int((self._mouse_position.x()) / self._scale_factor)
            image_y = int((self._mouse_position.y()) / self._scale_factor)
            
            # Check bounds
            if (image_x < 0 or image_y < 0 or 
                image_x >= self._image_data.shape[1] or 
                image_y >= self._image_data.shape[0]):
                return None
            
            # Sample pixels in a small area around cursor
            radius = self._background_sample_radius
            y_start = max(0, image_y - radius)
            y_end = min(self._image_data.shape[0], image_y + radius + 1)
            x_start = max(0, image_x - radius)
            x_end = min(self._image_data.shape[1], image_x + radius + 1)
            
            # Sample area
            sample_area = self._image_data[y_start:y_end, x_start:x_end]
            
            # Calculate average color
            if sample_area.ndim == 3:
                # Color image
                avg_color = np.mean(sample_area, axis=(0, 1))
                if len(avg_color) >= 3:
                    return QColor(int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))
            else:
                # Grayscale image
                avg_intensity = np.mean(sample_area)
                return QColor(int(avg_intensity), int(avg_intensity), int(avg_intensity))
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error sampling background color: {str(e)}")
            return None
    
    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """Calculate contrast ratio between two colors."""
        try:
            # Calculate relative luminance
            def relative_luminance(color):
                def srgb_to_linear(c):
                    c = c / 255.0
                    if c <= 0.03928:
                        return c / 12.92
                    else:
                        return ((c + 0.055) / 1.055) ** 2.4
                
                r = srgb_to_linear(color.red())
                g = srgb_to_linear(color.green())
                b = srgb_to_linear(color.blue())
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            lum1 = relative_luminance(color1)
            lum2 = relative_luminance(color2)
            
            # Calculate contrast ratio
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            
            return (lighter + 0.05) / (darker + 0.05)
            
        except Exception as e:
            self.emit_error(f"Error calculating contrast ratio: {str(e)}")
            return 1.0
    
    def _apply_magnetic_snap(self, position: QPoint) -> QPoint:
        """Apply magnetic snapping to nearest target."""
        try:
            if not self._snap_targets:
                return position
            
            min_distance = float('inf')
            snap_target = None
            
            for target in self._snap_targets:
                distance = ((position.x() - target.x()) ** 2 + (position.y() - target.y()) ** 2) ** 0.5
                if distance < min_distance and distance <= self._snap_radius:
                    min_distance = distance
                    snap_target = target
            
            return snap_target if snap_target else position
            
        except Exception as e:
            self.emit_error(f"Error applying magnetic snap: {str(e)}")
            return position
    
    def _draw_cross_crosshair(self, painter: QPainter) -> None:
        """Draw cross-style crosshair."""
        try:
            if not self._mouse_position:
                return
            
            x = self._mouse_position.x()
            y = self._mouse_position.y()
            
            arm_length = self._cross_arm_length
            if self._scale_with_zoom:
                arm_length = int(arm_length * self._zoom_scale_factor)
            
            # Draw cross arms
            painter.drawLine(x - arm_length, y, x + arm_length, y)  # Horizontal
            painter.drawLine(x, y - arm_length, x, y + arm_length)  # Vertical
            
        except Exception as e:
            self.emit_error(f"Error drawing cross crosshair: {str(e)}")
    
    def _draw_adaptive_crosshair(self, painter: QPainter) -> None:
        """Draw adaptive crosshair based on zoom level."""
        try:
            if self._scale_factor < 0.5:
                self._draw_dot_crosshair(painter)
            elif self._scale_factor > 2.0:
                self._draw_full_crosshair(painter)
            else:
                self._draw_center_crosshair(painter, self._center_gap, self._center_size)
            
        except Exception as e:
            self.emit_error(f"Error drawing adaptive crosshair: {str(e)}")
    
    def _draw_rulers(self, painter: QPainter) -> None:
        """Draw measurement rulers."""
        try:
            if not self._mouse_position:
                return
            
            x = self._mouse_position.x()
            y = self._mouse_position.y()
            
            ruler_length = self._ruler_length
            if self._scale_with_zoom:
                ruler_length = int(ruler_length * self._zoom_scale_factor)
            
            # Draw ruler lines
            painter.drawLine(x - ruler_length, y, x + ruler_length, y)  # Horizontal ruler
            painter.drawLine(x, y - ruler_length, x, y + ruler_length)  # Vertical ruler
            
            # Draw tick marks
            mark_spacing = ruler_length // self._ruler_marks
            for i in range(1, self._ruler_marks):
                mark_x = x + i * mark_spacing
                mark_y = y + i * mark_spacing
                
                # Horizontal ruler marks
                painter.drawLine(mark_x, y - 3, mark_x, y + 3)
                painter.drawLine(x - i * mark_spacing, y - 3, x - i * mark_spacing, y + 3)
                
                # Vertical ruler marks
                painter.drawLine(x - 3, mark_y, x + 3, mark_y)
                painter.drawLine(x - 3, y - i * mark_spacing, x + 3, y - i * mark_spacing)
            
        except Exception as e:
            self.emit_error(f"Error drawing rulers: {str(e)}")
    
    def _draw_coordinates(self, painter: QPainter) -> None:
        """Draw coordinate display."""
        try:
            if not self._mouse_position:
                return
            
            # Convert to image coordinates
            image_x = int((self._mouse_position.x()) / self._scale_factor)
            image_y = int((self._mouse_position.y()) / self._scale_factor)
            
            # Format coordinates
            coord_text = self._coordinate_format.format(image_x, image_y)
            
            # Draw coordinate text
            text_pos = self._mouse_position + self._coordinate_offset
            painter.drawText(text_pos, coord_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing coordinates: {str(e)}")
    
    def _draw_snap_targets(self, painter: QPainter) -> None:
        """Draw magnetic snap targets."""
        try:
            # Use a different color for snap targets
            snap_color = QColor(255, 255, 0, 100)  # Yellow with transparency
            pen = QPen(snap_color)
            pen.setWidth(2)
            painter.setPen(pen)
            
            for target in self._snap_targets:
                # Draw small circle at snap target
                painter.drawEllipse(target, 3, 3)
                
                # Draw snap radius if cursor is nearby
                if self._mouse_position:
                    distance = ((self._mouse_position.x() - target.x()) ** 2 + 
                              (self._mouse_position.y() - target.y()) ** 2) ** 0.5
                    if distance <= self._snap_radius * 1.5:
                        # Draw snap radius circle
                        snap_color.setAlpha(50)
                        pen.setColor(snap_color)
                        painter.setPen(pen)
                        painter.drawEllipse(target, self._snap_radius, self._snap_radius)
            
        except Exception as e:
            self.emit_error(f"Error drawing snap targets: {str(e)}")
    
    def _setup_animation_timer(self) -> None:
        """Setup animation timer."""
        try:
            if self._animation_timer:
                self._animation_timer.stop()
            
            self._animation_timer = QTimer()
            self._animation_timer.timeout.connect(self._update_animation)
            self._animation_timer.start(1000 // self._animation_fps)
            
        except Exception as e:
            self.emit_error(f"Error setting up animation timer: {str(e)}")
    
    def _update_animation(self) -> None:
        """Update animation state."""
        try:
            self._animation_frame += 1
            
            # Update pulse phase
            if self._pulse_enabled:
                self._pulse_phase += self._pulse_speed
                if self._pulse_phase > 1.0:
                    self._pulse_phase = -1.0
                elif self._pulse_phase < -1.0:
                    self._pulse_phase = 1.0
            
            # Request repaint for animation
            if self._canvas and self._enabled:
                self._canvas.update()
            
        except Exception as e:
            self.emit_error(f"Error updating animation: {str(e)}")
    
    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return {
            'draw_calls': self._draw_calls,
            'last_draw_time_ms': self._last_draw_time * 1000,
            'average_draw_time_ms': self._average_draw_time * 1000,
            'use_fast_drawing': self._use_fast_drawing,
            'redraw_on_move': self._redraw_on_move,
            'animation_fps': self._animation_fps
        }
    
    def get_statistics(self) -> dict:
        """Get enhanced crosshair cursor statistics."""
        stats = super().get_statistics()
        stats.update({
            'crosshair_style': self._crosshair_style,
            'adaptive_color': self._adaptive_color,
            'background_sampling': self._background_sampling,
            'fade_with_zoom': self._fade_with_zoom,
            'scale_with_zoom': self._scale_with_zoom,
            'animate_enabled': self._animate_enabled,
            'pulse_enabled': self._pulse_enabled,
            'breathe_enabled': self._breathe_enabled,
            'show_coordinates': self._show_coordinates,
            'show_rulers': self._show_rulers,
            'magnetic_snap': self._magnetic_snap,
            'snap_targets_count': len(self._snap_targets),
            'current_tool': self._current_tool,
            'performance_metrics': self.get_performance_metrics()
        })
        return stats