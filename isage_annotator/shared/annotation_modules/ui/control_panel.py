"""
Control Panel - Main control interface for annotation tools

This module provides the main control panel with tool selection, settings,
and action buttons for the annotation interface.
"""

import time
from typing import Dict, Any, List, Optional, Callable
from ..base_protocols import BaseComponent, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from ..base_protocols import QPushButton, QLabel, QSlider, QSpinBox, QCheckBox, QComboBox, QGroupBox
from .base_ui import BaseUI


class ControlPanel(BaseUI, QWidget):
    """Main control panel for annotation interface."""
    
    # Control panel signals
    toolSelected = pyqtSignal(str)  # tool_name
    settingChanged = pyqtSignal(str, object)  # setting_name, value
    actionTriggered = pyqtSignal(str)  # action_name
    panelToggled = pyqtSignal(bool)  # visible
    
    def __init__(self, name: str = "control_panel", version: str = "1.0.0", parent=None):
        BaseUI.__init__(self, name, version)
        QWidget.__init__(self, parent)
        
        # Panel configuration
        self._panel_width: int = 300
        self._panel_height: int = 600
        self._collapsible: bool = True
        self._collapsed: bool = False
        
        # Tool configuration
        self._available_tools: Dict[str, Dict[str, Any]] = {}
        self._current_tool: Optional[str] = None
        self._tool_buttons: Dict[str, QPushButton] = {}
        
        # Settings configuration
        self._settings: Dict[str, Any] = {}
        self._setting_widgets: Dict[str, QWidget] = {}
        
        # Actions configuration
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._action_buttons: Dict[str, QPushButton] = {}
        
        # Layout
        self._main_layout: QVBoxLayout = QVBoxLayout()
        self._tool_group: QGroupBox = QGroupBox("Tools")
        self._settings_group: QGroupBox = QGroupBox("Settings")
        self._actions_group: QGroupBox = QGroupBox("Actions")
        
        # Theme
        self._theme: str = "light"
        self._theme_colors: Dict[str, Dict[str, str]] = {
            'light': {
                'background': '#f0f0f0',
                'text': '#000000',
                'button': '#e0e0e0',
                'button_hover': '#d0d0d0',
                'button_pressed': '#c0c0c0',
                'button_selected': '#4a90e2',
                'border': '#c0c0c0',
                'group_background': '#fafafa'
            },
            'dark': {
                'background': '#2b2b2b',
                'text': '#ffffff',
                'button': '#3c3c3c',
                'button_hover': '#4c4c4c',
                'button_pressed': '#5c5c5c',
                'button_selected': '#4a90e2',
                'border': '#555555',
                'group_background': '#353535'
            }
        }
        
        # Initialize UI
        self._setup_ui()
        self._apply_theme()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize control panel."""
        self._panel_width = kwargs.get('panel_width', 300)
        self._panel_height = kwargs.get('panel_height', 600)
        self._collapsible = kwargs.get('collapsible', True)
        self._theme = kwargs.get('theme', 'light')
        
        # Set size
        self.setFixedSize(self._panel_width, self._panel_height)
        
        # Apply theme
        self._apply_theme()
        
        return super().initialize(**kwargs)
    
    def add_tool(self, tool_name: str, tool_config: Dict[str, Any]) -> None:
        """Add tool to control panel."""
        try:
            self._available_tools[tool_name] = tool_config
            
            # Create tool button
            button = QPushButton(tool_config.get('display_name', tool_name))
            button.setCheckable(True)
            button.setToolTip(tool_config.get('tooltip', ''))
            button.clicked.connect(lambda: self._on_tool_selected(tool_name))
            
            # Add to tool group
            tool_layout = self._tool_group.layout()
            if tool_layout is None:
                tool_layout = QVBoxLayout()
                self._tool_group.setLayout(tool_layout)
            
            tool_layout.addWidget(button)
            self._tool_buttons[tool_name] = button
            
            # Apply theme to button
            self._apply_button_theme(button)
            
            self.emit_state_changed({'tools_count': len(self._available_tools)})
            
        except Exception as e:
            self.emit_error(f"Error adding tool: {str(e)}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove tool from control panel."""
        try:
            if tool_name not in self._available_tools:
                return False
            
            # Remove button
            if tool_name in self._tool_buttons:
                button = self._tool_buttons[tool_name]
                button.setParent(None)
                del self._tool_buttons[tool_name]
            
            # Remove from available tools
            del self._available_tools[tool_name]
            
            # Update current tool if necessary
            if self._current_tool == tool_name:
                self._current_tool = None
            
            self.emit_state_changed({'tools_count': len(self._available_tools)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error removing tool: {str(e)}")
            return False
    
    def select_tool(self, tool_name: str) -> bool:
        """Select tool programmatically."""
        try:
            if tool_name not in self._available_tools:
                return False
            
            # Update button states
            for name, button in self._tool_buttons.items():
                button.setChecked(name == tool_name)
            
            # Update current tool
            self._current_tool = tool_name
            
            # Update settings for selected tool
            self._update_tool_settings(tool_name)
            
            self.toolSelected.emit(tool_name)
            self.emit_state_changed({'current_tool': tool_name})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error selecting tool: {str(e)}")
            return False
    
    def get_selected_tool(self) -> Optional[str]:
        """Get currently selected tool."""
        return self._current_tool
    
    def add_setting(self, setting_name: str, setting_config: Dict[str, Any]) -> None:
        """Add setting control to panel."""
        try:
            self._settings[setting_name] = setting_config
            
            # Create setting widget based on type
            widget = self._create_setting_widget(setting_name, setting_config)
            
            if widget:
                # Add to settings group
                settings_layout = self._settings_group.layout()
                if settings_layout is None:
                    settings_layout = QVBoxLayout()
                    self._settings_group.setLayout(settings_layout)
                
                # Create label if needed
                if 'label' in setting_config:
                    label = QLabel(setting_config['label'])
                    self._apply_label_theme(label)
                    settings_layout.addWidget(label)
                
                settings_layout.addWidget(widget)
                self._setting_widgets[setting_name] = widget
                
                # Apply theme
                self._apply_widget_theme(widget)
            
            self.emit_state_changed({'settings_count': len(self._settings)})
            
        except Exception as e:
            self.emit_error(f"Error adding setting: {str(e)}")
    
    def remove_setting(self, setting_name: str) -> bool:
        """Remove setting from panel."""
        try:
            if setting_name not in self._settings:
                return False
            
            # Remove widget
            if setting_name in self._setting_widgets:
                widget = self._setting_widgets[setting_name]
                widget.setParent(None)
                del self._setting_widgets[setting_name]
            
            # Remove from settings
            del self._settings[setting_name]
            
            self.emit_state_changed({'settings_count': len(self._settings)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error removing setting: {str(e)}")
            return False
    
    def get_setting_value(self, setting_name: str) -> Any:
        """Get setting value."""
        try:
            if setting_name not in self._setting_widgets:
                return None
            
            widget = self._setting_widgets[setting_name]
            return self._get_widget_value(widget)
            
        except Exception as e:
            self.emit_error(f"Error getting setting value: {str(e)}")
            return None
    
    def set_setting_value(self, setting_name: str, value: Any) -> bool:
        """Set setting value."""
        try:
            if setting_name not in self._setting_widgets:
                return False
            
            widget = self._setting_widgets[setting_name]
            return self._set_widget_value(widget, value)
            
        except Exception as e:
            self.emit_error(f"Error setting value: {str(e)}")
            return False
    
    def add_action(self, action_name: str, action_config: Dict[str, Any]) -> None:
        """Add action button to panel."""
        try:
            self._actions[action_name] = action_config
            
            # Create action button
            button = QPushButton(action_config.get('display_name', action_name))
            button.setToolTip(action_config.get('tooltip', ''))
            button.clicked.connect(lambda: self._on_action_triggered(action_name))
            
            # Set button properties
            if 'enabled' in action_config:
                button.setEnabled(action_config['enabled'])
            
            # Add to actions group
            actions_layout = self._actions_group.layout()
            if actions_layout is None:
                actions_layout = QVBoxLayout()
                self._actions_group.setLayout(actions_layout)
            
            actions_layout.addWidget(button)
            self._action_buttons[action_name] = button
            
            # Apply theme to button
            self._apply_button_theme(button)
            
            self.emit_state_changed({'actions_count': len(self._actions)})
            
        except Exception as e:
            self.emit_error(f"Error adding action: {str(e)}")
    
    def remove_action(self, action_name: str) -> bool:
        """Remove action from panel."""
        try:
            if action_name not in self._actions:
                return False
            
            # Remove button
            if action_name in self._action_buttons:
                button = self._action_buttons[action_name]
                button.setParent(None)
                del self._action_buttons[action_name]
            
            # Remove from actions
            del self._actions[action_name]
            
            self.emit_state_changed({'actions_count': len(self._actions)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error removing action: {str(e)}")
            return False
    
    def set_action_enabled(self, action_name: str, enabled: bool) -> bool:
        """Enable/disable action button."""
        try:
            if action_name not in self._action_buttons:
                return False
            
            button = self._action_buttons[action_name]
            button.setEnabled(enabled)
            
            # Update config
            self._actions[action_name]['enabled'] = enabled
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting action enabled: {str(e)}")
            return False
    
    def set_theme(self, theme: str) -> None:
        """Set UI theme."""
        if theme in self._theme_colors:
            self._theme = theme
            self._apply_theme()
            self.emit_state_changed({'theme': theme})
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self._theme
    
    def set_collapsed(self, collapsed: bool) -> None:
        """Set panel collapsed state."""
        if self._collapsible:
            self._collapsed = collapsed
            
            if collapsed:
                self.setFixedWidth(50)  # Collapsed width
            else:
                self.setFixedWidth(self._panel_width)
            
            self.panelToggled.emit(not collapsed)
            self.emit_state_changed({'collapsed': collapsed})
    
    def is_collapsed(self) -> bool:
        """Check if panel is collapsed."""
        return self._collapsed
    
    def toggle_collapsed(self) -> None:
        """Toggle panel collapsed state."""
        self.set_collapsed(not self._collapsed)
    
    def _setup_ui(self) -> None:
        """Setup UI layout."""
        try:
            # Set main layout
            self.setLayout(self._main_layout)
            
            # Add groups
            self._main_layout.addWidget(self._tool_group)
            self._main_layout.addWidget(self._settings_group)
            self._main_layout.addWidget(self._actions_group)
            
            # Add stretch
            self._main_layout.addStretch()
            
            # Set initial size
            self.setFixedSize(self._panel_width, self._panel_height)
            
        except Exception as e:
            self.emit_error(f"Error setting up UI: {str(e)}")
    
    def _apply_theme(self) -> None:
        """Apply theme to all UI elements."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            # Apply to main widget
            self.setStyleSheet(f"""
                ControlPanel {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                }}
                
                QGroupBox {{
                    background-color: {colors['group_background']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    margin: 8px 0px;
                    padding-top: 12px;
                    font-weight: bold;
                }}
                
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px 0 4px;
                }}
            """)
            
            # Apply to existing widgets
            for button in self._tool_buttons.values():
                self._apply_button_theme(button)
            
            for button in self._action_buttons.values():
                self._apply_button_theme(button)
            
            for widget in self._setting_widgets.values():
                self._apply_widget_theme(widget)
            
        except Exception as e:
            self.emit_error(f"Error applying theme: {str(e)}")
    
    def _apply_button_theme(self, button: QPushButton) -> None:
        """Apply theme to button."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['button']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: normal;
                    min-height: 20px;
                }}
                
                QPushButton:hover {{
                    background-color: {colors['button_hover']};
                }}
                
                QPushButton:pressed {{
                    background-color: {colors['button_pressed']};
                }}
                
                QPushButton:checked {{
                    background-color: {colors['button_selected']};
                    color: white;
                }}
                
                QPushButton:disabled {{
                    background-color: {colors['background']};
                    color: {colors['border']};
                }}
            """)
            
        except Exception as e:
            self.emit_error(f"Error applying button theme: {str(e)}")
    
    def _apply_label_theme(self, label: QLabel) -> None:
        """Apply theme to label."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text']};
                    font-weight: normal;
                    margin: 4px 0px;
                }}
            """)
            
        except Exception as e:
            self.emit_error(f"Error applying label theme: {str(e)}")
    
    def _apply_widget_theme(self, widget: QWidget) -> None:
        """Apply theme to widget."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            if isinstance(widget, QSlider):
                widget.setStyleSheet(f"""
                    QSlider::groove:horizontal {{
                        border: 1px solid {colors['border']};
                        height: 4px;
                        background: {colors['background']};
                        margin: 2px 0;
                        border-radius: 2px;
                    }}
                    
                    QSlider::handle:horizontal {{
                        background: {colors['button_selected']};
                        border: 1px solid {colors['border']};
                        width: 16px;
                        margin: -8px 0;
                        border-radius: 8px;
                    }}
                """)
            
            elif isinstance(widget, (QSpinBox, QComboBox)):
                widget.setStyleSheet(f"""
                    QSpinBox, QComboBox {{
                        background-color: {colors['background']};
                        color: {colors['text']};
                        border: 1px solid {colors['border']};
                        border-radius: 4px;
                        padding: 4px;
                        min-height: 20px;
                    }}
                    
                    QSpinBox:focus, QComboBox:focus {{
                        border: 2px solid {colors['button_selected']};
                    }}
                """)
            
            elif isinstance(widget, QCheckBox):
                widget.setStyleSheet(f"""
                    QCheckBox {{
                        color: {colors['text']};
                        spacing: 8px;
                    }}
                    
                    QCheckBox::indicator {{
                        width: 16px;
                        height: 16px;
                        border: 1px solid {colors['border']};
                        border-radius: 3px;
                        background-color: {colors['background']};
                    }}
                    
                    QCheckBox::indicator:checked {{
                        background-color: {colors['button_selected']};
                    }}
                """)
            
        except Exception as e:
            self.emit_error(f"Error applying widget theme: {str(e)}")
    
    def _create_setting_widget(self, setting_name: str, setting_config: Dict[str, Any]) -> Optional[QWidget]:
        """Create setting widget based on type."""
        try:
            setting_type = setting_config.get('type', 'text')
            
            if setting_type == 'slider':
                widget = QSlider(1)  # Qt.Horizontal
                widget.setMinimum(setting_config.get('min', 0))
                widget.setMaximum(setting_config.get('max', 100))
                widget.setValue(setting_config.get('default', 50))
                widget.valueChanged.connect(lambda v: self._on_setting_changed(setting_name, v))
                return widget
            
            elif setting_type == 'spinbox':
                widget = QSpinBox()
                widget.setMinimum(setting_config.get('min', 0))
                widget.setMaximum(setting_config.get('max', 100))
                widget.setValue(setting_config.get('default', 0))
                widget.valueChanged.connect(lambda v: self._on_setting_changed(setting_name, v))
                return widget
            
            elif setting_type == 'checkbox':
                widget = QCheckBox(setting_config.get('text', ''))
                widget.setChecked(setting_config.get('default', False))
                widget.toggled.connect(lambda v: self._on_setting_changed(setting_name, v))
                return widget
            
            elif setting_type == 'combobox':
                widget = QComboBox()
                items = setting_config.get('items', [])
                widget.addItems(items)
                default_index = setting_config.get('default', 0)
                if default_index < len(items):
                    widget.setCurrentIndex(default_index)
                widget.currentIndexChanged.connect(lambda i: self._on_setting_changed(setting_name, items[i] if i < len(items) else ''))
                return widget
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error creating setting widget: {str(e)}")
            return None
    
    def _get_widget_value(self, widget: QWidget) -> Any:
        """Get value from widget."""
        try:
            if isinstance(widget, QSlider):
                return widget.value()
            elif isinstance(widget, QSpinBox):
                return widget.value()
            elif isinstance(widget, QCheckBox):
                return widget.isChecked()
            elif isinstance(widget, QComboBox):
                return widget.currentText()
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error getting widget value: {str(e)}")
            return None
    
    def _set_widget_value(self, widget: QWidget, value: Any) -> bool:
        """Set value to widget."""
        try:
            if isinstance(widget, QSlider):
                widget.setValue(int(value))
                return True
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
                return True
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
                return True
            elif isinstance(widget, QComboBox):
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
                    return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error setting widget value: {str(e)}")
            return False
    
    def _update_tool_settings(self, tool_name: str) -> None:
        """Update settings for selected tool."""
        try:
            tool_config = self._available_tools.get(tool_name, {})
            tool_settings = tool_config.get('settings', {})
            
            # Show/hide settings based on tool
            for setting_name, widget in self._setting_widgets.items():
                if setting_name in tool_settings:
                    widget.setVisible(True)
                    # Update widget with tool-specific config
                    tool_setting = tool_settings[setting_name]
                    if 'default' in tool_setting:
                        self._set_widget_value(widget, tool_setting['default'])
                else:
                    widget.setVisible(False)
                    
        except Exception as e:
            self.emit_error(f"Error updating tool settings: {str(e)}")
    
    def _on_tool_selected(self, tool_name: str) -> None:
        """Handle tool selection."""
        try:
            self.select_tool(tool_name)
            
        except Exception as e:
            self.emit_error(f"Error handling tool selection: {str(e)}")
    
    def _on_setting_changed(self, setting_name: str, value: Any) -> None:
        """Handle setting change."""
        try:
            self.settingChanged.emit(setting_name, value)
            self.emit_state_changed({f'setting_{setting_name}': value})
            
        except Exception as e:
            self.emit_error(f"Error handling setting change: {str(e)}")
    
    def _on_action_triggered(self, action_name: str) -> None:
        """Handle action trigger."""
        try:
            self.actionTriggered.emit(action_name)
            self.emit_state_changed({f'action_{action_name}': time.time()})
            
        except Exception as e:
            self.emit_error(f"Error handling action trigger: {str(e)}")
    
    def get_panel_info(self) -> Dict[str, Any]:
        """Get control panel information."""
        return {
            'panel_size': (self._panel_width, self._panel_height),
            'collapsible': self._collapsible,
            'collapsed': self._collapsed,
            'theme': self._theme,
            'current_tool': self._current_tool,
            'tools_count': len(self._available_tools),
            'settings_count': len(self._settings),
            'actions_count': len(self._actions)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get control panel statistics."""
        stats = super().get_statistics()
        stats.update({
            'panel_width': self._panel_width,
            'panel_height': self._panel_height,
            'collapsible': self._collapsible,
            'collapsed': self._collapsed,
            'theme': self._theme,
            'available_tools': list(self._available_tools.keys()),
            'current_tool': self._current_tool,
            'available_settings': list(self._settings.keys()),
            'available_actions': list(self._actions.keys()),
            'panel_info': self.get_panel_info()
        })
        return stats