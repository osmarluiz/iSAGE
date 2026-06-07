"""
Auto-Save Threading for Annotation System
Provides background auto-save functionality with change detection.
Based on legacy ABILIUS auto-save implementation.
"""

import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


class AutoSaveThread:
    """Background auto-save thread with change detection."""
    
    def __init__(self, 
                 save_interval: float = 30.0,
                 change_detection: bool = True,
                 max_retries: int = 3):
        """
        Initialize auto-save thread.
        
        Args:
            save_interval: Interval between saves in seconds
            change_detection: Whether to detect changes before saving
            max_retries: Maximum number of retry attempts
        """
        self.save_interval = save_interval
        self.change_detection = change_detection
        self.max_retries = max_retries
        
        # Threading
        self._save_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._save_lock = threading.Lock()
        self._running = False
        
        # Save callback and path
        self._save_callback: Optional[Callable[[str], bool]] = None
        self._output_path: Optional[str] = None
        
        # Change detection
        self._has_unsaved_changes = False
        self._last_data_hash: Optional[str] = None
        self._last_save_time: Optional[float] = None
        
        # Statistics
        self._save_count = 0
        self._failed_saves = 0
        self._total_save_time = 0.0
        
    def set_save_callback(self, callback: Callable[[str], bool], output_path: str) -> None:
        """
        Set the save callback and output path.
        
        Args:
            callback: Function that performs the save, returns True on success
            output_path: Path where to save the data
        """
        with self._save_lock:
            self._save_callback = callback
            self._output_path = output_path
            
    def start(self) -> bool:
        """Start auto-save thread."""
        if self._running:
            logger.warning("Auto-save thread already running")
            return False
            
        if not self._save_callback or not self._output_path:
            logger.error("Save callback and output path must be set before starting")
            return False
            
        self._stop_event.clear()
        self._running = True
        
        self._save_thread = threading.Thread(target=self._save_loop, daemon=True)
        self._save_thread.start()
        
        logger.info(f"Auto-save started with {self.save_interval}s interval")
        return True
        
    def stop(self, timeout: float = 5.0) -> bool:
        """Stop auto-save thread."""
        if not self._running:
            return True
            
        self._stop_event.set()
        self._running = False
        
        if self._save_thread and self._save_thread.is_alive():
            self._save_thread.join(timeout=timeout)
            
            if self._save_thread.is_alive():
                logger.warning("Auto-save thread did not stop within timeout")
                return False
                
        logger.info("Auto-save stopped")
        return True
        
    def trigger_save(self) -> bool:
        """Trigger an immediate save."""
        if not self._running:
            return False
            
        return self._perform_save()
        
    def mark_changed(self, data_hash: str = None) -> None:
        """Mark that data has changed."""
        with self._save_lock:
            self._has_unsaved_changes = True
            
            if data_hash:
                self._last_data_hash = data_hash
                
    def _save_loop(self) -> None:
        """Main save loop running in separate thread."""
        while not self._stop_event.is_set():
            try:
                # Wait for save interval or stop event
                if self._stop_event.wait(timeout=self.save_interval):
                    break  # Stop event was set
                    
                # Check if we need to save
                should_save = False
                
                with self._save_lock:
                    if self._has_unsaved_changes or not self.change_detection:
                        should_save = True
                        
                if should_save:
                    self._perform_save()
                    
            except Exception as e:
                logger.error(f"Error in auto-save loop: {str(e)}")
                time.sleep(1.0)  # Brief pause before continuing
                
    def _perform_save(self) -> bool:
        """Perform actual save operation."""
        if not self._save_callback or not self._output_path:
            return False
            
        save_start_time = time.time()
        
        with self._save_lock:
            for attempt in range(self.max_retries + 1):
                try:
                    # Call save callback
                    success = self._save_callback(self._output_path)
                    
                    if success:
                        # Save successful
                        self._has_unsaved_changes = False
                        self._last_save_time = time.time()
                        self._save_count += 1
                        
                        save_duration = time.time() - save_start_time
                        self._total_save_time += save_duration
                        
                        logger.debug(f"Auto-save successful ({save_duration:.2f}s)")
                        return True
                    else:
                        logger.warning(f"Save callback returned False (attempt {attempt + 1})")
                        
                except Exception as e:
                    logger.error(f"Error during save (attempt {attempt + 1}): {str(e)}")
                    
                # Wait before retry
                if attempt < self.max_retries:
                    time.sleep(min(2.0 ** attempt, 10.0))  # Exponential backoff
                    
            # All attempts failed
            self._failed_saves += 1
            logger.error(f"Auto-save failed after {self.max_retries + 1} attempts")
            return False
            
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of data for change detection."""
        try:
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, sort_keys=True)
            else:
                data_str = str(data)
                
            return hashlib.md5(data_str.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Error calculating data hash: {e}")
            return str(hash(str(data)))
            
    def check_data_changed(self, data: Any) -> bool:
        """Check if data has changed since last save."""
        if not self.change_detection:
            return True
            
        current_hash = self._calculate_data_hash(data)
        
        with self._save_lock:
            if current_hash != self._last_data_hash:
                self._last_data_hash = current_hash
                self._has_unsaved_changes = True
                return True
                
        return False
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get auto-save statistics."""
        with self._save_lock:
            avg_save_time = self._total_save_time / max(1, self._save_count)
            
            return {
                'running': self._running,
                'save_interval': self.save_interval,
                'change_detection': self.change_detection,
                'save_count': self._save_count,
                'failed_saves': self._failed_saves,
                'total_save_time': self._total_save_time,
                'average_save_time': avg_save_time,
                'has_unsaved_changes': self._has_unsaved_changes,
                'last_save_time': self._last_save_time,
                'output_path': self._output_path
            }
            
    def is_running(self) -> bool:
        """Check if auto-save is running."""
        return self._running
        
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        with self._save_lock:
            return self._has_unsaved_changes
            
    def get_last_save_time(self) -> Optional[float]:
        """Get timestamp of last save."""
        with self._save_lock:
            return self._last_save_time


class AutoSaveManager:
    """Manager for multiple auto-save threads."""
    
    def __init__(self):
        self._auto_savers: Dict[str, AutoSaveThread] = {}
        self._manager_lock = threading.Lock()
        
    def register_auto_saver(self, name: str, auto_saver: AutoSaveThread) -> None:
        """Register an auto-saver."""
        with self._manager_lock:
            if name in self._auto_savers:
                logger.warning(f"Auto-saver {name} already registered, replacing")
                old_saver = self._auto_savers[name]
                old_saver.stop()
                
            self._auto_savers[name] = auto_saver
            
    def unregister_auto_saver(self, name: str) -> bool:
        """Unregister an auto-saver."""
        with self._manager_lock:
            if name in self._auto_savers:
                auto_saver = self._auto_savers[name]
                auto_saver.stop()
                del self._auto_savers[name]
                return True
                
        return False
        
    def start_all(self) -> Dict[str, bool]:
        """Start all registered auto-savers."""
        results = {}
        
        with self._manager_lock:
            for name, auto_saver in self._auto_savers.items():
                results[name] = auto_saver.start()
                
        return results
        
    def stop_all(self, timeout: float = 5.0) -> Dict[str, bool]:
        """Stop all registered auto-savers."""
        results = {}
        
        with self._manager_lock:
            for name, auto_saver in self._auto_savers.items():
                results[name] = auto_saver.stop(timeout)
                
        return results
        
    def trigger_save_all(self) -> Dict[str, bool]:
        """Trigger immediate save for all auto-savers."""
        results = {}
        
        with self._manager_lock:
            for name, auto_saver in self._auto_savers.items():
                results[name] = auto_saver.trigger_save()
                
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """Get status of all auto-savers."""
        status = {}
        
        with self._manager_lock:
            for name, auto_saver in self._auto_savers.items():
                status[name] = auto_saver.get_statistics()
                
        return status
        
    def get_auto_saver(self, name: str) -> Optional[AutoSaveThread]:
        """Get auto-saver by name."""
        with self._manager_lock:
            return self._auto_savers.get(name)


# Global auto-save manager
_global_auto_save_manager = AutoSaveManager()

def get_auto_save_manager() -> AutoSaveManager:
    """Get global auto-save manager."""
    return _global_auto_save_manager