"""
UI Components - User interface elements

This module contains UI components:
- control_panel: Main control interface with tool selection and settings
- status_panel: Status and progress display with logging
- theme_manager: Theme and styling management with light/dark modes
- dialog_manager: Modal dialogs and user interactions
- opacity_controls: Opacity controls for overlays
- class_color_scheme: Class color scheme management
- point_visibility_controls: Point visibility toggle system
"""

# Import base components
try:
    from .base_ui import BaseUI, UIProtocol
    base_ui_available = True
except ImportError:
    base_ui_available = False

try:
    from .control_panel import ControlPanel
    control_panel_available = True
except ImportError:
    control_panel_available = False

try:
    from .status_panel import StatusPanel
    status_panel_available = True
except ImportError:
    status_panel_available = False

try:
    from .theme_manager import ThemeManager
    theme_manager_available = True
except ImportError:
    theme_manager_available = False

try:
    from .dialog_manager import DialogManager
    dialog_manager_available = True
except ImportError:
    dialog_manager_available = False

try:
    from .opacity_controls import OpacityControls
    opacity_controls_available = True
except ImportError:
    opacity_controls_available = False

try:
    from .class_color_scheme import ClassColorScheme
    class_color_scheme_available = True
except ImportError:
    class_color_scheme_available = False

try:
    from .point_visibility_controls import PointVisibilityControls
    point_visibility_available = True
except ImportError:
    point_visibility_available = False

try:
    from .progress_indicator import ProgressIndicator, ProgressNotificationManager, get_progress_notification_manager
    progress_indicator_available = True
except ImportError:
    progress_indicator_available = False

try:
    from .header_bar import HeaderBar
    enhanced_header_available = True
except ImportError:
    enhanced_header_available = False

# Build __all__ dynamically
__all__ = []
if base_ui_available:
    __all__.extend(['BaseUI', 'UIProtocol'])
if control_panel_available:
    __all__.append('ControlPanel')
if status_panel_available:
    __all__.append('StatusPanel')
if theme_manager_available:
    __all__.append('ThemeManager')
if dialog_manager_available:
    __all__.append('DialogManager')
if opacity_controls_available:
    __all__.append('OpacityControls')
if class_color_scheme_available:
    __all__.append('ClassColorScheme')
if point_visibility_available:
    __all__.append('PointVisibilityControls')
if progress_indicator_available:
    __all__.extend(['ProgressIndicator', 'ProgressNotificationManager', 'get_progress_notification_manager'])
if enhanced_header_available:
    __all__.append('HeaderBar')