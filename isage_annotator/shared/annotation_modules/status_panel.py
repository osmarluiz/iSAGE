"""
Enhanced Status Panel - Professional status panel with interactive minimap

This component provides the enhanced status panel that matches the functioning system exactly,
including the interactive minimap, image info, and comprehensive status tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QProgressBar, QTextEdit, QFrame, QScrollArea, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
from datetime import datetime, timedelta
import time

# Import the interactive minimap with absolute path
import importlib.util
import os
from pathlib import Path

# Get the current directory and construct path to interactive_minimap
current_dir = Path(__file__).parent
minimap_path = current_dir / 'ui' / 'interactive_minimap.py'

# Import interactive minimap module
spec = importlib.util.spec_from_file_location("interactive_minimap", minimap_path)
minimap_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(minimap_module)
InteractiveMinimap = minimap_module.InteractiveMinimap

logger = logging.getLogger(__name__)


class StatusPanel(QWidget):
    """
    Enhanced status panel matching the functioning system exactly.
    
    Features:
    - Interactive minimap with viewport navigation
    - Image information display (filename, size, format)
    - System status and progress tracking
    - Message log with timestamps
    - Component status tracking
    - Professional styling matching functioning system
    """
    
    # Signals
    statusChanged = pyqtSignal(str, str)  # status_type, message
    minimapNavigated = pyqtSignal(int, int)  # pan_x, pan_y
    minimapClicked = pyqtSignal(float, float)  # image_x, image_y
    
    def __init__(self, parent=None, name: str = "enhanced_status_panel", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        self.initialized = False
        
        # State
        self._current_status: str = "Ready"
        self._current_status_type: str = "info"
        self._messages: List[Dict[str, Any]] = []
        self._max_messages: int = 100
        self._component_status: Dict[str, str] = {}
        
        # Time and annotation tracking
        self._session_start_time = time.time()
        self._total_annotations = 0
        self._current_image_annotations = 0
        self._annotation_times = []  # Track time per annotation
        self._last_annotation_time = None
        
        # Messages UI state
        self._messages_expanded = False
        
        # Image information
        self._current_image_info = {
            'filename': '-',
            'resolution': '-',
            'format': '-',
            'size_mb': 0.0
        }
        
        # UI components
        self.minimap_widget = None
        self.filename_label = None
        self.resolution_label = None
        self.format_label = None
        self.messages_text = None
        self.progress_bar = None
        
        # Enhanced progress components
        self.time_elapsed_label = None
        self.time_remaining_label = None
        self.avg_time_label = None
        self.annotation_count_label = None
        self.current_image_count_label = None
        
        # Messages components
        self.messages_toggle_button = None
        self.last_message_label = None
        self.messages_container = None
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"EnhancedStatusPanel '{name}' v{version} created")
    
    def initialize(self, panel_width: int = 384, theme: str = 'dark', **kwargs) -> bool:
        """Initialize the enhanced status panel."""
        try:
            # Apply sizing - match functioning system exactly
            if panel_width:
                self.setFixedWidth(panel_width)
            
            # Apply theme
            if theme == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            
            self.initialized = True
            self.add_status_message("System", "Enhanced status panel initialized", "info")
            logger.info(f"EnhancedStatusPanel initialized: width={panel_width}, theme={theme}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced status panel: {e}")
            return False
    
    def setup_ui(self):
        """Create the enhanced status panel UI matching functioning system."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Interactive minimap section
        minimap_group = self.create_minimap_section()
        layout.addWidget(minimap_group)
        
        # Image information section
        image_info_group = self.create_image_info_section()
        layout.addWidget(image_info_group)
        
        # Current status section removed as requested

        # Progress section - expands to fill available vertical space
        progress_group = self.create_progress_section()
        layout.addWidget(progress_group, 1)

        # Messages section (fixed height)
        messages_group = self.create_messages_section()
        layout.addWidget(messages_group)
    
    def create_header(self) -> QWidget:
        """Create a minimal header section."""
        # Return an empty widget instead of the header text
        header = QWidget()
        header.setFixedHeight(0)  # No space for header
        return header
    
    def create_minimap_section(self) -> QGroupBox:
        """Create the interactive minimap section matching functioning system."""
        group = QGroupBox("🗺️ Mini-Map")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create interactive minimap widget
        self.minimap_widget = InteractiveMinimap(
            parent=self,
            name="status_panel_minimap",
            version="1.0.0"
        )
        
        # Connect minimap signals
        self.minimap_widget.viewChanged.connect(self.on_minimap_view_changed)
        self.minimap_widget.navigationRequested.connect(self.on_minimap_navigation_requested)
        
        layout.addWidget(self.minimap_widget)
        
        # Center the minimap in the group
        layout.setAlignment(Qt.AlignCenter)
        
        return group
    
    def create_image_info_section(self) -> QGroupBox:
        """Create the image information section matching functioning system."""
        group = QGroupBox("📸 Image Info")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # File name
        self.filename_label = QLabel("File: -")
        self.filename_label.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.filename_label)
        
        # Resolution
        self.resolution_label = QLabel("Size: -")
        self.resolution_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.resolution_label)
        
        # Format
        self.format_label = QLabel("Format: -")
        self.format_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.format_label)
        
        # File size
        self.size_label = QLabel("Size: -")
        self.size_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.size_label)
        
        return group
    
    
    def create_progress_section(self) -> QGroupBox:
        """Create annotation counts section with per-class breakdown."""
        group = QGroupBox("📊 Annotation Points")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Overall counts section
        count_layout = QHBoxLayout()
        count_layout.setSpacing(10)

        # Total annotations
        count_left = QVBoxLayout()
        self.annotation_count_label = QLabel("🎯 0")
        self.annotation_count_label.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        self.annotation_count_label.setAlignment(Qt.AlignCenter)
        count_left.addWidget(QLabel("Total Points"))
        count_left.addWidget(self.annotation_count_label)
        count_left.itemAt(0).widget().setStyleSheet("color: #6b7280; font-size: 9px;")
        count_left.itemAt(0).widget().setAlignment(Qt.AlignCenter)
        count_layout.addLayout(count_left)

        # Current image annotations
        count_right = QVBoxLayout()
        self.current_image_count_label = QLabel("📍 0")
        self.current_image_count_label.setStyleSheet("color: #8b5cf6; font-size: 11px; font-weight: bold;")
        self.current_image_count_label.setAlignment(Qt.AlignCenter)
        count_right.addWidget(QLabel("This Image"))
        count_right.addWidget(self.current_image_count_label)
        count_right.itemAt(0).widget().setStyleSheet("color: #6b7280; font-size: 9px;")
        count_right.itemAt(0).widget().setAlignment(Qt.AlignCenter)
        count_layout.addLayout(count_right)

        layout.addLayout(count_layout)

        # Per-class counts with Img and Total columns
        per_class_group = QGroupBox("Points by Class")
        per_class_layout = QVBoxLayout(per_class_group)
        per_class_layout.setSpacing(3)
        per_class_layout.setContentsMargins(8, 8, 8, 8)

        # Header row
        header_row = QHBoxLayout()
        header_row.setSpacing(4)
        class_header = QLabel("Class")
        class_header.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        header_row.addWidget(class_header)
        header_row.addStretch()

        img_header = QLabel("Img")
        img_header.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        img_header.setFixedWidth(35)
        img_header.setAlignment(Qt.AlignRight)
        header_row.addWidget(img_header)

        total_header = QLabel("Total")
        total_header.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        total_header.setFixedWidth(45)
        total_header.setAlignment(Qt.AlignRight)
        header_row.addWidget(total_header)

        per_class_layout.addLayout(header_row)

        # Store per-class labels for updating {class_id: {'current': QLabel, 'total': QLabel}}
        self.class_count_labels = {}

        # Will be populated when class config is loaded
        self.per_class_container = per_class_layout

        layout.addWidget(per_class_group)

        # New points in this session
        new_points_layout = QHBoxLayout()
        new_points_left = QVBoxLayout()
        self.new_points_label = QLabel("✨ 0")
        self.new_points_label.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold;")
        self.new_points_label.setAlignment(Qt.AlignCenter)
        new_points_left.addWidget(QLabel("New Points"))
        new_points_left.addWidget(self.new_points_label)
        new_points_left.itemAt(0).widget().setStyleSheet("color: #6b7280; font-size: 9px;")
        new_points_left.itemAt(0).widget().setAlignment(Qt.AlignCenter)
        new_points_layout.addLayout(new_points_left)

        layout.addLayout(new_points_layout)

        return group
    
    def create_messages_section(self) -> QGroupBox:
        """Create the collapsible messages section."""
        group = QGroupBox("💬 Messages")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        
        # Toggle button and last message display
        header_layout = QHBoxLayout()
        
        # Last message label (compact display)
        self.last_message_label = QLabel("Ready")
        self.last_message_label.setStyleSheet("""
            QLabel {
                background: #1a202c;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 10px;
                padding: 6px;
            }
        """)
        self.last_message_label.setWordWrap(True)
        header_layout.addWidget(self.last_message_label, 1)
        
        # Toggle button
        self.messages_toggle_button = QPushButton("⬇")
        self.messages_toggle_button.setFixedSize(24, 24)
        self.messages_toggle_button.setStyleSheet("""
            QPushButton {
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #4b5563;
            }
            QPushButton:pressed {
                background: #1f2937;
            }
        """)
        self.messages_toggle_button.clicked.connect(self.toggle_messages)
        header_layout.addWidget(self.messages_toggle_button)
        
        layout.addLayout(header_layout)
        
        # Expandable messages container
        self.messages_container = QWidget()
        self.messages_container.setVisible(False)  # Start collapsed
        container_layout = QVBoxLayout(self.messages_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Full messages text area
        self.messages_text = QTextEdit()
        self.messages_text.setMaximumHeight(120)  # Smaller when expanded
        self.messages_text.setReadOnly(True)
        self.messages_text.setStyleSheet("""
            QTextEdit {
                background: #1a202c;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 10px;
                padding: 4px;
            }
        """)
        container_layout.addWidget(self.messages_text)
        
        # Message count badge
        self.message_count_label = QLabel("0 messages")
        self.message_count_label.setStyleSheet("color: #6b7280; font-size: 9px;")
        self.message_count_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.message_count_label)
        
        layout.addWidget(self.messages_container)
        
        return group
    
    def apply_dark_theme(self):
        """Apply dark theme styling matching functioning system."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: #e2e8f0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #374151;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #111827;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #f3f4f6;
            }
        """)
    
    def apply_light_theme(self):
        """Apply light theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #1f2937;
            }
            QGroupBox {
                border: 2px solid #d1d5db;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #f9fafb;
            }
        """)
    
    # Minimap integration methods
    
    def update_minimap_image(self, image: QPixmap):
        """Update the minimap with a new image."""
        if self.minimap_widget:
            self.minimap_widget.update_image(image)
            logger.debug("Minimap image updated")
    
    def update_minimap_view(self, widget_size: QSize, zoom: float, pan_x: int, pan_y: int):
        """Update the minimap viewport rectangle."""
        if self.minimap_widget:
            self.minimap_widget.update_view(widget_size, zoom, pan_x, pan_y)
            logger.debug(f"Minimap view updated: zoom={zoom:.2f}, pan=({pan_x}, {pan_y})")
    
    def on_minimap_view_changed(self, pan_x: int, pan_y: int):
        """Handle minimap navigation signal."""
        logger.info(f"Minimap navigation: pan=({pan_x}, {pan_y})")
        self.minimapNavigated.emit(pan_x, pan_y)
        self.add_status_message("Minimap", f"View navigated to ({pan_x}, {pan_y})", "info")
    
    def on_minimap_navigation_requested(self, click_x, click_y):
        """Handle minimap click navigation."""
        # The InteractiveMinimap emits navigationRequested(float, float) signal
        # with click_x, click_y parameters directly
        image_x = float(click_x)
        image_y = float(click_y)
            
        logger.info(f"Minimap click navigation: image coordinates ({image_x:.0f}, {image_y:.0f})")
        self.minimapClicked.emit(image_x, image_y)
    
    # Image information methods
    
    def update_image_info(self, filename: str, width: int = 0, height: int = 0, 
                         format_type: str = "", size_mb: float = 0.0):
        """Update the image information display."""
        self._current_image_info = {
            'filename': filename,
            'resolution': f"{width}x{height}" if width and height else "-",
            'format': format_type if format_type else "-",
            'size_mb': size_mb
        }
        
        # Update labels
        self.filename_label.setText(f"File: {filename}")
        self.resolution_label.setText(f"Size: {self._current_image_info['resolution']}")
        self.format_label.setText(f"Format: {self._current_image_info['format']}")
        
        if size_mb > 0:
            self.size_label.setText(f"Size: {size_mb:.2f} MB")
        else:
            self.size_label.setText("Size: -")
        
        logger.debug(f"Image info updated: {filename} ({width}x{height})")
    
    # Status management methods
    
    def update_status(self, status: str, detail: str = "", status_type: str = "info"):
        """Update the main status display - now adds status messages instead."""
        self._current_status = status
        self._current_status_type = status_type
        
        # Since we removed the status section, just add this as a message
        message = f"{status}: {detail}" if detail else status
        self.add_status_message("System", message, status_type)
        
        # Emit signal
        self.statusChanged.emit(status_type, status)
        
        logger.debug(f"Status updated: {status} ({status_type})")
    
    def update_component_status(self, component: str, status: str, status_type: str = "info"):
        """Update status for a specific component."""
        self._component_status[component] = f"{status} ({status_type})"
        
        # Add to messages
        self.add_status_message(component, status, status_type)
    
    def add_status_message(self, category: str, message: str, msg_type: str = "info"):
        """Add a message to the status log."""
        from datetime import datetime
        
        # Create message entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg_entry = {
            'timestamp': timestamp,
            'category': category,
            'message': message,
            'type': msg_type
        }
        
        # Add to messages list
        self._messages.append(msg_entry)
        
        # Limit message history
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]
        
        # Update display
        self.update_messages_display()
        
        logger.debug(f"Status message added: [{category}] {message}")
    
    def update_messages_display(self):
        """Update the messages display."""
        if not self._messages:
            return
        
        # Update last message display (compact view)
        if self.last_message_label:
            last_msg = self._messages[-1]
            color_map = {
                'info': '#94a3b8',      # Gray
                'success': '#10b981',   # Green
                'warning': '#f59e0b',   # Yellow
                'error': '#ef4444',     # Red
                'debug': '#6b7280'      # Dark gray
            }
            
            color = color_map.get(last_msg['type'], '#94a3b8')
            # Truncate long messages for compact display
            message_text = last_msg['message']
            if len(message_text) > 60:
                message_text = message_text[:57] + "..."
            
            compact_text = f'<span style="color: {color}; font-weight: bold;">[{last_msg["category"]}]</span> <span style="color: #e2e8f0;">{message_text}</span>'
            self.last_message_label.setText(compact_text)
        
        # Update message count
        if self.message_count_label:
            self.message_count_label.setText(f"{len(self._messages)} messages")
        
        # Update full messages view (when expanded)
        if not self.messages_text:
            return
        
        # Format messages with colors
        formatted_messages = []
        
        for msg in self._messages[-20:]:  # Show last 20 messages
            color_map = {
                'info': '#94a3b8',      # Gray
                'success': '#10b981',   # Green
                'warning': '#f59e0b',   # Yellow
                'error': '#ef4444',     # Red
                'debug': '#6b7280'      # Dark gray
            }
            
            color = color_map.get(msg['type'], '#94a3b8')
            formatted_msg = (
                f'<span style="color: #6b7280;">{msg["timestamp"]}</span> '
                f'<span style="color: {color}; font-weight: bold;">[{msg["category"]}]</span> '
                f'<span style="color: #e2e8f0;">{msg["message"]}</span>'
            )
            formatted_messages.append(formatted_msg)
        
        # Update text area
        html_content = "<br>".join(formatted_messages)
        self.messages_text.setHtml(html_content)
        
        # Auto-scroll to bottom
        scrollbar = self.messages_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_progress(self, current: int, total: int):
        """Update session progress (matches working annotation widget)."""
        if self.progress_bar:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current + 1)
        
        # Update progress text with current/total info  
        if hasattr(self, 'progress_text') and self.progress_text:
            self.progress_text.setText(f"{current + 1}/{total}")
    
    def initialize_class_counts(self, class_names: list, class_colors: list):
        """Initialize per-class count display with class names and colors."""
        # Clear existing class count labels (skip header row at index 0)
        while self.per_class_container.count() > 1:
            child = self.per_class_container.takeAt(1)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # Clear layout items
                while child.layout().count():
                    item = child.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

        self.class_count_labels = {}

        # Create a row for each class with current and total columns
        for i, (name, color) in enumerate(zip(class_names, class_colors)):
            class_layout = QHBoxLayout()
            class_layout.setSpacing(4)

            # Color indicator
            r, g, b = color
            color_label = QLabel()
            color_label.setFixedSize(16, 16)
            color_label.setStyleSheet(f"""
                background-color: rgb({r}, {g}, {b});
                border-radius: 8px;
                border: 1px solid #4a5568;
            """)

            # Class name
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #e2e8f0; font-size: 12px;")

            # Current image count
            current_label = QLabel("0")
            current_label.setStyleSheet("color: #e2e8f0; font-size: 12px; font-family: monospace;")
            current_label.setFixedWidth(35)
            current_label.setAlignment(Qt.AlignRight)

            # Total session count
            total_label = QLabel("0")
            total_label.setStyleSheet("color: #e2e8f0; font-size: 12px; font-family: monospace;")
            total_label.setFixedWidth(45)
            total_label.setAlignment(Qt.AlignRight)

            class_layout.addWidget(color_label)
            class_layout.addWidget(name_label)
            class_layout.addStretch()
            class_layout.addWidget(current_label)
            class_layout.addWidget(total_label)

            self.per_class_container.addLayout(class_layout)
            self.class_count_labels[i] = {'current': current_label, 'total': total_label}

    def update_class_counts(self, current_counts: dict, total_counts: dict = None):
        """Update per-class annotation counts.

        Args:
            current_counts: Dict mapping class_id -> count for current image
            total_counts: Dict mapping class_id -> count for session total (optional)
        """
        if total_counts is None:
            total_counts = current_counts

        for class_id, labels in self.class_count_labels.items():
            current = current_counts.get(class_id, 0)
            total = total_counts.get(class_id, 0)

            if isinstance(labels, dict):
                labels['current'].setText(str(current))
                labels['total'].setText(str(total))
            else:
                # Fallback for old format
                labels.setText(str(current))
    
    def format_time(self, seconds: int) -> str:
        """Format seconds into MM:SS or HH:MM:SS format."""
        if seconds < 3600:  # Less than 1 hour
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"
        else:  # 1 hour or more
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:01d}:{minutes:02d}:{seconds % 60:02d}"
    
    def add_annotation(self, annotation_type: str = "point"):
        """Track a new annotation and update metrics."""
        current_time = time.time()
        
        # Track timing if we have a previous annotation
        if self._last_annotation_time is not None:
            time_diff = current_time - self._last_annotation_time
            self._annotation_times.append(time_diff)
            
            # Keep only last 50 annotations for rolling average
            if len(self._annotation_times) > 50:
                self._annotation_times = self._annotation_times[-50:]
        
        self._last_annotation_time = current_time
        self._total_annotations += 1
        self._current_image_annotations += 1
        
        # Update displays
        self.update_annotation_displays()
        
        logger.debug(f"Annotation added: total={self._total_annotations}, current_image={self._current_image_annotations}")
    
    def reset_current_image_annotations(self):
        """Reset annotation count for new image."""
        self._current_image_annotations = 0
        self.update_annotation_displays()
        logger.debug("Current image annotation count reset")
    
    def update_annotation_displays(self):
        """Update annotation count displays."""
        if self.annotation_count_label:
            self.annotation_count_label.setText(f"🎯 {self._total_annotations}")
        
        if self.current_image_count_label:
            self.current_image_count_label.setText(f"📍 {self._current_image_annotations}")
    
    def toggle_messages(self):
        """Toggle the messages section expansion."""
        self._messages_expanded = not self._messages_expanded
        self.messages_container.setVisible(self._messages_expanded)
        
        # Update button text
        if self._messages_expanded:
            self.messages_toggle_button.setText("⬆")
        else:
            self.messages_toggle_button.setText("⬇")
        
        logger.debug(f"Messages section toggled: expanded={self._messages_expanded}")
    
    def clear_messages(self):
        """Clear all status messages."""
        self._messages.clear()
        if self.messages_text:
            self.messages_text.clear()
    
    # Public API methods
    
    def get_minimap_widget(self) -> Optional[InteractiveMinimap]:
        """Get the minimap widget for direct access."""
        return self.minimap_widget
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current status information."""
        return {
            'status': self._current_status,
            'type': self._current_status_type,
            'component_count': len(self._component_status),
            'message_count': len(self._messages),
            'image_info': self._current_image_info.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive status panel statistics."""
        elapsed_seconds = int(time.time() - self._session_start_time)
        avg_time_per_annotation = sum(self._annotation_times) / len(self._annotation_times) if self._annotation_times else 0
        
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'current_status': self._current_status,
            'status_type': self._current_status_type,
            'messages_count': len(self._messages),
            'messages_expanded': self._messages_expanded,
            'components_tracked': len(self._component_status),
            'minimap_available': self.minimap_widget is not None,
            'minimap_has_image': self.minimap_widget.has_image() if self.minimap_widget else False,
            'image_info': self._current_image_info.copy(),
            'session_elapsed_seconds': elapsed_seconds,
            'total_annotations': self._total_annotations,
            'current_image_annotations': self._current_image_annotations,
            'average_time_per_annotation': avg_time_per_annotation,
            'annotation_times_tracked': len(self._annotation_times)
        }