"""
Improved Grid Overlay - Enhanced grid display with better performance and features

This enhanced version addresses potential issues and adds improvements:
- Better memory management
- Improved drawing performance
- More grid styles
- Better integration with canvas coordinate system
"""

import numpy as np
from typing import Optional, Tuple, List
from ..base_protocols import BaseComponent, QPainter, QColor, QPen, QRect, QPoint
from ..base_protocols import pyqtSignal, QPixmap, QBrush


class GridOverlay(BaseComponent):
    """Enhanced grid overlay component with improved performance and features."""
    
    # Grid overlay signals
    gridToggled = pyqtSignal(bool)  # enabled
    gridSizeChanged = pyqtSignal(int)  # grid_size
    gridColorChanged = pyqtSignal(object)  # QColor
    gridStyleChanged = pyqtSignal(str)  # grid_style
    
    def __init__(self, name: str = "grid_overlay", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Grid configuration
        self._enabled: bool = False
        self._grid_size: int = 50  # Grid spacing in pixels
        self._min_grid_size: int = 5
        self._max_grid_size: int = 500
        self._grid_color: QColor = QColor(128, 128, 128, 80)
        
        # Enhanced grid styles
        self._grid_style: str = "lines"  # lines, dots, crosses, dashes, hybrid
        self._line_width: int = 1
        self._line_style: int = 1  # Qt.DashLine
        self._dot_size: int = 2
        self._cross_size: int = 5
        
        # Adaptive appearance
        self._adaptive_opacity: bool = True
        self._adaptive_size: bool = False
        self._fade_threshold: float = 0.3
        self._min_opacity: float = 0.1
        self._max_opacity: float = 0.8
        
        # Canvas integration
        self._canvas = None
        self._canvas_rect: QRect = QRect(0, 0, 800, 600)
        self._scale_factor: float = 1.0
        self._image_offset: QPoint = QPoint(0, 0)
        
        # Performance optimizations
        self._use_pixmap_cache: bool = True
        self._cached_pixmap: Optional[QPixmap] = None
        self._cache_valid: bool = False
        self._last_cache_params: Tuple = (0, 0, 0, 0, 0)  # scale, size, offset_x, offset_y, grid_size
        
        # Drawing optimization
        self._use_viewport_culling: bool = True
        self._draw_batch_size: int = 1000  # Maximum lines/dots per batch
        
        # Grid alignment
        self._snap_to_pixels: bool = True
        self._align_to_image: bool = True
        self._grid_origin: QPoint = QPoint(0, 0)
        
        # Advanced features
        self._major_grid_enabled: bool = False
        self._major_grid_interval: int = 5  # Every 5th line is major
        self._major_grid_color: QColor = QColor(64, 64, 64, 120)
        self._major_grid_width: int = 2
        
        # Measurement features
        self._show_coordinates: bool = False
        self._coordinate_font_size: int = 8
        self._coordinate_frequency: int = 5  # Show coordinates every 5th intersection
        
        # Memory management
        self._max_cache_size: int = 10 * 1024 * 1024  # 10MB cache limit
        self._auto_cleanup: bool = True
        
    def initialize(self, **kwargs) -> bool:
        """Initialize improved grid overlay."""
        self._enabled = kwargs.get('enabled', False)
        self._grid_size = kwargs.get('grid_size', 50)
        self._grid_color = kwargs.get('grid_color', QColor(128, 128, 128, 80))
        self._grid_style = kwargs.get('grid_style', 'lines')
        self._line_width = kwargs.get('line_width', 1)
        self._line_style = kwargs.get('line_style', 1)
        self._dot_size = kwargs.get('dot_size', 2)
        self._cross_size = kwargs.get('cross_size', 5)
        self._adaptive_opacity = kwargs.get('adaptive_opacity', True)
        self._adaptive_size = kwargs.get('adaptive_size', False)
        self._fade_threshold = kwargs.get('fade_threshold', 0.3)
        self._min_opacity = kwargs.get('min_opacity', 0.1)
        self._max_opacity = kwargs.get('max_opacity', 0.8)
        self._use_pixmap_cache = kwargs.get('use_pixmap_cache', True)
        self._use_viewport_culling = kwargs.get('use_viewport_culling', True)
        self._draw_batch_size = kwargs.get('draw_batch_size', 1000)
        self._snap_to_pixels = kwargs.get('snap_to_pixels', True)
        self._align_to_image = kwargs.get('align_to_image', True)
        self._major_grid_enabled = kwargs.get('major_grid_enabled', False)
        self._major_grid_interval = kwargs.get('major_grid_interval', 5)
        self._major_grid_color = kwargs.get('major_grid_color', QColor(64, 64, 64, 120))
        self._major_grid_width = kwargs.get('major_grid_width', 2)
        self._show_coordinates = kwargs.get('show_coordinates', False)
        self._coordinate_font_size = kwargs.get('coordinate_font_size', 8)
        self._coordinate_frequency = kwargs.get('coordinate_frequency', 5)
        
        return super().initialize(**kwargs)
    
    def set_canvas_parameters(self, canvas_rect: QRect, scale_factor: float, image_offset: QPoint) -> None:
        """Set canvas parameters for accurate grid positioning."""
        self._canvas_rect = canvas_rect
        self._scale_factor = scale_factor
        self._image_offset = image_offset
        
        # Invalidate cache
        self._cache_valid = False
        
        # Update grid if enabled
        if self._enabled and self._canvas:
            self._canvas.update()
    
    def set_grid_style(self, style: str) -> None:
        """Set grid drawing style."""
        valid_styles = ['lines', 'dots', 'crosses', 'dashes', 'hybrid']
        if style in valid_styles and self._grid_style != style:
            self._grid_style = style
            self._cache_valid = False
            self.gridStyleChanged.emit(style)
            self.emit_state_changed({'grid_style': style})
            
            if self._canvas and self._enabled:
                self._canvas.update()
    
    def set_major_grid_enabled(self, enabled: bool) -> None:
        """Enable or disable major grid lines."""
        if self._major_grid_enabled != enabled:
            self._major_grid_enabled = enabled
            self._cache_valid = False
            self.emit_state_changed({'major_grid_enabled': enabled})
            
            if self._canvas and self._enabled:
                self._canvas.update()
    
    def set_coordinate_display(self, enabled: bool) -> None:
        """Enable or disable coordinate display."""
        if self._show_coordinates != enabled:
            self._show_coordinates = enabled
            self._cache_valid = False
            self.emit_state_changed({'show_coordinates': enabled})
            
            if self._canvas and self._enabled:
                self._canvas.update()
    
    def draw_grid(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Draw grid overlay with improved performance."""
        try:
            if not self._enabled:
                return
            
            # Check if we can use cached pixmap
            if self._use_pixmap_cache and self._is_cache_valid():
                if self._cached_pixmap:
                    painter.drawPixmap(viewport_rect, self._cached_pixmap, viewport_rect)
                    return
            
            # Calculate grid parameters
            grid_params = self._calculate_grid_parameters(viewport_rect)
            if not grid_params:
                return
            
            # Setup painter
            painter.setRenderHint(QPainter.Antialiasing, False)  # Disable for grid lines
            
            # Draw grid based on style
            if self._grid_style == 'lines':
                self._draw_grid_lines(painter, grid_params)
            elif self._grid_style == 'dots':
                self._draw_grid_dots(painter, grid_params)
            elif self._grid_style == 'crosses':
                self._draw_grid_crosses(painter, grid_params)
            elif self._grid_style == 'dashes':
                self._draw_grid_dashes(painter, grid_params)
            elif self._grid_style == 'hybrid':
                self._draw_grid_hybrid(painter, grid_params)
            
            # Draw major grid if enabled
            if self._major_grid_enabled:
                self._draw_major_grid(painter, grid_params)
            
            # Draw coordinates if enabled
            if self._show_coordinates:
                self._draw_coordinates(painter, grid_params)
            
            # Update cache
            if self._use_pixmap_cache:
                self._update_cache(painter, viewport_rect)
            
        except Exception as e:
            self.emit_error(f"Error drawing grid: {str(e)}")
    
    def _calculate_grid_parameters(self, viewport_rect: QRect) -> Optional[dict]:
        """Calculate grid drawing parameters."""
        try:
            # Calculate effective grid size
            effective_grid_size = self._grid_size * self._scale_factor
            
            # Skip if grid is too small to be useful
            if effective_grid_size < 3:
                return None
            
            # Calculate grid opacity
            opacity = self._calculate_grid_opacity()
            if opacity <= 0:
                return None
            
            # Calculate grid bounds
            if self._align_to_image:
                # Align grid to image coordinates
                start_x = self._image_offset.x()
                start_y = self._image_offset.y()
            else:
                # Align grid to canvas coordinates
                start_x = viewport_rect.left()
                start_y = viewport_rect.top()
            
            # Calculate grid positions
            if self._use_viewport_culling:
                # Only calculate lines within viewport
                grid_lines_x = []
                grid_lines_y = []
                
                x = start_x
                while x <= viewport_rect.right():
                    if x >= viewport_rect.left():
                        grid_lines_x.append(x)
                    x += effective_grid_size
                
                y = start_y
                while y <= viewport_rect.bottom():
                    if y >= viewport_rect.top():
                        grid_lines_y.append(y)
                    y += effective_grid_size
                
                # Also add lines before the start if needed
                x = start_x - effective_grid_size
                while x >= viewport_rect.left():
                    grid_lines_x.append(x)
                    x -= effective_grid_size
                
                y = start_y - effective_grid_size
                while y >= viewport_rect.top():
                    grid_lines_y.append(y)
                    y -= effective_grid_size
            else:
                # Calculate all grid lines
                grid_lines_x = []
                grid_lines_y = []
                
                # This would be implemented for non-culled drawing
                pass
            
            return {
                'grid_lines_x': sorted(grid_lines_x),
                'grid_lines_y': sorted(grid_lines_y),
                'effective_size': effective_grid_size,
                'opacity': opacity,
                'viewport': viewport_rect
            }
            
        except Exception as e:
            self.emit_error(f"Error calculating grid parameters: {str(e)}")
            return None
    
    def _calculate_grid_opacity(self) -> float:
        """Calculate grid opacity based on scale and settings."""
        try:
            if not self._adaptive_opacity:
                return self._max_opacity
            
            # Base opacity on scale factor
            if self._scale_factor < self._fade_threshold:
                return 0.0
            
            # Linear interpolation between min and max opacity
            if self._scale_factor < 1.0:
                ratio = (self._scale_factor - self._fade_threshold) / (1.0 - self._fade_threshold)
                return self._min_opacity + (self._max_opacity - self._min_opacity) * ratio
            else:
                return self._max_opacity
                
        except Exception as e:
            self.emit_error(f"Error calculating grid opacity: {str(e)}")
            return self._max_opacity
    
    def _draw_grid_lines(self, painter: QPainter, grid_params: dict) -> None:
        """Draw grid as lines."""
        try:
            grid_color = QColor(self._grid_color)
            grid_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(grid_color)
            pen.setWidth(self._line_width)
            pen.setStyle(self._line_style)
            painter.setPen(pen)
            
            viewport = grid_params['viewport']
            
            # Draw vertical lines
            for x in grid_params['grid_lines_x']:
                if self._snap_to_pixels:
                    x = int(x) + 0.5  # Snap to pixel boundaries
                painter.drawLine(x, viewport.top(), x, viewport.bottom())
            
            # Draw horizontal lines
            for y in grid_params['grid_lines_y']:
                if self._snap_to_pixels:
                    y = int(y) + 0.5  # Snap to pixel boundaries
                painter.drawLine(viewport.left(), y, viewport.right(), y)
            
        except Exception as e:
            self.emit_error(f"Error drawing grid lines: {str(e)}")
    
    def _draw_grid_dots(self, painter: QPainter, grid_params: dict) -> None:
        """Draw grid as dots."""
        try:
            grid_color = QColor(self._grid_color)
            grid_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(grid_color)
            pen.setWidth(self._dot_size)
            painter.setPen(pen)
            
            # Draw dots at intersections
            batch_count = 0
            for x in grid_params['grid_lines_x']:
                for y in grid_params['grid_lines_y']:
                    painter.drawPoint(x, y)
                    batch_count += 1
                    
                    # Break into batches for performance
                    if batch_count >= self._draw_batch_size:
                        painter.save()
                        painter.restore()
                        batch_count = 0
            
        except Exception as e:
            self.emit_error(f"Error drawing grid dots: {str(e)}")
    
    def _draw_grid_crosses(self, painter: QPainter, grid_params: dict) -> None:
        """Draw grid as crosses."""
        try:
            grid_color = QColor(self._grid_color)
            grid_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(grid_color)
            pen.setWidth(self._line_width)
            painter.setPen(pen)
            
            half_size = self._cross_size // 2
            
            # Draw crosses at intersections
            batch_count = 0
            for x in grid_params['grid_lines_x']:
                for y in grid_params['grid_lines_y']:
                    # Horizontal line
                    painter.drawLine(x - half_size, y, x + half_size, y)
                    # Vertical line
                    painter.drawLine(x, y - half_size, x, y + half_size)
                    batch_count += 1
                    
                    # Break into batches for performance
                    if batch_count >= self._draw_batch_size // 2:  # Each cross is 2 lines
                        painter.save()
                        painter.restore()
                        batch_count = 0
            
        except Exception as e:
            self.emit_error(f"Error drawing grid crosses: {str(e)}")
    
    def _draw_grid_dashes(self, painter: QPainter, grid_params: dict) -> None:
        """Draw grid as dashed lines."""
        try:
            grid_color = QColor(self._grid_color)
            grid_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(grid_color)
            pen.setWidth(self._line_width)
            pen.setStyle(2)  # Qt.DashLine
            painter.setPen(pen)
            
            viewport = grid_params['viewport']
            
            # Draw dashed vertical lines
            for x in grid_params['grid_lines_x']:
                painter.drawLine(x, viewport.top(), x, viewport.bottom())
            
            # Draw dashed horizontal lines
            for y in grid_params['grid_lines_y']:
                painter.drawLine(viewport.left(), y, viewport.right(), y)
            
        except Exception as e:
            self.emit_error(f"Error drawing grid dashes: {str(e)}")
    
    def _draw_grid_hybrid(self, painter: QPainter, grid_params: dict) -> None:
        """Draw grid as hybrid (lines + dots)."""
        try:
            # Draw lines first
            self._draw_grid_lines(painter, grid_params)
            
            # Then draw dots at intersections
            grid_color = QColor(self._grid_color)
            grid_color.setAlpha(int(grid_params['opacity'] * 255 * 0.8))  # Slightly transparent
            
            pen = QPen(grid_color)
            pen.setWidth(self._dot_size + 1)
            painter.setPen(pen)
            
            # Draw dots at intersections
            for x in grid_params['grid_lines_x'][::2]:  # Every other intersection
                for y in grid_params['grid_lines_y'][::2]:
                    painter.drawPoint(x, y)
            
        except Exception as e:
            self.emit_error(f"Error drawing grid hybrid: {str(e)}")
    
    def _draw_major_grid(self, painter: QPainter, grid_params: dict) -> None:
        """Draw major grid lines."""
        try:
            major_color = QColor(self._major_grid_color)
            major_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(major_color)
            pen.setWidth(self._major_grid_width)
            painter.setPen(pen)
            
            viewport = grid_params['viewport']
            
            # Draw major vertical lines
            for i, x in enumerate(grid_params['grid_lines_x']):
                if i % self._major_grid_interval == 0:
                    painter.drawLine(x, viewport.top(), x, viewport.bottom())
            
            # Draw major horizontal lines
            for i, y in enumerate(grid_params['grid_lines_y']):
                if i % self._major_grid_interval == 0:
                    painter.drawLine(viewport.left(), y, viewport.right(), y)
            
        except Exception as e:
            self.emit_error(f"Error drawing major grid: {str(e)}")
    
    def _draw_coordinates(self, painter: QPainter, grid_params: dict) -> None:
        """Draw coordinate labels."""
        try:
            coord_color = QColor(self._grid_color)
            coord_color.setAlpha(int(grid_params['opacity'] * 255))
            
            pen = QPen(coord_color)
            painter.setPen(pen)
            
            font = painter.font()
            font.setPointSize(self._coordinate_font_size)
            painter.setFont(font)
            
            # Draw coordinates at intersections
            for i, x in enumerate(grid_params['grid_lines_x']):
                for j, y in enumerate(grid_params['grid_lines_y']):
                    if i % self._coordinate_frequency == 0 and j % self._coordinate_frequency == 0:
                        # Convert to image coordinates
                        image_x = int((x - self._image_offset.x()) / self._scale_factor)
                        image_y = int((y - self._image_offset.y()) / self._scale_factor)
                        
                        coord_text = f"({image_x},{image_y})"
                        painter.drawText(x + 5, y - 5, coord_text)
            
        except Exception as e:
            self.emit_error(f"Error drawing coordinates: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """Check if pixmap cache is valid."""
        try:
            current_params = (
                self._scale_factor,
                self._grid_size,
                self._image_offset.x(),
                self._image_offset.y(),
                hash(self._grid_style)
            )
            
            return (self._cache_valid and 
                    self._cached_pixmap and 
                    current_params == self._last_cache_params)
            
        except Exception as e:
            self.emit_error(f"Error checking cache validity: {str(e)}")
            return False
    
    def _update_cache(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Update pixmap cache."""
        try:
            if not self._use_pixmap_cache:
                return
            
            # Check cache size limits
            cache_size = viewport_rect.width() * viewport_rect.height() * 4  # 4 bytes per pixel
            if cache_size > self._max_cache_size:
                return
            
            # Create cached pixmap
            self._cached_pixmap = QPixmap(viewport_rect.size())
            self._cached_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            
            # Update cache parameters
            self._last_cache_params = (
                self._scale_factor,
                self._grid_size,
                self._image_offset.x(),
                self._image_offset.y(),
                hash(self._grid_style)
            )
            
            self._cache_valid = True
            
        except Exception as e:
            self.emit_error(f"Error updating cache: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the pixmap cache."""
        self._cached_pixmap = None
        self._cache_valid = False
        self.emit_state_changed({'cache_cleared': True})
    
    def get_memory_usage(self) -> dict:
        """Get memory usage statistics."""
        try:
            cache_size = 0
            if self._cached_pixmap:
                cache_size = self._cached_pixmap.width() * self._cached_pixmap.height() * 4
            
            return {
                'cache_size_bytes': cache_size,
                'cache_size_mb': cache_size / (1024 * 1024),
                'cache_valid': self._cache_valid,
                'max_cache_size_mb': self._max_cache_size / (1024 * 1024)
            }
            
        except Exception as e:
            self.emit_error(f"Error getting memory usage: {str(e)}")
            return {'cache_size_bytes': 0, 'cache_size_mb': 0, 'cache_valid': False}
    
    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return {
            'use_pixmap_cache': self._use_pixmap_cache,
            'use_viewport_culling': self._use_viewport_culling,
            'draw_batch_size': self._draw_batch_size,
            'snap_to_pixels': self._snap_to_pixels,
            'memory_usage': self.get_memory_usage()
        }
    
    def get_statistics(self) -> dict:
        """Get improved grid overlay statistics."""
        stats = super().get_statistics()
        stats.update({
            'grid_style': self._grid_style,
            'major_grid_enabled': self._major_grid_enabled,
            'show_coordinates': self._show_coordinates,
            'adaptive_opacity': self._adaptive_opacity,
            'adaptive_size': self._adaptive_size,
            'performance_metrics': self.get_performance_metrics()
        })
        return stats