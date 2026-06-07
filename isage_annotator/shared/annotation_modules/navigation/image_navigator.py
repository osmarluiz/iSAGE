"""
Image Navigator - Navigation through image datasets

This module provides image navigation functionality with thumbnail generation,
filtering, and batch operations for annotation workflows.
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from pathlib import Path
from ..base_protocols import BaseComponent, QPixmap, QSize
from .base_navigator import BaseNavigator


class ImageNavigator(BaseNavigator):
    """Navigates through image datasets with thumbnail support."""
    
    # Navigation signals
    imageChanged = pyqtSignal(str)  # image_path
    imageLoadFailed = pyqtSignal(str)  # error_message
    thumbnailGenerated = pyqtSignal(str)  # image_path
    batchProcessed = pyqtSignal(int)  # processed_count
    
    def __init__(self, name: str = "image_navigator", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Image navigation state
        self._image_paths: List[str] = []
        self._current_index: int = -1
        self._current_image_path: Optional[str] = None
        self._current_image_size: Tuple[int, int] = (0, 0)
        
        # Thumbnail configuration
        self._thumbnail_size: QSize = QSize(128, 128)
        self._thumbnail_cache: Dict[str, QPixmap] = {}
        self._cache_enabled: bool = True
        self._max_cache_size: int = 1000
        
        # Supported formats
        self._supported_formats: List[str] = [
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', 
            '.gif', '.webp', '.jp2', '.j2k', '.hdr', '.exr'
        ]
        
        # Filtering
        self._filters: Dict[str, Callable[[str], bool]] = {}
        self._filtered_paths: List[str] = []
        self._filter_enabled: bool = False
        
        # Loading configuration
        self._preload_enabled: bool = True
        self._preload_count: int = 3
        self._preload_cache: Dict[str, QPixmap] = {}
        
        # Statistics
        self._navigation_count: int = 0
        self._thumbnail_generation_count: int = 0
        self._load_errors: List[str] = []
        
        # Batch processing
        self._batch_size: int = 50
        self._batch_processing: bool = False
    
    def initialize(self, **kwargs) -> bool:
        """Initialize image navigator."""
        self._thumbnail_size = kwargs.get('thumbnail_size', QSize(128, 128))
        self._cache_enabled = kwargs.get('cache_enabled', True)
        self._max_cache_size = kwargs.get('max_cache_size', 1000)
        self._preload_enabled = kwargs.get('preload_enabled', True)
        self._preload_count = kwargs.get('preload_count', 3)
        self._batch_size = kwargs.get('batch_size', 50)
        
        # Add custom formats if provided
        if 'supported_formats' in kwargs:
            self._supported_formats.extend(kwargs['supported_formats'])
        
        return super().initialize(**kwargs)
    
    def load_directory(self, directory_path: str, recursive: bool = False) -> bool:
        """Load images from directory."""
        try:
            if not os.path.exists(directory_path):
                self.emit_error(f"Directory not found: {directory_path}")
                return False
            
            # Find image files
            image_paths = []
            
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._is_supported_format(file_path):
                            image_paths.append(file_path)
            else:
                for file in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, file)
                    if os.path.isfile(file_path) and self._is_supported_format(file_path):
                        image_paths.append(file_path)
            
            # Sort paths
            image_paths.sort()
            
            # Set image paths
            self._image_paths = image_paths
            self._current_index = 0 if image_paths else -1
            self._current_image_path = image_paths[0] if image_paths else None
            
            # Apply filters
            self._apply_filters()
            
            # Start preloading
            if self._preload_enabled:
                self._preload_images()
            
            self.emit_state_changed({
                'directory_loaded': directory_path,
                'image_count': len(image_paths),
                'current_index': self._current_index
            })
            
            if self._current_image_path:
                self.imageChanged.emit(self._current_image_path)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error loading directory: {str(e)}")
            return False
    
    def load_file_list(self, file_paths: List[str]) -> bool:
        """Load specific list of image files."""
        try:
            # Filter supported formats
            valid_paths = []
            for path in file_paths:
                if os.path.exists(path) and self._is_supported_format(path):
                    valid_paths.append(path)
                else:
                    self._load_errors.append(f"Invalid or unsupported file: {path}")
            
            # Sort paths
            valid_paths.sort()
            
            # Set image paths
            self._image_paths = valid_paths
            self._current_index = 0 if valid_paths else -1
            self._current_image_path = valid_paths[0] if valid_paths else None
            
            # Apply filters
            self._apply_filters()
            
            # Start preloading
            if self._preload_enabled:
                self._preload_images()
            
            self.emit_state_changed({
                'file_list_loaded': True,
                'image_count': len(valid_paths),
                'current_index': self._current_index,
                'load_errors': len(self._load_errors)
            })
            
            if self._current_image_path:
                self.imageChanged.emit(self._current_image_path)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error loading file list: {str(e)}")
            return False
    
    def navigate_to_index(self, index: int) -> bool:
        """Navigate to specific image index."""
        try:
            paths = self._filtered_paths if self._filter_enabled else self._image_paths
            
            if not paths or index < 0 or index >= len(paths):
                return False
            
            self._current_index = index
            self._current_image_path = paths[index]
            
            # Update navigation count
            self._navigation_count += 1
            
            # Preload surrounding images
            if self._preload_enabled:
                self._preload_images()
            
            self.emit_state_changed({
                'current_index': self._current_index,
                'navigation_count': self._navigation_count
            })
            
            self.imageChanged.emit(self._current_image_path)
            return True
            
        except Exception as e:
            self.emit_error(f"Error navigating to index: {str(e)}")
            return False
    
    def navigate_to_file(self, file_path: str) -> bool:
        """Navigate to specific image file."""
        try:
            paths = self._filtered_paths if self._filter_enabled else self._image_paths
            
            if file_path in paths:
                index = paths.index(file_path)
                return self.navigate_to_index(index)
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error navigating to file: {str(e)}")
            return False
    
    def navigate_next(self) -> bool:
        """Navigate to next image."""
        paths = self._filtered_paths if self._filter_enabled else self._image_paths
        
        if not paths:
            return False
        
        next_index = (self._current_index + 1) % len(paths)
        return self.navigate_to_index(next_index)
    
    def navigate_previous(self) -> bool:
        """Navigate to previous image."""
        paths = self._filtered_paths if self._filter_enabled else self._image_paths
        
        if not paths:
            return False
        
        prev_index = (self._current_index - 1) % len(paths)
        return self.navigate_to_index(prev_index)
    
    def navigate_first(self) -> bool:
        """Navigate to first image."""
        return self.navigate_to_index(0)
    
    def navigate_last(self) -> bool:
        """Navigate to last image."""
        paths = self._filtered_paths if self._filter_enabled else self._image_paths
        
        if not paths:
            return False
        
        return self.navigate_to_index(len(paths) - 1)
    
    def get_current_image_path(self) -> Optional[str]:
        """Get current image path."""
        return self._current_image_path
    
    def get_current_index(self) -> int:
        """Get current image index."""
        return self._current_index
    
    def get_image_count(self) -> int:
        """Get total image count."""
        paths = self._filtered_paths if self._filter_enabled else self._image_paths
        return len(paths)
    
    def get_image_paths(self) -> List[str]:
        """Get all image paths."""
        return (self._filtered_paths if self._filter_enabled else self._image_paths).copy()
    
    def get_image_info(self, image_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get image information."""
        try:
            if image_path is None:
                image_path = self._current_image_path
            
            if not image_path or not os.path.exists(image_path):
                return None
            
            # Get file stats
            stat = os.stat(image_path)
            
            # Get image dimensions
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    mode = img.mode
                    format_name = img.format
            except ImportError:
                # Fallback without PIL
                width, height = 0, 0
                mode = 'unknown'
                format_name = 'unknown'
            
            info = {
                'path': image_path,
                'filename': os.path.basename(image_path),
                'directory': os.path.dirname(image_path),
                'size_bytes': stat.st_size,
                'modified_time': stat.st_mtime,
                'width': width,
                'height': height,
                'mode': mode,
                'format': format_name,
                'aspect_ratio': width / height if height > 0 else 0
            }
            
            return info
            
        except Exception as e:
            self.emit_error(f"Error getting image info: {str(e)}")
            return None
    
    def generate_thumbnail(self, image_path: str, size: Optional[QSize] = None) -> Optional[QPixmap]:
        """Generate thumbnail for image."""
        try:
            if size is None:
                size = self._thumbnail_size
            
            # Check cache
            cache_key = f"{image_path}_{size.width()}x{size.height()}"
            if self._cache_enabled and cache_key in self._thumbnail_cache:
                return self._thumbnail_cache[cache_key]
            
            # Load and resize image
            try:
                from PIL import Image
                from PyQt5.QtGui import QPixmap, QImage
                
                # Open image
                with Image.open(image_path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Calculate thumbnail size maintaining aspect ratio
                    img.thumbnail((size.width(), size.height()), Image.Resampling.LANCZOS)
                    
                    # Convert to QPixmap
                    width, height = img.size
                    bytes_per_line = 3 * width
                    
                    q_image = QImage(
                        img.tobytes(),
                        width,
                        height,
                        bytes_per_line,
                        QImage.Format_RGB888
                    )
                    
                    thumbnail = QPixmap.fromImage(q_image)
                    
                    # Cache thumbnail
                    if self._cache_enabled:
                        self._cache_thumbnail(cache_key, thumbnail)
                    
                    self._thumbnail_generation_count += 1
                    self.thumbnailGenerated.emit(image_path)
                    
                    return thumbnail
                    
            except ImportError:
                # Fallback: load directly as QPixmap
                from PyQt5.QtGui import QPixmap
                
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(size, aspectRatioMode=1, transformMode=1)  # Qt.KeepAspectRatio, Qt.SmoothTransformation
                    
                    # Cache thumbnail
                    if self._cache_enabled:
                        self._cache_thumbnail(cache_key, thumbnail)
                    
                    self._thumbnail_generation_count += 1
                    self.thumbnailGenerated.emit(image_path)
                    
                    return thumbnail
                
                return None
                
        except Exception as e:
            self.emit_error(f"Error generating thumbnail: {str(e)}")
            return None
    
    def generate_thumbnails_batch(self, image_paths: Optional[List[str]] = None) -> int:
        """Generate thumbnails for multiple images."""
        if image_paths is None:
            image_paths = self._filtered_paths if self._filter_enabled else self._image_paths
        
        generated_count = 0
        self._batch_processing = True
        
        try:
            # Process in batches
            for i in range(0, len(image_paths), self._batch_size):
                batch = image_paths[i:i + self._batch_size]
                
                for image_path in batch:
                    if self.generate_thumbnail(image_path):
                        generated_count += 1
                
                # Emit progress
                self.batchProcessed.emit(i + len(batch))
                
                # Allow UI updates
                if hasattr(self, 'processEvents'):
                    self.processEvents()
            
            return generated_count
            
        except Exception as e:
            self.emit_error(f"Error in batch thumbnail generation: {str(e)}")
            return generated_count
        finally:
            self._batch_processing = False
    
    def clear_thumbnail_cache(self) -> None:
        """Clear thumbnail cache."""
        self._thumbnail_cache.clear()
        self._preload_cache.clear()
        self.emit_state_changed({'thumbnail_cache_cleared': True})
    
    def set_thumbnail_size(self, size: QSize) -> None:
        """Set thumbnail size."""
        self._thumbnail_size = size
        self.clear_thumbnail_cache()  # Clear cache as size changed
        self.emit_state_changed({'thumbnail_size': (size.width(), size.height())})
    
    def get_thumbnail_size(self) -> QSize:
        """Get thumbnail size."""
        return self._thumbnail_size
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable/disable thumbnail caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_thumbnail_cache()
        self.emit_state_changed({'cache_enabled': enabled})
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._cache_enabled
    
    def add_filter(self, name: str, filter_func: Callable[[str], bool]) -> None:
        """Add image filter."""
        self._filters[name] = filter_func
        self._apply_filters()
        self.emit_state_changed({'filters': list(self._filters.keys())})
    
    def remove_filter(self, name: str) -> bool:
        """Remove image filter."""
        if name in self._filters:
            del self._filters[name]
            self._apply_filters()
            self.emit_state_changed({'filters': list(self._filters.keys())})
            return True
        return False
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        self._filters.clear()
        self._apply_filters()
        self.emit_state_changed({'filters': []})
    
    def set_filter_enabled(self, enabled: bool) -> None:
        """Enable/disable filtering."""
        self._filter_enabled = enabled
        self._apply_filters()
        self.emit_state_changed({'filter_enabled': enabled})
    
    def is_filter_enabled(self) -> bool:
        """Check if filtering is enabled."""
        return self._filter_enabled
    
    def get_filtered_paths(self) -> List[str]:
        """Get filtered image paths."""
        return self._filtered_paths.copy()
    
    def set_preload_enabled(self, enabled: bool) -> None:
        """Enable/disable preloading."""
        self._preload_enabled = enabled
        if not enabled:
            self._preload_cache.clear()
        self.emit_state_changed({'preload_enabled': enabled})
    
    def is_preload_enabled(self) -> bool:
        """Check if preloading is enabled."""
        return self._preload_enabled
    
    def set_preload_count(self, count: int) -> None:
        """Set preload count."""
        self._preload_count = max(1, count)
        self.emit_state_changed({'preload_count': count})
    
    def get_preload_count(self) -> int:
        """Get preload count."""
        return self._preload_count
    
    def get_navigation_statistics(self) -> Dict[str, Any]:
        """Get navigation statistics."""
        return {
            'navigation_count': self._navigation_count,
            'thumbnail_generation_count': self._thumbnail_generation_count,
            'thumbnail_cache_size': len(self._thumbnail_cache),
            'preload_cache_size': len(self._preload_cache),
            'load_errors': len(self._load_errors),
            'batch_processing': self._batch_processing,
            'filter_enabled': self._filter_enabled,
            'active_filters': len(self._filters),
            'image_count': len(self._image_paths),
            'filtered_count': len(self._filtered_paths)
        }
    
    def _is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self._supported_formats
    
    def _apply_filters(self) -> None:
        """Apply active filters to image paths."""
        if not self._filter_enabled or not self._filters:
            self._filtered_paths = self._image_paths.copy()
            return
        
        filtered_paths = []
        for path in self._image_paths:
            # Apply all filters
            passes_all = True
            for filter_func in self._filters.values():
                if not filter_func(path):
                    passes_all = False
                    break
            
            if passes_all:
                filtered_paths.append(path)
        
        self._filtered_paths = filtered_paths
        
        # Update current index if needed
        if self._current_image_path:
            if self._current_image_path in self._filtered_paths:
                self._current_index = self._filtered_paths.index(self._current_image_path)
            else:
                # Current image filtered out, go to first
                self._current_index = 0 if self._filtered_paths else -1
                self._current_image_path = self._filtered_paths[0] if self._filtered_paths else None
    
    def _preload_images(self) -> None:
        """Preload surrounding images."""
        if not self._preload_enabled:
            return
        
        try:
            paths = self._filtered_paths if self._filter_enabled else self._image_paths
            
            if not paths or self._current_index < 0:
                return
            
            # Determine preload range
            start_index = max(0, self._current_index - self._preload_count)
            end_index = min(len(paths), self._current_index + self._preload_count + 1)
            
            # Preload images
            for i in range(start_index, end_index):
                if i != self._current_index:  # Don't preload current image
                    path = paths[i]
                    if path not in self._preload_cache:
                        thumbnail = self.generate_thumbnail(path)
                        if thumbnail:
                            self._preload_cache[path] = thumbnail
            
            # Limit preload cache size
            if len(self._preload_cache) > self._preload_count * 2:
                # Remove oldest entries
                items = list(self._preload_cache.items())
                for path, _ in items[:len(items) - self._preload_count * 2]:
                    del self._preload_cache[path]
                    
        except Exception as e:
            self.emit_error(f"Error preloading images: {str(e)}")
    
    def _cache_thumbnail(self, cache_key: str, thumbnail: QPixmap) -> None:
        """Cache thumbnail with size limit."""
        if not self._cache_enabled:
            return
        
        # Remove oldest entries if cache is full
        if len(self._thumbnail_cache) >= self._max_cache_size:
            # Remove 10% of oldest entries
            items = list(self._thumbnail_cache.items())
            remove_count = self._max_cache_size // 10
            for key, _ in items[:remove_count]:
                del self._thumbnail_cache[key]
        
        self._thumbnail_cache[cache_key] = thumbnail
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get image navigator statistics."""
        stats = super().get_statistics()
        stats.update({
            'thumbnail_size': (self._thumbnail_size.width(), self._thumbnail_size.height()),
            'cache_enabled': self._cache_enabled,
            'max_cache_size': self._max_cache_size,
            'preload_enabled': self._preload_enabled,
            'preload_count': self._preload_count,
            'batch_size': self._batch_size,
            'supported_formats': self._supported_formats,
            'current_image_path': self._current_image_path,
            'current_index': self._current_index,
            'navigation_statistics': self.get_navigation_statistics()
        })
        return stats