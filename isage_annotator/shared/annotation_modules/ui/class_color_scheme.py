"""
Class Color Scheme - Manages class colors and color schemes for annotation

This module provides color scheme management for annotation classes, including
the exact ABILIUS color scheme and support for custom color schemes.
"""

from typing import Dict, Any, List, Optional, Tuple
from ..base_protocols import BaseComponent, QColor, pyqtSignal
from .base_ui import BaseUI


class ClassColorScheme(BaseUI):
    """Class color scheme manager for annotation classes."""
    
    # Color scheme signals
    colorSchemeChanged = pyqtSignal(str)  # scheme_name
    classColorChanged = pyqtSignal(int, object)  # class_id, QColor
    colorsUpdated = pyqtSignal()
    
    def __init__(self, name: str = "class_color_scheme", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Color scheme configuration
        self._current_scheme: str = "abilius_legacy"
        self._class_colors: Dict[int, QColor] = {}
        self._max_classes: int = 20
        
        # Color scheme definitions
        self._color_schemes: Dict[str, Dict[str, Any]] = {}
        
        # Color generation settings
        self._auto_generate_colors: bool = True
        self._color_generation_method: str = "hsv"  # hsv, rgb, predefined
        self._color_saturation: float = 0.8
        self._color_value: float = 0.9
        self._color_alpha: int = 255
        
        # Color validation
        self._validate_colors: bool = True
        self._min_color_distance: float = 50.0  # Minimum distance between colors
        self._ensure_contrast: bool = True
        
        # Color persistence
        self._save_custom_schemes: bool = True
        self._custom_schemes_file: Optional[str] = None
        
        # Initialize default color schemes
        self._initialize_default_schemes()
        
        # Set initial scheme
        self.set_color_scheme(self._current_scheme)
    
    def initialize(self, **kwargs) -> bool:
        """Initialize class color scheme."""
        self._current_scheme = kwargs.get('current_scheme', 'abilius_legacy')
        self._max_classes = kwargs.get('max_classes', 20)
        self._auto_generate_colors = kwargs.get('auto_generate_colors', True)
        self._color_generation_method = kwargs.get('color_generation_method', 'hsv')
        self._color_saturation = kwargs.get('color_saturation', 0.8)
        self._color_value = kwargs.get('color_value', 0.9)
        self._color_alpha = kwargs.get('color_alpha', 255)
        self._validate_colors = kwargs.get('validate_colors', True)
        self._min_color_distance = kwargs.get('min_color_distance', 50.0)
        self._ensure_contrast = kwargs.get('ensure_contrast', True)
        self._save_custom_schemes = kwargs.get('save_custom_schemes', True)
        self._custom_schemes_file = kwargs.get('custom_schemes_file', None)
        
        # Add custom schemes if provided
        if 'custom_schemes' in kwargs:
            for scheme_name, scheme_data in kwargs['custom_schemes'].items():
                self.add_color_scheme(scheme_name, scheme_data)
        
        # Set initial scheme
        self.set_color_scheme(self._current_scheme)
        
        return super().initialize(**kwargs)
    
    def _initialize_default_schemes(self) -> None:
        """Initialize default color schemes."""
        try:
            # ABILIUS Legacy scheme (exact match)
            self._color_schemes['abilius_legacy'] = {
                'name': 'ABILIUS Legacy',
                'description': 'Original ABILIUS color scheme',
                'colors': {
                    0: QColor(255, 0, 0),    # Red - Class 0
                    1: QColor(0, 255, 0),    # Green - Class 1
                    2: QColor(0, 0, 255),    # Blue - Class 2
                    3: QColor(255, 255, 0),  # Yellow - Class 3
                    4: QColor(255, 0, 255),  # Magenta - Class 4
                    5: QColor(0, 255, 255),  # Cyan - Class 5
                    6: QColor(255, 255, 255),# White - Class 6
                    7: QColor(128, 0, 0),    # Dark Red - Class 7
                    8: QColor(0, 128, 0),    # Dark Green - Class 8
                    9: QColor(0, 0, 128),    # Dark Blue - Class 9
                },
                'auto_generate': True,
                'generation_method': 'hsv'
            }
            
            # Rainbow scheme
            self._color_schemes['rainbow'] = {
                'name': 'Rainbow',
                'description': 'Rainbow color scheme',
                'colors': {},
                'auto_generate': True,
                'generation_method': 'hsv'
            }
            
            # Pastel scheme
            self._color_schemes['pastel'] = {
                'name': 'Pastel',
                'description': 'Soft pastel colors',
                'colors': {
                    0: QColor(255, 182, 193),  # Light Pink
                    1: QColor(173, 216, 230),  # Light Blue
                    2: QColor(144, 238, 144),  # Light Green
                    3: QColor(255, 218, 185),  # Peach
                    4: QColor(221, 160, 221),  # Plum
                    5: QColor(255, 255, 224),  # Light Yellow
                    6: QColor(230, 230, 250),  # Lavender
                    7: QColor(255, 228, 196),  # Bisque
                    8: QColor(175, 238, 238),  # Pale Turquoise
                    9: QColor(255, 192, 203),  # Pink
                },
                'auto_generate': True,
                'generation_method': 'pastel'
            }
            
            # High contrast scheme
            self._color_schemes['high_contrast'] = {
                'name': 'High Contrast',
                'description': 'High contrast colors for accessibility',
                'colors': {
                    0: QColor(255, 0, 0),      # Red
                    1: QColor(0, 255, 0),      # Green
                    2: QColor(0, 0, 255),      # Blue
                    3: QColor(255, 255, 0),    # Yellow
                    4: QColor(255, 0, 255),    # Magenta
                    5: QColor(0, 255, 255),    # Cyan
                    6: QColor(255, 255, 255),  # White
                    7: QColor(0, 0, 0),        # Black
                    8: QColor(128, 128, 128),  # Gray
                    9: QColor(255, 128, 0),    # Orange
                },
                'auto_generate': True,
                'generation_method': 'high_contrast'
            }
            
            # Colorblind-friendly scheme
            self._color_schemes['colorblind_friendly'] = {
                'name': 'Colorblind Friendly',
                'description': 'Colors distinguishable for colorblind users',
                'colors': {
                    0: QColor(230, 159, 0),    # Orange
                    1: QColor(86, 180, 233),   # Sky Blue
                    2: QColor(0, 158, 115),    # Bluish Green
                    3: QColor(240, 228, 66),   # Yellow
                    4: QColor(0, 114, 178),    # Blue
                    5: QColor(213, 94, 0),     # Vermillion
                    6: QColor(204, 121, 167),  # Reddish Purple
                    7: QColor(117, 112, 179),  # Blue Purple
                    8: QColor(102, 194, 165),  # Green
                    9: QColor(252, 141, 98),   # Light Orange
                },
                'auto_generate': True,
                'generation_method': 'colorblind_friendly'
            }
            
        except Exception as e:
            self.emit_error(f"Error initializing default schemes: {str(e)}")
    
    def add_color_scheme(self, scheme_name: str, scheme_data: Dict[str, Any]) -> None:
        """Add a new color scheme."""
        try:
            self._color_schemes[scheme_name] = scheme_data
            self.emit_state_changed({'color_schemes_count': len(self._color_schemes)})
            
        except Exception as e:
            self.emit_error(f"Error adding color scheme: {str(e)}")
    
    def remove_color_scheme(self, scheme_name: str) -> bool:
        """Remove a color scheme."""
        try:
            if scheme_name in self._color_schemes and scheme_name != 'abilius_legacy':
                del self._color_schemes[scheme_name]
                
                # Switch to default scheme if current scheme was removed
                if self._current_scheme == scheme_name:
                    self.set_color_scheme('abilius_legacy')
                
                self.emit_state_changed({'color_schemes_count': len(self._color_schemes)})
                return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error removing color scheme: {str(e)}")
            return False
    
    def get_color_schemes(self) -> Dict[str, Dict[str, Any]]:
        """Get all available color schemes."""
        return self._color_schemes.copy()
    
    def get_color_scheme_names(self) -> List[str]:
        """Get names of all available color schemes."""
        return list(self._color_schemes.keys())
    
    def set_color_scheme(self, scheme_name: str) -> bool:
        """Set the current color scheme."""
        try:
            if scheme_name not in self._color_schemes:
                self.emit_error(f"Color scheme '{scheme_name}' not found")
                return False
            
            self._current_scheme = scheme_name
            scheme_data = self._color_schemes[scheme_name]
            
            # Load predefined colors
            self._class_colors = {}
            for class_id, color in scheme_data.get('colors', {}).items():
                self._class_colors[class_id] = QColor(color)
            
            # Generate additional colors if auto-generate is enabled
            if scheme_data.get('auto_generate', False):
                self._generate_missing_colors(scheme_data.get('generation_method', 'hsv'))
            
            # Emit signals
            self.colorSchemeChanged.emit(scheme_name)
            self.colorsUpdated.emit()
            self.emit_state_changed({'current_scheme': scheme_name})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting color scheme: {str(e)}")
            return False
    
    def get_current_scheme(self) -> str:
        """Get the current color scheme name."""
        return self._current_scheme
    
    def get_class_color(self, class_id: int) -> QColor:
        """Get color for a specific class."""
        try:
            if class_id in self._class_colors:
                return QColor(self._class_colors[class_id])
            
            # Generate color if not found and auto-generation is enabled
            if self._auto_generate_colors:
                color = self._generate_color_for_class(class_id)
                self._class_colors[class_id] = color
                return QColor(color)
            
            # Return default color
            return QColor(128, 128, 128)
            
        except Exception as e:
            self.emit_error(f"Error getting class color: {str(e)}")
            return QColor(128, 128, 128)
    
    def set_class_color(self, class_id: int, color: QColor) -> None:
        """Set color for a specific class."""
        try:
            # Validate color if enabled
            if self._validate_colors:
                if not self._validate_color(color, class_id):
                    self.emit_error(f"Color validation failed for class {class_id}")
                    return
            
            self._class_colors[class_id] = QColor(color)
            self.classColorChanged.emit(class_id, color)
            self.colorsUpdated.emit()
            self.emit_state_changed({'class_colors_count': len(self._class_colors)})
            
        except Exception as e:
            self.emit_error(f"Error setting class color: {str(e)}")
    
    def get_all_class_colors(self) -> Dict[int, QColor]:
        """Get all class colors."""
        return {class_id: QColor(color) for class_id, color in self._class_colors.items()}
    
    def _generate_missing_colors(self, method: str) -> None:
        """Generate colors for missing classes."""
        try:
            existing_classes = set(self._class_colors.keys())
            
            for class_id in range(self._max_classes):
                if class_id not in existing_classes:
                    color = self._generate_color_for_class(class_id, method)
                    self._class_colors[class_id] = color
            
        except Exception as e:
            self.emit_error(f"Error generating missing colors: {str(e)}")
    
    def _generate_color_for_class(self, class_id: int, method: Optional[str] = None) -> QColor:
        """Generate a color for a specific class."""
        try:
            if method is None:
                method = self._color_generation_method
            
            if method == 'hsv':
                return self._generate_hsv_color(class_id)
            elif method == 'rgb':
                return self._generate_rgb_color(class_id)
            elif method == 'pastel':
                return self._generate_pastel_color(class_id)
            elif method == 'high_contrast':
                return self._generate_high_contrast_color(class_id)
            elif method == 'colorblind_friendly':
                return self._generate_colorblind_friendly_color(class_id)
            else:
                return self._generate_hsv_color(class_id)
            
        except Exception as e:
            self.emit_error(f"Error generating color for class: {str(e)}")
            return QColor(128, 128, 128)
    
    def _generate_hsv_color(self, class_id: int) -> QColor:
        """Generate HSV-based color."""
        try:
            # Generate hue based on class ID
            hue = (class_id * 137.5) % 360  # Golden angle for better distribution
            
            # Use configured saturation and value
            saturation = int(self._color_saturation * 255)
            value = int(self._color_value * 255)
            
            color = QColor()
            color.setHsv(int(hue), saturation, value, self._color_alpha)
            
            return color
            
        except Exception as e:
            self.emit_error(f"Error generating HSV color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _generate_rgb_color(self, class_id: int) -> QColor:
        """Generate RGB-based color."""
        try:
            # Simple RGB generation
            r = (class_id * 67) % 256
            g = (class_id * 131) % 256
            b = (class_id * 199) % 256
            
            return QColor(r, g, b, self._color_alpha)
            
        except Exception as e:
            self.emit_error(f"Error generating RGB color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _generate_pastel_color(self, class_id: int) -> QColor:
        """Generate pastel color."""
        try:
            # Generate base HSV color
            hue = (class_id * 137.5) % 360
            saturation = int(0.3 * 255)  # Low saturation for pastel
            value = int(0.9 * 255)       # High value for pastel
            
            color = QColor()
            color.setHsv(int(hue), saturation, value, self._color_alpha)
            
            return color
            
        except Exception as e:
            self.emit_error(f"Error generating pastel color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _generate_high_contrast_color(self, class_id: int) -> QColor:
        """Generate high contrast color."""
        try:
            # Use predefined high contrast colors
            high_contrast_colors = [
                QColor(255, 0, 0),      # Red
                QColor(0, 255, 0),      # Green
                QColor(0, 0, 255),      # Blue
                QColor(255, 255, 0),    # Yellow
                QColor(255, 0, 255),    # Magenta
                QColor(0, 255, 255),    # Cyan
                QColor(255, 255, 255),  # White
                QColor(0, 0, 0),        # Black
                QColor(255, 128, 0),    # Orange
                QColor(128, 0, 128),    # Purple
            ]
            
            if class_id < len(high_contrast_colors):
                return high_contrast_colors[class_id]
            else:
                # Generate additional colors
                return self._generate_hsv_color(class_id)
            
        except Exception as e:
            self.emit_error(f"Error generating high contrast color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _generate_colorblind_friendly_color(self, class_id: int) -> QColor:
        """Generate colorblind-friendly color."""
        try:
            # Use predefined colorblind-friendly colors
            colorblind_colors = [
                QColor(230, 159, 0),    # Orange
                QColor(86, 180, 233),   # Sky Blue
                QColor(0, 158, 115),    # Bluish Green
                QColor(240, 228, 66),   # Yellow
                QColor(0, 114, 178),    # Blue
                QColor(213, 94, 0),     # Vermillion
                QColor(204, 121, 167),  # Reddish Purple
                QColor(117, 112, 179),  # Blue Purple
                QColor(102, 194, 165),  # Green
                QColor(252, 141, 98),   # Light Orange
            ]
            
            if class_id < len(colorblind_colors):
                return colorblind_colors[class_id]
            else:
                # Generate additional colors using HSV
                return self._generate_hsv_color(class_id)
            
        except Exception as e:
            self.emit_error(f"Error generating colorblind-friendly color: {str(e)}")
            return QColor(128, 128, 128)
    
    def _validate_color(self, color: QColor, class_id: int) -> bool:
        """Validate color against existing colors."""
        try:
            if not self._validate_colors:
                return True
            
            # Check minimum distance from existing colors
            if self._min_color_distance > 0:
                for existing_id, existing_color in self._class_colors.items():
                    if existing_id != class_id:
                        distance = self._calculate_color_distance(color, existing_color)
                        if distance < self._min_color_distance:
                            return False
            
            # Check contrast if enabled
            if self._ensure_contrast:
                # Check contrast against white and black backgrounds
                white_contrast = self._calculate_contrast_ratio(color, QColor(255, 255, 255))
                black_contrast = self._calculate_contrast_ratio(color, QColor(0, 0, 0))
                
                if white_contrast < 1.5 and black_contrast < 1.5:
                    return False
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error validating color: {str(e)}")
            return True
    
    def _calculate_color_distance(self, color1: QColor, color2: QColor) -> float:
        """Calculate Euclidean distance between two colors in RGB space."""
        try:
            r1, g1, b1 = color1.red(), color1.green(), color1.blue()
            r2, g2, b2 = color2.red(), color2.green(), color2.blue()
            
            return ((r2 - r1) ** 2 + (g2 - g1) ** 2 + (b2 - b1) ** 2) ** 0.5
            
        except Exception as e:
            self.emit_error(f"Error calculating color distance: {str(e)}")
            return 0.0
    
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
    
    def export_color_scheme(self, scheme_name: str, file_path: str) -> bool:
        """Export color scheme to file."""
        try:
            if scheme_name not in self._color_schemes:
                return False
            
            scheme_data = self._color_schemes[scheme_name]
            
            # Convert colors to serializable format
            exportable_scheme = {
                'name': scheme_data['name'],
                'description': scheme_data['description'],
                'colors': {},
                'auto_generate': scheme_data.get('auto_generate', False),
                'generation_method': scheme_data.get('generation_method', 'hsv')
            }
            
            for class_id, color in scheme_data['colors'].items():
                exportable_scheme['colors'][class_id] = {
                    'r': color.red(),
                    'g': color.green(),
                    'b': color.blue(),
                    'a': color.alpha()
                }
            
            # Save to file (implementation would depend on file format)
            # For now, just emit state change
            self.emit_state_changed({'scheme_exported': scheme_name})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error exporting color scheme: {str(e)}")
            return False
    
    def import_color_scheme(self, file_path: str) -> Optional[str]:
        """Import color scheme from file."""
        try:
            # Load from file (implementation would depend on file format)
            # For now, just emit state change
            self.emit_state_changed({'scheme_imported': file_path})
            
            return "imported_scheme"
            
        except Exception as e:
            self.emit_error(f"Error importing color scheme: {str(e)}")
            return None
    
    def reset_to_default_scheme(self) -> None:
        """Reset to default ABILIUS scheme."""
        self.set_color_scheme('abilius_legacy')
    
    def create_custom_scheme(self, name: str, description: str, colors: Dict[int, QColor]) -> bool:
        """Create a custom color scheme."""
        try:
            scheme_data = {
                'name': name,
                'description': description,
                'colors': colors,
                'auto_generate': False,
                'generation_method': 'custom'
            }
            
            self.add_color_scheme(name, scheme_data)
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating custom scheme: {str(e)}")
            return False
    
    def get_color_scheme_info(self, scheme_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a color scheme."""
        try:
            if scheme_name in self._color_schemes:
                scheme_data = self._color_schemes[scheme_name]
                return {
                    'name': scheme_data['name'],
                    'description': scheme_data['description'],
                    'color_count': len(scheme_data['colors']),
                    'auto_generate': scheme_data.get('auto_generate', False),
                    'generation_method': scheme_data.get('generation_method', 'hsv')
                }
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error getting color scheme info: {str(e)}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get color scheme statistics."""
        stats = super().get_statistics()
        stats.update({
            'current_scheme': self._current_scheme,
            'available_schemes': len(self._color_schemes),
            'defined_class_colors': len(self._class_colors),
            'max_classes': self._max_classes,
            'auto_generate_colors': self._auto_generate_colors,
            'color_generation_method': self._color_generation_method,
            'validate_colors': self._validate_colors,
            'min_color_distance': self._min_color_distance,
            'ensure_contrast': self._ensure_contrast
        })
        return stats