"""
Resource Monitor Thread for Annotation System
Provides system resource monitoring with threading support.
Based on legacy ABILIUS resource monitoring implementation.
"""

import threading
import time
import logging
import psutil
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

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


@dataclass
class SystemMetrics:
    """System resource metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    gpu_percent: Optional[float] = None
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    process_cpu_percent: Optional[float] = None
    process_memory_mb: Optional[float] = None
    

class ResourceMonitor(QThread):
    """Thread for monitoring system resources."""
    
    # Signals for resource updates
    metrics_updated = pyqtSignal(object)  # SystemMetrics
    alert_triggered = pyqtSignal(str, float)  # alert_type, value
    
    def __init__(self, update_interval: float = 1.0):
        super().__init__()
        self.update_interval = update_interval
        self.should_stop = False
        self.is_paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially not paused
        
        # Resource thresholds for alerts
        self._cpu_threshold = 80.0
        self._memory_threshold = 85.0
        self._disk_threshold = 90.0
        self._gpu_threshold = 90.0
        
        # Callbacks
        self._metrics_callbacks: List[Callable[[SystemMetrics], None]] = []
        self._alert_callbacks: List[Callable[[str, float], None]] = []
        
        # History
        self._metrics_history: List[SystemMetrics] = []
        self._max_history_length = 1000
        
        # Statistics
        self._update_count = 0
        self._start_time: Optional[float] = None
        self._alert_count = 0
        
        # Process monitoring
        self._monitor_process = True
        self._current_process = psutil.Process()
        
    def set_thresholds(self, cpu: float = None, memory: float = None, 
                      disk: float = None, gpu: float = None) -> None:
        """Set resource thresholds for alerts."""
        if cpu is not None:
            self._cpu_threshold = cpu
        if memory is not None:
            self._memory_threshold = memory
        if disk is not None:
            self._disk_threshold = disk
        if gpu is not None:
            self._gpu_threshold = gpu
            
    def add_metrics_callback(self, callback: Callable[[SystemMetrics], None]) -> None:
        """Add callback for metrics updates."""
        self._metrics_callbacks.append(callback)
        
    def add_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        """Add callback for alerts."""
        self._alert_callbacks.append(callback)
        
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if not self.isRunning():
            self.should_stop = False
            self.is_paused = False
            self._start_time = time.time()
            self.start()
            logger.info("Resource monitoring started")
            
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.should_stop = True
        self._pause_event.set()  # Unpause if paused
        self.wait(5000)  # Wait up to 5 seconds for thread to stop
        logger.info("Resource monitoring stopped")
        
    def pause_monitoring(self) -> None:
        """Pause resource monitoring."""
        self.is_paused = True
        self._pause_event.clear()
        logger.info("Resource monitoring paused")
        
    def resume_monitoring(self) -> None:
        """Resume resource monitoring."""
        self.is_paused = False
        self._pause_event.set()
        logger.info("Resource monitoring resumed")
        
    def run(self) -> None:
        """Main monitoring loop."""
        while not self.should_stop:
            try:
                # Wait if paused
                if self.is_paused:
                    self._pause_event.wait()
                    
                if self.should_stop:
                    break
                    
                # Collect metrics
                metrics = self._collect_system_metrics()
                
                # Add to history
                self._add_to_history(metrics)
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Emit signal
                if PYQT5_AVAILABLE:
                    self.metrics_updated.emit(metrics)
                    
                # Notify callbacks
                self._notify_metrics_callbacks(metrics)
                
                self._update_count += 1
                
                # Sleep for update interval
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.update_interval)
                
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system resource metrics."""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # GPU metrics (if available)
        gpu_percent = None
        gpu_memory_used_mb = None
        gpu_memory_total_mb = None
        
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                gpu_percent = gpu.load * 100
                gpu_memory_used_mb = gpu.memoryUsed
                gpu_memory_total_mb = gpu.memoryTotal
        except (ImportError, Exception):
            pass  # GPU monitoring not available
            
        # Process metrics
        process_cpu_percent = None
        process_memory_mb = None
        
        if self._monitor_process:
            try:
                process_cpu_percent = self._current_process.cpu_percent()
                process_memory_mb = self._current_process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass  # Process monitoring failed
                
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk_usage_percent,
            disk_used_gb=disk.used / (1024 * 1024 * 1024),
            disk_free_gb=disk.free / (1024 * 1024 * 1024),
            gpu_percent=gpu_percent,
            gpu_memory_used_mb=gpu_memory_used_mb,
            gpu_memory_total_mb=gpu_memory_total_mb,
            process_cpu_percent=process_cpu_percent,
            process_memory_mb=process_memory_mb
        )
        
    def _add_to_history(self, metrics: SystemMetrics) -> None:
        """Add metrics to history."""
        self._metrics_history.append(metrics)
        
        # Limit history size
        if len(self._metrics_history) > self._max_history_length:
            self._metrics_history = self._metrics_history[-self._max_history_length//2:]
            
    def _check_alerts(self, metrics: SystemMetrics) -> None:
        """Check for resource alerts."""
        alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self._cpu_threshold:
            alerts.append(("cpu", metrics.cpu_percent))
            
        # Memory alert
        if metrics.memory_percent > self._memory_threshold:
            alerts.append(("memory", metrics.memory_percent))
            
        # Disk alert
        if metrics.disk_usage_percent > self._disk_threshold:
            alerts.append(("disk", metrics.disk_usage_percent))
            
        # GPU alert
        if metrics.gpu_percent and metrics.gpu_percent > self._gpu_threshold:
            alerts.append(("gpu", metrics.gpu_percent))
            
        # Trigger alerts
        for alert_type, value in alerts:
            self._alert_count += 1
            
            if PYQT5_AVAILABLE:
                self.alert_triggered.emit(alert_type, value)
                
            self._notify_alert_callbacks(alert_type, value)
            
    def _notify_metrics_callbacks(self, metrics: SystemMetrics) -> None:
        """Notify metrics callbacks."""
        for callback in self._metrics_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Error in metrics callback: {e}")
                
    def _notify_alert_callbacks(self, alert_type: str, value: float) -> None:
        """Notify alert callbacks."""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, value)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
                
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get current metrics."""
        if self._metrics_history:
            return self._metrics_history[-1]
        return None
        
    def get_metrics_history(self, limit: int = 100) -> List[SystemMetrics]:
        """Get metrics history."""
        return self._metrics_history[-limit:]
        
    def get_average_metrics(self, duration_seconds: int = 60) -> Optional[SystemMetrics]:
        """Get average metrics over specified duration."""
        if not self._metrics_history:
            return None
            
        # Filter metrics within duration
        current_time = time.time()
        cutoff_time = current_time - duration_seconds
        
        recent_metrics = [m for m in self._metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return None
            
        # Calculate averages
        count = len(recent_metrics)
        
        return SystemMetrics(
            timestamp=current_time,
            cpu_percent=sum(m.cpu_percent for m in recent_metrics) / count,
            memory_percent=sum(m.memory_percent for m in recent_metrics) / count,
            memory_used_mb=sum(m.memory_used_mb for m in recent_metrics) / count,
            memory_available_mb=sum(m.memory_available_mb for m in recent_metrics) / count,
            disk_usage_percent=sum(m.disk_usage_percent for m in recent_metrics) / count,
            disk_used_gb=sum(m.disk_used_gb for m in recent_metrics) / count,
            disk_free_gb=sum(m.disk_free_gb for m in recent_metrics) / count,
            gpu_percent=sum(m.gpu_percent for m in recent_metrics if m.gpu_percent) / count if any(m.gpu_percent for m in recent_metrics) else None,
            gpu_memory_used_mb=sum(m.gpu_memory_used_mb for m in recent_metrics if m.gpu_memory_used_mb) / count if any(m.gpu_memory_used_mb for m in recent_metrics) else None,
            gpu_memory_total_mb=sum(m.gpu_memory_total_mb for m in recent_metrics if m.gpu_memory_total_mb) / count if any(m.gpu_memory_total_mb for m in recent_metrics) else None,
            process_cpu_percent=sum(m.process_cpu_percent for m in recent_metrics if m.process_cpu_percent) / count if any(m.process_cpu_percent for m in recent_metrics) else None,
            process_memory_mb=sum(m.process_memory_mb for m in recent_metrics if m.process_memory_mb) / count if any(m.process_memory_mb for m in recent_metrics) else None
        )
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        current_time = time.time()
        elapsed_time = current_time - self._start_time if self._start_time else 0
        
        return {
            'running': self.isRunning(),
            'paused': self.is_paused,
            'update_interval': self.update_interval,
            'update_count': self._update_count,
            'alert_count': self._alert_count,
            'history_length': len(self._metrics_history),
            'elapsed_time': elapsed_time,
            'thresholds': {
                'cpu': self._cpu_threshold,
                'memory': self._memory_threshold,
                'disk': self._disk_threshold,
                'gpu': self._gpu_threshold
            },
            'callbacks_registered': len(self._metrics_callbacks)
        }
        
    def enable_process_monitoring(self) -> None:
        """Enable process-specific monitoring."""
        self._monitor_process = True
        
    def disable_process_monitoring(self) -> None:
        """Disable process-specific monitoring."""
        self._monitor_process = False


# Global resource monitor
_global_resource_monitor = None

def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor."""
    global _global_resource_monitor
    if _global_resource_monitor is None:
        _global_resource_monitor = ResourceMonitor()
    return _global_resource_monitor