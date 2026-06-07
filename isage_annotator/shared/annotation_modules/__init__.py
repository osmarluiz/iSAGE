"""
Modular Annotation System - Plug-and-Play Components

This package provides a modular, LEGO-like annotation system where components
can be mixed and matched to create different annotation interfaces.

Architecture:
- tools/: Different annotation tools (point, polygon, brush, etc.)
- canvas/: Canvas functionality (zoom, pan, rendering, grid overlay, crosshair)
- overlays/: Visual overlays (predictions, ground truth, etc.)
- io/: Input/output operations (save, load, auto-save)
- navigation/: Image navigation (sequential, batch, session)
- ui/: User interface components (panels, themes, controls, opacity, colors)
- display/: Display utilities (channel mapping, color schemes)
- tracking/: Time tracking and productivity metrics
- builders/: Composition layer for creating annotation interfaces

Example usage:
    from annotation_modules.builders import AnnotationBuilder
    from annotation_modules.tools import PointTool
    from annotation_modules.overlays import PredictionOverlay
    
    # Create annotation system using fluent interface
    main_window = (AnnotationBuilder()
        .set_preset('active_learning')
        .add_component('point_tool', PointTool, {'point_size': 8})
        .add_component('prediction_overlay', PredictionOverlay, {'confidence_threshold': 0.5})
        .build())
"""

__version__ = "1.0.0"
__author__ = "viz_software"

# Import main builder for convenience (if available)
try:
    from .builders.annotation_builder import AnnotationBuilder
    builder_available = True
except ImportError:
    builder_available = False

# Import core simple components for easier access
try:
    from .simple_canvas import SimpleAnnotationCanvas
    from .simple_control_panel import SimpleControlPanel  
    from .simple_status_panel import SimpleStatusPanel
    simple_components_available = True
except ImportError:
    simple_components_available = False

# Import advanced components
try:
    from .canvas.advanced_annotation_canvas import AdvancedAnnotationCanvas
    advanced_canvas_available = True
except ImportError:
    advanced_canvas_available = False

# Build __all__ dynamically based on what's available
__all__ = []
if builder_available:
    __all__.append('AnnotationBuilder')
if simple_components_available:
    __all__.extend(['SimpleAnnotationCanvas', 'SimpleControlPanel', 'SimpleStatusPanel'])
if advanced_canvas_available:
    __all__.append('AdvancedAnnotationCanvas')