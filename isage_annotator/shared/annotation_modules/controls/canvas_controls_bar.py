"""
Canvas Controls Bar - Advanced toolbar for annotation canvas

This component provides sophisticated canvas control functionality including:
- Zoom controls with presets and custom levels
- Pan/navigation tools 
- Display toggle controls (grid, overlays, channels)
- View mode switching
- Canvas statistics display
- Quick action buttons
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QSlider, QComboBox, QSpinBox, QCheckBox, QButtonGroup,
    QFrame, QToolButton, QMenu, QAction, QSeparator, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QPixmap

logger = logging.getLogger(__name__)


class ZoomControls(QWidget):
    """Zoom control widget with buttons and slider."""
    
    # Signals
    zoomChanged = pyqtSignal(float)  # zoom_factor
    zoomToFit = pyqtSignal()
    zoomToSelection = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._zoom_factor = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._zoom_presets = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0]
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup zoom controls UI."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Zoom out button
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_out_btn.setToolTip("Zoom out (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(self.zoom_out_btn)
        
        # Zoom level display/input
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(80)
        self.zoom_combo.addItems([f"{int(z*100)}%" for z in self._zoom_presets])
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_text_changed)
        layout.addWidget(self.zoom_combo)
        
        # Zoom in button
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(self.zoom_in_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Fit buttons
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setToolTip("Zoom to fit image (Ctrl+0)")
        self.fit_btn.clicked.connect(self.zoomToFit.emit)
        layout.addWidget(self.fit_btn)
        
        # 1:1 button
        self.actual_size_btn = QPushButton("1:1")
        self.actual_size_btn.setToolTip("Actual size (Ctrl+1)")
        self.actual_size_btn.clicked.connect(lambda: self.set_zoom(1.0))
        layout.addWidget(self.actual_size_btn)
        
        # Apply styling
        self.apply_styling()
    
    def apply_styling(self):
        """Apply consistent styling to zoom controls."""
        button_style = """
            QPushButton {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #e2e8f0;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border-color: #6b7280;
            }
            QPushButton:pressed {
                background-color: #1f2937;
            }
        """
        
        self.zoom_out_btn.setStyleSheet(button_style)
        self.zoom_in_btn.setStyleSheet(button_style)
        self.fit_btn.setStyleSheet(button_style)
        self.actual_size_btn.setStyleSheet(button_style)
        
        self.zoom_combo.setStyleSheet("""
            QComboBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e2e8f0;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                color: #9ca3af;
            }
        """)
    
    def zoom_in(self):
        """Zoom in by 25%."""
        new_zoom = min(self._max_zoom, self._zoom_factor * 1.25)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        """Zoom out by 25%."""
        new_zoom = max(self._min_zoom, self._zoom_factor * 0.8)
        self.set_zoom(new_zoom)
    
    def set_zoom(self, zoom_factor: float):
        """Set zoom level."""
        zoom_factor = max(self._min_zoom, min(self._max_zoom, zoom_factor))
        if zoom_factor != self._zoom_factor:
            self._zoom_factor = zoom_factor
            self.update_zoom_display()
            self.zoomChanged.emit(zoom_factor)
    
    def update_zoom_display(self):
        """Update zoom display in combo box."""
        percentage = int(self._zoom_factor * 100)
        self.zoom_combo.setCurrentText(f"{percentage}%")
    
    def on_zoom_text_changed(self, text: str):
        """Handle manual zoom input."""
        try:
            # Parse percentage
            text = text.replace('%', '').strip()
            if text:
                percentage = float(text)
                zoom_factor = percentage / 100.0
                self.set_zoom(zoom_factor)
        except ValueError:
            # Invalid input, restore current zoom
            self.update_zoom_display()
    
    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._zoom_factor


class ViewModeControls(QWidget):
    """View mode controls for different canvas display modes."""
    
    # Signals
    viewModeChanged = pyqtSignal(str)  # mode_name
    overlayToggled = pyqtSignal(str, bool)  # overlay_name, visible
    channelToggled = pyqtSignal(str, bool)  # channel_name, visible
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._view_modes = ["Annotation", "Review", "Comparison", "Analysis"]
        self._current_mode = "Annotation"
        self._overlays = {"Grid": False, "Ground Truth": False, "Predictions": False}
        self._channels = {"Red": True, "Green": True, "Blue": True}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup view mode controls."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # View mode selector
        layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self._view_modes)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Overlay toggles
        layout.addWidget(QLabel("Show:"))
        
        self.overlay_checkboxes = {}
        for overlay_name in self._overlays:
            checkbox = QCheckBox(overlay_name)
            checkbox.setChecked(self._overlays[overlay_name])
            checkbox.stateChanged.connect(
                lambda state, name=overlay_name: self.on_overlay_toggled(name, state == 2)
            )
            self.overlay_checkboxes[overlay_name] = checkbox
            layout.addWidget(checkbox)
        
        # RGB channel toggles
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        self.channel_checkboxes = {}
        for channel_name in self._channels:
            checkbox = QCheckBox(channel_name[0])  # Use first letter (R, G, B)
            checkbox.setChecked(self._channels[channel_name])
            checkbox.setToolTip(f"{channel_name} channel")
            checkbox.stateChanged.connect(
                lambda state, name=channel_name: self.on_channel_toggled(name, state == 2)
            )
            self.channel_checkboxes[channel_name] = checkbox
            layout.addWidget(checkbox)
        
        # Apply styling
        self.apply_styling()
    
    def apply_styling(self):
        """Apply styling to view mode controls."""
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e2e8f0;
                min-width: 80px;
            }
        """)
        
        checkbox_style = """
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #4b5563;
                border-radius: 2px;
                background: #374151;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #2563eb;
            }
        """
        
        for checkbox in self.overlay_checkboxes.values():
            checkbox.setStyleSheet(checkbox_style)
        
        for checkbox in self.channel_checkboxes.values():
            checkbox.setStyleSheet(checkbox_style)
    
    def on_mode_changed(self, mode: str):
        """Handle view mode change."""
        self._current_mode = mode
        self.viewModeChanged.emit(mode)
        logger.info(f"View mode changed to: {mode}")
    
    def on_overlay_toggled(self, overlay_name: str, visible: bool):
        """Handle overlay toggle."""
        self._overlays[overlay_name] = visible
        self.overlayToggled.emit(overlay_name, visible)
        logger.debug(f"Overlay '{overlay_name}' {'enabled' if visible else 'disabled'}")
    
    def on_channel_toggled(self, channel_name: str, visible: bool):
        """Handle channel toggle."""
        self._channels[channel_name] = visible
        self.channelToggled.emit(channel_name, visible)
        logger.debug(f"Channel '{channel_name}' {'enabled' if visible else 'disabled'}")
    
    def get_current_mode(self) -> str:
        """Get current view mode."""
        return self._current_mode
    
    def get_overlay_states(self) -> Dict[str, bool]:
        """Get current overlay states."""
        return self._overlays.copy()
    
    def get_channel_states(self) -> Dict[str, bool]:
        """Get current channel states."""
        return self._channels.copy()


class StatusDisplay(QWidget):
    """Status and information display for canvas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._image_info = {"name": "", "size": (0, 0), "format": ""}
        self._canvas_info = {"zoom": 1.0, "pan": (0, 0)}
        self._annotation_stats = {"count": 0, "classes": 0}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup status display."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        
        # Image info
        self.image_label = QLabel("No image")
        self.image_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.image_label)
        
        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #4b5563;")
        layout.addWidget(separator)
        
        # Mouse coordinates
        self.coords_label = QLabel("(0, 0)")
        self.coords_label.setStyleSheet("color: #10b981; font-size: 11px; font-family: monospace;")
        layout.addWidget(self.coords_label)
        
        # Separator
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #4b5563;")
        layout.addWidget(separator2)
        
        # Annotation count
        self.annotations_label = QLabel("0 annotations")
        self.annotations_label.setStyleSheet("color: #3b82f6; font-size: 11px;")
        layout.addWidget(self.annotations_label)
        
        layout.addStretch()
        
        # Progress indicator for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(100, 14)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4b5563;
                border-radius: 3px;
                background: #374151;
                text-align: center;
                font-size: 10px;
                color: #e2e8f0;
            }
            QProgressBar::chunk {
                background: #3b82f6;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
    
    def update_image_info(self, name: str, size: Tuple[int, int], format: str = ""):
        """Update image information display."""
        self._image_info = {"name": name, "size": size, "format": format}
        width, height = size
        text = f"{name} ({width}×{height})"
        if format:
            text += f" {format}"
        self.image_label.setText(text)
        self.image_label.setToolTip(f"Image: {name}\nSize: {width}×{height}\nFormat: {format}")
    
    def update_mouse_coordinates(self, x: int, y: int):
        """Update mouse coordinate display."""
        self.coords_label.setText(f"({x}, {y})")
    
    def update_annotation_count(self, count: int, classes: int = 0):
        """Update annotation statistics."""
        self._annotation_stats = {"count": count, "classes": classes}
        if classes > 0:
            self.annotations_label.setText(f"{count} annotations ({classes} classes)")
        else:
            self.annotations_label.setText(f"{count} annotations")
    
    def show_progress(self, message: str = "", maximum: int = 0):
        """Show progress bar with optional message."""
        self.progress_bar.setVisible(True)
        if maximum > 0:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(0)
        else:
            # Indeterminate progress
            self.progress_bar.setRange(0, 0)
        
        if message:
            self.progress_bar.setFormat(message)
    
    def update_progress(self, value: int):
        """Update progress bar value."""
        self.progress_bar.setValue(value)
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)


class CanvasControlsBar(QWidget):
    """
    Advanced canvas controls bar providing comprehensive canvas control functionality.
    
    Features:
    - Zoom controls with presets and custom input
    - View mode switching (annotation, review, comparison)
    - Display toggles (grid, overlays, RGB channels)
    - Real-time status and coordinate display
    - Progress indication for long operations
    - Keyboard shortcut support
    """
    
    # Signals
    zoomChanged = pyqtSignal(float)  # zoom_factor
    zoomToFit = pyqtSignal()
    viewModeChanged = pyqtSignal(str)  # mode_name
    overlayToggled = pyqtSignal(str, bool)  # overlay_name, visible
    channelToggled = pyqtSignal(str, bool)  # channel_name, visible
    actionRequested = pyqtSignal(str, object)  # action_name, data
    
    def __init__(self, parent=None, name: str = "canvas_controls_bar", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # Components
        self.zoom_controls = None
        self.view_mode_controls = None
        self.status_display = None
        
        # State
        self._enabled = True
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"CanvasControlsBar '{name}' v{version} created")
    
    def setup_ui(self):
        """Setup the controls bar UI."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)
        
        # Canvas tools section
        tools_frame = self.create_tools_section()
        layout.addWidget(tools_frame)
        
        # Zoom controls
        self.zoom_controls = ZoomControls()
        self.zoom_controls.zoomChanged.connect(self.zoomChanged.emit)
        self.zoom_controls.zoomToFit.connect(self.zoomToFit.emit)
        layout.addWidget(self.zoom_controls)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # View mode controls
        self.view_mode_controls = ViewModeControls()
        self.view_mode_controls.viewModeChanged.connect(self.viewModeChanged.emit)
        self.view_mode_controls.overlayToggled.connect(self.overlayToggled.emit)
        self.view_mode_controls.channelToggled.connect(self.channelToggled.emit)
        layout.addWidget(self.view_mode_controls)
        
        # Flexible space
        layout.addStretch()
        
        # Status display
        self.status_display = StatusDisplay()
        layout.addWidget(self.status_display)
        
        # Apply theme
        self.apply_dark_theme()
    
    def create_tools_section(self) -> QWidget:
        """Create quick tools section."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Quick action buttons
        self.pan_btn = QPushButton("PAN")
        self.pan_btn.setFixedSize(35, 28)
        self.pan_btn.setToolTip("Pan tool (Space)")
        self.pan_btn.setCheckable(True)
        self.pan_btn.clicked.connect(lambda: self.actionRequested.emit("pan_mode", self.pan_btn.isChecked()))
        layout.addWidget(self.pan_btn)
        
        self.select_btn = QPushButton("SEL")
        self.select_btn.setFixedSize(35, 28)
        self.select_btn.setToolTip("Selection tool (S)")
        self.select_btn.setCheckable(True)
        self.select_btn.clicked.connect(lambda: self.actionRequested.emit("select_mode", self.select_btn.isChecked()))
        layout.addWidget(self.select_btn)
        
        return frame
    
    def apply_dark_theme(self):
        """Apply dark theme to the controls bar."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: #e2e8f0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QFrame {
                border: none;
            }
            QLabel {
                color: #e2e8f0;
                border: none;
                background: transparent;
            }
        """)
        
        # Style tool buttons
        tool_button_style = """
            QPushButton {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                border-color: #2563eb;
            }
        """
        
        if hasattr(self, 'pan_btn'):
            self.pan_btn.setStyleSheet(tool_button_style)
        if hasattr(self, 'select_btn'):
            self.select_btn.setStyleSheet(tool_button_style)
    
    # Public API for external control
    
    def set_zoom(self, zoom_factor: float):
        """Set zoom level from external source."""
        if self.zoom_controls:
            self.zoom_controls.set_zoom(zoom_factor)
    
    def set_view_mode(self, mode: str):
        """Set view mode from external source."""
        if self.view_mode_controls and mode in self.view_mode_controls._view_modes:
            index = self.view_mode_controls._view_modes.index(mode)
            self.view_mode_controls.mode_combo.setCurrentIndex(index)
    
    def update_image_info(self, name: str, size: Tuple[int, int], format: str = ""):
        """Update image information display."""
        if self.status_display:
            self.status_display.update_image_info(name, size, format)
    
    def update_mouse_coordinates(self, x: int, y: int):
        """Update mouse coordinate display."""
        if self.status_display:
            self.status_display.update_mouse_coordinates(x, y)
    
    def update_annotation_count(self, count: int, classes: int = 0):
        """Update annotation count display."""
        if self.status_display:
            self.status_display.update_annotation_count(count, classes)
    
    def show_progress(self, message: str = "", maximum: int = 0):
        """Show progress indicator."""
        if self.status_display:
            self.status_display.show_progress(message, maximum)
    
    def update_progress(self, value: int):
        """Update progress value."""
        if self.status_display:
            self.status_display.update_progress(value)
    
    def hide_progress(self):
        """Hide progress indicator."""
        if self.status_display:
            self.status_display.hide_progress()
    
    def set_enabled(self, enabled: bool):
        """Enable/disable the controls bar."""
        self._enabled = enabled
        self.setEnabled(enabled)
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current control settings."""
        settings = {
            'zoom_factor': self.zoom_controls.get_zoom_factor() if self.zoom_controls else 1.0,
            'view_mode': self.view_mode_controls.get_current_mode() if self.view_mode_controls else "Annotation",
            'overlays': self.view_mode_controls.get_overlay_states() if self.view_mode_controls else {},
            'channels': self.view_mode_controls.get_channel_states() if self.view_mode_controls else {},
            'enabled': self._enabled
        }
        return settings
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get controls bar statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'enabled': self._enabled,
            'current_settings': self.get_current_settings()
        }