"""
Point Visibility Controls - UI controls for managing point visibility settings

This module provides UI controls for managing the visibility of different types
of annotation points, including previous/current session points, class filtering,
and other visibility options.
"""

from typing import Dict, Any, List, Optional, Set, Callable
from ..base_protocols import BaseComponent, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from ..base_protocols import QCheckBox, QComboBox, QSlider, QGroupBox, QPushButton
from ..base_protocols import QButtonGroup, QRadioButton, pyqtSignal
from .base_ui import BaseUI


class PointVisibilityControls(BaseUI):
    """UI controls for managing point visibility settings."""
    
    # Point visibility signals
    visibilityChanged = pyqtSignal(str, bool)  # visibility_type, enabled
    classVisibilityChanged = pyqtSignal(int, bool)  # class_id, visible
    sessionVisibilityChanged = pyqtSignal(str, bool)  # session_type, visible
    opacityChanged = pyqtSignal(str, float)  # point_type, opacity
    allPointsToggled = pyqtSignal(bool)  # visible
    
    def __init__(self, name: str = "point_visibility_controls", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Widget setup
        self._widget = QWidget()
        self._layout = QVBoxLayout()
        self._widget.setLayout(self._layout)
        
        # Visibility states
        self._visibility_states: Dict[str, bool] = {
            'all_points': True,
            'current_session': True,
            'previous_session': True,
            'selected_points': True,
            'unselected_points': True,
            'recent_points': True,
            'old_points': True
        }
        
        # Class visibility
        self._class_visibility: Dict[int, bool] = {}
        self._max_classes: int = 10
        
        # Session visibility
        self._session_visibility: Dict[str, bool] = {
            'current': True,
            'previous': False,
            'all_previous': False
        }
        
        # Point opacity settings
        self._point_opacities: Dict[str, float] = {
            'current_session': 1.0,
            'previous_session': 0.5,
            'selected_points': 1.0,
            'unselected_points': 0.8,
            'recent_points': 1.0,
            'old_points': 0.6
        }
        
        # UI components
        self._visibility_checkboxes: Dict[str, QCheckBox] = {}
        self._class_checkboxes: Dict[int, QCheckBox] = {}
        self._session_checkboxes: Dict[str, QCheckBox] = {}
        self._opacity_sliders: Dict[str, QSlider] = {}
        self._opacity_labels: Dict[str, QLabel] = {}
        
        # Button groups
        self._session_button_group: Optional[QButtonGroup] = None
        self._class_button_group: Optional[QButtonGroup] = None
        
        # Layout settings
        self._compact_layout: bool = False
        self._show_opacity_controls: bool = True
        self._show_class_controls: bool = True
        self._show_session_controls: bool = True
        self._collapsible_groups: bool = True
        
        # Callbacks
        self._visibility_callbacks: Dict[str, Callable[[bool], None]] = {}
        self._class_callbacks: Dict[int, Callable[[bool], None]] = {}
        self._session_callbacks: Dict[str, Callable[[bool], None]] = {}
        self._opacity_callbacks: Dict[str, Callable[[float], None]] = {}
        
        # Point filtering
        self._filter_enabled: bool = True
        self._filter_criteria: Dict[str, Any] = {}
        self._active_filters: Set[str] = set()
        
        # Quick presets
        self._visibility_presets: Dict[str, Dict[str, Any]] = {
            'all_visible': {
                'name': 'All Visible',
                'description': 'Show all points',
                'settings': {
                    'all_points': True,
                    'current_session': True,
                    'previous_session': True,
                    'selected_points': True,
                    'unselected_points': True
                }
            },
            'current_only': {
                'name': 'Current Session Only',
                'description': 'Show only current session points',
                'settings': {
                    'all_points': True,
                    'current_session': True,
                    'previous_session': False,
                    'selected_points': True,
                    'unselected_points': True
                }
            },
            'selected_only': {
                'name': 'Selected Only',
                'description': 'Show only selected points',
                'settings': {
                    'all_points': True,
                    'current_session': True,
                    'previous_session': True,
                    'selected_points': True,
                    'unselected_points': False
                }
            },
            'none_visible': {
                'name': 'None Visible',
                'description': 'Hide all points',
                'settings': {
                    'all_points': False,
                    'current_session': False,
                    'previous_session': False,
                    'selected_points': False,
                    'unselected_points': False
                }
            }
        }
        
        # Statistics
        self._visibility_stats: Dict[str, int] = {
            'total_toggles': 0,
            'class_toggles': 0,
            'session_toggles': 0,
            'opacity_changes': 0
        }
    
    def initialize(self, **kwargs) -> bool:
        """Initialize point visibility controls."""
        self._max_classes = kwargs.get('max_classes', 10)
        self._compact_layout = kwargs.get('compact_layout', False)
        self._show_opacity_controls = kwargs.get('show_opacity_controls', True)
        self._show_class_controls = kwargs.get('show_class_controls', True)
        self._show_session_controls = kwargs.get('show_session_controls', True)
        self._collapsible_groups = kwargs.get('collapsible_groups', True)
        self._filter_enabled = kwargs.get('filter_enabled', True)
        
        # Initialize class visibility
        for class_id in range(self._max_classes):
            self._class_visibility[class_id] = True
        
        # Set initial visibility states
        if 'initial_visibility' in kwargs:
            self._visibility_states.update(kwargs['initial_visibility'])
        
        # Set initial opacities
        if 'initial_opacities' in kwargs:
            self._point_opacities.update(kwargs['initial_opacities'])
        
        # Add custom presets
        if 'custom_presets' in kwargs:
            self._visibility_presets.update(kwargs['custom_presets'])
        
        # Build UI
        self._build_ui()
        
        return super().initialize(**kwargs)
    
    def get_widget(self) -> QWidget:
        """Get the visibility controls widget."""
        return self._widget
    
    def _build_ui(self) -> None:
        """Build the UI layout."""
        try:
            # Clear existing layout
            self._clear_layout()
            
            # Add general visibility controls
            self._add_general_visibility_group()
            
            # Add session visibility controls
            if self._show_session_controls:
                self._add_session_visibility_group()
            
            # Add class visibility controls
            if self._show_class_controls:
                self._add_class_visibility_group()
            
            # Add opacity controls
            if self._show_opacity_controls:
                self._add_opacity_controls_group()
            
            # Add preset controls
            self._add_preset_controls()
            
            # Add action buttons
            self._add_action_buttons()
            
        except Exception as e:
            self.emit_error(f"Error building UI: {str(e)}")
    
    def _add_general_visibility_group(self) -> None:
        """Add general visibility controls group."""
        try:
            group = QGroupBox("General Visibility")
            layout = QVBoxLayout()
            
            # All points master toggle
            all_points_cb = QCheckBox("Show All Points")
            all_points_cb.setChecked(self._visibility_states['all_points'])
            all_points_cb.toggled.connect(lambda checked: self._on_visibility_toggled('all_points', checked))
            self._visibility_checkboxes['all_points'] = all_points_cb
            layout.addWidget(all_points_cb)
            
            # Individual visibility controls
            visibility_controls = [
                ('current_session', 'Current Session Points'),
                ('previous_session', 'Previous Session Points'),
                ('selected_points', 'Selected Points'),
                ('unselected_points', 'Unselected Points'),
                ('recent_points', 'Recent Points'),
                ('old_points', 'Old Points')
            ]
            
            for vis_type, display_name in visibility_controls:
                checkbox = QCheckBox(display_name)
                checkbox.setChecked(self._visibility_states[vis_type])
                checkbox.toggled.connect(lambda checked, vt=vis_type: self._on_visibility_toggled(vt, checked))
                self._visibility_checkboxes[vis_type] = checkbox
                layout.addWidget(checkbox)
            
            group.setLayout(layout)
            self._layout.addWidget(group)
            
        except Exception as e:
            self.emit_error(f"Error adding general visibility group: {str(e)}")
    
    def _add_session_visibility_group(self) -> None:
        """Add session visibility controls group."""
        try:
            group = QGroupBox("Session Visibility")
            layout = QVBoxLayout()
            
            # Session type selection
            session_types = [
                ('current', 'Current Session'),
                ('previous', 'Previous Session'),
                ('all_previous', 'All Previous Sessions')
            ]
            
            for session_type, display_name in session_types:
                checkbox = QCheckBox(display_name)
                checkbox.setChecked(self._session_visibility[session_type])
                checkbox.toggled.connect(lambda checked, st=session_type: self._on_session_visibility_toggled(st, checked))
                self._session_checkboxes[session_type] = checkbox
                layout.addWidget(checkbox)
            
            group.setLayout(layout)
            self._layout.addWidget(group)
            
        except Exception as e:
            self.emit_error(f"Error adding session visibility group: {str(e)}")
    
    def _add_class_visibility_group(self) -> None:
        """Add class visibility controls group."""
        try:
            group = QGroupBox("Class Visibility")
            layout = QVBoxLayout()
            
            # Class selection controls
            class_layout = QHBoxLayout()
            
            # All classes toggle
            all_classes_cb = QCheckBox("All Classes")
            all_classes_cb.setChecked(all(self._class_visibility.values()))
            all_classes_cb.toggled.connect(self._on_all_classes_toggled)
            class_layout.addWidget(all_classes_cb)
            
            # Individual class toggles
            for class_id in range(min(self._max_classes, 8)):  # Show first 8 classes
                checkbox = QCheckBox(f"C{class_id}")
                checkbox.setChecked(self._class_visibility[class_id])
                checkbox.toggled.connect(lambda checked, cid=class_id: self._on_class_visibility_toggled(cid, checked))
                self._class_checkboxes[class_id] = checkbox
                class_layout.addWidget(checkbox)
            
            layout.addLayout(class_layout)
            
            # Additional classes if more than 8
            if self._max_classes > 8:
                additional_layout = QHBoxLayout()
                for class_id in range(8, self._max_classes):
                    checkbox = QCheckBox(f"C{class_id}")
                    checkbox.setChecked(self._class_visibility[class_id])
                    checkbox.toggled.connect(lambda checked, cid=class_id: self._on_class_visibility_toggled(cid, checked))
                    self._class_checkboxes[class_id] = checkbox
                    additional_layout.addWidget(checkbox)
                layout.addLayout(additional_layout)
            
            group.setLayout(layout)
            self._layout.addWidget(group)
            
        except Exception as e:
            self.emit_error(f"Error adding class visibility group: {str(e)}")
    
    def _add_opacity_controls_group(self) -> None:
        """Add opacity controls group."""
        try:
            group = QGroupBox("Point Opacity")
            layout = QVBoxLayout()
            
            # Opacity controls for different point types
            opacity_controls = [
                ('current_session', 'Current Session'),
                ('previous_session', 'Previous Session'),
                ('selected_points', 'Selected Points'),
                ('unselected_points', 'Unselected Points'),
                ('recent_points', 'Recent Points'),
                ('old_points', 'Old Points')
            ]
            
            for opacity_type, display_name in opacity_controls:
                control_layout = QHBoxLayout()
                
                # Label
                label = QLabel(display_name)
                control_layout.addWidget(label)
                
                # Slider
                slider = QSlider(1)  # Qt.Horizontal
                slider.setRange(0, 100)
                slider.setValue(int(self._point_opacities[opacity_type] * 100))
                slider.valueChanged.connect(lambda value, ot=opacity_type: self._on_opacity_changed(ot, value))
                self._opacity_sliders[opacity_type] = slider
                control_layout.addWidget(slider)
                
                # Value label
                value_label = QLabel(f"{int(self._point_opacities[opacity_type] * 100)}%")
                self._opacity_labels[opacity_type] = value_label
                control_layout.addWidget(value_label)
                
                layout.addLayout(control_layout)
            
            group.setLayout(layout)
            self._layout.addWidget(group)
            
        except Exception as e:
            self.emit_error(f"Error adding opacity controls group: {str(e)}")
    
    def _add_preset_controls(self) -> None:
        """Add preset controls."""
        try:
            group = QGroupBox("Visibility Presets")
            layout = QHBoxLayout()
            
            # Preset selection
            preset_combo = QComboBox()
            for preset_name, preset_data in self._visibility_presets.items():
                preset_combo.addItem(preset_data['name'], preset_name)
            preset_combo.currentTextChanged.connect(self._on_preset_selected)
            layout.addWidget(preset_combo)
            
            # Apply preset button
            apply_button = QPushButton("Apply")
            apply_button.clicked.connect(lambda: self._apply_preset(preset_combo.currentData()))
            layout.addWidget(apply_button)
            
            group.setLayout(layout)
            self._layout.addWidget(group)
            
        except Exception as e:
            self.emit_error(f"Error adding preset controls: {str(e)}")
    
    def _add_action_buttons(self) -> None:
        """Add action buttons."""
        try:
            button_layout = QHBoxLayout()
            
            # Show all button
            show_all_button = QPushButton("Show All")
            show_all_button.clicked.connect(self._show_all_points)
            button_layout.addWidget(show_all_button)
            
            # Hide all button
            hide_all_button = QPushButton("Hide All")
            hide_all_button.clicked.connect(self._hide_all_points)
            button_layout.addWidget(hide_all_button)
            
            # Reset button
            reset_button = QPushButton("Reset")
            reset_button.clicked.connect(self._reset_to_defaults)
            button_layout.addWidget(reset_button)
            
            self._layout.addLayout(button_layout)
            
        except Exception as e:
            self.emit_error(f"Error adding action buttons: {str(e)}")
    
    def _on_visibility_toggled(self, visibility_type: str, checked: bool) -> None:
        """Handle visibility toggle."""
        try:
            self._visibility_states[visibility_type] = checked
            self._visibility_stats['total_toggles'] += 1
            
            # Handle all points toggle
            if visibility_type == 'all_points':
                for other_type in self._visibility_states:
                    if other_type != 'all_points':
                        self._visibility_states[other_type] = checked
                        if other_type in self._visibility_checkboxes:
                            self._visibility_checkboxes[other_type].setChecked(checked)
            
            # Emit signal
            self.visibilityChanged.emit(visibility_type, checked)
            
            # Call callback if registered
            if visibility_type in self._visibility_callbacks:
                self._visibility_callbacks[visibility_type](checked)
            
        except Exception as e:
            self.emit_error(f"Error handling visibility toggle: {str(e)}")
    
    def _on_class_visibility_toggled(self, class_id: int, checked: bool) -> None:
        """Handle class visibility toggle."""
        try:
            self._class_visibility[class_id] = checked
            self._visibility_stats['class_toggles'] += 1
            
            # Emit signal
            self.classVisibilityChanged.emit(class_id, checked)
            
            # Call callback if registered
            if class_id in self._class_callbacks:
                self._class_callbacks[class_id](checked)
            
        except Exception as e:
            self.emit_error(f"Error handling class visibility toggle: {str(e)}")
    
    def _on_session_visibility_toggled(self, session_type: str, checked: bool) -> None:
        """Handle session visibility toggle."""
        try:
            self._session_visibility[session_type] = checked
            self._visibility_stats['session_toggles'] += 1
            
            # Emit signal
            self.sessionVisibilityChanged.emit(session_type, checked)
            
            # Call callback if registered
            if session_type in self._session_callbacks:
                self._session_callbacks[session_type](checked)
            
        except Exception as e:
            self.emit_error(f"Error handling session visibility toggle: {str(e)}")
    
    def _on_all_classes_toggled(self, checked: bool) -> None:
        """Handle all classes toggle."""
        try:
            for class_id in range(self._max_classes):
                self._class_visibility[class_id] = checked
                if class_id in self._class_checkboxes:
                    self._class_checkboxes[class_id].setChecked(checked)
                
                # Emit signal for each class
                self.classVisibilityChanged.emit(class_id, checked)
            
        except Exception as e:
            self.emit_error(f"Error handling all classes toggle: {str(e)}")
    
    def _on_opacity_changed(self, opacity_type: str, value: int) -> None:
        """Handle opacity change."""
        try:
            opacity = value / 100.0
            self._point_opacities[opacity_type] = opacity
            self._visibility_stats['opacity_changes'] += 1
            
            # Update label
            if opacity_type in self._opacity_labels:
                self._opacity_labels[opacity_type].setText(f"{value}%")
            
            # Emit signal
            self.opacityChanged.emit(opacity_type, opacity)
            
            # Call callback if registered
            if opacity_type in self._opacity_callbacks:
                self._opacity_callbacks[opacity_type](opacity)
            
        except Exception as e:
            self.emit_error(f"Error handling opacity change: {str(e)}")
    
    def _on_preset_selected(self, preset_name: str) -> None:
        """Handle preset selection."""
        # This is just for UI feedback, actual application happens on button click
        pass
    
    def _apply_preset(self, preset_name: str) -> None:
        """Apply a visibility preset."""
        try:
            if preset_name not in self._visibility_presets:
                return
            
            preset_data = self._visibility_presets[preset_name]
            settings = preset_data['settings']
            
            # Apply settings
            for visibility_type, value in settings.items():
                if visibility_type in self._visibility_states:
                    self._visibility_states[visibility_type] = value
                    if visibility_type in self._visibility_checkboxes:
                        self._visibility_checkboxes[visibility_type].setChecked(value)
                    
                    # Emit signal
                    self.visibilityChanged.emit(visibility_type, value)
            
            self.emit_state_changed({'preset_applied': preset_name})
            
        except Exception as e:
            self.emit_error(f"Error applying preset: {str(e)}")
    
    def _show_all_points(self) -> None:
        """Show all points."""
        try:
            for visibility_type in self._visibility_states:
                self._visibility_states[visibility_type] = True
                if visibility_type in self._visibility_checkboxes:
                    self._visibility_checkboxes[visibility_type].setChecked(True)
            
            for class_id in range(self._max_classes):
                self._class_visibility[class_id] = True
                if class_id in self._class_checkboxes:
                    self._class_checkboxes[class_id].setChecked(True)
            
            self.allPointsToggled.emit(True)
            
        except Exception as e:
            self.emit_error(f"Error showing all points: {str(e)}")
    
    def _hide_all_points(self) -> None:
        """Hide all points."""
        try:
            for visibility_type in self._visibility_states:
                self._visibility_states[visibility_type] = False
                if visibility_type in self._visibility_checkboxes:
                    self._visibility_checkboxes[visibility_type].setChecked(False)
            
            for class_id in range(self._max_classes):
                self._class_visibility[class_id] = False
                if class_id in self._class_checkboxes:
                    self._class_checkboxes[class_id].setChecked(False)
            
            self.allPointsToggled.emit(False)
            
        except Exception as e:
            self.emit_error(f"Error hiding all points: {str(e)}")
    
    def _reset_to_defaults(self) -> None:
        """Reset to default visibility settings."""
        try:
            # Reset visibility states
            default_states = {
                'all_points': True,
                'current_session': True,
                'previous_session': True,
                'selected_points': True,
                'unselected_points': True,
                'recent_points': True,
                'old_points': True
            }
            
            for visibility_type, default_value in default_states.items():
                self._visibility_states[visibility_type] = default_value
                if visibility_type in self._visibility_checkboxes:
                    self._visibility_checkboxes[visibility_type].setChecked(default_value)
            
            # Reset class visibility
            for class_id in range(self._max_classes):
                self._class_visibility[class_id] = True
                if class_id in self._class_checkboxes:
                    self._class_checkboxes[class_id].setChecked(True)
            
            # Reset opacities
            default_opacities = {
                'current_session': 1.0,
                'previous_session': 0.5,
                'selected_points': 1.0,
                'unselected_points': 0.8,
                'recent_points': 1.0,
                'old_points': 0.6
            }
            
            for opacity_type, default_value in default_opacities.items():
                self._point_opacities[opacity_type] = default_value
                if opacity_type in self._opacity_sliders:
                    self._opacity_sliders[opacity_type].setValue(int(default_value * 100))
                if opacity_type in self._opacity_labels:
                    self._opacity_labels[opacity_type].setText(f"{int(default_value * 100)}%")
            
            self.emit_state_changed({'reset_to_defaults': True})
            
        except Exception as e:
            self.emit_error(f"Error resetting to defaults: {str(e)}")
    
    def _clear_layout(self) -> None:
        """Clear the layout."""
        try:
            while self._layout.count():
                child = self._layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
        except Exception as e:
            self.emit_error(f"Error clearing layout: {str(e)}")
    
    def set_visibility_callback(self, visibility_type: str, callback: Callable[[bool], None]) -> None:
        """Set callback for visibility changes."""
        self._visibility_callbacks[visibility_type] = callback
    
    def set_class_callback(self, class_id: int, callback: Callable[[bool], None]) -> None:
        """Set callback for class visibility changes."""
        self._class_callbacks[class_id] = callback
    
    def set_session_callback(self, session_type: str, callback: Callable[[bool], None]) -> None:
        """Set callback for session visibility changes."""
        self._session_callbacks[session_type] = callback
    
    def set_opacity_callback(self, opacity_type: str, callback: Callable[[float], None]) -> None:
        """Set callback for opacity changes."""
        self._opacity_callbacks[opacity_type] = callback
    
    def get_visibility_state(self, visibility_type: str) -> bool:
        """Get visibility state."""
        return self._visibility_states.get(visibility_type, True)
    
    def get_class_visibility(self, class_id: int) -> bool:
        """Get class visibility."""
        return self._class_visibility.get(class_id, True)
    
    def get_session_visibility(self, session_type: str) -> bool:
        """Get session visibility."""
        return self._session_visibility.get(session_type, True)
    
    def get_opacity(self, opacity_type: str) -> float:
        """Get opacity value."""
        return self._point_opacities.get(opacity_type, 1.0)
    
    def get_all_visibility_states(self) -> Dict[str, bool]:
        """Get all visibility states."""
        return self._visibility_states.copy()
    
    def get_all_class_visibility(self) -> Dict[int, bool]:
        """Get all class visibility states."""
        return self._class_visibility.copy()
    
    def get_all_session_visibility(self) -> Dict[str, bool]:
        """Get all session visibility states."""
        return self._session_visibility.copy()
    
    def get_all_opacities(self) -> Dict[str, float]:
        """Get all opacity values."""
        return self._point_opacities.copy()
    
    def add_visibility_preset(self, name: str, preset_data: Dict[str, Any]) -> None:
        """Add a custom visibility preset."""
        self._visibility_presets[name] = preset_data
        self.emit_state_changed({'presets_count': len(self._visibility_presets)})
    
    def remove_visibility_preset(self, name: str) -> bool:
        """Remove a visibility preset."""
        if name in self._visibility_presets:
            del self._visibility_presets[name]
            self.emit_state_changed({'presets_count': len(self._visibility_presets)})
            return True
        return False
    
    def get_visibility_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get all visibility presets."""
        return self._visibility_presets.copy()
    
    def get_visibility_statistics(self) -> Dict[str, Any]:
        """Get visibility control statistics."""
        return {
            'total_toggles': self._visibility_stats['total_toggles'],
            'class_toggles': self._visibility_stats['class_toggles'],
            'session_toggles': self._visibility_stats['session_toggles'],
            'opacity_changes': self._visibility_stats['opacity_changes'],
            'visible_classes': sum(1 for visible in self._class_visibility.values() if visible),
            'total_classes': len(self._class_visibility),
            'all_points_visible': self._visibility_states['all_points'],
            'presets_count': len(self._visibility_presets)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get point visibility controls statistics."""
        stats = super().get_statistics()
        stats.update({
            'max_classes': self._max_classes,
            'compact_layout': self._compact_layout,
            'show_opacity_controls': self._show_opacity_controls,
            'show_class_controls': self._show_class_controls,
            'show_session_controls': self._show_session_controls,
            'filter_enabled': self._filter_enabled,
            'visibility_statistics': self.get_visibility_statistics()
        })
        return stats