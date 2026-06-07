"""
Base Performance - Foundation for all performance components

This module provides the base class for performance components that handle
optimization and caching.
"""

from typing import Dict, Any, Optional, Callable, Union
import time
from ..base_protocols import BaseComponent, PerformanceProtocol


class BasePerformance(BaseComponent):
    """Base class for all performance components."""
    
    # Performance-specific signals
    performanceImproved = pyqtSignal(str, float)  # operation, improvement_factor
    cacheHit = pyqtSignal(str)  # operation
    cacheMiss = pyqtSignal(str)  # operation
    memoryWarning = pyqtSignal(float)  # memory_usage_mb
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Performance metrics
        self._operation_times: Dict[str, list] = {}
        self._cache_hits: Dict[str, int] = {}
        self._cache_misses: Dict[str, int] = {}
        self._memory_usage: float = 0.0
        
        # Configuration
        self._max_cache_size: int = 1000
        self._memory_threshold: float = 512.0  # MB
        self._enable_profiling: bool = False
        self._enable_caching: bool = True
        
        # Cache storage
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_access_count: Dict[str, int] = {}
        
        # Performance optimizations
        self._optimization_functions: Dict[str, Callable] = {}
    
    # PerformanceProtocol implementation
    def optimize(self, operation: str, data: Any) -> Any:
        """Optimize a specific operation."""
        start_time = time.time()
        
        try:
            # Check cache first
            if self._enable_caching:
                cache_key = self._generate_cache_key(operation, data)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self.cacheHit.emit(operation)
                    self._cache_hits[operation] = self._cache_hits.get(operation, 0) + 1
                    return cached_result
                else:
                    self.cacheMiss.emit(operation)
                    self._cache_misses[operation] = self._cache_misses.get(operation, 0) + 1
            
            # Apply optimization if available
            if operation in self._optimization_functions:
                result = self._optimization_functions[operation](data)
            else:
                result = self._default_optimization(operation, data)
            
            # Cache the result
            if self._enable_caching:
                self._add_to_cache(cache_key, result)
            
            # Record performance
            end_time = time.time()
            operation_time = end_time - start_time
            self._record_operation_time(operation, operation_time)
            
            return result
            
        except Exception as e:
            self.emit_error(f"Error optimizing operation '{operation}': {str(e)}")
            return data
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics."""
        metrics = {
            'memory_usage_mb': self._memory_usage,
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'total_operations': sum(len(times) for times in self._operation_times.values()),
            'average_operation_time': self._calculate_average_operation_time()
        }
        
        # Add per-operation metrics
        for operation, times in self._operation_times.items():
            if times:
                metrics[f'{operation}_avg_time'] = sum(times) / len(times)
                metrics[f'{operation}_min_time'] = min(times)
                metrics[f'{operation}_max_time'] = max(times)
                metrics[f'{operation}_count'] = len(times)
        
        return metrics
    
    def clear_cache(self) -> None:
        """Clear performance caches."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._cache_access_count.clear()
        self.emit_state_changed({'cache_size': 0})
    
    # Performance-specific methods
    def set_max_cache_size(self, size: int) -> None:
        """Set maximum cache size."""
        self._max_cache_size = max(1, size)
        self._cleanup_cache()
        self.emit_state_changed({'max_cache_size': size})
    
    def get_max_cache_size(self) -> int:
        """Get maximum cache size."""
        return self._max_cache_size
    
    def set_memory_threshold(self, threshold_mb: float) -> None:
        """Set memory usage threshold."""
        self._memory_threshold = max(1.0, threshold_mb)
        self.emit_state_changed({'memory_threshold': threshold_mb})
    
    def get_memory_threshold(self) -> float:
        """Get memory usage threshold."""
        return self._memory_threshold
    
    def set_enable_profiling(self, enabled: bool) -> None:
        """Enable/disable profiling."""
        self._enable_profiling = enabled
        self.emit_state_changed({'profiling_enabled': enabled})
    
    def is_profiling_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enable_profiling
    
    def set_enable_caching(self, enabled: bool) -> None:
        """Enable/disable caching."""
        self._enable_caching = enabled
        if not enabled:
            self.clear_cache()
        self.emit_state_changed({'caching_enabled': enabled})
    
    def is_caching_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enable_caching
    
    def add_optimization_function(self, operation: str, func: Callable) -> None:
        """Add optimization function for operation."""
        self._optimization_functions[operation] = func
        self.emit_state_changed({
            'optimization_functions': list(self._optimization_functions.keys())
        })
    
    def remove_optimization_function(self, operation: str) -> None:
        """Remove optimization function for operation."""
        if operation in self._optimization_functions:
            del self._optimization_functions[operation]
            self.emit_state_changed({
                'optimization_functions': list(self._optimization_functions.keys())
            })
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            'size': len(self._cache),
            'max_size': self._max_cache_size,
            'hit_rate': self._calculate_cache_hit_rate(),
            'memory_usage_mb': self._estimate_cache_memory_usage(),
            'oldest_entry': min(self._cache_timestamps.values()) if self._cache_timestamps else 0,
            'newest_entry': max(self._cache_timestamps.values()) if self._cache_timestamps else 0
        }
    
    def get_operation_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed operation statistics."""
        stats = {}
        
        for operation, times in self._operation_times.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'total_time': sum(times),
                    'average_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'cache_hits': self._cache_hits.get(operation, 0),
                    'cache_misses': self._cache_misses.get(operation, 0)
                }
        
        return stats
    
    def reset_performance_metrics(self) -> None:
        """Reset all performance metrics."""
        self._operation_times.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()
        self._memory_usage = 0.0
        self.emit_state_changed({'metrics_reset': True})
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        self._update_memory_usage()
        return self._memory_usage
    
    def profile_operation(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """Profile a specific operation."""
        if not self._enable_profiling:
            return func(*args, **kwargs)
        
        start_time = time.time()
        start_memory = self.get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = self.get_memory_usage()
            
            operation_time = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self._record_operation_time(operation, operation_time)
            
            profile_data = {
                'operation': operation,
                'time': operation_time,
                'memory_delta': memory_delta,
                'timestamp': end_time
            }
            
            self.emit_state_changed({'last_profile': profile_data})
            
            return result
            
        except Exception as e:
            self.emit_error(f"Error profiling operation '{operation}': {str(e)}")
            return func(*args, **kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'cache_info': self.get_cache_info(),
            'performance_metrics': self.get_performance_metrics(),
            'operation_statistics': self.get_operation_statistics(),
            'memory_usage_mb': self.get_memory_usage(),
            'profiling_enabled': self._enable_profiling,
            'caching_enabled': self._enable_caching,
            'optimization_functions': list(self._optimization_functions.keys())
        }
    
    # Helper methods
    def _generate_cache_key(self, operation: str, data: Any) -> str:
        """Generate cache key for operation and data."""
        try:
            # Simple hash-based key generation
            import hashlib
            data_str = str(data)[:1000]  # Limit string length
            key = f"{operation}:{hashlib.md5(data_str.encode()).hexdigest()}"
            return key
        except Exception:
            return f"{operation}:no_key"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            # Update access count and timestamp
            self._cache_access_count[key] = self._cache_access_count.get(key, 0) + 1
            self._cache_timestamps[key] = time.time()
            return self._cache[key]
        return None
    
    def _add_to_cache(self, key: str, value: Any) -> None:
        """Add value to cache."""
        if len(self._cache) >= self._max_cache_size:
            self._cleanup_cache()
        
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        self._cache_access_count[key] = 1
    
    def _cleanup_cache(self) -> None:
        """Clean up cache using LRU strategy."""
        if len(self._cache) <= self._max_cache_size:
            return
        
        # Sort by access count and timestamp (LRU)
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: (self._cache_access_count.get(k, 0), self._cache_timestamps.get(k, 0))
        )
        
        # Remove oldest entries
        remove_count = len(self._cache) - self._max_cache_size + 1
        for key in sorted_keys[:remove_count]:
            del self._cache[key]
            del self._cache_timestamps[key]
            del self._cache_access_count[key]
    
    def _record_operation_time(self, operation: str, time_taken: float) -> None:
        """Record operation execution time."""
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        
        self._operation_times[operation].append(time_taken)
        
        # Keep only last 1000 entries per operation
        if len(self._operation_times[operation]) > 1000:
            self._operation_times[operation] = self._operation_times[operation][-1000:]
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate overall cache hit rate."""
        total_hits = sum(self._cache_hits.values())
        total_misses = sum(self._cache_misses.values())
        total_requests = total_hits + total_misses
        
        if total_requests == 0:
            return 0.0
        
        return total_hits / total_requests
    
    def _calculate_average_operation_time(self) -> float:
        """Calculate average operation time across all operations."""
        all_times = []
        for times in self._operation_times.values():
            all_times.extend(times)
        
        if not all_times:
            return 0.0
        
        return sum(all_times) / len(all_times)
    
    def _estimate_cache_memory_usage(self) -> float:
        """Estimate cache memory usage in MB."""
        try:
            import sys
            total_size = 0
            for key, value in self._cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _update_memory_usage(self) -> None:
        """Update current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            self._memory_usage = process.memory_info().rss / (1024 * 1024)  # Convert to MB
            
            if self._memory_usage > self._memory_threshold:
                self.memoryWarning.emit(self._memory_usage)
        except ImportError:
            # psutil not available
            pass
        except Exception:
            pass
    
    def _default_optimization(self, operation: str, data: Any) -> Any:
        """Default optimization (no-op)."""
        return data


# Re-export for convenience
PerformanceProtocol = PerformanceProtocol