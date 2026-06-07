"""
Canvas Components - Image display and interaction

This module contains canvas-related components:
- base_canvas: Core canvas engine with coordinate conversion
- zoom_controller: Zoom functionality (0.1x to 5.0x)
- pan_controller: Pan functionality with middle mouse drag
- minimap_navigator: Interactive thumbnail navigation
- selection_controller: Selection and hover handling
- annotation_canvas: Main annotation canvas widget
- grid_overlay: Grid overlay system for precise annotation
- crosshair_cursor: Crosshair cursor support
- pixel_info_tooltip: Pixel information tooltip system
"""

# Import base components (if available)
try:
    from .base_canvas import BaseCanvas, CanvasProtocol
    base_available = True
except ImportError:
    base_available = False

try:
    from .annotation_canvas import AnnotationCanvas
    basic_canvas_available = True
except ImportError:
    basic_canvas_available = False

try:
    from .advanced_annotation_canvas import AdvancedAnnotationCanvas
    advanced_canvas_available = True
except ImportError:
    advanced_canvas_available = False

try:
    from .grid_overlay import GridOverlay
    grid_available = True
except ImportError:
    grid_available = False

try:
    from .crosshair_cursor import CrosshairCursor
    crosshair_available = True
except ImportError:
    crosshair_available = False

try:
    from .pixel_info_tooltip import PixelInfoTooltip
    tooltip_available = True
except ImportError:
    tooltip_available = False

# Build __all__ dynamically
__all__ = []
if base_available:
    __all__.extend(['BaseCanvas', 'CanvasProtocol'])
if basic_canvas_available:
    __all__.append('AnnotationCanvas')
if advanced_canvas_available:
    __all__.append('AdvancedAnnotationCanvas')
if grid_available:
    __all__.append('GridOverlay')
if crosshair_available:
    __all__.append('CrosshairCursor')
if tooltip_available:
    __all__.append('PixelInfoTooltip')