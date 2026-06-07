"""
Professional Dark Theme System

Provides sophisticated dark theme styling for annotation interfaces.
Replicates ABILIUS professional appearance with modern enhancements.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import QWidget, QApplication
    from PyQt5.QtCore import QObject, pyqtSignal
    from PyQt5.QtGui import QColor, QPalette
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QObject: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ThemeColor(Enum):
    """Professional dark theme color palette."""
    # Primary colors
    PRIMARY_DARK = "#1a1a1a"
    PRIMARY_MEDIUM = "#2d2d2d"
    PRIMARY_LIGHT = "#3d3d3d"
    
    # Accent colors
    ACCENT_BLUE = "#3b82f6"
    ACCENT_BLUE_HOVER = "#2563eb"
    ACCENT_BLUE_PRESSED = "#1d4ed8"
    
    # Status colors
    SUCCESS_GREEN = "#10b981"
    WARNING_ORANGE = "#f59e0b"
    ERROR_RED = "#ef4444"
    INFO_CYAN = "#06b6d4"
    
    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#d1d5db"
    TEXT_MUTED = "#9ca3af"
    TEXT_DISABLED = "#6b7280"
    
    # Border colors
    BORDER_PRIMARY = "#404040"
    BORDER_SECONDARY = "#333333"
    BORDER_HOVER = "#525252"
    
    # Background colors
    BG_CANVAS = "#0f0f0f"
    BG_PANEL = "#262626"
    BG_CARD = "#1f1f1f"
    BG_INPUT = "#171717"
    
    # Overlay colors
    OVERLAY_LIGHT = "rgba(255, 255, 255, 0.1)"
    OVERLAY_MEDIUM = "rgba(255, 255, 255, 0.2)"
    OVERLAY_HEAVY = "rgba(0, 0, 0, 0.7)"


@dataclass
class ThemeMetrics:
    """Theme spacing and sizing metrics."""
    # Border radius
    radius_small: int = 4
    radius_medium: int = 6
    radius_large: int = 8
    radius_xl: int = 12
    
    # Spacing
    spacing_xs: int = 2
    spacing_sm: int = 4
    spacing_md: int = 8
    spacing_lg: int = 12
    spacing_xl: int = 16
    spacing_2xl: int = 24
    
    # Shadows
    shadow_sm: str = "0 1px 2px rgba(0, 0, 0, 0.1)"
    shadow_md: str = "0 4px 6px rgba(0, 0, 0, 0.1)"
    shadow_lg: str = "0 10px 15px rgba(0, 0, 0, 0.1)"
    
    # Animation
    transition_fast: str = "150ms ease"
    transition_normal: str = "250ms ease"
    transition_slow: str = "350ms ease"


class ProfessionalDarkTheme(QObject):
    """
    Professional dark theme system for annotation interfaces.
    
    Features:
    - ABILIUS-inspired professional styling
    - Consistent color palette and metrics
    - Component-specific styles
    - High contrast for accessibility
    - Customizable accent colors
    """
    
    theme_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.colors = ThemeColor
        self.metrics = ThemeMetrics()
        self._custom_colors = {}
        self._component_styles = {}
        self._initialize_component_styles()
    
    def _initialize_component_styles(self):
        """Initialize component-specific styles."""
        
        # Annotation canvas styles
        self._component_styles['annotation_canvas'] = f"""
            QWidget {{
                background-color: {self.colors.BG_CANVAS.value};
                border: 1px solid {self.colors.BORDER_SECONDARY.value};
            }}
        """
        
        # Tool panel styles
        self._component_styles['tool_panel'] = f"""
            QWidget {{
                background-color: {self.colors.PRIMARY_MEDIUM.value};
                border: 1px solid {self.colors.BORDER_PRIMARY.value};
                border-radius: {self.metrics.radius_medium}px;
            }}
            
            QLabel {{
                color: {self.colors.TEXT_PRIMARY.value};
                font-weight: bold;
                padding: {self.metrics.spacing_sm}px;
            }}
        """
        
        # Modern button styles
        self._component_styles['modern_button'] = f"""
            QPushButton {{
                background-color: {self.colors.PRIMARY_LIGHT.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border: 1px solid {self.colors.BORDER_PRIMARY.value};
                border-radius: {self.metrics.radius_medium}px;
                padding: {self.metrics.spacing_md}px {self.metrics.spacing_lg}px;
                font-weight: 500;
                transition: all {self.metrics.transition_fast};
            }}
            
            QPushButton:hover {{
                background-color: {self.colors.ACCENT_BLUE.value};
                border-color: {self.colors.ACCENT_BLUE_HOVER.value};
                color: {self.colors.TEXT_PRIMARY.value};
            }}
            
            QPushButton:pressed {{
                background-color: {self.colors.ACCENT_BLUE_PRESSED.value};
                border-color: {self.colors.ACCENT_BLUE_PRESSED.value};
            }}
            
            QPushButton:disabled {{
                background-color: {self.colors.PRIMARY_DARK.value};
                color: {self.colors.TEXT_DISABLED.value};
                border-color: {self.colors.BORDER_SECONDARY.value};
            }}
        """
        
        # Primary action button
        self._component_styles['primary_button'] = f"""
            QPushButton {{
                background-color: {self.colors.ACCENT_BLUE.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border: none;
                border-radius: {self.metrics.radius_medium}px;
                padding: {self.metrics.spacing_md}px {self.metrics.spacing_xl}px;
                font-weight: 600;
                transition: all {self.metrics.transition_fast};
            }}
            
            QPushButton:hover {{
                background-color: {self.colors.ACCENT_BLUE_HOVER.value};
            }}
            
            QPushButton:pressed {{
                background-color: {self.colors.ACCENT_BLUE_PRESSED.value};
            }}
        """
        
        # Sidebar panel styles
        self._component_styles['sidebar_panel'] = f"""
            QWidget {{
                background-color: {self.colors.PRIMARY_MEDIUM.value};
                border-right: 1px solid {self.colors.BORDER_PRIMARY.value};
            }}
            
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            
            QScrollBar:vertical {{
                background-color: {self.colors.PRIMARY_DARK.value};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.colors.PRIMARY_LIGHT.value};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors.BORDER_HOVER.value};
            }}
        """
        
        # Info card styles
        self._component_styles['info_card'] = f"""
            QFrame {{
                background-color: {self.colors.BG_CARD.value};
                border: 1px solid {self.colors.BORDER_PRIMARY.value};
                border-radius: {self.metrics.radius_medium}px;
                padding: {self.metrics.spacing_lg}px;
            }}
            
            QLabel {{
                color: {self.colors.TEXT_SECONDARY.value};
                padding: {self.metrics.spacing_xs}px 0px;
            }}
        """
        
        # Form input styles
        self._component_styles['form_input'] = f"""
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {self.colors.BG_INPUT.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border: 1px solid {self.colors.BORDER_SECONDARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: {self.metrics.spacing_md}px;
                font-size: 13px;
            }}
            
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border-color: {self.colors.ACCENT_BLUE.value};
                background-color: {self.colors.PRIMARY_DARK.value};
            }}
            
            QComboBox::drop-down {{
                border: none;
                padding-right: {self.metrics.spacing_md}px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {self.colors.TEXT_SECONDARY.value};
            }}
        """
        
        # Status indicator styles
        self._component_styles['status_indicator'] = f"""
            .status-success {{
                background-color: {self.colors.SUCCESS_GREEN.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: {self.metrics.spacing_xs}px {self.metrics.spacing_sm}px;
                font-size: 11px;
                font-weight: 600;
            }}
            
            .status-warning {{
                background-color: {self.colors.WARNING_ORANGE.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: {self.metrics.spacing_xs}px {self.metrics.spacing_sm}px;
                font-size: 11px;
                font-weight: 600;
            }}
            
            .status-error {{
                background-color: {self.colors.ERROR_RED.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: {self.metrics.spacing_xs}px {self.metrics.spacing_sm}px;
                font-size: 11px;
                font-weight: 600;
            }}
        """
        
        # Progress bar styles
        self._component_styles['progress_bar'] = f"""
            QProgressBar {{
                background-color: {self.colors.PRIMARY_DARK.value};
                border: 1px solid {self.colors.BORDER_SECONDARY.value};
                border-radius: {self.metrics.radius_small}px;
                text-align: center;
                color: {self.colors.TEXT_PRIMARY.value};
                font-weight: 500;
            }}
            
            QProgressBar::chunk {{
                background-color: {self.colors.ACCENT_BLUE.value};
                border-radius: {self.metrics.radius_small}px;
            }}
        """
        
        # Tooltip styles
        self._component_styles['tooltip'] = f"""
            QToolTip {{
                background-color: {self.colors.PRIMARY_DARK.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border: 1px solid {self.colors.BORDER_PRIMARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: {self.metrics.spacing_sm}px {self.metrics.spacing_md}px;
                font-size: 12px;
            }}
        """
    
    def get_color(self, color_name: str) -> str:
        """Get a color value by name."""
        try:
            return self.colors[color_name.upper()].value
        except KeyError:
            return self._custom_colors.get(color_name, "#ffffff")
    
    def set_custom_color(self, name: str, value: str):
        """Set a custom color value."""
        self._custom_colors[name] = value
        self.theme_changed.emit()
    
    def get_component_style(self, component_name: str) -> str:
        """Get the stylesheet for a specific component."""
        return self._component_styles.get(component_name, "")
    
    def get_full_stylesheet(self) -> str:
        """Get the complete application stylesheet."""
        base_style = f"""
            /* Global application styles */
            QMainWindow {{
                background-color: {self.colors.PRIMARY_DARK.value};
                color: {self.colors.TEXT_PRIMARY.value};
            }}
            
            QWidget {{
                background-color: {self.colors.PRIMARY_DARK.value};
                color: {self.colors.TEXT_PRIMARY.value};
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }}
            
            /* Menu and status bar */
            QMenuBar {{
                background-color: {self.colors.PRIMARY_MEDIUM.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border-bottom: 1px solid {self.colors.BORDER_PRIMARY.value};
                padding: 2px;
            }}
            
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 8px;
                border-radius: {self.metrics.radius_small}px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {self.colors.ACCENT_BLUE.value};
            }}
            
            QMenu {{
                background-color: {self.colors.PRIMARY_MEDIUM.value};
                color: {self.colors.TEXT_PRIMARY.value};
                border: 1px solid {self.colors.BORDER_PRIMARY.value};
                border-radius: {self.metrics.radius_small}px;
                padding: 4px;
            }}
            
            QMenu::item {{
                padding: 6px 12px;
                border-radius: {self.metrics.radius_small}px;
            }}
            
            QMenu::item:selected {{
                background-color: {self.colors.ACCENT_BLUE.value};
            }}
            
            QStatusBar {{
                background-color: {self.colors.PRIMARY_MEDIUM.value};
                color: {self.colors.TEXT_SECONDARY.value};
                border-top: 1px solid {self.colors.BORDER_PRIMARY.value};
            }}
        """
        
        # Combine with all component styles
        combined_style = base_style
        for style in self._component_styles.values():
            combined_style += "\n" + style
        
        return combined_style
    
    def apply_to_widget(self, widget: 'QWidget', component_type: str = None):
        """Apply theme to a specific widget."""
        if not PYQT5_AVAILABLE:
            return
            
        if component_type and component_type in self._component_styles:
            widget.setStyleSheet(self._component_styles[component_type])
        else:
            # Apply base theme
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {self.colors.PRIMARY_DARK.value};
                    color: {self.colors.TEXT_PRIMARY.value};
                    font-family: "Segoe UI", Arial, sans-serif;
                }}
            """)
    
    def apply_to_application(self, app: 'QApplication'):
        """Apply theme to the entire application."""
        if not PYQT5_AVAILABLE:
            return
            
        app.setStyleSheet(self.get_full_stylesheet())
        
        # Set application palette for native widgets
        palette = app.palette()
        palette.setColor(QPalette.Window, QColor(self.colors.PRIMARY_DARK.value))
        palette.setColor(QPalette.WindowText, QColor(self.colors.TEXT_PRIMARY.value))
        palette.setColor(QPalette.Base, QColor(self.colors.BG_INPUT.value))
        palette.setColor(QPalette.AlternateBase, QColor(self.colors.PRIMARY_MEDIUM.value))
        palette.setColor(QPalette.ToolTipBase, QColor(self.colors.PRIMARY_DARK.value))
        palette.setColor(QPalette.ToolTipText, QColor(self.colors.TEXT_PRIMARY.value))
        palette.setColor(QPalette.Text, QColor(self.colors.TEXT_PRIMARY.value))
        palette.setColor(QPalette.Button, QColor(self.colors.PRIMARY_LIGHT.value))
        palette.setColor(QPalette.ButtonText, QColor(self.colors.TEXT_PRIMARY.value))
        palette.setColor(QPalette.BrightText, QColor(self.colors.TEXT_PRIMARY.value))
        palette.setColor(QPalette.Link, QColor(self.colors.ACCENT_BLUE.value))
        palette.setColor(QPalette.Highlight, QColor(self.colors.ACCENT_BLUE.value))
        palette.setColor(QPalette.HighlightedText, QColor(self.colors.TEXT_PRIMARY.value))
        
        app.setPalette(palette)
    
    def create_status_label(self, text: str, status_type: str = "info") -> str:
        """Create HTML for a styled status label."""
        color_map = {
            "success": self.colors.SUCCESS_GREEN.value,
            "warning": self.colors.WARNING_ORANGE.value,
            "error": self.colors.ERROR_RED.value,
            "info": self.colors.INFO_CYAN.value
        }
        
        color = color_map.get(status_type, self.colors.INFO_CYAN.value)
        
        return f"""
            <span style="
                background-color: {color};
                color: {self.colors.TEXT_PRIMARY.value};
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
            ">{text}</span>
        """
    
    def get_accent_variants(self) -> Dict[str, str]:
        """Get accent color variants for different states."""
        return {
            "normal": self.colors.ACCENT_BLUE.value,
            "hover": self.colors.ACCENT_BLUE_HOVER.value,
            "pressed": self.colors.ACCENT_BLUE_PRESSED.value,
            "disabled": self.colors.TEXT_DISABLED.value
        }


# Global theme instance
theme = ProfessionalDarkTheme()


def get_theme() -> ProfessionalDarkTheme:
    """Get the global theme instance."""
    return theme


def apply_theme_to_app(app: 'QApplication'):
    """Apply the professional dark theme to the application."""
    theme.apply_to_application(app)


def main():
    """Test the professional dark theme."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
        QWidget, QPushButton, QLabel, QLineEdit, QProgressBar
    )
    
    app = QApplication(sys.argv)
    
    # Apply theme
    apply_theme_to_app(app)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Professional Dark Theme Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Central widget
    central_widget = QWidget()
    layout = QVBoxLayout()
    
    # Test components
    title = QLabel("Professional Dark Theme Demo")
    title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 16px;")
    
    # Button row
    button_layout = QHBoxLayout()
    
    primary_btn = QPushButton("Primary Action")
    theme.apply_to_widget(primary_btn, "primary_button")
    
    secondary_btn = QPushButton("Secondary Action")
    theme.apply_to_widget(secondary_btn, "modern_button")
    
    button_layout.addWidget(primary_btn)
    button_layout.addWidget(secondary_btn)
    button_layout.addStretch()
    
    # Input field
    input_field = QLineEdit("Sample input field")
    theme.apply_to_widget(input_field, "form_input")
    
    # Progress bar
    progress = QProgressBar()
    progress.setValue(65)
    theme.apply_to_widget(progress, "progress_bar")
    
    # Status labels
    status_layout = QHBoxLayout()
    
    success_label = QLabel(theme.create_status_label("Success", "success"))
    warning_label = QLabel(theme.create_status_label("Warning", "warning"))
    error_label = QLabel(theme.create_status_label("Error", "error"))
    info_label = QLabel(theme.create_status_label("Info", "info"))
    
    for label in [success_label, warning_label, error_label, info_label]:
        label.setWordWrap(True)
        status_layout.addWidget(label)
    
    status_layout.addStretch()
    
    # Add to layout
    layout.addWidget(title)
    layout.addLayout(button_layout)
    layout.addWidget(input_field)
    layout.addWidget(progress)
    layout.addLayout(status_layout)
    layout.addStretch()
    
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    
    window.show()
    
    # Print color palette
    print("Professional Dark Theme Color Palette:")
    for color in ThemeColor:
        print(f"  {color.name}: {color.value}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()