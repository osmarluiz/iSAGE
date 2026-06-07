"""
Background Worker Thread for Annotation System
Provides base class for background operations with progress reporting.
Based on legacy ABILIUS threading implementations.
"""

import threading
import time
import logging
from typing import Optional, Any, Callable, Dict
from abc import ABC, abstractmethod

# Handle PyQt5 imports
try:
    from PyQt5.QtCore import QThread, pyqtSignal
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    # Mock QThread for environments without PyQt5
    class QThread:
        def __init__(self):
            self._thread = None
            self._should_stop = False
            
        def start(self):
            self._should_stop = False
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()
            
        def stop(self):
            self._should_stop = True
            if self._thread:
                self._thread.join(timeout=5.0)
                
        def run(self):
            pass
            
    def pyqtSignal(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


class BackgroundWorker(QThread):
    """Base class for background worker threads."""
    
    # Signals for progress reporting
    progress_updated = pyqtSignal(int, str)  # progress percent, message
    task_completed = pyqtSignal(object)  # result object
    error_occurred = pyqtSignal(str)  # error message
    status_changed = pyqtSignal(str)  # status message
    
    def __init__(self, task_name: str = "Background Task"):
        super().__init__()
        self.task_name = task_name
        self.should_stop = False
        self.is_paused = False
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._task_lock = threading.Lock()
        
        # Progress tracking
        self._progress = 0
        self._total_steps = 100
        self._current_step = 0
        self._status_message = "Initializing..."
        
        # Error handling
        self._error_callback: Optional[Callable] = None
        self._completion_callback: Optional[Callable] = None
        
    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for error handling."""
        self._error_callback = callback
        
    def set_completion_callback(self, callback: Callable[[Any], None]) -> None:
        """Set callback for task completion."""
        self._completion_callback = callback
        
    def stop(self) -> None:
        """Stop the background task."""
        with self._task_lock:
            self.should_stop = True
            self._stop_event.set()
            self._pause_event.set()  # Unpause if paused
            
        logger.info(f"Stop requested for {self.task_name}")
        
    def pause(self) -> None:
        """Pause the background task."""
        with self._task_lock:
            self.is_paused = True
            self._pause_event.clear()
            
        logger.info(f"Pause requested for {self.task_name}")
        
    def resume(self) -> None:
        """Resume the paused background task."""
        with self._task_lock:
            self.is_paused = False
            self._pause_event.set()
            
        logger.info(f"Resume requested for {self.task_name}")
        
    def update_progress(self, step: int, message: str = None) -> None:
        """Update progress and emit signal."""
        with self._task_lock:
            self._current_step = step
            self._progress = int((step / self._total_steps) * 100)
            
            if message:
                self._status_message = message
                
            # Emit progress signal
            if PYQT5_AVAILABLE:
                self.progress_updated.emit(self._progress, self._status_message)
                
    def set_total_steps(self, total: int) -> None:
        """Set total number of steps for progress calculation."""
        with self._task_lock:
            self._total_steps = max(1, total)
            
    def check_should_stop(self) -> bool:
        """Check if task should stop."""
        return self.should_stop or self._stop_event.is_set()
        
    def wait_if_paused(self) -> bool:
        """Wait if task is paused. Returns True if should continue, False if should stop."""
        if self.is_paused:
            logger.info(f"Task {self.task_name} is paused, waiting...")
            # Wait for resume or stop
            while not self._pause_event.wait(timeout=0.1):
                if self.check_should_stop():
                    return False
                    
        return not self.check_should_stop()
        
    def run(self) -> None:
        """Main thread execution."""
        try:
            logger.info(f"Starting background task: {self.task_name}")
            
            if PYQT5_AVAILABLE:
                self.status_changed.emit(f"Starting {self.task_name}")
                
            # Initialize pause event
            self._pause_event.set()
            
            # Execute the main task
            result = self.execute_task()
            
            # Check if task was stopped
            if self.check_should_stop():
                logger.info(f"Task {self.task_name} was stopped")
                return
                
            # Task completed successfully
            logger.info(f"Task {self.task_name} completed successfully")
            
            if PYQT5_AVAILABLE:
                self.task_completed.emit(result)
                self.status_changed.emit(f"{self.task_name} completed")
                
            # Call completion callback
            if self._completion_callback:
                self._completion_callback(result)
                
        except Exception as e:
            error_msg = f"Error in {self.task_name}: {str(e)}"
            logger.error(error_msg)
            
            if PYQT5_AVAILABLE:
                self.error_occurred.emit(error_msg)
                self.status_changed.emit(f"{self.task_name} failed")
                
            # Call error callback
            if self._error_callback:
                self._error_callback(error_msg)
                
    @abstractmethod
    def execute_task(self) -> Any:
        """Execute the main task. Must be implemented by subclasses."""
        pass
        
    def get_status(self) -> Dict[str, Any]:
        """Get current task status."""
        with self._task_lock:
            return {
                'task_name': self.task_name,
                'progress': self._progress,
                'current_step': self._current_step,
                'total_steps': self._total_steps,
                'status_message': self._status_message,
                'is_paused': self.is_paused,
                'should_stop': self.should_stop
            }


class DatasetAnalyzer(BackgroundWorker):
    """Background worker for dataset analysis."""
    
    def __init__(self, dataset_path: str, dataset_type: str):
        super().__init__(f"Dataset Analysis: {dataset_type}")
        self.dataset_path = dataset_path
        self.dataset_type = dataset_type
        
    def execute_task(self) -> Dict[str, Any]:
        """Execute dataset analysis."""
        import os
        from pathlib import Path
        
        dataset_path = Path(self.dataset_path)
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")
            
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(dataset_path.glob(f"**/*{ext}"))
            image_files.extend(dataset_path.glob(f"**/*{ext.upper()}"))
            
        total_files = len(image_files)
        self.set_total_steps(total_files)
        
        # Analyze each image
        stats = {
            'total_images': total_files,
            'total_size_mb': 0,
            'image_sizes': [],
            'file_types': {},
            'corrupted_files': []
        }
        
        for i, img_path in enumerate(image_files):
            # Check if should stop
            if not self.wait_if_paused():
                break
                
            try:
                # Get file info
                file_stat = img_path.stat()
                file_size_mb = file_stat.st_size / (1024 * 1024)
                stats['total_size_mb'] += file_size_mb
                
                # Track file type
                ext = img_path.suffix.lower()
                stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                
                # Try to get image dimensions (requires PIL)
                try:
                    from PIL import Image
                    with Image.open(img_path) as img:
                        stats['image_sizes'].append(img.size)
                except ImportError:
                    # PIL not available, skip size analysis
                    pass
                except Exception as e:
                    stats['corrupted_files'].append(str(img_path))
                    
            except Exception as e:
                logger.warning(f"Error analyzing {img_path}: {e}")
                stats['corrupted_files'].append(str(img_path))
                
            # Update progress
            self.update_progress(i + 1, f"Analyzing {img_path.name}")
            
        # Calculate summary statistics
        if stats['image_sizes']:
            widths = [size[0] for size in stats['image_sizes']]
            heights = [size[1] for size in stats['image_sizes']]
            
            stats['avg_width'] = sum(widths) / len(widths)
            stats['avg_height'] = sum(heights) / len(heights)
            stats['min_width'] = min(widths)
            stats['max_width'] = max(widths)
            stats['min_height'] = min(heights)
            stats['max_height'] = max(heights)
            
        return stats


class ImageProcessor(BackgroundWorker):
    """Background worker for image processing operations."""
    
    def __init__(self, image_paths: list, processing_func: Callable, output_dir: str):
        super().__init__("Image Processing")
        self.image_paths = image_paths
        self.processing_func = processing_func
        self.output_dir = output_dir
        
    def execute_task(self) -> Dict[str, Any]:
        """Execute image processing."""
        from pathlib import Path
        import os
        
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        total_images = len(self.image_paths)
        self.set_total_steps(total_images)
        
        results = {
            'processed_images': 0,
            'failed_images': 0,
            'output_files': [],
            'errors': []
        }
        
        for i, img_path in enumerate(self.image_paths):
            # Check if should stop
            if not self.wait_if_paused():
                break
                
            try:
                # Process image
                output_file = self.processing_func(img_path, output_path)
                results['output_files'].append(output_file)
                results['processed_images'] += 1
                
            except Exception as e:
                error_msg = f"Error processing {img_path}: {str(e)}"
                results['errors'].append(error_msg)
                results['failed_images'] += 1
                logger.error(error_msg)
                
            # Update progress
            self.update_progress(i + 1, f"Processing {Path(img_path).name}")
            
        return results