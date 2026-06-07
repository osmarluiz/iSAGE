"""
Enhanced Opacity Controls - Improved UI component for controlling overlay opacity settings

This enhanced version addresses potential issues and adds improvements:
- Better performance with optimized UI updates
- Enhanced accessibility features
- Improved user experience with better visual feedback
- More flexible configuration options
- Better memory management
"""

from typing import Dict, Any, Optional, List, Callable, Tuple
from ..base_protocols import BaseComponent, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from ..base_protocols import QSlider, QSpinBox, QGroupBox, QCheckBox, QPushButton
from ..base_protocols import QFrame, QSizePolicy, QTimer, QPropertyAnimation, QEasingCurve
from ..base_protocols import pyqtSignal, QApplication
from .base_ui import BaseUI
import json


class OpacityControls(BaseUI):
    """Enhanced UI component for controlling overlay opacity settings."""
    
    # Enhanced opacity control signals
    opacityChanged = pyqtSignal(str, float)  # overlay_name, opacity
    overlayToggled = pyqtSignal(str, bool)  # overlay_name, enabled
    opacityReset = pyqtSignal(str)  # overlay_name
    allOpacitiesReset = pyqtSignal()
    opacityPresetLoaded = pyqtSignal(str)  # preset_name
    opacityPresetSaved = pyqtSignal(str)  # preset_name
    batchOpacityChanged = pyqtSignal(dict)  # {overlay_name: opacity}
    
    def __init__(self, name: str = "enhanced_opacity_controls", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Widget setup
        self._widget = QWidget()
        self._layout = QVBoxLayout()
        self._widget.setLayout(self._layout)
        
        # Opacity configurations
        self._opacity_configs: Dict[str, Dict[str, Any]] = {}
        self._opacity_sliders: Dict[str, QSlider] = {}
        self._opacity_spinboxes: Dict[str, QSpinBox] = {}
        self._opacity_labels: Dict[str, QLabel] = {}
        self._toggle_checkboxes: Dict[str, QCheckBox] = {}
        self._reset_buttons: Dict[str, QPushButton] = {}
        self._control_containers: Dict[str, QWidget] = {}
        
        # Enhanced control settings
        self._slider_range: tuple = (0, 100)  # Slider range (0-100%)
        self._default_opacity: float = 0.7
        self._precision: int = 2  # Decimal places for opacity display
        self._show_percentages: bool = True
        self._show_reset_buttons: bool = True
        self._show_toggle_checkboxes: bool = True
        self._show_value_labels: bool = True
        self._show_icons: bool = True
        
        # Enhanced layout settings
        self._compact_layout: bool = False
        self._group_by_category: bool = True
        self._collapsible_groups: bool = True
        self._animate_changes: bool = True
        self._show_separators: bool = True
        self._uniform_spacing: bool = True
        
        # Theme integration
        self._theme_manager = None
        self._current_theme: str = "light"
        
        # Callbacks and validation
        self._opacity_callbacks: Dict[str, Callable[[float], None]] = {}
        self._toggle_callbacks: Dict[str, Callable[[bool], None]] = {}
        self._validation_callbacks: Dict[str, Callable[[float], bool]] = {}
        
        # Performance optimization
        self._update_timer: Optional[QTimer] = None
        self._pending_updates: Dict[str, float] = {}
        self._update_delay: int = 50  # milliseconds
        self._batch_updates: bool = True
        
        # Enhanced features
        self._opacity_presets: Dict[str, Dict[str, float]] = {}
        self._preset_buttons: Dict[str, QPushButton] = {}
        self._global_opacity_multiplier: float = 1.0
        self._linked_controls: Dict[str, List[str]] = {}
        
        # Accessibility
        self._accessibility_enabled: bool = True
        self._keyboard_shortcuts: Dict[str, str] = {}
        self._high_contrast_mode: bool = False
        
        # Visual feedback
        self._animations: Dict[str, QPropertyAnimation] = {}
        self._highlight_on_change: bool = True
        self._fade_disabled_controls: bool = True
        
        # Memory management
        self._max_undo_states: int = 10
        self._undo_stack: List[Dict[str, float]] = []
        self._undo_index: int = -1
        
        # State persistence
        self._auto_save_state: bool = True
        self._state_file: Optional[str] = None
        
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced opacity controls."""
        self._slider_range = kwargs.get('slider_range', (0, 100))
        self._default_opacity = kwargs.get('default_opacity', 0.7)
        self._precision = kwargs.get('precision', 2)
        self._show_percentages = kwargs.get('show_percentages', True)
        self._show_reset_buttons = kwargs.get('show_reset_buttons', True)
        self._show_toggle_checkboxes = kwargs.get('show_toggle_checkboxes', True)
        self._show_value_labels = kwargs.get('show_value_labels', True)
        self._show_icons = kwargs.get('show_icons', True)
        self._compact_layout = kwargs.get('compact_layout', False)
        self._group_by_category = kwargs.get('group_by_category', True)
        self._collapsible_groups = kwargs.get('collapsible_groups', True)
        self._animate_changes = kwargs.get('animate_changes', True)
        self._show_separators = kwargs.get('show_separators', True)
        self._uniform_spacing = kwargs.get('uniform_spacing', True)
        self._theme_manager = kwargs.get('theme_manager', None)
        self._current_theme = kwargs.get('current_theme', 'light')
        self._update_delay = kwargs.get('update_delay', 50)
        self._batch_updates = kwargs.get('batch_updates', True)
        self._accessibility_enabled = kwargs.get('accessibility_enabled', True)
        self._highlight_on_change = kwargs.get('highlight_on_change', True)
        self._fade_disabled_controls = kwargs.get('fade_disabled_controls', True)
        self._max_undo_states = kwargs.get('max_undo_states', 10)
        self._auto_save_state = kwargs.get('auto_save_state', True)
        self._state_file = kwargs.get('state_file', None)
        
        # Initialize update timer
        if self._batch_updates:
            self._setup_update_timer()
        
        # Set up default overlay configurations
        self._setup_default_overlays()
        
        # Load preset configurations
        self._setup_default_presets()
        
        # Build initial UI
        self._build_ui()
        
        # Load saved state if available
        if self._auto_save_state and self._state_file:
            self._load_state()
        
        return super().initialize(**kwargs)
    
    def get_widget(self) -> QWidget:
        """Get the enhanced opacity controls widget."""
        return self._widget
    
    def add_overlay_control(self, overlay_name: str, config: Dict[str, Any]) -> None:
        """Add opacity control for an overlay with enhanced features."""
        try:
            # Store configuration with enhancements
            self._opacity_configs[overlay_name] = {
                'display_name': config.get('display_name', overlay_name.replace('_', ' ').title()),
                'default_opacity': config.get('default_opacity', self._default_opacity),
                'min_opacity': config.get('min_opacity', 0.0),
                'max_opacity': config.get('max_opacity', 1.0),
                'step': config.get('step', 0.01),
                'category': config.get('category', 'General'),
                'enabled': config.get('enabled', True),
                'tooltip': config.get('tooltip', f'Adjust {overlay_name} opacity'),
                'color': config.get('color', None),
                'icon': config.get('icon', None),
                'keyboard_shortcut': config.get('keyboard_shortcut', None),
                'linked_controls': config.get('linked_controls', []),
                'validation_range': config.get('validation_range', (0.0, 1.0)),
                'priority': config.get('priority', 0),
                'description': config.get('description', ''),
                'affects_performance': config.get('affects_performance', False)
            }
            
            # Add to linked controls
            if config.get('linked_controls'):
                self._linked_controls[overlay_name] = config['linked_controls']
            
            # Save current state for undo
            self._save_undo_state()
            
            # Rebuild UI
            self._build_ui()
            
            # Connect callbacks if provided
            if 'opacity_callback' in config:
                self.set_opacity_callback(overlay_name, config['opacity_callback'])
            if 'toggle_callback' in config:
                self.set_toggle_callback(overlay_name, config['toggle_callback'])
            if 'validation_callback' in config:
                self.set_validation_callback(overlay_name, config['validation_callback'])
            
            # Setup keyboard shortcut
            if config.get('keyboard_shortcut'):
                self._setup_keyboard_shortcut(overlay_name, config['keyboard_shortcut'])
            
            self.emit_state_changed({'overlay_controls_count': len(self._opacity_configs)})
            
        except Exception as e:
            self.emit_error(f"Error adding overlay control: {str(e)}")
    
    def set_opacity(self, overlay_name: str, opacity: float, animate: bool = True) -> None:
        """Set opacity for an overlay with enhanced features."""
        try:
            if overlay_name not in self._opacity_configs:
                return
            
            config = self._opacity_configs[overlay_name]
            
            # Validate opacity
            if overlay_name in self._validation_callbacks:
                if not self._validation_callbacks[overlay_name](opacity):
                    self.emit_error(f"Opacity validation failed for {overlay_name}")
                    return
            
            # Clamp opacity to valid range
            opacity = max(config['min_opacity'], min(opacity, config['max_opacity']))
            
            # Apply global opacity multiplier
            effective_opacity = opacity * self._global_opacity_multiplier
            effective_opacity = max(0.0, min(1.0, effective_opacity))
            
            # Update controls with animation
            if animate and self._animate_changes:
                self._animate_opacity_change(overlay_name, opacity)
            else:
                self._update_opacity_controls(overlay_name, opacity)
            
            # Handle linked controls
            if overlay_name in self._linked_controls:
                for linked_name in self._linked_controls[overlay_name]:
                    if linked_name in self._opacity_configs:
                        self._update_opacity_controls(linked_name, opacity)
            
            # Batch or immediate update
            if self._batch_updates:
                self._pending_updates[overlay_name] = opacity
                self._update_timer.start()
            else:
                self._emit_opacity_change(overlay_name, opacity)
            
            # Visual feedback
            if self._highlight_on_change:
                self._highlight_control(overlay_name)
            
            # Auto-save state
            if self._auto_save_state:
                self._save_state()
            
        except Exception as e:
            self.emit_error(f"Error setting opacity: {str(e)}")
    
    def set_global_opacity_multiplier(self, multiplier: float) -> None:
        """Set global opacity multiplier affecting all overlays."""
        try:
            self._global_opacity_multiplier = max(0.0, min(1.0, multiplier))
            
            # Update all controls
            for overlay_name in self._opacity_configs:
                current_opacity = self.get_opacity(overlay_name)
                self._update_opacity_controls(overlay_name, current_opacity)
            
            self.emit_state_changed({'global_opacity_multiplier': self._global_opacity_multiplier})
            
        except Exception as e:
            self.emit_error(f"Error setting global opacity multiplier: {str(e)}")
    
    def get_global_opacity_multiplier(self) -> float:
        """Get current global opacity multiplier."""
        return self._global_opacity_multiplier
    
    def save_preset(self, preset_name: str) -> None:
        """Save current opacity configuration as preset."""
        try:
            preset = {}
            for overlay_name in self._opacity_configs:
                preset[overlay_name] = self.get_opacity(overlay_name)
            
            self._opacity_presets[preset_name] = preset
            self._add_preset_button(preset_name)
            
            self.opacityPresetSaved.emit(preset_name)
            self.emit_state_changed({'presets_count': len(self._opacity_presets)})
            
        except Exception as e:
            self.emit_error(f"Error saving preset: {str(e)}")
    
    def load_preset(self, preset_name: str, animate: bool = True) -> None:
        """Load opacity configuration from preset."""
        try:
            if preset_name not in self._opacity_presets:
                return
            
            preset = self._opacity_presets[preset_name]
            
            # Save current state for undo
            self._save_undo_state()
            
            # Apply preset
            for overlay_name, opacity in preset.items():
                if overlay_name in self._opacity_configs:
                    self.set_opacity(overlay_name, opacity, animate)
            
            self.opacityPresetLoaded.emit(preset_name)
            
        except Exception as e:
            self.emit_error(f"Error loading preset: {str(e)}")
    
    def delete_preset(self, preset_name: str) -> None:
        """Delete an opacity preset."""
        try:
            if preset_name in self._opacity_presets:
                del self._opacity_presets[preset_name]
                
                # Remove button
                if preset_name in self._preset_buttons:
                    self._preset_buttons[preset_name].deleteLater()
                    del self._preset_buttons[preset_name]
                
                self.emit_state_changed({'presets_count': len(self._opacity_presets)})
            
        except Exception as e:
            self.emit_error(f"Error deleting preset: {str(e)}")
    
    def undo(self) -> None:
        """Undo last opacity changes."""
        try:
            if self._undo_index > 0:
                self._undo_index -= 1
                state = self._undo_stack[self._undo_index]
                
                for overlay_name, opacity in state.items():
                    if overlay_name in self._opacity_configs:
                        self.set_opacity(overlay_name, opacity, animate=False)
                
                self.emit_state_changed({'undo_index': self._undo_index})
            
        except Exception as e:
            self.emit_error(f"Error during undo: {str(e)}")
    
    def redo(self) -> None:
        """Redo last undone opacity changes."""
        try:
            if self._undo_index < len(self._undo_stack) - 1:
                self._undo_index += 1
                state = self._undo_stack[self._undo_index]
                
                for overlay_name, opacity in state.items():
                    if overlay_name in self._opacity_configs:
                        self.set_opacity(overlay_name, opacity, animate=False)
                
                self.emit_state_changed({'undo_index': self._undo_index})
            
        except Exception as e:
            self.emit_error(f"Error during redo: {str(e)}")
    
    def set_validation_callback(self, overlay_name: str, callback: Callable[[float], bool]) -> None:
        """Set validation callback for opacity values."""
        self._validation_callbacks[overlay_name] = callback
    
    def set_accessibility_mode(self, enabled: bool) -> None:
        """Enable or disable accessibility features."""
        try:
            self._accessibility_enabled = enabled
            
            # Update all controls
            for overlay_name in self._opacity_configs:
                self._update_accessibility_features(overlay_name)
            
            self.emit_state_changed({'accessibility_enabled': enabled})
            
        except Exception as e:
            self.emit_error(f"Error setting accessibility mode: {str(e)}")
    
    def set_high_contrast_mode(self, enabled: bool) -> None:
        """Enable or disable high contrast mode."""
        try:
            self._high_contrast_mode = enabled
            self._apply_theme()
            
            self.emit_state_changed({'high_contrast_mode': enabled})
            
        except Exception as e:
            self.emit_error(f"Error setting high contrast mode: {str(e)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the opacity controls."""
        try:
            return {
                'controls_count': len(self._opacity_configs),
                'update_delay': self._update_delay,
                'batch_updates': self._batch_updates,
                'pending_updates': len(self._pending_updates),
                'animations_active': len(self._animations),
                'memory_usage': self._get_memory_usage(),
                'undo_states': len(self._undo_stack),
                'presets_count': len(self._opacity_presets)
            }
        except Exception as e:
            self.emit_error(f"Error getting performance metrics: {str(e)}")
            return {}
    
    def _setup_update_timer(self) -> None:
        """Setup update timer for batch processing."""
        try:
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._process_pending_updates)
            self._update_timer.setInterval(self._update_delay)
            
        except Exception as e:
            self.emit_error(f"Error setting up update timer: {str(e)}")
    
    def _process_pending_updates(self) -> None:
        """Process pending opacity updates."""
        try:
            if not self._pending_updates:
                return
            
            # Emit batch signal
            self.batchOpacityChanged.emit(self._pending_updates.copy())
            
            # Emit individual signals
            for overlay_name, opacity in self._pending_updates.items():
                self._emit_opacity_change(overlay_name, opacity)
            
            self._pending_updates.clear()
            
        except Exception as e:
            self.emit_error(f"Error processing pending updates: {str(e)}")
    
    def _emit_opacity_change(self, overlay_name: str, opacity: float) -> None:
        """Emit opacity change signal and call callback."""
        try:
            self.opacityChanged.emit(overlay_name, opacity)
            
            if overlay_name in self._opacity_callbacks:
                self._opacity_callbacks[overlay_name](opacity)
                
        except Exception as e:
            self.emit_error(f"Error emitting opacity change: {str(e)}")
    
    def _animate_opacity_change(self, overlay_name: str, target_opacity: float) -> None:
        """Animate opacity change with smooth transition."""
        try:
            if not self._animate_changes or overlay_name not in self._opacity_sliders:
                self._update_opacity_controls(overlay_name, target_opacity)
                return
            
            slider = self._opacity_sliders[overlay_name]
            current_value = slider.value()
            target_value = int(target_opacity * (self._slider_range[1] - self._slider_range[0]) + self._slider_range[0])
            
            # Create animation
            animation = QPropertyAnimation(slider, b"value")
            animation.setDuration(200)  # 200ms animation
            animation.setStartValue(current_value)
            animation.setEndValue(target_value)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # Store animation
            self._animations[overlay_name] = animation
            
            # Start animation
            animation.start()
            
        except Exception as e:
            self.emit_error(f"Error animating opacity change: {str(e)}")
            # Fallback to immediate update
            self._update_opacity_controls(overlay_name, target_opacity)
    
    def _highlight_control(self, overlay_name: str) -> None:
        """Highlight control to provide visual feedback."""
        try:
            if overlay_name not in self._control_containers:
                return
            
            container = self._control_containers[overlay_name]
            
            # Create highlight effect
            original_style = container.styleSheet()
            highlight_style = original_style + "QWidget { border: 2px solid #4CAF50; border-radius: 4px; }"
            
            container.setStyleSheet(highlight_style)
            
            # Reset after delay
            QTimer.singleShot(500, lambda: container.setStyleSheet(original_style))
            
        except Exception as e:
            self.emit_error(f"Error highlighting control: {str(e)}")
    
    def _save_undo_state(self) -> None:
        """Save current state for undo functionality."""
        try:
            current_state = {}
            for overlay_name in self._opacity_configs:
                current_state[overlay_name] = self.get_opacity(overlay_name)
            
            # Remove states after current index
            self._undo_stack = self._undo_stack[:self._undo_index + 1]
            
            # Add new state
            self._undo_stack.append(current_state)
            self._undo_index = len(self._undo_stack) - 1
            
            # Limit stack size
            if len(self._undo_stack) > self._max_undo_states:
                self._undo_stack = self._undo_stack[-self._max_undo_states:]
                self._undo_index = len(self._undo_stack) - 1
            
        except Exception as e:
            self.emit_error(f"Error saving undo state: {str(e)}")
    
    def _save_state(self) -> None:
        """Save current state to file."""
        try:
            if not self._state_file:
                return
            
            state = {
                'opacities': self.get_all_opacities(),
                'global_multiplier': self._global_opacity_multiplier,
                'presets': self._opacity_presets,
                'theme': self._current_theme
            }
            
            with open(self._state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
        except Exception as e:
            self.emit_error(f"Error saving state: {str(e)}")
    
    def _load_state(self) -> None:
        """Load state from file."""
        try:
            if not self._state_file:
                return
            
            try:
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                
                # Restore opacities
                if 'opacities' in state:
                    self.set_all_opacities(state['opacities'])
                
                # Restore global multiplier
                if 'global_multiplier' in state:
                    self.set_global_opacity_multiplier(state['global_multiplier'])
                
                # Restore presets
                if 'presets' in state:
                    self._opacity_presets = state['presets']
                
                # Restore theme
                if 'theme' in state:
                    self._current_theme = state['theme']
                
            except FileNotFoundError:
                # File doesn't exist yet, that's okay
                pass
            
        except Exception as e:
            self.emit_error(f"Error loading state: {str(e)}")
    
    def _get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        try:
            return {
                'widgets_count': len(self._opacity_sliders) + len(self._opacity_spinboxes) + len(self._toggle_checkboxes),
                'animations_count': len(self._animations),
                'callbacks_count': len(self._opacity_callbacks) + len(self._toggle_callbacks),
                'undo_states_count': len(self._undo_stack),
                'presets_count': len(self._opacity_presets)
            }
        except Exception as e:
            self.emit_error(f"Error getting memory usage: {str(e)}")
            return {}
    
    def _setup_default_overlays(self) -> None:
        """Setup default overlay configurations with enhancements."""
        try:
            default_overlays = [
                {
                    'name': 'prediction_overlay',
                    'display_name': 'Prediction',
                    'default_opacity': 0.7,
                    'category': 'Model Output',
                    'tooltip': 'Adjust prediction overlay opacity - affects model output visibility',
                    'description': 'Controls visibility of model predictions',
                    'affects_performance': True,
                    'keyboard_shortcut': 'P'
                },
                {
                    'name': 'ground_truth_overlay',
                    'display_name': 'Ground Truth',
                    'default_opacity': 0.5,
                    'category': 'Reference',
                    'tooltip': 'Adjust ground truth overlay opacity - affects reference data visibility',
                    'description': 'Controls visibility of ground truth annotations',
                    'affects_performance': False,
                    'keyboard_shortcut': 'G'
                },
                {
                    'name': 'mistake_overlay',
                    'display_name': 'Mistakes',
                    'default_opacity': 0.8,
                    'category': 'Analysis',
                    'tooltip': 'Adjust mistake overlay opacity - affects error highlighting',
                    'description': 'Controls visibility of prediction errors',
                    'affects_performance': False,
                    'keyboard_shortcut': 'M'
                }
            ]
            
            for overlay in default_overlays:
                self.add_overlay_control(overlay['name'], overlay)
            
        except Exception as e:
            self.emit_error(f"Error setting up default overlays: {str(e)}")
    
    def _setup_default_presets(self) -> None:
        """Setup default opacity presets."""
        try:
            default_presets = {
                'High Visibility': {
                    'prediction_overlay': 0.9,
                    'ground_truth_overlay': 0.8,
                    'mistake_overlay': 1.0
                },
                'Balanced': {
                    'prediction_overlay': 0.7,
                    'ground_truth_overlay': 0.5,
                    'mistake_overlay': 0.8
                },
                'Subtle': {
                    'prediction_overlay': 0.4,
                    'ground_truth_overlay': 0.3,
                    'mistake_overlay': 0.5
                }
            }
            
            for preset_name, preset_data in default_presets.items():
                self._opacity_presets[preset_name] = preset_data
            
        except Exception as e:
            self.emit_error(f"Error setting up default presets: {str(e)}")
    
    def _update_opacity_controls(self, overlay_name: str, opacity: float) -> None:
        """Update opacity controls without animation."""
        try:
            # Update slider
            if overlay_name in self._opacity_sliders:
                slider = self._opacity_sliders[overlay_name]
                slider_value = int(opacity * (self._slider_range[1] - self._slider_range[0]) + self._slider_range[0])
                slider.setValue(slider_value)
            
            # Update spinbox
            if overlay_name in self._opacity_spinboxes:
                spinbox = self._opacity_spinboxes[overlay_name]
                spinbox.setValue(int(opacity * 100))
            
            # Update label
            if overlay_name in self._opacity_labels:
                label = self._opacity_labels[overlay_name]
                if self._show_percentages:
                    label.setText(f"{opacity * 100:.{self._precision}f}%")
                else:
                    label.setText(f"{opacity:.{self._precision}f}")
            
        except Exception as e:
            self.emit_error(f"Error updating opacity controls: {str(e)}")
    
    def _update_accessibility_features(self, overlay_name: str) -> None:
        """Update accessibility features for a control."""
        try:
            if not self._accessibility_enabled:
                return
            
            # Update slider accessibility
            if overlay_name in self._opacity_sliders:
                slider = self._opacity_sliders[overlay_name]
                config = self._opacity_configs[overlay_name]
                
                slider.setAccessibleName(f"{config['display_name']} Opacity")
                slider.setAccessibleDescription(config['description'])
                
                # Set ARIA attributes
                slider.setProperty("aria-valuemin", int(config['min_opacity'] * 100))
                slider.setProperty("aria-valuemax", int(config['max_opacity'] * 100))
                slider.setProperty("aria-valuenow", int(self.get_opacity(overlay_name) * 100))
                slider.setProperty("aria-label", f"{config['display_name']} opacity slider")
            
        except Exception as e:
            self.emit_error(f"Error updating accessibility features: {str(e)}")
    
    def _build_ui(self) -> None:
        """Build the enhanced UI layout."""
        try:
            # Clear existing layout
            self._clear_layout()
            
            # Add presets section
            self._add_presets_section()
            
            # Add separator
            if self._show_separators:
                self._add_separator()
            
            # Build controls
            if self._group_by_category:
                self._build_grouped_ui()
            else:
                self._build_flat_ui()
            
            # Add global controls
            self._add_global_controls()
            
            # Apply theme
            if self._theme_manager:
                self._apply_theme()
            
        except Exception as e:
            self.emit_error(f"Error building UI: {str(e)}")
    
    def _add_presets_section(self) -> None:
        """Add presets section to UI."""
        try:
            if not self._opacity_presets:
                return
            
            presets_group = QGroupBox("Presets")
            presets_layout = QHBoxLayout()
            
            for preset_name in self._opacity_presets:
                self._add_preset_button(preset_name, presets_layout)
            
            presets_group.setLayout(presets_layout)
            self._layout.addWidget(presets_group)
            
        except Exception as e:
            self.emit_error(f"Error adding presets section: {str(e)}")
    
    def _add_preset_button(self, preset_name: str, layout: QHBoxLayout = None) -> None:
        """Add preset button."""
        try:
            button = QPushButton(preset_name)
            button.setToolTip(f"Load {preset_name} preset")
            button.clicked.connect(lambda _, name=preset_name: self.load_preset(name))
            
            self._preset_buttons[preset_name] = button
            
            if layout:
                layout.addWidget(button)
            
        except Exception as e:
            self.emit_error(f"Error adding preset button: {str(e)}")
    
    def _add_separator(self) -> None:
        """Add visual separator."""
        try:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self._layout.addWidget(separator)
            
        except Exception as e:
            self.emit_error(f"Error adding separator: {str(e)}")
    
    def _add_global_controls(self) -> None:
        """Add global control section."""
        try:
            # Add separator
            if self._show_separators:
                self._add_separator()
            
            # Add global multiplier control
            global_group = QGroupBox("Global Controls")
            global_layout = QVBoxLayout()
            
            # Global multiplier
            multiplier_layout = QHBoxLayout()
            multiplier_layout.addWidget(QLabel("Global Opacity:"))
            
            multiplier_slider = QSlider(1)  # Qt.Horizontal
            multiplier_slider.setRange(0, 100)
            multiplier_slider.setValue(int(self._global_opacity_multiplier * 100))
            multiplier_slider.valueChanged.connect(lambda v: self.set_global_opacity_multiplier(v / 100.0))
            multiplier_layout.addWidget(multiplier_slider)
            
            multiplier_label = QLabel(f"{self._global_opacity_multiplier * 100:.0f}%")
            multiplier_layout.addWidget(multiplier_label)
            
            global_layout.addLayout(multiplier_layout)
            
            # Reset all button
            if self._show_reset_buttons:
                reset_all_button = QPushButton('Reset All')
                reset_all_button.setToolTip('Reset all overlay opacities to default')
                reset_all_button.clicked.connect(self.reset_all_opacities)
                global_layout.addWidget(reset_all_button)
            
            global_group.setLayout(global_layout)
            self._layout.addWidget(global_group)
            
        except Exception as e:
            self.emit_error(f"Error adding global controls: {str(e)}")
    
    def _clear_layout(self) -> None:
        """Clear the layout efficiently."""
        try:
            # Stop all animations
            for animation in self._animations.values():
                animation.stop()
            self._animations.clear()
            
            # Clear widgets
            while self._layout.count():
                child = self._layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Clear references
            self._opacity_sliders.clear()
            self._opacity_spinboxes.clear()
            self._opacity_labels.clear()
            self._toggle_checkboxes.clear()
            self._reset_buttons.clear()
            self._control_containers.clear()
            
        except Exception as e:
            self.emit_error(f"Error clearing layout: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced opacity controls statistics."""
        stats = super().get_statistics()
        stats.update({
            'overlay_count': len(self._opacity_configs),
            'current_opacities': self.get_all_opacities(),
            'global_multiplier': self._global_opacity_multiplier,
            'presets_count': len(self._opacity_presets),
            'compact_layout': self._compact_layout,
            'group_by_category': self._group_by_category,
            'animate_changes': self._animate_changes,
            'accessibility_enabled': self._accessibility_enabled,
            'high_contrast_mode': self._high_contrast_mode,
            'performance_metrics': self.get_performance_metrics()
        })
        return stats