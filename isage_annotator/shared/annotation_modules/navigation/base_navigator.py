"""
Base Navigator - Foundation for all navigation components

This module provides the base class for navigation components that handle
image navigation and session management.
"""

from typing import List, Optional, Dict, Any, Callable
from ..base_protocols import BaseComponent, NavigatorProtocol


class BaseNavigator(BaseComponent):
    """Base class for all navigation components."""
    
    # Navigation-specific signals
    imageChanged = pyqtSignal(int, str)  # index, path
    indexChanged = pyqtSignal(int)  # index
    listChanged = pyqtSignal(list)  # image_paths
    navigationCompleted = pyqtSignal()
    navigationError = pyqtSignal(str)
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        
        self._image_paths: List[str] = []
        self._current_index: int = -1
        self._loop_navigation: bool = True
        self._auto_advance: bool = False
        self._auto_advance_interval: float = 2.0  # seconds
        
        # Navigation history
        self._navigation_history: List[int] = []
        self._max_history_size: int = 100
        
        # Filters and sorting
        self._path_filter: Optional[Callable[[str], bool]] = None
        self._sort_function: Optional[Callable[[List[str]], List[str]]] = None
    
    # NavigatorProtocol implementation
    def set_image_list(self, image_paths: List[str]) -> None:
        """Set list of images to navigate."""
        # Apply filter if set
        if self._path_filter:
            image_paths = [path for path in image_paths if self._path_filter(path)]
        
        # Apply sorting if set
        if self._sort_function:
            image_paths = self._sort_function(image_paths)
        
        self._image_paths = image_paths.copy()
        
        # Reset current index
        if self._image_paths:
            self._current_index = 0
        else:
            self._current_index = -1
        
        # Clear navigation history
        self._navigation_history.clear()
        
        self.listChanged.emit(self._image_paths)
        self.emit_state_changed({
            'image_count': len(self._image_paths),
            'current_index': self._current_index,
            'has_images': len(self._image_paths) > 0
        })
        
        # Emit current image changed if we have images
        if self._image_paths and self._current_index >= 0:
            self.imageChanged.emit(self._current_index, self._image_paths[self._current_index])
    
    def get_image_list(self) -> List[str]:
        """Get current image list."""
        return self._image_paths.copy()
    
    def get_current_index(self) -> int:
        """Get current image index."""
        return self._current_index
    
    def set_current_index(self, index: int) -> bool:
        """Set current image index."""
        if not self._image_paths:
            return False
        
        if 0 <= index < len(self._image_paths):
            old_index = self._current_index
            self._current_index = index
            
            # Add to navigation history
            self._add_to_history(old_index)
            
            # Emit signals
            self.indexChanged.emit(index)
            self.imageChanged.emit(index, self._image_paths[index])
            self.emit_state_changed({'current_index': index})
            
            return True
        
        return False
    
    def next_image(self) -> bool:
        """Navigate to next image."""
        if not self._image_paths:
            return False
        
        if self._current_index < len(self._image_paths) - 1:
            return self.set_current_index(self._current_index + 1)
        elif self._loop_navigation:
            return self.set_current_index(0)
        else:
            self.navigationCompleted.emit()
            return False
    
    def previous_image(self) -> bool:
        """Navigate to previous image."""
        if not self._image_paths:
            return False
        
        if self._current_index > 0:
            return self.set_current_index(self._current_index - 1)
        elif self._loop_navigation:
            return self.set_current_index(len(self._image_paths) - 1)
        else:
            return False
    
    def get_current_image_path(self) -> Optional[str]:
        """Get current image path."""
        if self._image_paths and 0 <= self._current_index < len(self._image_paths):
            return self._image_paths[self._current_index]
        return None
    
    # Navigation-specific methods
    def first_image(self) -> bool:
        """Navigate to first image."""
        if self._image_paths:
            return self.set_current_index(0)
        return False
    
    def last_image(self) -> bool:
        """Navigate to last image."""
        if self._image_paths:
            return self.set_current_index(len(self._image_paths) - 1)
        return False
    
    def jump_to_image(self, image_path: str) -> bool:
        """Jump to specific image by path."""
        try:
            index = self._image_paths.index(image_path)
            return self.set_current_index(index)
        except ValueError:
            return False
    
    def random_image(self) -> bool:
        """Navigate to random image."""
        if not self._image_paths:
            return False
        
        import random
        random_index = random.randint(0, len(self._image_paths) - 1)
        return self.set_current_index(random_index)
    
    def set_loop_navigation(self, enabled: bool) -> None:
        """Enable/disable loop navigation."""
        self._loop_navigation = enabled
        self.emit_state_changed({'loop_navigation': enabled})
    
    def is_loop_navigation_enabled(self) -> bool:
        """Check if loop navigation is enabled."""
        return self._loop_navigation
    
    def set_auto_advance(self, enabled: bool) -> None:
        """Enable/disable auto advance."""
        self._auto_advance = enabled
        self.emit_state_changed({'auto_advance': enabled})
    
    def is_auto_advance_enabled(self) -> bool:
        """Check if auto advance is enabled."""
        return self._auto_advance
    
    def set_auto_advance_interval(self, interval: float) -> None:
        """Set auto advance interval in seconds."""
        self._auto_advance_interval = max(0.1, interval)
        self.emit_state_changed({'auto_advance_interval': interval})
    
    def get_auto_advance_interval(self) -> float:
        """Get auto advance interval."""
        return self._auto_advance_interval
    
    def get_navigation_progress(self) -> Dict[str, Any]:
        """Get navigation progress information."""
        if not self._image_paths:
            return {
                'current': 0,
                'total': 0,
                'progress': 0.0,
                'remaining': 0
            }
        
        current = self._current_index + 1
        total = len(self._image_paths)
        progress = current / total if total > 0 else 0.0
        remaining = total - current
        
        return {
            'current': current,
            'total': total,
            'progress': progress,
            'remaining': remaining
        }
    
    def get_navigation_history(self) -> List[int]:
        """Get navigation history."""
        return self._navigation_history.copy()
    
    def clear_navigation_history(self) -> None:
        """Clear navigation history."""
        self._navigation_history.clear()
        self.emit_state_changed({'history_size': 0})
    
    def can_go_back(self) -> bool:
        """Check if can go back in history."""
        return len(self._navigation_history) > 0
    
    def go_back(self) -> bool:
        """Go back in navigation history."""
        if self._navigation_history:
            previous_index = self._navigation_history.pop()
            if 0 <= previous_index < len(self._image_paths):
                self._current_index = previous_index
                self.indexChanged.emit(previous_index)
                self.imageChanged.emit(previous_index, self._image_paths[previous_index])
                self.emit_state_changed({'current_index': previous_index})
                return True
        return False
    
    def set_path_filter(self, filter_func: Optional[Callable[[str], bool]]) -> None:
        """Set path filter function."""
        self._path_filter = filter_func
        # Reapply filter to current list
        if self._image_paths:
            current_path = self.get_current_image_path()
            original_paths = self._image_paths.copy()
            self.set_image_list(original_paths)
            # Try to maintain current image if it passes filter
            if current_path and current_path in self._image_paths:
                self.jump_to_image(current_path)
    
    def set_sort_function(self, sort_func: Optional[Callable[[List[str]], List[str]]]) -> None:
        """Set sort function."""
        self._sort_function = sort_func
        # Reapply sort to current list
        if self._image_paths:
            current_path = self.get_current_image_path()
            original_paths = self._image_paths.copy()
            self.set_image_list(original_paths)
            # Try to maintain current image after sorting
            if current_path and current_path in self._image_paths:
                self.jump_to_image(current_path)
    
    def find_images_by_pattern(self, pattern: str) -> List[int]:
        """Find images matching pattern."""
        import re
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = []
            for i, path in enumerate(self._image_paths):
                if regex.search(path):
                    matches.append(i)
            return matches
        except re.error:
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get navigation statistics."""
        return {
            'image_count': len(self._image_paths),
            'current_index': self._current_index,
            'current_path': self.get_current_image_path(),
            'loop_navigation': self._loop_navigation,
            'auto_advance': self._auto_advance,
            'auto_advance_interval': self._auto_advance_interval,
            'history_size': len(self._navigation_history),
            'can_go_back': self.can_go_back(),
            'has_filter': self._path_filter is not None,
            'has_sort': self._sort_function is not None,
            'progress': self.get_navigation_progress()
        }
    
    # Helper methods
    def _add_to_history(self, index: int) -> None:
        """Add index to navigation history."""
        if index >= 0 and index != self._current_index:
            self._navigation_history.append(index)
            
            # Limit history size
            if len(self._navigation_history) > self._max_history_size:
                self._navigation_history.pop(0)
            
            self.emit_state_changed({'history_size': len(self._navigation_history)})
    
    def _validate_index(self, index: int) -> bool:
        """Validate if index is valid."""
        return 0 <= index < len(self._image_paths)
    
    def _validate_path(self, path: str) -> bool:
        """Validate if path exists in current list."""
        return path in self._image_paths


# Re-export for convenience
NavigatorProtocol = NavigatorProtocol