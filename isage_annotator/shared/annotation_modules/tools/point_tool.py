"""
Enhanced Point Tool - Advanced point annotation tool with size adjustment and visual enhancements

This enhanced version of the point tool includes dynamic size adjustment, advanced visualization,
and additional features to match the legacy ABILIUS functionality.
"""

from typing import List, Optional, Dict, Any, Tuple
import time
from ..base_protocols import BaseComponent, AnnotationPoint, QPointF, QColor, QPainter, QRect
from ..base_protocols import pyqtSignal
from .base_tool import BaseTool


class PointTool(BaseTool):
    """Enhanced point annotation tool with size adjustment and advanced features."""
    
    # Enhanced point-specific signals
    pointAdded = pyqtSignal(object)  # AnnotationPoint
    pointRemoved = pyqtSignal(object)  # AnnotationPoint
    pointSelected = pyqtSignal(object)  # AnnotationPoint
    pointModified = pyqtSignal(object)  # AnnotationPoint
    pointSizeChanged = pyqtSignal(int)  # point_size
    pointStyleChanged = pyqtSignal(str)  # point_style
    confidenceDisplayToggled = pyqtSignal(bool)  # show_confidence
    
    def __init__(self, name: str = "enhanced_point_tool", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Point size configuration
        self._point_size: int = 8
        self._min_point_size: int = 4
        self._max_point_size: int = 32
        self._point_size_step: int = 2
        self._adaptive_size: bool = True
        self._size_scale_factor: float = 1.0
        
        # Point style configuration
        self._point_style: str = "circle"  # circle, square, cross, diamond
        self._point_outline_width: int = 2
        self._point_outline_color: QColor = QColor(0, 0, 0, 128)
        self._point_fill_alpha: int = 200
        
        # Legacy ABILIUS color scheme (exact match)
        self._point_colors: List[QColor] = [
            QColor(255, 0, 0),    # Red - Class 0
            QColor(0, 255, 0),    # Green - Class 1
            QColor(0, 0, 255),    # Blue - Class 2
            QColor(255, 255, 0),  # Yellow - Class 3
            QColor(255, 0, 255),  # Magenta - Class 4
            QColor(0, 255, 255),  # Cyan - Class 5
            QColor(255, 255, 255) # White - Class 6
        ]
        
        # Point visualization settings
        self._click_tolerance: float = 10.0
        self._show_point_labels: bool = True
        self._show_confidence: bool = False
        self._show_point_ids: bool = False
        self._show_timestamps: bool = False
        
        # Point appearance states
        self._point_opacity: float = 0.8
        self._selected_point_scale: float = 1.5
        self._hover_point_scale: float = 1.2
        self._dragging_point_scale: float = 1.3
        
        # Interaction state
        self._selected_point: Optional[AnnotationPoint] = None
        self._hover_point: Optional[AnnotationPoint] = None
        self._dragging_point: Optional[AnnotationPoint] = None
        self._drag_start_pos: QPointF = QPointF(0, 0)
        
        # Point management
        self._point_counter: int = 0
        self._point_history: List[AnnotationPoint] = []
        self._max_history_size: int = 100
        
        # Animation and effects
        self._animate_additions: bool = True
        self._animate_removals: bool = True
        self._pulse_selected: bool = False
        self._pulse_phase: float = 0.0
        self._pulse_speed: float = 0.1
        
        # Performance optimization
        self._use_point_cache: bool = True
        self._point_cache: Dict[int, Any] = {}
        self._dirty_cache: bool = True
        
        # Advanced features
        self._snap_to_grid: bool = False
        self._grid_size: int = 10
        self._magnetic_snap: bool = False
        self._magnetic_distance: float = 20.0
        self._auto_class_assignment: bool = False
        
        # Keyboard shortcuts
        self._keyboard_shortcuts: Dict[str, str] = {
            'increase_size': '+',
            'decrease_size': '-',
            'reset_size': '0',
            'next_style': 'S',
            'toggle_confidence': 'C',
            'toggle_labels': 'L'
        }
        
        # Visual feedback
        self._highlight_recent_points: bool = True
        self._recent_point_highlight_duration: float = 2.0
        self._recent_points: List[Tuple[AnnotationPoint, float]] = []
        
        # Statistics
        self._point_stats: Dict[str, Any] = {
            'total_points_added': 0,
            'total_points_removed': 0,
            'total_points_moved': 0,
            'points_per_class': {},
            'average_annotation_time': 0.0,
            'last_annotation_time': 0.0
        }
    
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced point tool."""
        self._point_size = kwargs.get('point_size', 8)
        self._min_point_size = kwargs.get('min_point_size', 4)
        self._max_point_size = kwargs.get('max_point_size', 32)
        self._point_size_step = kwargs.get('point_size_step', 2)
        self._adaptive_size = kwargs.get('adaptive_size', True)
        self._point_style = kwargs.get('point_style', 'circle')
        self._point_outline_width = kwargs.get('outline_width', 2)
        self._point_outline_color = kwargs.get('outline_color', QColor(0, 0, 0, 128))
        self._point_fill_alpha = kwargs.get('fill_alpha', 200)
        self._click_tolerance = kwargs.get('click_tolerance', 10.0)
        self._show_point_labels = kwargs.get('show_point_labels', True)
        self._show_confidence = kwargs.get('show_confidence', False)
        self._show_point_ids = kwargs.get('show_point_ids', False)
        self._show_timestamps = kwargs.get('show_timestamps', False)
        self._point_opacity = kwargs.get('point_opacity', 0.8)
        self._selected_point_scale = kwargs.get('selected_point_scale', 1.5)
        self._hover_point_scale = kwargs.get('hover_point_scale', 1.2)
        self._animate_additions = kwargs.get('animate_additions', True)
        self._animate_removals = kwargs.get('animate_removals', True)
        self._pulse_selected = kwargs.get('pulse_selected', False)
        self._snap_to_grid = kwargs.get('snap_to_grid', False)
        self._grid_size = kwargs.get('grid_size', 10)
        self._magnetic_snap = kwargs.get('magnetic_snap', False)
        self._magnetic_distance = kwargs.get('magnetic_distance', 20.0)
        self._highlight_recent_points = kwargs.get('highlight_recent_points', True)
        self._recent_point_highlight_duration = kwargs.get('recent_point_highlight_duration', 2.0)
        
        # Set custom colors if provided
        if 'point_colors' in kwargs:
            self._point_colors = kwargs['point_colors']
        
        # Set keyboard shortcuts if provided
        if 'keyboard_shortcuts' in kwargs:
            self._keyboard_shortcuts.update(kwargs['keyboard_shortcuts'])
        
        return super().initialize(**kwargs)
    
    def set_point_size(self, size: int) -> None:
        """Set point size with validation."""
        try:
            size = max(self._min_point_size, min(size, self._max_point_size))
            if self._point_size != size:
                self._point_size = size
                self._dirty_cache = True
                self.pointSizeChanged.emit(size)
                self.emit_state_changed({'point_size': size})
                
                # Request canvas repaint
                if self._canvas:
                    self._canvas.update()
        
        except Exception as e:
            self.emit_error(f"Error setting point size: {str(e)}")
    
    def get_point_size(self) -> int:
        """Get current point size."""
        return self._point_size
    
    def increase_point_size(self) -> None:
        """Increase point size by step."""
        new_size = min(self._point_size + self._point_size_step, self._max_point_size)
        self.set_point_size(new_size)
    
    def decrease_point_size(self) -> None:
        """Decrease point size by step."""
        new_size = max(self._point_size - self._point_size_step, self._min_point_size)
        self.set_point_size(new_size)
    
    def reset_point_size(self) -> None:
        """Reset point size to default."""
        self.set_point_size(8)
    
    def set_point_style(self, style: str) -> None:
        """Set point style."""
        try:
            valid_styles = ['circle', 'square', 'cross', 'diamond']
            if style in valid_styles and self._point_style != style:
                self._point_style = style
                self._dirty_cache = True
                self.pointStyleChanged.emit(style)
                self.emit_state_changed({'point_style': style})
                
                # Request canvas repaint
                if self._canvas:
                    self._canvas.update()
        
        except Exception as e:
            self.emit_error(f"Error setting point style: {str(e)}")
    
    def get_point_style(self) -> str:
        """Get current point style."""
        return self._point_style
    
    def cycle_point_style(self) -> None:
        """Cycle through point styles."""
        styles = ['circle', 'square', 'cross', 'diamond']
        current_index = styles.index(self._point_style)
        next_index = (current_index + 1) % len(styles)
        self.set_point_style(styles[next_index])
    
    def set_show_confidence(self, show: bool) -> None:
        """Set whether to show confidence values."""
        if self._show_confidence != show:
            self._show_confidence = show
            self.confidenceDisplayToggled.emit(show)
            self.emit_state_changed({'show_confidence': show})
            
            # Request canvas repaint
            if self._canvas:
                self._canvas.update()
    
    def is_show_confidence(self) -> bool:
        """Check if confidence values are shown."""
        return self._show_confidence
    
    def toggle_confidence_display(self) -> None:
        """Toggle confidence display."""
        self.set_show_confidence(not self._show_confidence)
    
    def set_show_point_labels(self, show: bool) -> None:
        """Set whether to show point labels."""
        if self._show_point_labels != show:
            self._show_point_labels = show
            self.emit_state_changed({'show_point_labels': show})
            
            # Request canvas repaint
            if self._canvas:
                self._canvas.update()
    
    def is_show_point_labels(self) -> bool:
        """Check if point labels are shown."""
        return self._show_point_labels
    
    def toggle_point_labels(self) -> None:
        """Toggle point labels display."""
        self.set_show_point_labels(not self._show_point_labels)
    
    def set_adaptive_size(self, enabled: bool) -> None:
        """Enable or disable adaptive point size based on zoom."""
        if self._adaptive_size != enabled:
            self._adaptive_size = enabled
            self._dirty_cache = True
            self.emit_state_changed({'adaptive_size': enabled})
            
            # Request canvas repaint
            if self._canvas:
                self._canvas.update()
    
    def is_adaptive_size(self) -> bool:
        """Check if adaptive size is enabled."""
        return self._adaptive_size
    
    def set_size_scale_factor(self, factor: float) -> None:
        """Set size scale factor for adaptive sizing."""
        if self._size_scale_factor != factor:
            self._size_scale_factor = factor
            self._dirty_cache = True
            self.emit_state_changed({'size_scale_factor': factor})
            
            # Request canvas repaint if adaptive size is enabled
            if self._adaptive_size and self._canvas:
                self._canvas.update()
    
    def get_size_scale_factor(self) -> float:
        """Get current size scale factor."""
        return self._size_scale_factor
    
    def set_snap_to_grid(self, enabled: bool) -> None:
        """Enable or disable grid snapping."""
        if self._snap_to_grid != enabled:
            self._snap_to_grid = enabled
            self.emit_state_changed({'snap_to_grid': enabled})
    
    def is_snap_to_grid(self) -> bool:
        """Check if grid snapping is enabled."""
        return self._snap_to_grid
    
    def set_grid_size(self, size: int) -> None:
        """Set grid size for snapping."""
        if size > 0 and self._grid_size != size:
            self._grid_size = size
            self.emit_state_changed({'grid_size': size})
    
    def get_grid_size(self) -> int:
        """Get current grid size."""
        return self._grid_size
    
    def set_magnetic_snap(self, enabled: bool) -> None:
        """Enable or disable magnetic snapping to existing points."""
        if self._magnetic_snap != enabled:
            self._magnetic_snap = enabled
            self.emit_state_changed({'magnetic_snap': enabled})
    
    def is_magnetic_snap(self) -> bool:
        """Check if magnetic snapping is enabled."""
        return self._magnetic_snap
    
    def set_magnetic_distance(self, distance: float) -> None:
        """Set magnetic snapping distance."""
        if distance > 0 and self._magnetic_distance != distance:
            self._magnetic_distance = distance
            self.emit_state_changed({'magnetic_distance': distance})
    
    def get_magnetic_distance(self) -> float:
        """Get current magnetic distance."""
        return self._magnetic_distance
    
    def _calculate_effective_point_size(self, point: AnnotationPoint) -> int:
        """Calculate effective point size considering scale and state."""
        try:
            base_size = self._point_size
            
            # Apply adaptive sizing
            if self._adaptive_size:
                base_size = int(base_size * self._size_scale_factor)
            
            # Apply state-based scaling
            if point == self._selected_point:
                base_size = int(base_size * self._selected_point_scale)
            elif point == self._hover_point:
                base_size = int(base_size * self._hover_point_scale)
            elif point == self._dragging_point:
                base_size = int(base_size * self._dragging_point_scale)
            
            # Apply pulse effect if enabled
            if self._pulse_selected and point == self._selected_point:
                pulse_factor = 1.0 + 0.2 * abs(self._pulse_phase)
                base_size = int(base_size * pulse_factor)
            
            return max(self._min_point_size, min(base_size, self._max_point_size))
            
        except Exception as e:
            self.emit_error(f"Error calculating effective point size: {str(e)}")
            return self._point_size
    
    def _get_point_color(self, point: AnnotationPoint) -> QColor:
        """Get color for a specific point."""
        try:
            class_id = point.class_id
            if 0 <= class_id < len(self._point_colors):
                color = QColor(self._point_colors[class_id])
                color.setAlpha(self._point_fill_alpha)
                return color
            else:
                # Default color for unknown classes
                color = QColor(128, 128, 128)
                color.setAlpha(self._point_fill_alpha)
                return color
            
        except Exception as e:
            self.emit_error(f"Error getting point color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _snap_position(self, pos: QPointF) -> QPointF:
        """Apply position snapping if enabled."""
        try:
            snapped_pos = QPointF(pos)
            
            # Grid snapping
            if self._snap_to_grid:
                grid_x = round(pos.x() / self._grid_size) * self._grid_size
                grid_y = round(pos.y() / self._grid_size) * self._grid_size
                snapped_pos = QPointF(grid_x, grid_y)
            
            # Magnetic snapping
            if self._magnetic_snap and self._annotation_manager:
                points = self._annotation_manager.get_all_points()
                for point in points:
                    point_pos = QPointF(point.x, point.y)
                    distance = (snapped_pos - point_pos).manhattanLength()
                    
                    if distance <= self._magnetic_distance:
                        snapped_pos = point_pos
                        break
            
            return snapped_pos
            
        except Exception as e:
            self.emit_error(f"Error snapping position: {str(e)}")
            return pos
    
    def _update_recent_points(self) -> None:
        """Update recent points list for highlighting."""
        try:
            current_time = time.time()
            
            # Remove expired points
            self._recent_points = [
                (point, timestamp) for point, timestamp in self._recent_points
                if current_time - timestamp <= self._recent_point_highlight_duration
            ]
            
        except Exception as e:
            self.emit_error(f"Error updating recent points: {str(e)}")
    
    def _update_pulse_animation(self) -> None:
        """Update pulse animation phase."""
        try:
            if self._pulse_selected:
                self._pulse_phase += self._pulse_speed
                if self._pulse_phase > 1.0:
                    self._pulse_phase = -1.0
                elif self._pulse_phase < -1.0:
                    self._pulse_phase = 1.0
            
        except Exception as e:
            self.emit_error(f"Error updating pulse animation: {str(e)}")
    
    def draw_point(self, painter: QPainter, point: AnnotationPoint, canvas_rect: QRect) -> None:
        """Draw a single point with enhanced visualization."""
        try:
            # Calculate effective size and color
            point_size = self._calculate_effective_point_size(point)
            point_color = self._get_point_color(point)
            
            # Convert point position to screen coordinates
            screen_pos = self._image_to_screen_coords(QPointF(point.x, point.y))
            
            # Check if point is within canvas bounds
            if not canvas_rect.contains(screen_pos.toPoint()):
                return
            
            # Set up painter
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            # Draw point outline
            if self._point_outline_width > 0:
                painter.setPen(QPen(self._point_outline_color, self._point_outline_width))
            else:
                painter.setPen(QPen(point_color))
            
            painter.setBrush(QBrush(point_color))
            
            # Draw point based on style
            if self._point_style == 'circle':
                painter.drawEllipse(screen_pos, point_size, point_size)
            elif self._point_style == 'square':
                painter.drawRect(screen_pos.x() - point_size//2, screen_pos.y() - point_size//2, 
                               point_size, point_size)
            elif self._point_style == 'cross':
                self._draw_cross(painter, screen_pos, point_size)
            elif self._point_style == 'diamond':
                self._draw_diamond(painter, screen_pos, point_size)
            
            # Draw point labels if enabled
            if self._show_point_labels:
                self._draw_point_label(painter, point, screen_pos, point_size)
            
            # Draw confidence if enabled
            if self._show_confidence and hasattr(point, 'confidence'):
                self._draw_confidence(painter, point, screen_pos, point_size)
            
        except Exception as e:
            self.emit_error(f"Error drawing point: {str(e)}")
    
    def _draw_cross(self, painter: QPainter, center: QPointF, size: int) -> None:
        """Draw cross-shaped point."""
        half_size = size // 2
        painter.drawLine(center.x() - half_size, center.y(), 
                        center.x() + half_size, center.y())
        painter.drawLine(center.x(), center.y() - half_size, 
                        center.x(), center.y() + half_size)
    
    def _draw_diamond(self, painter: QPainter, center: QPointF, size: int) -> None:
        """Draw diamond-shaped point."""
        half_size = size // 2
        points = [
            QPointF(center.x(), center.y() - half_size),  # Top
            QPointF(center.x() + half_size, center.y()),  # Right
            QPointF(center.x(), center.y() + half_size),  # Bottom
            QPointF(center.x() - half_size, center.y())   # Left
        ]
        painter.drawPolygon(points)
    
    def _draw_point_label(self, painter: QPainter, point: AnnotationPoint, 
                         screen_pos: QPointF, point_size: int) -> None:
        """Draw point label."""
        try:
            label_text = f"C{point.class_id}"
            
            # Add ID if enabled
            if self._show_point_ids and hasattr(point, 'id'):
                label_text += f" ({point.id})"
            
            # Position label above point
            label_pos = QPointF(screen_pos.x(), screen_pos.y() - point_size - 5)
            
            # Draw label background
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            
            # Draw label text
            painter.drawText(label_pos, label_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing point label: {str(e)}")
    
    def _draw_confidence(self, painter: QPainter, point: AnnotationPoint, 
                        screen_pos: QPointF, point_size: int) -> None:
        """Draw confidence value."""
        try:
            if hasattr(point, 'confidence'):
                confidence_text = f"{point.confidence:.2f}"
                
                # Position confidence below point
                confidence_pos = QPointF(screen_pos.x(), screen_pos.y() + point_size + 15)
                
                # Draw confidence text
                painter.setPen(QPen(QColor(0, 0, 0)))
                painter.drawText(confidence_pos, confidence_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing confidence: {str(e)}")
    
    def handle_keyboard_shortcut(self, key: str) -> bool:
        """Handle keyboard shortcut."""
        try:
            if key == self._keyboard_shortcuts.get('increase_size'):
                self.increase_point_size()
                return True
            elif key == self._keyboard_shortcuts.get('decrease_size'):
                self.decrease_point_size()
                return True
            elif key == self._keyboard_shortcuts.get('reset_size'):
                self.reset_point_size()
                return True
            elif key == self._keyboard_shortcuts.get('next_style'):
                self.cycle_point_style()
                return True
            elif key == self._keyboard_shortcuts.get('toggle_confidence'):
                self.toggle_confidence_display()
                return True
            elif key == self._keyboard_shortcuts.get('toggle_labels'):
                self.toggle_point_labels()
                return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error handling keyboard shortcut: {str(e)}")
            return False
    
    def update_animation(self) -> None:
        """Update animations (called by timer)."""
        try:
            # Update pulse animation
            self._update_pulse_animation()
            
            # Update recent points
            self._update_recent_points()
            
            # Request canvas repaint if animations are active
            if (self._pulse_selected and self._selected_point) or self._recent_points:
                if self._canvas:
                    self._canvas.update()
            
        except Exception as e:
            self.emit_error(f"Error updating animation: {str(e)}")
    
    def get_point_configuration(self) -> Dict[str, Any]:
        """Get current point configuration."""
        return {
            'point_size': self._point_size,
            'min_point_size': self._min_point_size,
            'max_point_size': self._max_point_size,
            'point_size_step': self._point_size_step,
            'adaptive_size': self._adaptive_size,
            'size_scale_factor': self._size_scale_factor,
            'point_style': self._point_style,
            'point_outline_width': self._point_outline_width,
            'point_outline_color': self._point_outline_color,
            'point_fill_alpha': self._point_fill_alpha,
            'show_point_labels': self._show_point_labels,
            'show_confidence': self._show_confidence,
            'show_point_ids': self._show_point_ids,
            'show_timestamps': self._show_timestamps,
            'snap_to_grid': self._snap_to_grid,
            'grid_size': self._grid_size,
            'magnetic_snap': self._magnetic_snap,
            'magnetic_distance': self._magnetic_distance,
            'highlight_recent_points': self._highlight_recent_points,
            'recent_point_highlight_duration': self._recent_point_highlight_duration,
            'keyboard_shortcuts': self._keyboard_shortcuts.copy()
        }
    
    def set_point_configuration(self, config: Dict[str, Any]) -> None:
        """Set point configuration from dictionary."""
        try:
            if 'point_size' in config:
                self.set_point_size(config['point_size'])
            if 'point_style' in config:
                self.set_point_style(config['point_style'])
            if 'show_point_labels' in config:
                self.set_show_point_labels(config['show_point_labels'])
            if 'show_confidence' in config:
                self.set_show_confidence(config['show_confidence'])
            if 'adaptive_size' in config:
                self.set_adaptive_size(config['adaptive_size'])
            if 'size_scale_factor' in config:
                self.set_size_scale_factor(config['size_scale_factor'])
            if 'snap_to_grid' in config:
                self.set_snap_to_grid(config['snap_to_grid'])
            if 'grid_size' in config:
                self.set_grid_size(config['grid_size'])
            if 'magnetic_snap' in config:
                self.set_magnetic_snap(config['magnetic_snap'])
            if 'magnetic_distance' in config:
                self.set_magnetic_distance(config['magnetic_distance'])
            
            # Update other settings
            for key, value in config.items():
                if hasattr(self, f'_{key}'):
                    setattr(self, f'_{key}', value)
            
        except Exception as e:
            self.emit_error(f"Error setting point configuration: {str(e)}")
    
    def get_point_statistics(self) -> Dict[str, Any]:
        """Get point tool statistics."""
        return self._point_stats.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced point tool statistics."""
        stats = super().get_statistics()
        stats.update({
            'point_size': self._point_size,
            'point_style': self._point_style,
            'adaptive_size': self._adaptive_size,
            'show_point_labels': self._show_point_labels,
            'show_confidence': self._show_confidence,
            'snap_to_grid': self._snap_to_grid,
            'magnetic_snap': self._magnetic_snap,
            'point_statistics': self.get_point_statistics(),
            'recent_points_count': len(self._recent_points),
            'cache_enabled': self._use_point_cache,
            'cache_dirty': self._dirty_cache
        })
        return stats