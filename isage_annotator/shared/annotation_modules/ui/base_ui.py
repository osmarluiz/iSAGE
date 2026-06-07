"""
Base UI - Foundation for all UI components

This module provides the base class for UI components that handle
user interface elements and interactions.
"""

from typing import Dict, Any, Optional, Callable
from ..base_protocols import BaseComponent, QWidget, pyqtSignal

# Try to get UIProtocol, but continue if missing
try:
    from ..base_protocols import UIProtocol
except ImportError:
    # Create dummy protocol if missing
    class UIProtocol:
        pass


class BaseUI(BaseComponent):
    """Base class for all UI components."""
    
    # UI-specific signals
    stateChanged = pyqtSignal(dict)
    userAction = pyqtSignal(str, object)  # action_name, data
    widgetReady = pyqtSignal()
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        
        self._widget: Optional[QWidget] = None
        self._state: Dict[str, Any] = {}
        self._enabled: bool = True
        self._visible: bool = True
        
        # Style and theme
        self._theme: str = "dark"
        self._custom_stylesheet: str = ""
        
        # Event handlers
        self._action_handlers: Dict[str, Callable] = {}
    
    # UIProtocol implementation
    def get_widget(self) -> QWidget:
        """Get the main widget for this UI component."""
        if self._widget is None:
            self._widget = self._create_widget()
            self._setup_widget()
            self.widgetReady.emit()
        return self._widget
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update UI state."""
        self._state.update(state)
        self._update_widget_state()
        self.stateChanged.emit(self._state)
        self.emit_state_changed(self._state)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current UI state."""
        return self._state.copy()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable UI component."""
        self._enabled = enabled
        if self._widget:
            self._widget.setEnabled(enabled)
        self.emit_state_changed({'enabled': enabled})
    
    # UI-specific methods
    def is_enabled(self) -> bool:
        """Check if UI component is enabled."""
        return self._enabled
    
    def set_visible(self, visible: bool) -> None:
        """Set UI component visibility."""
        self._visible = visible
        if self._widget:
            self._widget.setVisible(visible)
        self.emit_state_changed({'visible': visible})
    
    def is_visible(self) -> bool:
        """Check if UI component is visible."""
        return self._visible
    
    def set_theme(self, theme: str) -> None:
        """Set UI theme."""
        self._theme = theme
        self._apply_theme()
        self.emit_state_changed({'theme': theme})
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self._theme
    
    def set_custom_stylesheet(self, stylesheet: str) -> None:
        """Set custom stylesheet."""
        self._custom_stylesheet = stylesheet
        self._apply_stylesheet()
        self.emit_state_changed({'custom_stylesheet': len(stylesheet) > 0})
    
    def get_custom_stylesheet(self) -> str:
        """Get custom stylesheet."""
        return self._custom_stylesheet
    
    def add_action_handler(self, action_name: str, handler: Callable) -> None:
        """Add action handler."""
        self._action_handlers[action_name] = handler
    
    def remove_action_handler(self, action_name: str) -> None:
        """Remove action handler."""
        if action_name in self._action_handlers:
            del self._action_handlers[action_name]
    
    def trigger_action(self, action_name: str, data: Any = None) -> None:
        """Trigger user action."""
        if action_name in self._action_handlers:
            try:
                self._action_handlers[action_name](data)
            except Exception as e:
                self.emit_error(f"Error in action handler '{action_name}': {str(e)}")
        
        self.userAction.emit(action_name, data)
    
    def set_state_value(self, key: str, value: Any) -> None:
        """Set a single state value."""
        self._state[key] = value
        self._update_widget_state()
        self.emit_state_changed({key: value})
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get a single state value."""
        return self._state.get(key, default)
    
    def clear_state(self) -> None:
        """Clear all state."""
        self._state.clear()
        self._update_widget_state()
        self.emit_state_changed({})
    
    def refresh(self) -> None:
        """Refresh UI component."""
        if self._widget:
            self._update_widget_state()
            self._widget.update()
    
    def reset(self) -> None:
        """Reset UI component to default state."""
        self.clear_state()
        self.set_enabled(True)
        self.set_visible(True)
        self.refresh()
    
    def get_widget_geometry(self) -> Dict[str, int]:
        """Get widget geometry."""
        if self._widget:
            geometry = self._widget.geometry()
            return {
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height()
            }
        return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def set_widget_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """Set widget geometry."""
        if self._widget:
            self._widget.setGeometry(x, y, width, height)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get UI statistics."""
        return {
            'theme': self._theme,
            'enabled': self._enabled,
            'visible': self._visible,
            'state_keys': list(self._state.keys()),
            'action_handlers': list(self._action_handlers.keys()),
            'has_custom_stylesheet': len(self._custom_stylesheet) > 0,
            'geometry': self.get_widget_geometry(),
            'has_widget': self._widget is not None
        }
    
    # Theme presets
    def get_dark_theme_stylesheet(self) -> str:
        """Get dark theme stylesheet."""
        return """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: #3c3c3c;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px 0 8px;
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #4a4a4a;
            border: 1px solid #666666;
            border-radius: 4px;
            padding: 6px 12px;
            color: #ffffff;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #5a5a5a;
            border-color: #777777;
        }
        
        QPushButton:pressed {
            background-color: #3a3a3a;
            border-color: #555555;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            border-color: #444444;
            color: #666666;
        }
        
        QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px 8px;
            color: #ffffff;
        }
        
        QComboBox::drop-down {
            border: none;
            background-color: #4a4a4a;
        }
        
        QComboBox::down-arrow {
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iNiIgdmlld0JveD0iMCAwIDEwIDYiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNSA1TDkgMSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
        }
        
        QSlider::groove:horizontal {
            background: #3c3c3c;
            height: 8px;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background: #0078d4;
            border: 1px solid #005a9e;
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        
        QSlider::handle:horizontal:hover {
            background: #106ebe;
        }
        
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #555555;
            border-radius: 2px;
            background-color: #3c3c3c;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border-color: #005a9e;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            padding: 4px;
        }
        
        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            padding: 4px 8px;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            padding: 4px 8px;
        }
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 3px;
        }
        """
    
    def get_light_theme_stylesheet(self) -> str:
        """Get light theme stylesheet."""
        return """
        QWidget {
            background-color: #ffffff;
            color: #000000;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: #f5f5f5;
        }
        
        QPushButton {
            background-color: #e1e1e1;
            border: 1px solid #adadad;
            border-radius: 4px;
            padding: 6px 12px;
            color: #000000;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #d1d1d1;
        }
        
        QPushButton:pressed {
            background-color: #c1c1c1;
        }
        """
    
    # Abstract methods (to be implemented by subclasses)
    def _create_widget(self) -> QWidget:
        """Create the main widget. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _create_widget")
    
    def _setup_widget(self) -> None:
        """Setup widget after creation. Override in subclasses."""
        self._apply_theme()
        self._apply_stylesheet()
        self._update_widget_state()
    
    def _update_widget_state(self) -> None:
        """Update widget based on current state. Override in subclasses."""
        pass
    
    def _apply_theme(self) -> None:
        """Apply current theme to widget."""
        if self._widget:
            if self._theme == "dark":
                self._widget.setStyleSheet(self.get_dark_theme_stylesheet())
            elif self._theme == "light":
                self._widget.setStyleSheet(self.get_light_theme_stylesheet())
    
    def _apply_stylesheet(self) -> None:
        """Apply custom stylesheet to widget."""
        if self._widget and self._custom_stylesheet:
            current_style = self._widget.styleSheet()
            self._widget.setStyleSheet(current_style + "\n" + self._custom_stylesheet)


# Re-export for convenience
UIProtocol = UIProtocol