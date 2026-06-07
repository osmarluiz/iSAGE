"""
Progress Thread for Annotation System
Provides progress reporting and status updates for long-running operations.
Based on legacy ABILIUS progress reporting implementation.
"""

import threading
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressState(Enum):
    """Progress states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressUpdate:
    """Progress update information."""
    current: int
    total: int
    percentage: float
    message: str
    timestamp: float
    state: ProgressState
    data: Optional[Dict[str, Any]] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.current >= self.total or self.state == ProgressState.COMPLETED


class ProgressThread:
    """Thread for managing progress reporting of long-running operations."""
    
    def __init__(self, operation_name: str, update_interval: float = 0.1):
        """
        Initialize progress thread.
        
        Args:
            operation_name: Name of the operation
            update_interval: Interval between progress updates in seconds
        """
        self.operation_name = operation_name
        self.update_interval = update_interval
        
        # Threading
        self._progress_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Progress state
        self._progress_lock = threading.RLock()
        self._current_progress = 0
        self._total_progress = 100
        self._progress_message = "Initializing..."
        self._progress_state = ProgressState.IDLE
        self._progress_data: Optional[Dict[str, Any]] = None
        
        # Progress history
        self._progress_history: List[ProgressUpdate] = []
        self._max_history_length = 1000
        
        # Callbacks
        self._progress_callbacks: List[Callable[[ProgressUpdate], None]] = []
        self._completion_callbacks: List[Callable[[ProgressUpdate], None]] = []
        self._error_callbacks: List[Callable[[str], None]] = []
        
        # Statistics
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        self._update_count = 0
        
    def add_progress_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Add progress update callback."""
        with self._progress_lock:
            self._progress_callbacks.append(callback)
            
    def add_completion_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Add completion callback."""
        with self._progress_lock:
            self._completion_callbacks.append(callback)
            
    def add_error_callback(self, callback: Callable[[str], None]) -> None:
        """Add error callback."""
        with self._progress_lock:
            self._error_callbacks.append(callback)
            
    def start(self, total_steps: int = 100) -> bool:
        """Start progress tracking."""
        if self._running:
            logger.warning(f"Progress thread for {self.operation_name} already running")
            return False
            
        with self._progress_lock:
            self._total_progress = total_steps
            self._current_progress = 0
            self._progress_message = "Starting..."
            self._progress_state = ProgressState.RUNNING
            self._progress_data = None
            self._start_time = time.time()
            self._last_update_time = time.time()
            self._update_count = 0
            
        self._stop_event.clear()
        self._running = True
        
        self._progress_thread = threading.Thread(target=self._progress_loop, daemon=True)
        self._progress_thread.start()
        
        logger.info(f"Progress tracking started for {self.operation_name}")
        return True
        
    def stop(self, timeout: float = 2.0) -> bool:
        """Stop progress tracking."""
        if not self._running:
            return True
            
        self._stop_event.set()
        self._running = False
        
        if self._progress_thread and self._progress_thread.is_alive():
            self._progress_thread.join(timeout=timeout)
            
            if self._progress_thread.is_alive():
                logger.warning(f"Progress thread for {self.operation_name} did not stop within timeout")
                return False
                
        logger.info(f"Progress tracking stopped for {self.operation_name}")
        return True
        
    def update_progress(self, current: int, message: str = None, data: Dict[str, Any] = None) -> None:
        """Update progress."""
        with self._progress_lock:
            self._current_progress = max(0, min(current, self._total_progress))
            
            if message:
                self._progress_message = message
                
            if data:
                self._progress_data = data
                
            self._last_update_time = time.time()
            self._update_count += 1
            
    def set_total_steps(self, total: int) -> None:
        """Set total number of steps."""
        with self._progress_lock:
            self._total_progress = max(1, total)
            
    def set_message(self, message: str) -> None:
        """Set progress message."""
        with self._progress_lock:
            self._progress_message = message
            
    def set_state(self, state: ProgressState) -> None:
        """Set progress state."""
        with self._progress_lock:
            self._progress_state = state
            
    def complete(self, message: str = "Completed") -> None:
        """Mark progress as completed."""
        with self._progress_lock:
            self._current_progress = self._total_progress
            self._progress_message = message
            self._progress_state = ProgressState.COMPLETED
            
    def fail(self, message: str = "Failed") -> None:
        """Mark progress as failed."""
        with self._progress_lock:
            self._progress_message = message
            self._progress_state = ProgressState.FAILED
            
    def cancel(self, message: str = "Cancelled") -> None:
        """Mark progress as cancelled."""
        with self._progress_lock:
            self._progress_message = message
            self._progress_state = ProgressState.CANCELLED
            
    def pause(self) -> None:
        """Pause progress tracking."""
        with self._progress_lock:
            self._progress_state = ProgressState.PAUSED
            
    def resume(self) -> None:
        """Resume progress tracking."""
        with self._progress_lock:
            self._progress_state = ProgressState.RUNNING
            
    def _progress_loop(self) -> None:
        """Main progress loop."""
        while not self._stop_event.is_set():
            try:
                # Create progress update
                update = self._create_progress_update()
                
                # Add to history
                self._add_to_history(update)
                
                # Notify callbacks
                self._notify_progress_callbacks(update)
                
                # Check for completion
                if update.is_complete and update.state == ProgressState.COMPLETED:
                    self._notify_completion_callbacks(update)
                    break
                elif update.state in {ProgressState.FAILED, ProgressState.CANCELLED}:
                    break
                    
                # Wait for next update
                if self._stop_event.wait(timeout=self.update_interval):
                    break
                    
            except Exception as e:
                error_msg = f"Error in progress loop for {self.operation_name}: {str(e)}"
                logger.error(error_msg)
                self._notify_error_callbacks(error_msg)
                break
                
    def _create_progress_update(self) -> ProgressUpdate:
        """Create progress update object."""
        with self._progress_lock:
            percentage = (self._current_progress / self._total_progress) * 100
            
            return ProgressUpdate(
                current=self._current_progress,
                total=self._total_progress,
                percentage=percentage,
                message=self._progress_message,
                timestamp=time.time(),
                state=self._progress_state,
                data=self._progress_data.copy() if self._progress_data else None
            )
            
    def _add_to_history(self, update: ProgressUpdate) -> None:
        """Add update to history."""
        with self._progress_lock:
            self._progress_history.append(update)
            
            # Limit history size
            if len(self._progress_history) > self._max_history_length:
                self._progress_history = self._progress_history[-self._max_history_length//2:]
                
    def _notify_progress_callbacks(self, update: ProgressUpdate) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
                
    def _notify_completion_callbacks(self, update: ProgressUpdate) -> None:
        """Notify completion callbacks."""
        for callback in self._completion_callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
                
    def _notify_error_callbacks(self, error_msg: str) -> None:
        """Notify error callbacks."""
        for callback in self._error_callbacks:
            try:
                callback(error_msg)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
                
    def get_current_progress(self) -> ProgressUpdate:
        """Get current progress."""
        return self._create_progress_update()
        
    def get_progress_history(self, limit: int = 100) -> List[ProgressUpdate]:
        """Get progress history."""
        with self._progress_lock:
            return self._progress_history[-limit:]
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get progress statistics."""
        with self._progress_lock:
            current_time = time.time()
            elapsed_time = current_time - self._start_time if self._start_time else 0
            
            # Calculate ETA
            eta = None
            if self._current_progress > 0 and self._progress_state == ProgressState.RUNNING:
                progress_rate = self._current_progress / elapsed_time
                remaining_steps = self._total_progress - self._current_progress
                eta = remaining_steps / progress_rate if progress_rate > 0 else None
                
            return {
                'operation_name': self.operation_name,
                'current_progress': self._current_progress,
                'total_progress': self._total_progress,
                'percentage': (self._current_progress / self._total_progress) * 100,
                'state': self._progress_state.value,
                'message': self._progress_message,
                'running': self._running,
                'elapsed_time': elapsed_time,
                'eta': eta,
                'update_count': self._update_count,
                'history_length': len(self._progress_history),
                'callbacks_registered': len(self._progress_callbacks)
            }
            
    def is_running(self) -> bool:
        """Check if progress tracking is running."""
        return self._running
        
    def get_state(self) -> ProgressState:
        """Get current progress state."""
        with self._progress_lock:
            return self._progress_state


class ProgressManager:
    """Manager for multiple progress threads."""
    
    def __init__(self):
        self._progress_threads: Dict[str, ProgressThread] = {}
        self._manager_lock = threading.Lock()
        
    def create_progress_thread(self, operation_name: str, update_interval: float = 0.1) -> ProgressThread:
        """Create a new progress thread."""
        progress_thread = ProgressThread(operation_name, update_interval)
        
        with self._manager_lock:
            self._progress_threads[operation_name] = progress_thread
            
        return progress_thread
        
    def get_progress_thread(self, operation_name: str) -> Optional[ProgressThread]:
        """Get progress thread by name."""
        with self._manager_lock:
            return self._progress_threads.get(operation_name)
            
    def remove_progress_thread(self, operation_name: str) -> bool:
        """Remove progress thread."""
        with self._manager_lock:
            if operation_name in self._progress_threads:
                progress_thread = self._progress_threads[operation_name]
                progress_thread.stop()
                del self._progress_threads[operation_name]
                return True
                
        return False
        
    def get_all_progress(self) -> Dict[str, ProgressUpdate]:
        """Get current progress for all operations."""
        progress_data = {}
        
        with self._manager_lock:
            for name, progress_thread in self._progress_threads.items():
                progress_data[name] = progress_thread.get_current_progress()
                
        return progress_data
        
    def stop_all(self, timeout: float = 2.0) -> Dict[str, bool]:
        """Stop all progress threads."""
        results = {}
        
        with self._manager_lock:
            for name, progress_thread in self._progress_threads.items():
                results[name] = progress_thread.stop(timeout)
                
        return results
        
    def cleanup_completed(self) -> int:
        """Clean up completed progress threads."""
        completed_count = 0
        
        with self._manager_lock:
            completed_names = []
            
            for name, progress_thread in self._progress_threads.items():
                if not progress_thread.is_running():
                    completed_names.append(name)
                    
            for name in completed_names:
                del self._progress_threads[name]
                completed_count += 1
                
        return completed_count
        
    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._manager_lock:
            return {
                'active_threads': len(self._progress_threads),
                'thread_names': list(self._progress_threads.keys()),
                'running_threads': sum(1 for pt in self._progress_threads.values() if pt.is_running())
            }


# Global progress manager
_global_progress_manager = ProgressManager()

def get_progress_manager() -> ProgressManager:
    """Get global progress manager."""
    return _global_progress_manager