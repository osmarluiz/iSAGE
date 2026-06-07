"""
Auto Saver - Automatic saving with interval and change detection

This module provides automatic saving functionality with configurable intervals,
change detection, and backup management.
"""

import time
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from ..base_protocols import BaseComponent, AnnotationData
from .json_saver import JsonSaver


class AutoSaver(BaseComponent):
    """Automatic saving with interval and change detection."""
    
    # Auto saver signals
    autoSaveCompleted = pyqtSignal(str)  # file_path
    autoSaveFailed = pyqtSignal(str)  # error_message
    autoSaveIntervalChanged = pyqtSignal(float)  # interval_seconds
    
    def __init__(self, name: str = "auto_saver", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Auto save configuration
        self._enabled: bool = False
        self._save_interval: float = 300.0  # 5 minutes
        self._change_detection: bool = True
        self._save_on_change: bool = True
        self._max_unsaved_changes: int = 50
        
        # Save targets
        self._save_callback: Optional[Callable[[str], bool]] = None
        self._data_getter: Optional[Callable[[], AnnotationData]] = None
        self._output_path: Optional[str] = None
        
        # State tracking
        self._last_save_time: float = 0.0
        self._last_data_hash: Optional[str] = None
        self._unsaved_changes: int = 0
        self._has_unsaved_changes: bool = False
        
        # Thread management
        self._save_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._save_lock: threading.Lock = threading.Lock()
        
        # Statistics
        self._auto_save_count: int = 0
        self._auto_save_errors: int = 0
        self._last_auto_save_time: float = 0.0
        self._average_save_time: float = 0.0
        
        # JSON saver
        self._json_saver: JsonSaver = JsonSaver()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize auto saver."""
        self._save_interval = kwargs.get('save_interval', 300.0)
        self._change_detection = kwargs.get('change_detection', True)
        self._save_on_change = kwargs.get('save_on_change', True)
        self._max_unsaved_changes = kwargs.get('max_unsaved_changes', 50)
        
        # Initialize JSON saver
        saver_config = kwargs.get('saver_config', {})
        self._json_saver.initialize(**saver_config)
        
        return super().initialize(**kwargs)
    
    def start(self) -> bool:
        """Start auto saving."""
        if self._enabled:
            return True
        
        try:
            # Validate configuration
            if not self._validate_configuration():
                return False
            
            # Start save thread
            self._stop_event.clear()
            self._save_thread = threading.Thread(target=self._save_loop, daemon=True)
            self._save_thread.start()
            
            self._enabled = True
            self._last_save_time = time.time()
            
            self.emit_state_changed({'auto_save_enabled': True})
            return True
            
        except Exception as e:
            self.emit_error(f"Error starting auto saver: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """Stop auto saving."""
        if not self._enabled:
            return True
        
        try:
            # Stop save thread
            self._stop_event.set()
            
            if self._save_thread and self._save_thread.is_alive():
                self._save_thread.join(timeout=5.0)
                if self._save_thread.is_alive():
                    self.emit_error("Auto saver thread did not stop gracefully")
                    return False
            
            self._enabled = False
            self.emit_state_changed({'auto_save_enabled': False})
            return True
            
        except Exception as e:
            self.emit_error(f"Error stopping auto saver: {str(e)}")
            return False
    
    def force_save(self) -> bool:
        """Force immediate save."""
        if not self._enabled:
            return False
        
        try:
            return self._perform_save()
            
        except Exception as e:
            self.emit_error(f"Error in force save: {str(e)}")
            return False
    
    def set_save_callback(self, callback: Callable[[str], bool]) -> None:
        """Set save callback function."""
        self._save_callback = callback
    
    def set_data_getter(self, getter: Callable[[], AnnotationData]) -> None:
        """Set data getter function."""
        self._data_getter = getter
    
    def set_output_path(self, path: str) -> None:
        """Set output file path."""
        self._output_path = path
        self.emit_state_changed({'output_path': path})
    
    def get_output_path(self) -> Optional[str]:
        """Get output file path."""
        return self._output_path
    
    def set_save_interval(self, interval: float) -> None:
        """Set save interval in seconds."""
        self._save_interval = max(30.0, interval)  # Minimum 30 seconds
        self.autoSaveIntervalChanged.emit(self._save_interval)
        self.emit_state_changed({'save_interval': self._save_interval})
    
    def get_save_interval(self) -> float:
        """Get save interval."""
        return self._save_interval
    
    def set_change_detection(self, enabled: bool) -> None:
        """Enable/disable change detection."""
        self._change_detection = enabled
        self.emit_state_changed({'change_detection': enabled})
    
    def is_change_detection_enabled(self) -> bool:
        """Check if change detection is enabled."""
        return self._change_detection
    
    def set_save_on_change(self, enabled: bool) -> None:
        """Enable/disable save on change."""
        self._save_on_change = enabled
        self.emit_state_changed({'save_on_change': enabled})
    
    def is_save_on_change_enabled(self) -> bool:
        """Check if save on change is enabled."""
        return self._save_on_change
    
    def set_max_unsaved_changes(self, max_changes: int) -> None:
        """Set maximum unsaved changes before forced save."""
        self._max_unsaved_changes = max(1, max_changes)
        self.emit_state_changed({'max_unsaved_changes': max_changes})
    
    def get_max_unsaved_changes(self) -> int:
        """Get maximum unsaved changes."""
        return self._max_unsaved_changes
    
    def notify_data_changed(self) -> None:
        """Notify auto saver that data has changed."""
        if not self._enabled or not self._change_detection:
            return
        
        try:
            # Get current data hash
            current_hash = self._get_data_hash()
            
            if current_hash != self._last_data_hash:
                self._unsaved_changes += 1
                self._has_unsaved_changes = True
                self._last_data_hash = current_hash
                
                # Save immediately if enabled
                if self._save_on_change:
                    self._perform_save()
                
                # Force save if too many unsaved changes
                elif self._unsaved_changes >= self._max_unsaved_changes:
                    self._perform_save()
                
                self.emit_state_changed({
                    'unsaved_changes': self._unsaved_changes,
                    'has_unsaved_changes': self._has_unsaved_changes
                })
                
        except Exception as e:
            self.emit_error(f"Error in data change notification: {str(e)}")
    
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self._has_unsaved_changes
    
    def get_unsaved_changes_count(self) -> int:
        """Get number of unsaved changes."""
        return self._unsaved_changes
    
    def get_time_since_last_save(self) -> float:
        """Get time since last save in seconds."""
        return time.time() - self._last_save_time
    
    def get_next_save_time(self) -> float:
        """Get time until next scheduled save in seconds."""
        if not self._enabled:
            return 0.0
        
        elapsed = self.get_time_since_last_save()
        return max(0.0, self._save_interval - elapsed)
    
    def is_enabled(self) -> bool:
        """Check if auto saver is enabled."""
        return self._enabled
    
    def get_auto_save_statistics(self) -> Dict[str, Any]:
        """Get auto save statistics."""
        return {
            'enabled': self._enabled,
            'save_count': self._auto_save_count,
            'error_count': self._auto_save_errors,
            'last_save_time': self._last_auto_save_time,
            'average_save_time': self._average_save_time,
            'time_since_last_save': self.get_time_since_last_save(),
            'next_save_time': self.get_next_save_time(),
            'unsaved_changes': self._unsaved_changes,
            'has_unsaved_changes': self._has_unsaved_changes
        }
    
    def _validate_configuration(self) -> bool:
        """Validate auto saver configuration."""
        if not self._output_path:
            self.emit_error("Output path not configured")
            return False
        
        if not self._data_getter and not self._save_callback:
            self.emit_error("No data getter or save callback configured")
            return False
        
        if self._save_interval < 30.0:
            self.emit_error("Save interval must be at least 30 seconds")
            return False
        
        return True
    
    def _save_loop(self) -> None:
        """Main save loop running in separate thread."""
        while not self._stop_event.is_set():
            try:
                # Wait for save interval or stop event
                if self._stop_event.wait(timeout=self._save_interval):
                    break  # Stop event was set
                
                # Perform save if needed
                if self._has_unsaved_changes or not self._change_detection:
                    self._perform_save()
                
            except Exception as e:
                self.emit_error(f"Error in save loop: {str(e)}")
                self._auto_save_errors += 1
                
                # Wait before retrying
                if not self._stop_event.wait(timeout=30.0):
                    continue
    
    def _perform_save(self) -> bool:
        """Perform actual save operation."""
        if not self._enabled or not self._output_path:
            return False
        
        try:
            with self._save_lock:
                start_time = time.time()
                
                # Use custom callback if provided
                if self._save_callback:
                    success = self._save_callback(self._output_path)
                else:
                    # Use data getter and JSON saver
                    data = self._data_getter()
                    if data is None:
                        return False
                    
                    success = self._json_saver.save_annotation_data(data, self._output_path)
                
                # Update statistics
                save_time = time.time() - start_time
                if success:
                    self._auto_save_count += 1
                    self._last_auto_save_time = save_time
                    self._last_save_time = time.time()
                    
                    # Update average save time
                    if self._auto_save_count == 1:
                        self._average_save_time = save_time
                    else:
                        self._average_save_time = (
                            (self._average_save_time * (self._auto_save_count - 1) + save_time) /
                            self._auto_save_count
                        )
                    
                    # Reset change tracking
                    self._unsaved_changes = 0
                    self._has_unsaved_changes = False
                    
                    # Update data hash
                    self._last_data_hash = self._get_data_hash()
                    
                    self.autoSaveCompleted.emit(self._output_path)
                    self.emit_state_changed({
                        'last_auto_save': time.time(),
                        'unsaved_changes': 0,
                        'has_unsaved_changes': False
                    })
                    
                    return True
                else:
                    self._auto_save_errors += 1
                    self.autoSaveFailed.emit(f"Save failed to {self._output_path}")
                    return False
                    
        except Exception as e:
            self.emit_error(f"Error performing save: {str(e)}")
            self._auto_save_errors += 1
            self.autoSaveFailed.emit(str(e))
            return False
    
    def _get_data_hash(self) -> Optional[str]:
        """Get hash of current data for change detection."""
        if not self._data_getter:
            return None
        
        try:
            import hashlib
            
            data = self._data_getter()
            if data is None:
                return None
            
            # Create hash from data
            hash_data = {
                'points': [point.to_dict() for point in data.points],
                'image_path': data.image_path,
                'image_size': data.image_size,
                'class_names': data.class_names
            }
            
            import json
            json_str = json.dumps(hash_data, sort_keys=True)
            return hashlib.md5(json_str.encode()).hexdigest()
            
        except Exception as e:
            self.emit_error(f"Error calculating data hash: {str(e)}")
            return None
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop auto saver
            self.stop()
            
            # Clean up JSON saver
            if hasattr(self._json_saver, 'cleanup'):
                self._json_saver.cleanup()
                
        except Exception as e:
            self.emit_error(f"Error in cleanup: {str(e)}")
        
        super().cleanup()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get auto saver statistics."""
        stats = super().get_statistics()
        stats.update({
            'save_interval': self._save_interval,
            'change_detection': self._change_detection,
            'save_on_change': self._save_on_change,
            'max_unsaved_changes': self._max_unsaved_changes,
            'output_path': self._output_path,
            'auto_save_statistics': self.get_auto_save_statistics()
        })
        return stats