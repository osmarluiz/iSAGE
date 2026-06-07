"""
Status Panel - Display system status and statistics

This module provides a status panel showing annotation progress, system metrics,
and real-time feedback for the annotation interface.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from ..base_protocols import BaseComponent, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from ..base_protocols import QLabel, QProgressBar, QTextEdit, QFrame, QSizePolicy
from .base_ui import BaseUI


class StatusPanel(BaseUI, QWidget):
    """Status panel for annotation interface."""
    
    # Status panel signals
    statusUpdated = pyqtSignal(str, object)  # status_type, value
    alertTriggered = pyqtSignal(str, str)  # alert_type, message
    panelCleared = pyqtSignal()
    
    def __init__(self, name: str = "status_panel", version: str = "1.0.0", parent=None):
        BaseUI.__init__(self, name, version)
        QWidget.__init__(self, parent)
        
        # Panel configuration
        self._panel_width: int = 400
        self._panel_height: int = 300
        self._max_log_entries: int = 100
        self._auto_scroll: bool = True
        
        # Status tracking
        self._status_items: Dict[str, Dict[str, Any]] = {}
        self._progress_bars: Dict[str, QProgressBar] = {}
        self._status_labels: Dict[str, QLabel] = {}
        
        # Statistics tracking
        self._statistics: Dict[str, Any] = {}
        self._update_interval: float = 1.0  # Update every second
        self._last_update_time: float = 0.0
        
        # Log system
        self._log_entries: List[Dict[str, Any]] = []
        self._log_display: QTextEdit = QTextEdit()
        self._log_enabled: bool = True
        self._log_levels: Dict[str, int] = {
            'debug': 0,
            'info': 1,
            'warning': 2,
            'error': 3,
            'critical': 4
        }
        self._log_level: int = 1  # Info level
        
        # Theme
        self._theme: str = "light"
        self._theme_colors: Dict[str, Dict[str, str]] = {
            'light': {
                'background': '#ffffff',
                'text': '#000000',
                'border': '#c0c0c0',
                'progress_bg': '#f0f0f0',
                'progress_chunk': '#4a90e2',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'info': '#17a2b8'
            },
            'dark': {
                'background': '#2b2b2b',
                'text': '#ffffff',
                'border': '#555555',
                'progress_bg': '#3c3c3c',
                'progress_chunk': '#4a90e2',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545',
                'info': '#17a2b8'
            }
        }
        
        # Performance monitoring
        self._performance_metrics: Dict[str, List[float]] = {
            'update_times': [],
            'memory_usage': [],
            'cpu_usage': []
        }
        self._metrics_history_size: int = 60  # Keep 60 seconds of history
        
        # Layout
        self._main_layout: QVBoxLayout = QVBoxLayout()
        self._status_frame: QFrame = QFrame()
        self._stats_frame: QFrame = QFrame()
        self._log_frame: QFrame = QFrame()
        
        # Initialize UI
        self._setup_ui()
        self._apply_theme()
        
        # Start update timer
        self._setup_update_timer()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize status panel."""
        self._panel_width = kwargs.get('panel_width', 400)
        self._panel_height = kwargs.get('panel_height', 300)
        self._max_log_entries = kwargs.get('max_log_entries', 100)
        self._auto_scroll = kwargs.get('auto_scroll', True)
        self._log_enabled = kwargs.get('log_enabled', True)
        self._log_level = kwargs.get('log_level', 1)
        self._theme = kwargs.get('theme', 'light')
        self._update_interval = kwargs.get('update_interval', 1.0)
        
        # Set size
        self.setFixedSize(self._panel_width, self._panel_height)
        
        # Apply theme
        self._apply_theme()
        
        return super().initialize(**kwargs)
    
    def add_status_item(self, item_name: str, item_config: Dict[str, Any]) -> None:
        """Add status item to panel."""
        try:
            self._status_items[item_name] = item_config
            
            # Create widgets based on type
            item_type = item_config.get('type', 'label')
            
            if item_type == 'progress':
                # Create progress bar
                progress_bar = QProgressBar()
                progress_bar.setMinimum(item_config.get('min', 0))
                progress_bar.setMaximum(item_config.get('max', 100))
                progress_bar.setValue(item_config.get('value', 0))
                progress_bar.setFormat(item_config.get('format', '%p%'))
                
                # Add label if specified
                if 'label' in item_config:
                    label = QLabel(item_config['label'])
                    self._add_to_status_frame(label, progress_bar)
                    self._status_labels[item_name] = label
                else:
                    self._add_to_status_frame(progress_bar)
                
                self._progress_bars[item_name] = progress_bar
                self._apply_progress_theme(progress_bar)
                
            elif item_type == 'label':
                # Create label
                label = QLabel(item_config.get('text', ''))
                self._add_to_status_frame(label)
                self._status_labels[item_name] = label
                self._apply_label_theme(label)
            
            self.emit_state_changed({'status_items_count': len(self._status_items)})
            
        except Exception as e:
            self.emit_error(f"Error adding status item: {str(e)}")
    
    def remove_status_item(self, item_name: str) -> bool:
        """Remove status item from panel."""
        try:
            if item_name not in self._status_items:
                return False
            
            # Remove widgets
            if item_name in self._progress_bars:
                self._progress_bars[item_name].setParent(None)
                del self._progress_bars[item_name]
            
            if item_name in self._status_labels:
                self._status_labels[item_name].setParent(None)
                del self._status_labels[item_name]
            
            # Remove from config
            del self._status_items[item_name]
            
            self.emit_state_changed({'status_items_count': len(self._status_items)})
            return True
            
        except Exception as e:
            self.emit_error(f"Error removing status item: {str(e)}")
            return False
    
    def update_status_item(self, item_name: str, value: Any) -> bool:
        """Update status item value."""
        try:
            if item_name not in self._status_items:
                return False
            
            item_config = self._status_items[item_name]
            item_type = item_config.get('type', 'label')
            
            if item_type == 'progress' and item_name in self._progress_bars:
                progress_bar = self._progress_bars[item_name]
                progress_bar.setValue(int(value))
                
                # Update label if exists
                if item_name in self._status_labels:
                    label_format = item_config.get('label_format', '{label}: {value}%')
                    label_text = label_format.format(
                        label=item_config.get('label', ''),
                        value=value
                    )
                    self._status_labels[item_name].setText(label_text)
                
            elif item_type == 'label' and item_name in self._status_labels:
                self._status_labels[item_name].setText(str(value))
            
            self.statusUpdated.emit(item_name, value)
            self.emit_state_changed({f'status_{item_name}': value})
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error updating status item: {str(e)}")
            return False
    
    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """Update statistics display."""
        try:
            self._statistics.update(stats)
            
            # Update statistics display
            self._update_stats_display()
            
            self.emit_state_changed({'statistics_updated': time.time()})
            
        except Exception as e:
            self.emit_error(f"Error updating statistics: {str(e)}")
    
    def add_log_entry(self, level: str, message: str, source: str = "") -> None:
        """Add log entry."""
        try:
            if not self._log_enabled:
                return
            
            # Check log level
            if level not in self._log_levels:
                level = 'info'
            
            if self._log_levels[level] < self._log_level:
                return
            
            # Create log entry
            entry = {
                'timestamp': time.time(),
                'datetime': datetime.now(),
                'level': level,
                'message': message,
                'source': source
            }
            
            # Add to log
            self._log_entries.append(entry)
            
            # Limit log size
            if len(self._log_entries) > self._max_log_entries:
                self._log_entries.pop(0)
            
            # Update display
            self._update_log_display()
            
            # Emit alert for warnings and errors
            if level in ['warning', 'error', 'critical']:
                self.alertTriggered.emit(level, message)
            
        except Exception as e:
            self.emit_error(f"Error adding log entry: {str(e)}")
    
    def clear_log(self) -> None:
        """Clear log entries."""
        try:
            self._log_entries.clear()
            self._update_log_display()
            self.panelCleared.emit()
            
        except Exception as e:
            self.emit_error(f"Error clearing log: {str(e)}")
    
    def set_log_level(self, level: str) -> None:
        """Set log level."""
        try:
            if level in self._log_levels:
                self._log_level = self._log_levels[level]
                self._update_log_display()  # Refresh display
                self.emit_state_changed({'log_level': level})
                
        except Exception as e:
            self.emit_error(f"Error setting log level: {str(e)}")
    
    def get_log_level(self) -> str:
        """Get current log level."""
        for level, value in self._log_levels.items():
            if value == self._log_level:
                return level
        return 'info'
    
    def set_log_enabled(self, enabled: bool) -> None:
        """Enable/disable logging."""
        self._log_enabled = enabled
        self._log_display.setVisible(enabled)
        self.emit_state_changed({'log_enabled': enabled})
    
    def is_log_enabled(self) -> bool:
        """Check if logging is enabled."""
        return self._log_enabled
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable/disable auto scroll."""
        self._auto_scroll = enabled
        self.emit_state_changed({'auto_scroll': enabled})
    
    def is_auto_scroll_enabled(self) -> bool:
        """Check if auto scroll is enabled."""
        return self._auto_scroll
    
    def set_theme(self, theme: str) -> None:
        """Set UI theme."""
        if theme in self._theme_colors:
            self._theme = theme
            self._apply_theme()
            self.emit_state_changed({'theme': theme})
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self._theme
    
    def get_current_statistics(self) -> Dict[str, Any]:
        """Get current statistics."""
        return self._statistics.copy()
    
    def get_log_entries(self, level: Optional[str] = None, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get log entries."""
        try:
            entries = self._log_entries
            
            # Filter by level
            if level and level in self._log_levels:
                min_level = self._log_levels[level]
                entries = [e for e in entries if self._log_levels[e['level']] >= min_level]
            
            # Limit count
            if count:
                entries = entries[-count:]
            
            return entries
            
        except Exception as e:
            self.emit_error(f"Error getting log entries: {str(e)}")
            return []
    
    def export_log(self, file_path: str) -> bool:
        """Export log to file."""
        try:
            with open(file_path, 'w') as f:
                for entry in self._log_entries:
                    timestamp = entry['datetime'].strftime('%Y-%m-%d %H:%M:%S')
                    level = entry['level'].upper()
                    source = entry['source']
                    message = entry['message']
                    
                    line = f"[{timestamp}] {level}"
                    if source:
                        line += f" ({source})"
                    line += f": {message}\n"
                    
                    f.write(line)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error exporting log: {str(e)}")
            return False
    
    def _setup_ui(self) -> None:
        """Setup UI layout."""
        try:
            # Set main layout
            self.setLayout(self._main_layout)
            
            # Configure frames
            self._status_frame.setFrameStyle(QFrame.StyledPanel)
            self._status_frame.setLineWidth(1)
            self._status_frame.setLayout(QVBoxLayout())
            
            self._stats_frame.setFrameStyle(QFrame.StyledPanel)
            self._stats_frame.setLineWidth(1)
            self._stats_frame.setLayout(QVBoxLayout())
            
            self._log_frame.setFrameStyle(QFrame.StyledPanel)
            self._log_frame.setLineWidth(1)
            self._log_frame.setLayout(QVBoxLayout())
            
            # Configure log display
            self._log_display.setReadOnly(True)
            self._log_display.setMaximumHeight(100)
            self._log_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # Add frames to layout
            self._main_layout.addWidget(self._status_frame)
            self._main_layout.addWidget(self._stats_frame)
            
            # Add log frame
            self._log_frame.layout().addWidget(self._log_display)
            self._main_layout.addWidget(self._log_frame)
            
            # Set initial size
            self.setFixedSize(self._panel_width, self._panel_height)
            
        except Exception as e:
            self.emit_error(f"Error setting up UI: {str(e)}")
    
    def _setup_update_timer(self) -> None:
        """Setup automatic update timer."""
        try:
            from PyQt5.QtCore import QTimer
            
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._periodic_update)
            self._update_timer.start(int(self._update_interval * 1000))
            
        except Exception as e:
            self.emit_error(f"Error setting up update timer: {str(e)}")
    
    def _periodic_update(self) -> None:
        """Perform periodic updates."""
        try:
            current_time = time.time()
            
            # Update performance metrics
            self._update_performance_metrics()
            
            # Update statistics display
            self._update_stats_display()
            
            self._last_update_time = current_time
            
        except Exception as e:
            self.emit_error(f"Error in periodic update: {str(e)}")
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        try:
            # Get memory usage
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                self._performance_metrics['memory_usage'].append(memory_mb)
                self._performance_metrics['cpu_usage'].append(cpu_percent)
                
            except ImportError:
                # Fallback if psutil not available
                self._performance_metrics['memory_usage'].append(0)
                self._performance_metrics['cpu_usage'].append(0)
            
            # Limit history size
            for metric_list in self._performance_metrics.values():
                if len(metric_list) > self._metrics_history_size:
                    metric_list.pop(0)
            
        except Exception as e:
            self.emit_error(f"Error updating performance metrics: {str(e)}")
    
    def _update_stats_display(self) -> None:
        """Update statistics display."""
        try:
            # Clear existing stats layout
            stats_layout = self._stats_frame.layout()
            while stats_layout.count():
                child = stats_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Add current statistics
            if self._statistics:
                for key, value in self._statistics.items():
                    label = QLabel(f"{key}: {value}")
                    self._apply_label_theme(label)
                    stats_layout.addWidget(label)
            
            # Add performance metrics
            if self._performance_metrics['memory_usage']:
                memory_avg = sum(self._performance_metrics['memory_usage']) / len(self._performance_metrics['memory_usage'])
                memory_label = QLabel(f"Memory: {memory_avg:.1f} MB")
                self._apply_label_theme(memory_label)
                stats_layout.addWidget(memory_label)
            
            if self._performance_metrics['cpu_usage']:
                cpu_avg = sum(self._performance_metrics['cpu_usage']) / len(self._performance_metrics['cpu_usage'])
                cpu_label = QLabel(f"CPU: {cpu_avg:.1f}%")
                self._apply_label_theme(cpu_label)
                stats_layout.addWidget(cpu_label)
            
            # Add uptime
            uptime_label = QLabel(f"Uptime: {self._get_uptime()}")
            self._apply_label_theme(uptime_label)
            stats_layout.addWidget(uptime_label)
            
        except Exception as e:
            self.emit_error(f"Error updating stats display: {str(e)}")
    
    def _update_log_display(self) -> None:
        """Update log display."""
        try:
            if not self._log_enabled:
                return
            
            # Build log text
            log_text = ""
            for entry in self._log_entries:
                # Check if entry should be displayed
                if self._log_levels[entry['level']] >= self._log_level:
                    timestamp = entry['datetime'].strftime('%H:%M:%S')
                    level = entry['level'].upper()
                    source = entry['source']
                    message = entry['message']
                    
                    line = f"[{timestamp}] {level}"
                    if source:
                        line += f" ({source})"
                    line += f": {message}\n"
                    
                    log_text += line
            
            # Update display
            self._log_display.setPlainText(log_text)
            
            # Auto scroll to bottom
            if self._auto_scroll:
                cursor = self._log_display.textCursor()
                cursor.movePosition(cursor.End)
                self._log_display.setTextCursor(cursor)
            
        except Exception as e:
            self.emit_error(f"Error updating log display: {str(e)}")
    
    def _add_to_status_frame(self, *widgets) -> None:
        """Add widgets to status frame."""
        try:
            layout = self._status_frame.layout()
            
            if len(widgets) == 1:
                layout.addWidget(widgets[0])
            else:
                # Create horizontal layout for multiple widgets
                h_layout = QHBoxLayout()
                for widget in widgets:
                    h_layout.addWidget(widget)
                layout.addLayout(h_layout)
                
        except Exception as e:
            self.emit_error(f"Error adding to status frame: {str(e)}")
    
    def _apply_theme(self) -> None:
        """Apply theme to all UI elements."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            # Apply to main widget
            self.setStyleSheet(f"""
                StatusPanel {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                }}
                
                QFrame {{
                    background-color: {colors['background']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    margin: 2px;
                    padding: 4px;
                }}
                
                QTextEdit {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 10px;
                }}
            """)
            
            # Apply to existing widgets
            for progress_bar in self._progress_bars.values():
                self._apply_progress_theme(progress_bar)
            
            for label in self._status_labels.values():
                self._apply_label_theme(label)
            
        except Exception as e:
            self.emit_error(f"Error applying theme: {str(e)}")
    
    def _apply_progress_theme(self, progress_bar: QProgressBar) -> None:
        """Apply theme to progress bar."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {colors['progress_bg']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    text-align: center;
                    color: {colors['text']};
                    height: 20px;
                }}
                
                QProgressBar::chunk {{
                    background-color: {colors['progress_chunk']};
                    border-radius: 3px;
                }}
            """)
            
        except Exception as e:
            self.emit_error(f"Error applying progress theme: {str(e)}")
    
    def _apply_label_theme(self, label: QLabel) -> None:
        """Apply theme to label."""
        try:
            colors = self._theme_colors.get(self._theme, self._theme_colors['light'])
            
            label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text']};
                    font-size: 12px;
                    margin: 2px;
                }}
            """)
            
        except Exception as e:
            self.emit_error(f"Error applying label theme: {str(e)}")
    
    def _get_uptime(self) -> str:
        """Get formatted uptime."""
        try:
            uptime_seconds = time.time() - self._last_update_time
            uptime_delta = timedelta(seconds=int(uptime_seconds))
            
            # Format as HH:MM:SS
            total_seconds = int(uptime_delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        except Exception as e:
            self.emit_error(f"Error getting uptime: {str(e)}")
            return "00:00:00"
    
    def get_panel_info(self) -> Dict[str, Any]:
        """Get status panel information."""
        return {
            'panel_size': (self._panel_width, self._panel_height),
            'theme': self._theme,
            'log_enabled': self._log_enabled,
            'log_level': self.get_log_level(),
            'auto_scroll': self._auto_scroll,
            'status_items_count': len(self._status_items),
            'log_entries_count': len(self._log_entries),
            'statistics_count': len(self._statistics),
            'update_interval': self._update_interval
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get status panel statistics."""
        stats = super().get_statistics()
        stats.update({
            'panel_width': self._panel_width,
            'panel_height': self._panel_height,
            'max_log_entries': self._max_log_entries,
            'auto_scroll': self._auto_scroll,
            'log_enabled': self._log_enabled,
            'log_level': self.get_log_level(),
            'theme': self._theme,
            'update_interval': self._update_interval,
            'status_items': list(self._status_items.keys()),
            'current_statistics': self._statistics,
            'performance_metrics': {
                'memory_usage': self._performance_metrics['memory_usage'][-1] if self._performance_metrics['memory_usage'] else 0,
                'cpu_usage': self._performance_metrics['cpu_usage'][-1] if self._performance_metrics['cpu_usage'] else 0
            },
            'panel_info': self.get_panel_info()
        })
        return stats