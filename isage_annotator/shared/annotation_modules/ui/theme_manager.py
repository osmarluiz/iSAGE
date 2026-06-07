"""
Theme Manager - Centralized theme management for UI components

This module provides centralized theme management with support for light/dark themes,
custom color schemes, and dynamic theme switching.
"""

import json
import os
from typing import Dict, Any, List, Optional, Callable
from ..base_protocols import BaseComponent, QColor
from .base_ui import BaseUI


class ThemeManager(BaseUI):
    """Centralized theme management system."""
    
    # Theme manager signals
    themeChanged = pyqtSignal(str)  # theme_name
    themeLoaded = pyqtSignal(str)  # theme_name
    themeSaved = pyqtSignal(str)  # theme_name
    colorSchemeChanged = pyqtSignal(str)  # scheme_name
    
    def __init__(self, name: str = "theme_manager", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Theme configuration
        self._current_theme: str = "light"
        self._themes: Dict[str, Dict[str, Any]] = {}
        self._theme_callbacks: List[Callable[[str], None]] = []
        
        # Theme directory
        self._theme_directory: Optional[str] = None
        self._auto_save: bool = True
        
        # Default themes
        self._default_themes: Dict[str, Dict[str, Any]] = {
            'light': {
                'name': 'Light',
                'description': 'Default light theme',
                'colors': {
                    # Base colors
                    'background': '#ffffff',
                    'foreground': '#000000',
                    'text': '#000000',
                    'text_secondary': '#666666',
                    'text_disabled': '#999999',
                    
                    # UI elements
                    'border': '#c0c0c0',
                    'border_focus': '#4a90e2',
                    'border_disabled': '#e0e0e0',
                    
                    # Buttons
                    'button_background': '#f0f0f0',
                    'button_hover': '#e0e0e0',
                    'button_pressed': '#d0d0d0',
                    'button_selected': '#4a90e2',
                    'button_disabled': '#f8f8f8',
                    
                    # Input fields
                    'input_background': '#ffffff',
                    'input_border': '#c0c0c0',
                    'input_focus': '#4a90e2',
                    'input_disabled': '#f8f8f8',
                    
                    # Progress bars
                    'progress_background': '#f0f0f0',
                    'progress_chunk': '#4a90e2',
                    'progress_text': '#000000',
                    
                    # Status colors
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'error': '#dc3545',
                    'info': '#17a2b8',
                    
                    # Annotation colors
                    'annotation_point': '#ff0000',
                    'annotation_selected': '#ff6600',
                    'annotation_hover': '#ff9900',
                    'annotation_background': '#ffffff',
                    
                    # Overlay colors
                    'overlay_prediction': '#4a90e2',
                    'overlay_ground_truth': '#28a745',
                    'overlay_mistake': '#dc3545',
                    
                    # Panel colors
                    'panel_background': '#f8f8f8',
                    'panel_border': '#c0c0c0',
                    'panel_header': '#e0e0e0',
                    
                    # Canvas colors
                    'canvas_background': '#ffffff',
                    'canvas_grid': '#f0f0f0',
                    'canvas_crosshair': '#666666',
                    
                    # Minimap colors
                    'minimap_background': '#f0f0f0',
                    'minimap_border': '#c0c0c0',
                    'minimap_viewport': '#4a90e2',
                    
                    # Scrollbar colors
                    'scrollbar_background': '#f0f0f0',
                    'scrollbar_handle': '#c0c0c0',
                    'scrollbar_hover': '#a0a0a0'
                }
            },
            'dark': {
                'name': 'Dark',
                'description': 'Default dark theme',
                'colors': {
                    # Base colors
                    'background': '#2b2b2b',
                    'foreground': '#ffffff',
                    'text': '#ffffff',
                    'text_secondary': '#cccccc',
                    'text_disabled': '#666666',
                    
                    # UI elements
                    'border': '#555555',
                    'border_focus': '#4a90e2',
                    'border_disabled': '#444444',
                    
                    # Buttons
                    'button_background': '#3c3c3c',
                    'button_hover': '#4c4c4c',
                    'button_pressed': '#5c5c5c',
                    'button_selected': '#4a90e2',
                    'button_disabled': '#2a2a2a',
                    
                    # Input fields
                    'input_background': '#3c3c3c',
                    'input_border': '#555555',
                    'input_focus': '#4a90e2',
                    'input_disabled': '#2a2a2a',
                    
                    # Progress bars
                    'progress_background': '#3c3c3c',
                    'progress_chunk': '#4a90e2',
                    'progress_text': '#ffffff',
                    
                    # Status colors
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'error': '#dc3545',
                    'info': '#17a2b8',
                    
                    # Annotation colors
                    'annotation_point': '#ff4444',
                    'annotation_selected': '#ff6600',
                    'annotation_hover': '#ff9900',
                    'annotation_background': '#2b2b2b',
                    
                    # Overlay colors
                    'overlay_prediction': '#4a90e2',
                    'overlay_ground_truth': '#28a745',
                    'overlay_mistake': '#dc3545',
                    
                    # Panel colors
                    'panel_background': '#353535',
                    'panel_border': '#555555',
                    'panel_header': '#404040',
                    
                    # Canvas colors
                    'canvas_background': '#2b2b2b',
                    'canvas_grid': '#404040',
                    'canvas_crosshair': '#cccccc',
                    
                    # Minimap colors
                    'minimap_background': '#353535',
                    'minimap_border': '#555555',
                    'minimap_viewport': '#4a90e2',
                    
                    # Scrollbar colors
                    'scrollbar_background': '#3c3c3c',
                    'scrollbar_handle': '#555555',
                    'scrollbar_hover': '#777777'
                }
            }
        }
        
        # Color schemes
        self._color_schemes: Dict[str, Dict[str, str]] = {
            'blue': {
                'primary': '#4a90e2',
                'secondary': '#357abd',
                'accent': '#5ba0f2'
            },
            'green': {
                'primary': '#28a745',
                'secondary': '#1e7e34',
                'accent': '#34ce57'
            },
            'purple': {
                'primary': '#6f42c1',
                'secondary': '#59359a',
                'accent': '#7952b3'
            },
            'orange': {
                'primary': '#fd7e14',
                'secondary': '#e8650e',
                'accent': '#ff922b'
            }
        }
        
        self._current_color_scheme: str = "blue"
        
        # Initialize with default themes
        self._themes = self._default_themes.copy()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize theme manager."""
        self._theme_directory = kwargs.get('theme_directory', None)
        self._auto_save = kwargs.get('auto_save', True)
        self._current_theme = kwargs.get('default_theme', 'light')
        self._current_color_scheme = kwargs.get('default_color_scheme', 'blue')
        
        # Load themes from directory
        if self._theme_directory:
            self._load_themes_from_directory()
        
        # Apply current theme
        self._apply_current_theme()
        
        return super().initialize(**kwargs)
    
    def get_available_themes(self) -> List[str]:
        """Get list of available themes."""
        return list(self._themes.keys())
    
    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme
    
    def get_theme_info(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Get theme information."""
        return self._themes.get(theme_name)
    
    def set_theme(self, theme_name: str) -> bool:
        """Set active theme."""
        try:
            if theme_name not in self._themes:
                self.emit_error(f"Theme not found: {theme_name}")
                return False
            
            self._current_theme = theme_name
            self._apply_current_theme()
            
            # Save if auto save enabled
            if self._auto_save:
                self._save_current_settings()
            
            self.themeChanged.emit(theme_name)
            self.emit_state_changed({'current_theme': theme_name})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting theme: {str(e)}")
            return False
    
    def get_color(self, color_name: str, theme_name: Optional[str] = None) -> Optional[QColor]:
        """Get color from theme."""
        try:
            if theme_name is None:
                theme_name = self._current_theme
            
            theme = self._themes.get(theme_name)
            if not theme:
                return None
            
            color_value = theme.get('colors', {}).get(color_name)
            if not color_value:
                return None
            
            # Apply color scheme if needed
            if color_name in ['button_selected', 'border_focus', 'input_focus', 'progress_chunk']:
                scheme = self._color_schemes.get(self._current_color_scheme, {})
                if 'primary' in scheme:
                    color_value = scheme['primary']
            
            return QColor(color_value)
            
        except Exception as e:
            self.emit_error(f"Error getting color: {str(e)}")
            return None
    
    def get_color_hex(self, color_name: str, theme_name: Optional[str] = None) -> Optional[str]:
        """Get color as hex string."""
        try:
            color = self.get_color(color_name, theme_name)
            if color:
                return color.name()
            return None
            
        except Exception as e:
            self.emit_error(f"Error getting color hex: {str(e)}")
            return None
    
    def get_all_colors(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """Get all colors from theme."""
        try:
            if theme_name is None:
                theme_name = self._current_theme
            
            theme = self._themes.get(theme_name)
            if not theme:
                return {}
            
            colors = theme.get('colors', {}).copy()
            
            # Apply color scheme
            scheme = self._color_schemes.get(self._current_color_scheme, {})
            if scheme:
                for color_name in ['button_selected', 'border_focus', 'input_focus', 'progress_chunk']:
                    if color_name in colors and 'primary' in scheme:
                        colors[color_name] = scheme['primary']
            
            return colors
            
        except Exception as e:
            self.emit_error(f"Error getting all colors: {str(e)}")
            return {}
    
    def create_theme(self, theme_name: str, theme_data: Dict[str, Any]) -> bool:
        """Create new theme."""
        try:
            # Validate theme data
            if not self._validate_theme_data(theme_data):
                self.emit_error("Invalid theme data")
                return False
            
            self._themes[theme_name] = theme_data
            
            # Save to file if directory is set
            if self._theme_directory:
                self._save_theme_to_file(theme_name, theme_data)
            
            self.emit_state_changed({'themes_count': len(self._themes)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating theme: {str(e)}")
            return False
    
    def modify_theme(self, theme_name: str, modifications: Dict[str, Any]) -> bool:
        """Modify existing theme."""
        try:
            if theme_name not in self._themes:
                self.emit_error(f"Theme not found: {theme_name}")
                return False
            
            theme = self._themes[theme_name]
            
            # Apply modifications
            for key, value in modifications.items():
                if key == 'colors':
                    theme['colors'].update(value)
                else:
                    theme[key] = value
            
            # Save to file if directory is set
            if self._theme_directory:
                self._save_theme_to_file(theme_name, theme)
            
            # Re-apply theme if it's current
            if theme_name == self._current_theme:
                self._apply_current_theme()
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error modifying theme: {str(e)}")
            return False
    
    def delete_theme(self, theme_name: str) -> bool:
        """Delete theme."""
        try:
            if theme_name not in self._themes:
                return False
            
            # Cannot delete default themes
            if theme_name in self._default_themes:
                self.emit_error("Cannot delete default theme")
                return False
            
            # Cannot delete current theme
            if theme_name == self._current_theme:
                self.emit_error("Cannot delete current theme")
                return False
            
            del self._themes[theme_name]
            
            # Delete file if exists
            if self._theme_directory:
                theme_file = os.path.join(self._theme_directory, f"{theme_name}.json")
                if os.path.exists(theme_file):
                    os.remove(theme_file)
            
            self.emit_state_changed({'themes_count': len(self._themes)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error deleting theme: {str(e)}")
            return False
    
    def get_available_color_schemes(self) -> List[str]:
        """Get available color schemes."""
        return list(self._color_schemes.keys())
    
    def get_current_color_scheme(self) -> str:
        """Get current color scheme."""
        return self._current_color_scheme
    
    def set_color_scheme(self, scheme_name: str) -> bool:
        """Set color scheme."""
        try:
            if scheme_name not in self._color_schemes:
                self.emit_error(f"Color scheme not found: {scheme_name}")
                return False
            
            self._current_color_scheme = scheme_name
            self._apply_current_theme()  # Re-apply theme with new scheme
            
            # Save if auto save enabled
            if self._auto_save:
                self._save_current_settings()
            
            self.colorSchemeChanged.emit(scheme_name)
            self.emit_state_changed({'current_color_scheme': scheme_name})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting color scheme: {str(e)}")
            return False
    
    def add_color_scheme(self, scheme_name: str, colors: Dict[str, str]) -> bool:
        """Add custom color scheme."""
        try:
            self._color_schemes[scheme_name] = colors
            self.emit_state_changed({'color_schemes_count': len(self._color_schemes)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error adding color scheme: {str(e)}")
            return False
    
    def register_theme_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for theme changes."""
        if callback not in self._theme_callbacks:
            self._theme_callbacks.append(callback)
    
    def unregister_theme_callback(self, callback: Callable[[str], None]) -> None:
        """Unregister theme callback."""
        if callback in self._theme_callbacks:
            self._theme_callbacks.remove(callback)
    
    def generate_stylesheet(self, component_type: str, theme_name: Optional[str] = None) -> str:
        """Generate CSS stylesheet for component."""
        try:
            colors = self.get_all_colors(theme_name)
            
            if component_type == 'button':
                return f"""
                    QPushButton {{
                        background-color: {colors['button_background']};
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
                        background-color: {colors['button_disabled']};
                        color: {colors['text_disabled']};
                    }}
                """
            
            elif component_type == 'input':
                return f"""
                    QLineEdit, QSpinBox, QComboBox {{
                        background-color: {colors['input_background']};
                        color: {colors['text']};
                        border: 1px solid {colors['input_border']};
                        border-radius: 4px;
                        padding: 4px;
                        min-height: 20px;
                    }}
                    
                    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                        border: 2px solid {colors['input_focus']};
                    }}
                    
                    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
                        background-color: {colors['input_disabled']};
                        color: {colors['text_disabled']};
                    }}
                """
            
            elif component_type == 'panel':
                return f"""
                    QWidget {{
                        background-color: {colors['panel_background']};
                        color: {colors['text']};
                        border: 1px solid {colors['panel_border']};
                    }}
                    
                    QGroupBox {{
                        background-color: {colors['panel_background']};
                        border: 1px solid {colors['panel_border']};
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
                """
            
            elif component_type == 'progress':
                return f"""
                    QProgressBar {{
                        background-color: {colors['progress_background']};
                        border: 1px solid {colors['border']};
                        border-radius: 4px;
                        text-align: center;
                        color: {colors['progress_text']};
                        height: 20px;
                    }}
                    
                    QProgressBar::chunk {{
                        background-color: {colors['progress_chunk']};
                        border-radius: 3px;
                    }}
                """
            
            return ""
            
        except Exception as e:
            self.emit_error(f"Error generating stylesheet: {str(e)}")
            return ""
    
    def export_theme(self, theme_name: str, file_path: str) -> bool:
        """Export theme to file."""
        try:
            if theme_name not in self._themes:
                return False
            
            theme_data = self._themes[theme_name]
            
            with open(file_path, 'w') as f:
                json.dump(theme_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error exporting theme: {str(e)}")
            return False
    
    def import_theme(self, file_path: str) -> Optional[str]:
        """Import theme from file."""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                theme_data = json.load(f)
            
            if not self._validate_theme_data(theme_data):
                self.emit_error("Invalid theme file")
                return None
            
            theme_name = theme_data.get('name', os.path.splitext(os.path.basename(file_path))[0])
            
            # Avoid name conflicts
            original_name = theme_name
            counter = 1
            while theme_name in self._themes:
                theme_name = f"{original_name}_{counter}"
                counter += 1
            
            self._themes[theme_name] = theme_data
            
            self.themeLoaded.emit(theme_name)
            self.emit_state_changed({'themes_count': len(self._themes)})
            
            return theme_name
            
        except Exception as e:
            self.emit_error(f"Error importing theme: {str(e)}")
            return None
    
    def _validate_theme_data(self, theme_data: Dict[str, Any]) -> bool:
        """Validate theme data structure."""
        try:
            if not isinstance(theme_data, dict):
                return False
            
            # Check required fields
            if 'colors' not in theme_data:
                return False
            
            colors = theme_data['colors']
            if not isinstance(colors, dict):
                return False
            
            # Check for required color keys
            required_colors = ['background', 'text', 'border', 'button_background']
            for color_key in required_colors:
                if color_key not in colors:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _apply_current_theme(self) -> None:
        """Apply current theme to all registered components."""
        try:
            # Notify all registered callbacks
            for callback in self._theme_callbacks:
                try:
                    callback(self._current_theme)
                except Exception as e:
                    self.emit_error(f"Error in theme callback: {str(e)}")
            
        except Exception as e:
            self.emit_error(f"Error applying theme: {str(e)}")
    
    def _load_themes_from_directory(self) -> None:
        """Load themes from directory."""
        try:
            if not os.path.exists(self._theme_directory):
                os.makedirs(self._theme_directory)
                return
            
            for filename in os.listdir(self._theme_directory):
                if filename.endswith('.json'):
                    file_path = os.path.join(self._theme_directory, filename)
                    theme_name = os.path.splitext(filename)[0]
                    
                    try:
                        with open(file_path, 'r') as f:
                            theme_data = json.load(f)
                        
                        if self._validate_theme_data(theme_data):
                            self._themes[theme_name] = theme_data
                            
                    except Exception as e:
                        self.emit_error(f"Error loading theme {filename}: {str(e)}")
                        continue
            
        except Exception as e:
            self.emit_error(f"Error loading themes from directory: {str(e)}")
    
    def _save_theme_to_file(self, theme_name: str, theme_data: Dict[str, Any]) -> None:
        """Save theme to file."""
        try:
            if not self._theme_directory:
                return
            
            os.makedirs(self._theme_directory, exist_ok=True)
            
            file_path = os.path.join(self._theme_directory, f"{theme_name}.json")
            
            with open(file_path, 'w') as f:
                json.dump(theme_data, f, indent=2)
            
            self.themeSaved.emit(theme_name)
            
        except Exception as e:
            self.emit_error(f"Error saving theme to file: {str(e)}")
    
    def _save_current_settings(self) -> None:
        """Save current theme and color scheme settings."""
        try:
            if not self._theme_directory:
                return
            
            settings = {
                'current_theme': self._current_theme,
                'current_color_scheme': self._current_color_scheme
            }
            
            settings_file = os.path.join(self._theme_directory, 'settings.json')
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
        except Exception as e:
            self.emit_error(f"Error saving settings: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get theme manager statistics."""
        stats = super().get_statistics()
        stats.update({
            'current_theme': self._current_theme,
            'current_color_scheme': self._current_color_scheme,
            'themes_count': len(self._themes),
            'color_schemes_count': len(self._color_schemes),
            'theme_directory': self._theme_directory,
            'auto_save': self._auto_save,
            'callbacks_count': len(self._theme_callbacks),
            'available_themes': list(self._themes.keys()),
            'available_color_schemes': list(self._color_schemes.keys())
        })
        return stats