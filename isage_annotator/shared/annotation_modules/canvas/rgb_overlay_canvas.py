"""
RGB & Overlay Enhanced Canvas - Advanced canvas with RGB channel mapping and overlays

This component extends the annotation canvas with RGB channel mapping and overlay capabilities
matching the functioning system exactly, including ground truth and prediction overlays.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
import imageio

from PyQt5.QtWidgets import QLabel, QWidget, QFrame, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QBrush, QColor, QImage, QFont,
    QMouseEvent, QWheelEvent, QKeyEvent, QPaintEvent
)

# Initialize logger early for import logging
logger = logging.getLogger(__name__)

# Import spatial indexing for O(log n) point searches
try:
    import sys
    from pathlib import Path
    
    # Add spatial index module path
    current_dir = Path(__file__).parent
    tools_dir = current_dir.parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    
    from spatial_index import SpatialIndex, SpatialPoint, BoundingBox
    SPATIAL_INDEX_AVAILABLE = True
    logger.info("Spatial index loaded successfully - using O(log n) optimized searches")
except ImportError as e:
    SPATIAL_INDEX_AVAILABLE = False
    logger.warning(f"Spatial index not available ({e}) - falling back to O(n) search")

# Import default colors to avoid relative import issues in paintEvent
try:
    from ..advanced_control_panel import DEFAULT_CLASS_COLORS
except ImportError:
    # Fallback default colors
    DEFAULT_CLASS_COLORS = [
        (255, 255, 255),    # 0: Impervious - White
        (0, 0, 255),        # 1: Building - Blue
        (0, 255, 0),        # 2: Tree - Green
        (255, 255, 0),      # 3: Car - Yellow
        (0, 255, 255),      # 4: Low vegetation - Cyan
        (255, 0, 0),        # 5: Clutter - Red
    ]


class RGBOverlayCanvas(QLabel):
    """
    Enhanced annotation canvas with RGB channel mapping and overlay support.
    
    Features:
    - RGB channel mapping (R/G/B → 0/1/2 channel selection)
    - Ground truth overlay with opacity control
    - Prediction overlay with opacity control
    - Multi-channel image support
    - Dynamic channel remapping without reloading
    - Professional overlay rendering with class colors
    - Real-time channel mapping updates
    """
    
    # Signals - Enhanced with index and complete point data for O(1) widget operations
    point_added = pyqtSignal(float, float, int, int)  # x, y, class_id, index
    point_removed = pyqtSignal(float, float, int, list)  # x, y, index, point_data [x, y, class]
    point_moved = pyqtSignal(float, float, float, float, int, list)  # old_x, old_y, new_x, new_y, index, point_data
    point_drag_ended = pyqtSignal(float, float, int, int)  # x, y, class_id, index
    mouse_coordinates = pyqtSignal(int, int)     # x, y
    image_loaded = pyqtSignal()
    view_changed = pyqtSignal(float, float, float)  # zoom, pan_x, pan_y
    rgb_channels_changed = pyqtSignal(int, int, int)  # r, g, b channel indices
    overlay_toggled = pyqtSignal(str, bool)  # overlay_type, enabled
    
    def __init__(self, parent=None, name: str = "rgb_overlay_canvas", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # Canvas setup
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QLabel {
                background: #2d3748;
                border: 1px solid #4a5568;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        
        # Image state - OPTIMIZED: Reduced redundant storage
        self.original_image_array = None  # Primary storage as numpy array
        self.current_image_path = None
        self.image_path = None
        
        # Cache system for performance
        self._pixmap_cache = None  # Cached display pixmap
        self._overlay_cache = {}   # Cache for rendered overlays {(mask_id, opacity, size): pixmap}
        self._cache_valid = False  # Flag to invalidate cache
        
        # Annotation state - OPTIMIZED: Better data structure with spatial indexing
        self.annotations = []  # List of [x, y, class_id]
        self.current_class = 1
        self.class_colors = []  # Will be set by control panel
        self.point_size = 3
        self.prior_annotations = set()  # {(x,y,class)} already saved before this session
        self.show_new_halo = True       # halo around points added/edited this session
        self.render_mode = 'auto'       # 'auto' | 'smooth' | 'fast' (nearest-neighbor)
        self.highlighted_point_index = -1
        self.space_pressed = False
        # Undo stack: list of ("add", index, point) or ("remove", index, point)
        self._undo_stack = []
        self._undo_max = 200
        
        # PERFORMANCE: Spatial index for O(log n) point searches instead of O(n)
        self._spatial_index = SpatialIndex() if SPATIAL_INDEX_AVAILABLE else None
        self._spatial_points = {}  # {index: SpatialPoint} mapping for quick access
        
        # Performance optimization
        self._last_mouse_update = 0  # Throttle mouse events
        self._mouse_update_interval = 8  # ~120 FPS for better responsiveness
        self._pending_update_region = None  # For partial updates
        
        # Cache for expensive calculations
        self._cached_image_position = None
        self._cached_viewport_bounds = None
        
        # Mask loading optimization
        self._mask_cache = {}  # {file_path: mask_data} - persistent mask cache
        self._path_cache = {}  # {image_dir: successful_pattern} - path resolution cache
        self._current_gt_path = None  # Track loaded GT path to avoid reloading
        self._current_pred_path = None  # Track loaded prediction path
        
        # Mouse interaction state (sophisticated annotation features)
        self.dragging = False
        self.drag_point_index = -1
        self.last_mouse_pos = None
        self.panning = False
        self.pan_start_pos = None
        
        # Display settings
        self.show_grid = False
        self.grid_size = 50
        self.show_pixel_info = False
        
        # RGB channel mapping (0=R, 1=G, 2=B for standard RGB)
        self.rgb_channel_mapping = [0, 1, 2]  # [R_source, G_source, B_source]
        
        # Overlay settings
        self.show_gt_overlay = False
        self.show_prediction_overlay = False
        self.gt_overlay_opacity = 0.3
        self.prediction_overlay_opacity = 0.5
        
        # Overlay data (loaded when needed)
        self.gt_mask = None
        self.prediction_mask = None
        
        # Zoom and pan state
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 30.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        # Drag state
        self.dragging = False
        self.drag_point_index = -1
        self.last_mouse_pos = None
        
        # Panning state
        self.panning = False
        self.pan_start_pos = None
        
        # Enable mouse tracking and keyboard focus
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Allow keyboard focus
        
        # Performance optimization: Use viewport updates
        self.setUpdatesEnabled(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)  # Faster painting
        
        # Request initial focus
        QTimer.singleShot(100, lambda: self.setFocus())
        
        logger.info(f"RGBOverlayCanvas '{name}' v{version} initialized with performance optimizations")
    
    @property
    def current_image(self):
        """Get current display pixmap (cached for performance)."""
        if not self._cache_valid and self.original_image_array is not None:
            self._regenerate_pixmap_cache()
        return self._pixmap_cache
    
    @property
    def original_pixmap(self):
        """Get original pixmap (generated from array on demand)."""
        return self.current_image
    
    @property 
    def current_image_array(self):
        """Get image data for pixel access (returns numpy array directly)."""
        # With imageio, we work directly with numpy arrays - more efficient
        return self.original_image_array
    
    @property 
    def current_pil_image(self):
        """Deprecated: Use current_image_array instead. Kept for compatibility."""
        return self.current_image_array
    
    def _regenerate_pixmap_cache(self):
        """Regenerate cached pixmap from original array."""
        if self.original_image_array is None:
            return
            
        try:
            # Apply current RGB channel mapping
            display_array = self.apply_rgb_channel_mapping(self.original_image_array)
            
            # Convert to QPixmap
            height, width, channels = display_array.shape
            bytes_per_line = 3 * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Cache the pixmap
            self._pixmap_cache = QPixmap.fromImage(q_image)
            self._cache_valid = True
            
        except Exception as e:
            logger.error(f"Error regenerating pixmap cache: {e}")
            self._pixmap_cache = None
    
    def _cleanup_previous_image(self):
        """Clean up memory from previous image data with selective cache preservation."""
        self.original_image_array = None
        self._pixmap_cache = None
        # PIL cache no longer needed with imageio
        # Note: Keep mask_cache and path_cache for reuse across images
        self._overlay_cache.clear()  # Clear overlay cache but keep mask cache
        self._cache_valid = False
        self.gt_mask = None
        self.prediction_mask = None
        # Clear current path tracking for new image
        self._current_gt_path = None
        self._current_pred_path = None
        # Clear coordinate cache
        self._cached_image_position = None
    
    def _clear_overlay_cache(self, overlay_prefix: str = None):
        """Clear overlay cache entries, optionally filtered by prefix."""
        if overlay_prefix:
            # Clear specific overlay cache entries
            keys_to_remove = [k for k in self._overlay_cache.keys() if k[0].startswith(overlay_prefix)]
            for key in keys_to_remove:
                del self._overlay_cache[key]
        else:
            # Clear all overlay cache
            self._overlay_cache.clear()
    
    def _get_cached_overlay(self, mask: np.ndarray, opacity: float, overlay_type: str) -> QPixmap:
        """Get cached overlay pixmap with file-based caching."""
        if mask is None:
            return QPixmap()
        
        # Use file path for persistent cache keys
        mask_path = None
        if overlay_type == "gt" and self._current_gt_path:
            mask_path = self._current_gt_path
        elif overlay_type == "pred" and self._current_pred_path:
            mask_path = self._current_pred_path
        
        if mask_path:
            # Create persistent cache key based on file path
            cache_key = f"{mask_path}_{opacity}_{mask.shape[0]}x{mask.shape[1]}"
        else:
            # Fallback to shape-based key
            cache_key = f"{overlay_type}_{opacity}_{mask.shape[0]}x{mask.shape[1]}_{hash(mask.tobytes())}"
        
        # Check cache first
        if cache_key in self._overlay_cache:
            logger.debug(f"Using cached overlay: {cache_key}")
            return self._overlay_cache[cache_key]
        
        # Create new overlay pixmap
        alpha_value = int(opacity * 255)
        overlay_pixmap = self.create_colored_mask_pixmap(mask, alpha_value)
        
        # Cache with improved size management
        if len(self._overlay_cache) >= 25:  # Increased limit for better hit rates
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._overlay_cache.keys())[:5]  # Remove 5 oldest
            for key in keys_to_remove:
                del self._overlay_cache[key]
        
        self._overlay_cache[cache_key] = overlay_pixmap
        logger.debug(f"Cached overlay: {cache_key}, cache size: {len(self._overlay_cache)}")
        
        return overlay_pixmap
    
    def _get_cached_mask(self, file_path: str) -> Optional[np.ndarray]:
        """Get mask from cache if available."""
        if file_path in self._mask_cache:
            return self._mask_cache[file_path]
        return None
    
    def _cache_mask(self, file_path: str, mask_data: np.ndarray):
        """Cache mask data with size limit."""
        # Simple size limit to prevent memory explosion
        if len(self._mask_cache) >= 20:  # Limit to 20 cached masks
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._mask_cache))
            del self._mask_cache[oldest_key]
        
        self._mask_cache[file_path] = mask_data
        logger.debug(f"Cached mask: {file_path}, cache size: {len(self._mask_cache)}")
    
    def _find_mask_path_optimized(self, image_path: str, mask_type: str) -> Optional[Path]:
        """Find mask path using cached patterns for efficiency."""
        image_path_obj = Path(image_path)
        image_name = image_path_obj.stem
        image_dir = str(image_path_obj.parent)
        
        # Try cached successful pattern first
        if image_dir in self._path_cache:
            pattern = self._path_cache[image_dir]
            try:
                if pattern == "dense_masks":
                    candidate = image_path_obj.parent.parent / "dense_masks" / f"{image_name}.png"
                elif pattern == "masks":
                    candidate = image_path_obj.parent.parent / "masks" / f"{image_name}.png"
                elif pattern == "gt_directory" and hasattr(self, 'gt_mask_directory') and self.gt_mask_directory:
                    candidate = self.gt_mask_directory / f"{image_name}.png"
                else:
                    candidate = None
                
                if candidate and candidate.exists():
                    return candidate
            except:
                pass
        
        # Fallback to full search and cache the successful pattern
        patterns = [
            ("gt_directory", self.gt_mask_directory / f"{image_name}.png" if hasattr(self, 'gt_mask_directory') and self.gt_mask_directory else None),
            ("dense_masks", image_path_obj.parent.parent / "dense_masks" / f"{image_name}.png"),
            ("masks", image_path_obj.parent.parent / "masks" / f"{image_name}.png"),
            ("same_dir", image_path_obj.parent / f"{image_name}_mask.png"),
            ("ground_truth", image_path_obj.parent.parent / "ground_truth" / f"{image_name}.png"),
        ]
        
        for pattern_name, candidate_path in patterns:
            if candidate_path:
                try:
                    if candidate_path.exists():
                        # Cache the successful pattern
                        self._path_cache[image_dir] = pattern_name
                        logger.debug(f"Cached path pattern '{pattern_name}' for {image_dir}")
                        return candidate_path
                except:
                    continue
        
        return None
    
    def _process_image_data(self, image_data: np.ndarray) -> np.ndarray:
        """Process imageio loaded data for optimal RGB display."""
        logger.debug(f"Processing image: shape={image_data.shape}, dtype={image_data.dtype}")
        
        # Handle different image formats and dimensions
        if image_data.ndim == 2:
            # Grayscale - convert to RGB
            processed = np.stack([image_data] * 3, axis=-1)
        elif image_data.ndim == 3:
            if image_data.shape[2] == 1:
                # Single channel - convert to RGB
                processed = np.repeat(image_data, 3, axis=-1)
            elif image_data.shape[2] == 4:
                # RGBA - drop alpha channel
                processed = image_data[:, :, :3]
            elif image_data.shape[2] > 4:
                # Multi-channel - store all channels but display first 3
                # This enables channel remapping for hyperspectral data
                processed = image_data  # Keep all channels
                logger.info(f"Multi-channel image loaded: {image_data.shape[2]} channels")
            else:
                # RGB (shape[2] == 3) or other 3-channel format
                processed = image_data
        else:
            raise ValueError(f"Unsupported image dimensions: {image_data.shape}")
        
        # Handle different data types efficiently
        if processed.dtype == np.uint8:
            # Already optimal format
            return processed
        elif processed.dtype == np.uint16:
            # 16-bit to 8-bit conversion (common in scientific imaging)
            return (processed >> 8).astype(np.uint8)  # Fast bit shift
        elif processed.dtype in [np.float32, np.float64]:
            # Float to uint8 with proper scaling
            if processed.max() <= 1.0:
                # Normalized float [0,1] 
                return (processed * 255).astype(np.uint8)
            else:
                # Non-normalized float - scale to range
                processed_min = processed.min()
                processed_max = processed.max()
                if processed_max > processed_min:
                    return ((processed - processed_min) / (processed_max - processed_min) * 255).astype(np.uint8)
                else:
                    return np.zeros_like(processed, dtype=np.uint8)
        else:
            # Other data types - generic conversion
            logger.warning(f"Converting unusual dtype {processed.dtype} to uint8")
            return processed.astype(np.uint8)
    
    def _update_cached_coordinates(self):
        """Cache expensive coordinate calculations for better paint performance."""
        if not self.pixmap():
            self._cached_image_position = None
            return
            
        pixmap = self.pixmap()
        widget_rect = self.rect()
        pixmap_rect = pixmap.rect()
        
        # Calculate and cache image position
        x = (widget_rect.width() - pixmap_rect.width()) // 2
        y = (widget_rect.height() - pixmap_rect.height()) // 2
        
        self._cached_image_position = {
            'x': x + self.pan_offset_x,
            'y': y + self.pan_offset_y,
            'width': pixmap.width(),
            'height': pixmap.height()
        }
    
    def get_pixel_info(self, x: int, y: int) -> Dict:
        """Get comprehensive pixel information at coordinates (x, y)."""
        pixel_info = {
            'rgb': None,
            'gt': None,
            'pred': None
        }
        
        logger.debug(f"Getting pixel info for ({x}, {y})")
        
        try:
            # Get RGB values directly from numpy array (much faster than PIL)
            if self.current_pil_image is not None:
                image_array = self.current_pil_image  # This is now a numpy array
                logger.debug(f"Image array exists, shape: {image_array.shape}, dtype: {image_array.dtype}")
                
                img_height, img_width = image_array.shape[:2]
                logger.debug(f"Image dimensions: {img_width}x{img_height}")
                
                # Ensure coordinates are within bounds
                if 0 <= x < img_width and 0 <= y < img_height:
                    logger.debug(f"Coordinates ({x}, {y}) are within bounds")
                    
                    try:
                        # Direct numpy array access (much faster than PIL)
                        if len(image_array.shape) == 3 and image_array.shape[2] >= 3:
                            # RGB or multi-channel image
                            rgb_pixel = image_array[y, x, :3]  # Take first 3 channels
                            pixel_info['rgb'] = tuple(int(val) for val in rgb_pixel)
                            logger.debug(f"Got RGB pixel: {pixel_info['rgb']}")
                        elif len(image_array.shape) == 3 and image_array.shape[2] == 1:
                            # Single channel stored as 3D array
                            gray_val = int(image_array[y, x, 0])
                            pixel_info['rgb'] = (gray_val, gray_val, gray_val)
                            logger.debug(f"Got grayscale pixel: {pixel_info['rgb']}")
                        elif len(image_array.shape) == 2:
                            # Grayscale image
                            gray_val = int(image_array[y, x])
                            pixel_info['rgb'] = (gray_val, gray_val, gray_val)
                            logger.debug(f"Got grayscale pixel: {pixel_info['rgb']}")
                        else:
                            logger.warning(f"Unsupported image array shape: {image_array.shape}")
                            
                    except Exception as e:
                        logger.error(f"Error accessing pixel at ({x}, {y}): {e}")
                else:
                    logger.debug(f"Coordinates ({x}, {y}) out of bounds for {img_width}x{img_height}")
            else:
                logger.debug("No image array available")
            
            # Get ground truth value if available
            # print(f"[DEBUG] Checking GT mask - hasattr: {hasattr(self, 'gt_mask')}, gt_mask: {getattr(self, 'gt_mask', None)}")
            if hasattr(self, 'gt_mask') and self.gt_mask is not None:
                logger.debug(f"GT mask exists, shape: {self.gt_mask.shape}, type: {type(self.gt_mask)}")
                # print(f"[DEBUG] GT mask exists, shape: {self.gt_mask.shape}, type: {type(self.gt_mask)}")
                try:
                    # gt_mask is a numpy array
                    if 0 <= y < self.gt_mask.shape[0] and 0 <= x < self.gt_mask.shape[1]:
                        gt_pixel = self.gt_mask[y, x]  # Note: numpy arrays are [row, col] = [y, x]
                        logger.debug(f"GT pixel at ({x}, {y}): {gt_pixel}, type: {type(gt_pixel)}")
                        
                        # Handle different data types
                        if isinstance(gt_pixel, np.ndarray) and len(gt_pixel) > 0:
                            # Multi-channel ground truth
                            gt_value = int(gt_pixel[0]) if gt_pixel.ndim > 0 else int(gt_pixel)
                        else:
                            # Single value
                            gt_value = int(gt_pixel)
                        
                        logger.debug(f"GT value: {gt_value}")

                        # Return the integer class index directly (not the name)
                        # The bottom navigation panel will handle name lookup with correct class names
                        pixel_info['gt'] = gt_value
                        logger.debug(f"Set GT to class index: {pixel_info['gt']}")
                    else:
                        logger.debug(f"GT coordinates ({x}, {y}) out of bounds for shape {self.gt_mask.shape}")
                            
                except Exception as e:
                    logger.error(f"Error reading GT pixel at ({x}, {y}): {e}")
            else:
                logger.debug("No GT mask available or not loaded")
                # print(f"[DEBUG] No GT mask available or not loaded")
            
            # Get prediction value if available 
            if hasattr(self, 'prediction_mask') and self.prediction_mask is not None:
                try:
                    # prediction_mask is a numpy array
                    if 0 <= y < self.prediction_mask.shape[0] and 0 <= x < self.prediction_mask.shape[1]:
                        pred_pixel = self.prediction_mask[y, x]  # Note: numpy arrays are [row, col] = [y, x]
                        
                        # Handle different data types
                        if isinstance(pred_pixel, np.ndarray) and len(pred_pixel) > 0:
                            # Multi-channel prediction
                            pred_value = int(pred_pixel[0]) if pred_pixel.ndim > 0 else int(pred_pixel)
                        else:
                            # Single value
                            pred_value = int(pred_pixel)
                        
                        # Return the integer class index directly (not the name)
                        # The bottom navigation panel will handle name lookup with correct class names
                        pixel_info['pred'] = pred_value
                            
                except Exception as e:
                    logger.debug(f"Error reading prediction pixel at ({x}, {y}): {e}")
                    
        except Exception as e:
            logger.error(f"Error getting pixel info at ({x}, {y}): {e}")
        
        logger.debug(f"Returning pixel info: {pixel_info}")
        return pixel_info
    
    def load_image(self, image_path: str) -> bool:
        """Load and display an image with RGB channel mapping support.
        OPTIMIZED: Proper memory cleanup and reduced redundancy."""
        try:
            logger.info(f"Loading image with RGB support: {image_path}")
            
            # OPTIMIZATION: Clean up previous data first
            self._cleanup_previous_image()
            
            self.image_path = image_path
            self.current_image_path = image_path
            
            # Clear existing overlay data when loading new image
            self.gt_mask = None
            self.prediction_mask = None
            
            # Check if file exists
            if not Path(image_path).exists():
                logger.error(f"Image file does not exist: {image_path}")
                return False
            
            # OPTIMIZED: Use imageio for superior format support and performance
            try:
                # Load image with imageio
                image_data = imageio.imread(image_path)
                logger.info(f"Loaded image: shape={image_data.shape}, dtype={image_data.dtype}")
                
                # Process image format for RGB display
                self.original_image_array = self._process_image_data(image_data)
                self._cache_valid = False
                # Cache invalidated, will regenerate on next access
                
                # Apply zoom to generate and display the cached pixmap
                self.apply_zoom()
                
                # Try to automatically load ground truth mask
                self.load_ground_truth_mask()
                
            except Exception as e:
                logger.error(f"Failed to load image with imageio: {e}")
                return False
            
            logger.info(f"Successfully loaded image: {Path(image_path).name}")
            
            # Reload overlays if they are currently enabled
            if self.show_gt_overlay:
                self.load_ground_truth_mask()
            if self.show_prediction_overlay:
                self.load_prediction_mask()
            
            # Update display
            self.update()
            
            # Emit signal for minimap update
            self.image_loaded.emit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.setText(f"Failed to load image: {e}")
            return False
    
    def show_empty_state(self, message: str):
        """Show empty state message - MISSING METHOD FROM MODULAR CANVAS."""
        self.clear()
        self.setText(f"📂 {message}\n\nPlease ensure your session has images in:\ndataset/train/images/")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 16px;
                background: #1e293b;
                border: 2px dashed #374151;
                border-radius: 8px;
                padding: 40px;
            }
        """)
    
    def load_annotations(self, annotations: list):
        """Load annotations for current image - OPTIMIZED with spatial index rebuild."""
        self.annotations = annotations.copy() if annotations else []
        logger.info(f"Loaded {len(self.annotations)} annotations")

        # PERFORMANCE: Rebuild spatial index for O(log n) searching
        self._rebuild_spatial_index()

        self.update()  # Redraw to show annotations

    def set_prior_annotations(self, prior_list: list):
        """Mark which (x,y,class) tuples were already saved before this session.

        Points present here are rendered without the 'new' halo. Points missing
        from this set (i.e. added or edited this session) get a halo when
        show_new_halo is True.
        """
        self.prior_annotations = set(
            (int(p[0]), int(p[1]), int(p[2])) for p in (prior_list or [])
        )
        self.update()

    def set_show_new_halo(self, enabled: bool):
        """Toggle the halo around points added/edited this session."""
        self.show_new_halo = bool(enabled)
        self.update()

    def _pick_xform(self):
        """Pick Qt scaling mode based on render_mode and zoom."""
        if self.render_mode == 'smooth':
            return Qt.SmoothTransformation
        if self.render_mode == 'fast':
            return Qt.FastTransformation
        # 'auto': nearest on zoom-in, smooth on zoom-out
        return Qt.FastTransformation if self.zoom_factor >= 1.0 else Qt.SmoothTransformation

    def set_render_mode(self, mode: str):
        """Set render mode: 'auto', 'smooth', or 'fast'."""
        if mode in ('auto', 'smooth', 'fast'):
            self.render_mode = mode
            self.apply_zoom()  # rebuild scaled pixmap with new transform
            self.update()
    
    def clear_annotations(self):
        """Clear all annotations - OPTIMIZED with spatial index clearing."""
        self.annotations = []
        
        # PERFORMANCE: Clear spatial index as well
        if self._spatial_index and SPATIAL_INDEX_AVAILABLE:
            self._spatial_index.clear()
            self._spatial_points.clear()
        
        self.update()  # Redraw to clear annotations
    
    def set_current_class(self, class_id: int):
        """Set the current annotation class - MISSING METHOD FROM MODULAR CANVAS."""
        self.current_class = class_id
    
    def apply_rgb_channel_mapping(self, image_array: np.ndarray) -> np.ndarray:
        """Apply RGB channel mapping to image array."""
        if image_array is None or len(image_array.shape) != 3:
            return image_array
        
        height, width, channels = image_array.shape
        
        # Handle cases where image might have fewer than 3 channels
        available_channels = min(channels, 3)
        
        # Create output array
        mapped_array = np.zeros((height, width, 3), dtype=image_array.dtype)
        
        # Map each RGB channel to the selected source channel
        for output_channel, source_channel in enumerate(self.rgb_channel_mapping):
            if source_channel < available_channels:
                mapped_array[:, :, output_channel] = image_array[:, :, source_channel]
            else:
                # If source channel doesn't exist, use channel 0 as fallback
                mapped_array[:, :, output_channel] = image_array[:, :, 0] if available_channels > 0 else 0
        
        return mapped_array
    
    def regenerate_image_with_channels(self):
        """Regenerate the displayed image with current channel mapping.
        OPTIMIZED: Uses caching system."""
        if self.original_image_array is None:
            return
        
        try:
            # Invalidate caches to force regeneration with new channel mapping
            self._cache_valid = False
            # Cache invalidated due to channel change
            
            # Apply zoom will trigger cache regeneration
            self.apply_zoom()
            
            # Update display
            self.update()
            
            # Emit signal for minimap update
            self.image_loaded.emit()
            
            logger.debug(f"Regenerated image with channel mapping: {self.rgb_channel_mapping}")
            
        except Exception as e:
            logger.error(f"Error regenerating image with channel mapping: {str(e)}")
    
    def set_rgb_channel_mapping(self, channel: str, mapping: int):
        """Set RGB channel mapping and regenerate image display."""
        channel_index_map = {'r': 0, 'g': 1, 'b': 2}
        if channel.lower() in channel_index_map:
            channel_index = channel_index_map[channel.lower()]
            self.rgb_channel_mapping[channel_index] = mapping
            
            logger.info(f"RGB channel {channel.upper()} mapped to channel {mapping}")
            
            # Regenerate image with new channel mapping if image is loaded
            if self.original_image_array is not None:
                self.regenerate_image_with_channels()
            
            # Emit signal
            self.rgb_channels_changed.emit(*self.rgb_channel_mapping)
    
    def set_rgb_channels(self, r_channel: int, g_channel: int, b_channel: int):
        """Set RGB channel mapping and regenerate image display."""
        logger.info(f"RGB channel mapping changed: R={r_channel}, G={g_channel}, B={b_channel}")
        self.rgb_channel_mapping = [r_channel, g_channel, b_channel]
        
        # Regenerate image with new channel mapping if image is loaded
        if self.original_image_array is not None:
            self.regenerate_image_with_channels()
        
        # Emit signal
        self.rgb_channels_changed.emit(r_channel, g_channel, b_channel)
    
    def set_overlay_enabled(self, overlay_type: str, enabled: bool):
        """Enable/disable overlay display with proper memory management."""
        logger.info(f"Overlay {overlay_type} {'enabled' if enabled else 'disabled'}")
        
        if overlay_type == "ground_truth":
            self.show_gt_overlay = enabled
            if enabled and self.gt_mask is None:
                self.load_ground_truth_mask()
            elif not enabled:
                # MEMORY FIX: Release GT mask when disabled
                self.gt_mask = None
                # Clear related overlay cache entries
                self._clear_overlay_cache("gt")
        elif overlay_type == "prediction":
            self.show_prediction_overlay = enabled
            if enabled and self.prediction_mask is None:
                self.load_prediction_mask()
            elif not enabled:
                # MEMORY FIX: Release prediction mask when disabled
                self.prediction_mask = None
                # Clear related overlay cache entries
                self._clear_overlay_cache("pred")
        
        # Update display
        self.update()
        
        # Emit signal
        self.overlay_toggled.emit(overlay_type, enabled)
    
    def set_overlay_settings(self, overlay_type: str, opacity: float):
        """Update overlay display settings."""
        enabled = opacity > 0.0  # Interpret 0.0 opacity as disabled
        
        if overlay_type == "ground_truth":
            self.show_gt_overlay = enabled
            if enabled:
                self.gt_overlay_opacity = opacity
                
            # Load ground truth mask if enabled and not loaded
            if enabled and self.gt_mask is None:
                self.load_ground_truth_mask()
                
        elif overlay_type == "prediction":
            self.show_prediction_overlay = enabled
            if enabled:
                self.prediction_overlay_opacity = opacity
                
            # Load prediction mask if enabled and not loaded
            if enabled and self.prediction_mask is None:
                self.load_prediction_mask()
        
        self.update()  # Trigger repaint
        
        # Emit signal
        self.overlay_toggled.emit(overlay_type, enabled)
    
    def set_overlay_opacity(self, overlay_type: str, opacity: float):
        """Set overlay opacity (matches functioning system interface)."""
        if overlay_type == "ground_truth":
            self.gt_overlay_opacity = opacity
            # Enable/disable based on opacity
            self.show_gt_overlay = opacity > 0.0
            # Load mask if enabled and not loaded
            if self.show_gt_overlay and self.gt_mask is None:
                self.load_ground_truth_mask()
        elif overlay_type == "prediction":
            self.prediction_overlay_opacity = opacity
            # Enable/disable based on opacity
            self.show_prediction_overlay = opacity > 0.0
            # Load mask if enabled and not loaded
            if self.show_prediction_overlay and self.prediction_mask is None:
                self.load_prediction_mask()
        
        self.update()  # Trigger repaint
        logger.debug(f"Overlay {overlay_type} opacity set to {opacity}")
    
    def set_gt_mask_directory(self, mask_dir: str):
        """Set the directory where ground truth masks are stored."""
        self.gt_mask_directory = Path(mask_dir) if mask_dir else None
        logger.info(f"GT mask directory set to: {self.gt_mask_directory}")
        # Reload GT mask if image is loaded and overlay is enabled
        if self.current_image_path and self.show_gt_overlay:
            self.load_ground_truth_mask()

    def set_prediction_directory(self, pred_dir: str):
        """Set the directory where prediction masks are stored."""
        self.prediction_directory = Path(pred_dir) if pred_dir else None
        logger.info(f"Prediction directory set to: {self.prediction_directory}")
        # Reload prediction mask if image is loaded and overlay is enabled
        if self.current_image_path and self.show_prediction_overlay:
            self.load_prediction_mask()

    def load_ground_truth_mask(self):
        """Load ground truth mask with optimized caching and path resolution."""
        if not self.current_image_path:
            return
        
        try:
            # Find GT mask path using optimized search
            gt_mask_path = self._find_mask_path_optimized(self.current_image_path, "gt")
            
            if not gt_mask_path:
                logger.debug(f"No ground truth mask found for {Path(self.current_image_path).stem}")
                self.gt_mask = None
                self._current_gt_path = None
                return
            
            gt_mask_path_str = str(gt_mask_path)
            
            # Check if already loaded (avoid redundant loading)
            if self._current_gt_path == gt_mask_path_str and self.gt_mask is not None:
                logger.debug(f"GT mask already loaded from {gt_mask_path_str}")
                return
            
            # Try cache first
            cached_mask = self._get_cached_mask(gt_mask_path_str)
            if cached_mask is not None:
                self.gt_mask = cached_mask
                self._current_gt_path = gt_mask_path_str
                logger.info(f"Loaded GT mask from cache: {gt_mask_path.name}")
                
                # Emit signal to notify that GT was loaded
                if hasattr(self, 'overlay_toggled'):
                    self.overlay_toggled.emit("ground_truth", True)
                return
            
            # Load from file and cache
            logger.info(f"Loading ground truth mask: {gt_mask_path}")
            mask_data = imageio.imread(gt_mask_path_str)
            
            # Cache the loaded mask
            self._cache_mask(gt_mask_path_str, mask_data)
            
            # Set as current mask
            self.gt_mask = mask_data
            self._current_gt_path = gt_mask_path_str
            
            logger.info(f"Loaded GT mask: shape={self.gt_mask.shape}, dtype={self.gt_mask.dtype}")
            
            # Emit signal to notify that GT was loaded
            if hasattr(self, 'overlay_toggled'):
                self.overlay_toggled.emit("ground_truth", True)
                
        except Exception as e:
            logger.error(f"Error loading ground truth mask: {e}")
            self.gt_mask = None
            self._current_gt_path = None
    
    def load_prediction_mask(self):
        """Load prediction mask with optimized caching."""
        if not self.current_image_path:
            return

        try:
            # Find prediction mask path
            image_path_obj = Path(self.current_image_path)
            image_name = image_path_obj.stem

            pred_mask_path = None

            # SIAL ADAPTATION: Check configured prediction directory first
            if hasattr(self, 'prediction_directory') and self.prediction_directory:
                configured_path = self.prediction_directory / f"{image_name}.png"
                if configured_path.exists():
                    pred_mask_path = configured_path
                    logger.debug(f"Found prediction in configured directory: {pred_mask_path}")

            # Fallback: Common prediction mask locations relative to image
            if not pred_mask_path:
                possible_paths = [
                    image_path_obj.parent / "predictions" / f"{image_name}.png",
                    image_path_obj.parent / "pred" / f"{image_name}.png",
                    image_path_obj.parent / f"{image_name}_pred.png",
                ]

                for path in possible_paths:
                    if path.exists():
                        pred_mask_path = path
                        logger.debug(f"Found prediction in relative location: {pred_mask_path}")
                        break

            if not pred_mask_path:
                logger.debug(f"No prediction mask found for {image_name}")
                self.prediction_mask = None
                self._current_pred_path = None
                return
            
            pred_mask_path_str = str(pred_mask_path)
            
            # Check if already loaded (avoid redundant loading)
            if self._current_pred_path == pred_mask_path_str and self.prediction_mask is not None:
                logger.debug(f"Prediction mask already loaded from {pred_mask_path_str}")
                return
            
            # Try cache first
            cached_mask = self._get_cached_mask(pred_mask_path_str)
            if cached_mask is not None:
                self.prediction_mask = cached_mask
                self._current_pred_path = pred_mask_path_str
                logger.info(f"Loaded prediction mask from cache: {pred_mask_path.name}")
                return
            
            # Load from file and cache
            logger.info(f"Loading prediction mask: {pred_mask_path}")
            mask_data = imageio.imread(pred_mask_path_str)
            
            # Cache the loaded mask
            self._cache_mask(pred_mask_path_str, mask_data)
            
            # Set as current mask
            self.prediction_mask = mask_data
            self._current_pred_path = pred_mask_path_str
            
            logger.info(f"Loaded prediction mask: shape={self.prediction_mask.shape}, dtype={self.prediction_mask.dtype}")
            
        except Exception as e:
            logger.error(f"Error loading prediction mask: {e}")
            self.prediction_mask = None
            self._current_pred_path = None
    
    def apply_zoom(self):
        """Apply current zoom factor to the image.
        OPTIMIZED: Works with cached pixmap system."""
        if self.current_image:
            # Calculate new size based on zoom factor
            original_size = self.current_image.size()
            new_width = int(original_size.width() * self.zoom_factor)
            new_height = int(original_size.height() * self.zoom_factor)
            
            # Scale the image with mode chosen by render_mode + current zoom.
            scaled_pixmap = self.current_image.scaled(
                new_width, new_height,
                Qt.KeepAspectRatio,
                self._pick_xform()
            )
            
            # Update current image
            self.setPixmap(scaled_pixmap)
            
            # Invalidate coordinate cache since zoom changed
            self._cached_image_position = None
            
            self.update()  # Force repaint with new positioning
            self.view_changed.emit(self.zoom_factor, self.pan_offset_x, self.pan_offset_y)
    
    def zoom_in(self) -> bool:
        """Zoom in on the image."""
        # Use 1.15x step for smoother zoom control (matches wheel zoom)
        new_zoom = min(self.zoom_factor * 1.15, self.max_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
            return True
        return False

    def zoom_out(self) -> bool:
        """Zoom out on the image."""
        # Use 1.15x step for smoother zoom control (matches wheel zoom)
        new_zoom = max(self.zoom_factor / 1.15, self.min_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.apply_zoom()
            return True
        return False
    
    def reset_zoom(self) -> bool:
        """Reset zoom to fit image in widget."""
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            # Calculate zoom to fit
            widget_size = self.size()
            image_size = self.original_pixmap.size()
            
            scale_x = widget_size.width() / image_size.width()
            scale_y = widget_size.height() / image_size.height()
            self.zoom_factor = min(scale_x, scale_y)
            
            self.apply_zoom()
            return True
        return False
    
    def set_pan_offset(self, pan_x: int, pan_y: int):
        """Set pan offset for minimap navigation."""
        self.pan_offset_x = pan_x
        self.pan_offset_y = pan_y
        # Invalidate coordinate cache since pan changed
        self._cached_image_position = None
        self.update()
        self.view_changed.emit(self.zoom_factor, self.pan_offset_x, self.pan_offset_y)
    
    def paintEvent(self, event):
        """Custom paint event to draw image with overlays and annotations.
        OPTIMIZED: Uses cached coordinates for better performance."""
        # Clear the widget with professional dark background (matches working system)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2d3748"))  # Dark gray background matching theme
        
        if not self.pixmap() or self.pixmap().isNull():
            return
        
        painter.setRenderHint(QPainter.Antialiasing)
        
        try:
            pixmap = self.pixmap()
            
            # Use cached coordinates if available, otherwise calculate
            if not self._cached_image_position:
                self._update_cached_coordinates()
            
            if not self._cached_image_position:
                return  # Still no position available
                
            # Get cached position
            image_x = self._cached_image_position['x']
            image_y = self._cached_image_position['y']
            image_width = self._cached_image_position['width']
            image_height = self._cached_image_position['height']
            
            # Draw the image at the panned position (CRITICAL FIX!)
            painter.drawPixmap(image_x, image_y, pixmap)
            
            # Draw overlays if enabled
            if self.show_gt_overlay and self.gt_mask is not None:
                self.draw_overlay(painter, self.gt_mask, image_x, image_y, 
                                image_width, image_height, 
                                self.gt_overlay_opacity, "ground_truth")
            
            if self.show_prediction_overlay and self.prediction_mask is not None:
                self.draw_overlay(painter, self.prediction_mask, image_x, image_y, 
                                image_width, image_height, 
                                self.prediction_overlay_opacity, "prediction")
            
            # Draw grid if enabled
            if self.show_grid:
                self.draw_grid(painter, image_x, image_y, image_width, image_height)
            
            # Draw annotations
            if self.annotations:
                self.draw_annotations(painter, image_x, image_y, image_width, image_height)
            
        except Exception as e:
            logger.error(f"Error in paintEvent: {e}")
        finally:
            painter.end()
    
    def draw_overlay(self, painter: QPainter, mask: np.ndarray, image_x: int, image_y: int, 
                    image_width: int, image_height: int, opacity: float, overlay_type: str):
        """Draw segmentation overlay on the image with caching."""
        if mask is None:
            return
        
        try:
            # MEMORY OPTIMIZATION: Use cached overlay pixmap
            overlay_pixmap = self._get_cached_overlay(mask, opacity, overlay_type)
            
            if overlay_pixmap.isNull():
                return
            
            # Scale overlay to match image size, using the same render_mode rule.
            if overlay_pixmap.size() != QSize(image_width, image_height):
                overlay_pixmap = overlay_pixmap.scaled(
                    image_width, image_height,
                    Qt.IgnoreAspectRatio,
                    self._pick_xform()
                )
            
            # Draw the colored overlay
            painter.drawPixmap(image_x, image_y, overlay_pixmap)
            
        except Exception as e:
            logger.error(f"Error drawing {overlay_type} overlay: {str(e)}")
    
    def create_colored_mask_pixmap(self, mask: np.ndarray, alpha: int = 255) -> QPixmap:
        """Create a colored pixmap from a segmentation mask using class colors."""
        try:
            if mask is None:
                return QPixmap()
            
            # Convert mask to numpy array if it's not already
            if not isinstance(mask, np.ndarray):
                mask = np.array(mask)
            
            height, width = mask.shape[:2]
            
            # Create RGBA image
            colored_mask = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Use class colors from control panel if available, otherwise use defaults
            if hasattr(self, 'class_colors') and self.class_colors:
                class_colors = []
                for i, color_tuple in enumerate(self.class_colors):
                    # Use the RGB values from class_colors with alpha; respect config (no special-case for class 0)
                    class_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], alpha))
                # Add more default colors if needed
                while len(class_colors) < 9:
                    default_colors = [
                        (236, 72, 153, alpha),  # Class 6: Pink
                        (6, 182, 212, alpha),   # Class 7: Cyan
                        (132, 204, 22, alpha),  # Class 8: Lime
                    ]
                    idx = len(class_colors) - 6
                    if idx < len(default_colors):
                        class_colors.append(default_colors[idx])
                    else:
                        class_colors.append((255, 255, 255, alpha))  # White fallback
            else:
                # Fallback to default colors matching DEFAULT_CLASS_COLORS
                class_colors = [
                    (255, 255, 255, alpha),    # Class 0: Impervious - White
                    (0, 0, 255, alpha),        # Class 1: Building - Blue  
                    (0, 255, 255, alpha),      # Class 2: Low vegetation - Cyan
                    (0, 255, 0, alpha),        # Class 3: Tree - Green
                    (255, 255, 0, alpha),      # Class 4: Car - Yellow
                    (255, 0, 0, alpha),        # Class 5: Clutter - Red
                    (236, 72, 153, alpha),     # Class 6: Pink
                    (6, 182, 212, alpha),      # Class 7: Cyan
                    (132, 204, 22, alpha),     # Class 8: Lime
                ]
            
            # Apply colors based on mask values
            for class_id in range(len(class_colors)):
                mask_indices = (mask == class_id)
                if np.any(mask_indices):
                    colored_mask[mask_indices] = class_colors[class_id]
            
            # Convert to QImage and then QPixmap
            bytes_per_line = width * 4
            qimg = QImage(colored_mask.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            
            return QPixmap.fromImage(qimg)
            
        except Exception as e:
            logger.error(f"Error creating colored mask pixmap: {str(e)}")
            return QPixmap()
    
    def draw_grid(self, painter: QPainter, image_x: int, image_y: int, image_width: int, image_height: int):
        """Draw grid overlay on the image. grid_size is in IMAGE pixels."""
        painter.setRenderHint(QPainter.Antialiasing, False)  # Crisp grid lines

        # Set grid line color and style
        grid_color = QColor(255, 255, 255, 100)  # Semi-transparent white
        painter.setPen(QPen(grid_color, 1, Qt.SolidLine))

        if not self.current_image:
            return
        img_w = self.current_image.width()
        img_h = self.current_image.height()
        if img_w <= 0 or img_h <= 0:
            return

        # Convert grid spacing from image pixels to screen pixels.
        step_x = self.grid_size * image_width / img_w
        step_y = self.grid_size * image_height / img_h
        # If a grid line would be sub-pixel on screen, skip drawing (would all overlap).
        if step_x < 1.0 or step_y < 1.0:
            return

        # Vertical lines at each image-pixel multiple of grid_size.
        i = 0
        while True:
            sx = i * step_x
            if sx > image_width:
                break
            sx_int = int(image_x + sx)
            painter.drawLine(sx_int, image_y, sx_int, image_y + image_height)
            i += 1

        # Horizontal lines.
        j = 0
        while True:
            sy = j * step_y
            if sy > image_height:
                break
            sy_int = int(image_y + sy)
            painter.drawLine(image_x, sy_int, image_x + image_width, sy_int)
            j += 1
    
    def draw_annotations(self, painter: QPainter, image_x: int, image_y: int, image_width: int, image_height: int):
        """Draw annotation points on the image with viewport culling for optimal performance."""
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # VIEWPORT CULLING: Only render points that are visible in current viewport
        visible_points = self._get_visible_points(image_x, image_y, image_width, image_height)
        
        for i, x, y, class_id in visible_points:
            # Convert image coordinates to screen coordinates
            # Add 0.5 to center the point on the pixel (instead of top-left corner).
            screen_x = int(image_x + ((x + 0.5) / self.current_image.width()) * image_width)
            screen_y = int(image_y + ((y + 0.5) / self.current_image.height()) * image_height)
            
            # Get color for this class (matches control panel colors exactly)
            if hasattr(self, 'class_colors') and 0 <= class_id < len(self.class_colors):
                color_tuple = self.class_colors[class_id]
                color = QColor(*color_tuple)
            else:
                # Fallback to default colors if class_colors not available
                if 0 <= class_id < len(DEFAULT_CLASS_COLORS):
                    color_tuple = DEFAULT_CLASS_COLORS[class_id]
                    color = QColor(*color_tuple)
                else:
                    # Ultimate fallback
                    color = QColor(255, 255, 255)  # White
            
            # Draw point
            if i == self.highlighted_point_index:
                # Highlighted point (larger and with border)
                painter.setPen(QPen(Qt.white, 3))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(screen_x - self.point_size - 2, screen_y - self.point_size - 2,
                                  (self.point_size + 2) * 2, (self.point_size + 2) * 2)
            else:
                # Normal point (matches functioning system exactly)
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black border
                painter.setBrush(QBrush(color))
                painter.drawEllipse(screen_x - self.point_size, screen_y - self.point_size,
                                  self.point_size * 2, self.point_size * 2)

            # Halo around points added/edited this session (not in prior_annotations)
            if self.show_new_halo and (int(x), int(y), int(class_id)) not in self.prior_annotations:
                halo_r = self.point_size + 4
                painter.setPen(QPen(Qt.white, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(screen_x - halo_r, screen_y - halo_r, halo_r * 2, halo_r * 2)
    
    # Sophisticated Mouse Interaction System (matches functioning annotation widget)
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for annotation (sophisticated interaction)."""
        # Ensure this widget has focus for keyboard events
        self.setFocus()
        
        if not self.current_image or not self.pixmap():
            return
            
        # Get click position relative to image
        pixmap = self.pixmap()
        widget_size = self.size()
        
        # Calculate image position within widget (including pan offsets)
        x_offset = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
        y_offset = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y
        
        # Check if click is within image bounds
        click_x = event.x() - x_offset
        click_y = event.y() - y_offset
        
        if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
            # Convert to original image coordinates
            scale_x = pixmap.width() / self.current_image.width() if self.current_image else 1
            scale_y = pixmap.height() / self.current_image.height() if self.current_image else 1
            
            orig_x = click_x / scale_x
            orig_y = click_y / scale_y
            
            # Handle different mouse buttons (only if spacebar not pressed)
            if event.button() == Qt.RightButton and not self.space_pressed:
                # Right click: Delete point if near one
                nearest_idx = self.find_nearest_point(orig_x, orig_y)
                if nearest_idx >= 0:
                    removed_point = self.annotations.pop(nearest_idx)
                    self._push_undo(("remove", nearest_idx, list(removed_point)))
                    
                    # PERFORMANCE: Remove from spatial index and reindex remaining points
                    self._remove_from_spatial_index(nearest_idx)
                    # After removal, all indices > nearest_idx shift down by 1
                    self._rebuild_spatial_index()  # Rebuild to fix shifted indices
                    
                    # Enhanced signal: include index and complete point data for O(1) widget operations
                    self.point_removed.emit(removed_point[0], removed_point[1], nearest_idx, removed_point)
                    # Clear highlight since point was removed
                    self.highlighted_point_index = -1
                    self.update()
                return
                
            elif event.button() == Qt.MiddleButton:
                # Middle click: Always pan
                self.panning = True
                self.pan_start_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            elif event.button() == Qt.LeftButton:
                if self.space_pressed:
                    # Spacebar held - always add new point at exact location
                    new_index = len(self.annotations)
                    self.annotations.append([orig_x, orig_y, self.current_class])
                    self._push_undo(("add", new_index, [orig_x, orig_y, self.current_class]))

                    # PERFORMANCE: Add to spatial index for O(log n) searching
                    self._add_to_spatial_index(orig_x, orig_y, new_index)

                    # Enhanced signal: include index for O(1) widget operations
                    self.point_added.emit(orig_x, orig_y, self.current_class, new_index)
                    self.update()
                else:
                    # Normal behavior - check for existing points to drag
                    nearest_idx = self.find_nearest_point(orig_x, orig_y)

                    if 0 <= nearest_idx < len(self.annotations):
                        # Start dragging existing point
                        self.dragging = True
                        self.drag_point_index = nearest_idx

                        # Store the exact point position and calculate drag offset
                        point_x, point_y = self.annotations[nearest_idx][0], self.annotations[nearest_idx][1]
                        self.last_mouse_pos = (point_x, point_y)  # Store actual point position
                        self.drag_offset = (orig_x - point_x, orig_y - point_y)  # Mouse offset from point center

                        # Clear highlight during drag
                        self.highlighted_point_index = -1
                    else:
                        # Add new point
                        new_index = len(self.annotations)
                        self.annotations.append([orig_x, orig_y, self.current_class])
                        self._push_undo(("add", new_index, [orig_x, orig_y, self.current_class]))

                        # PERFORMANCE: Add to spatial index for O(log n) searching
                        self._add_to_spatial_index(orig_x, orig_y, new_index)

                        # Enhanced signal: include index for O(1) widget operations
                        self.point_added.emit(orig_x, orig_y, self.current_class, new_index)
                        self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points and coordinate tracking.
        OPTIMIZED: Throttled updates for better performance."""
        
        # SMART THROTTLING: Intelligent rate limiting for optimal performance
        import time
        current_time = int(time.perf_counter() * 1000)
        time_since_last = current_time - self._last_mouse_update
        
        # Smart throttling based on operation type
        if self.dragging:
            # Higher rate for dragging (120 FPS) for smooth interaction
            min_interval = 8  # 8ms = ~120 FPS
        elif self.panning:
            # Medium rate for panning (90 FPS) 
            min_interval = 11  # 11ms = ~90 FPS
        else:
            # Standard rate for hover/highlighting (60 FPS)
            min_interval = self._mouse_update_interval  # 16ms = ~60 FPS
        
        if time_since_last < min_interval:
            return  # Skip this event - too frequent
            
        self._last_mouse_update = current_time
        
        # Always emit coordinates for tracking and check for point highlighting
        if self.current_image and self.pixmap():
            pixmap = self.pixmap()
            widget_size = self.size()
            x_offset = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
            y_offset = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y
            
            click_x = event.x() - x_offset
            click_y = event.y() - y_offset
            
            if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
                # Convert to original image coordinates
                scale_x = pixmap.width() / self.current_image.width()
                scale_y = pixmap.height() / self.current_image.height()
                
                original_x = int(click_x / scale_x)
                original_y = int(click_y / scale_y)
                
                # Emit coordinates for live tracking
                self.mouse_coordinates.emit(original_x, original_y)
                
                # Show pixel info tooltip if enabled
                if self.show_pixel_info:
                    self.show_pixel_tooltip(event, original_x, original_y)
                
                # Update point highlighting when not panning, dragging, or space pressed
                if not self.panning and not self.dragging and not self.space_pressed:
                    # Find nearest point for highlighting
                    nearest_idx = self.find_nearest_point(original_x, original_y)
                    
                    # Update highlight if changed
                    if nearest_idx != self.highlighted_point_index:
                        self.highlighted_point_index = nearest_idx
                        self.update()  # Redraw to show/hide highlight
                elif self.space_pressed and self.highlighted_point_index != -1:
                    # Clear highlight when spacebar is pressed
                    self.highlighted_point_index = -1
                    self.update()
            else:
                # Mouse outside image bounds, clear highlight
                if self.highlighted_point_index != -1:
                    self.highlighted_point_index = -1
                    self.update()
        
        # Handle panning
        if self.panning and hasattr(self, 'pan_start_pos') and self.pan_start_pos:
            delta = event.pos() - self.pan_start_pos
            self.pan_offset_x += delta.x()
            self.pan_offset_y += delta.y()
            self.pan_start_pos = event.pos()
            # Invalidate coordinate cache since pan changed
            self._cached_image_position = None
            self.update()  # Trigger repaint with new offset
            self.view_changed.emit(self.zoom_factor, self.pan_offset_x, self.pan_offset_y)
            return
        
        # Handle dragging - use same coordinate system as mouse press for consistency
        if not self.dragging or self.drag_point_index < 0 or not self.current_image:
            return
            
        # Use SAME coordinate transformation as mousePressEvent for consistency
        if not self.current_image or not self.pixmap():
            return
            
        # Get click position relative to image (SAME as mousePressEvent)
        pixmap = self.pixmap()
        widget_size = self.size()
        
        # Calculate image position within widget (including pan offsets)
        x_offset = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
        y_offset = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y
        
        # Check if click is within image bounds
        click_x = event.x() - x_offset
        click_y = event.y() - y_offset
        
        if 0 <= click_x <= pixmap.width() and 0 <= click_y <= pixmap.height():
            # Convert to original image coordinates (SAME as mousePressEvent)
            scale_x = pixmap.width() / self.current_image.width() if self.current_image else 1
            scale_y = pixmap.height() / self.current_image.height() if self.current_image else 1
            
            mouse_x = click_x / scale_x
            mouse_y = click_y / scale_y
            
            # Apply drag offset to make dragging feel natural. hasattr alone
            # is not enough: a prior aborted mousePressEvent can leave
            # drag_offset as None while dragging is True.
            offset = getattr(self, 'drag_offset', None)
            if offset is not None:
                new_x = mouse_x - offset[0]
                new_y = mouse_y - offset[1]
            else:
                new_x = mouse_x
                new_y = mouse_y
            
            # Update point position
            if self.drag_point_index < len(self.annotations):
                old_x, old_y = self.last_mouse_pos if hasattr(self, 'last_mouse_pos') and self.last_mouse_pos else (0, 0)
                self.annotations[self.drag_point_index][0] = new_x
                self.annotations[self.drag_point_index][1] = new_y
                self.last_mouse_pos = (new_x, new_y)
                
                # PERFORMANCE: Update spatial index with new position
                self._update_spatial_index_point(self.drag_point_index, new_x, new_y)
                
                # Enhanced signal: include index and complete point data for O(1) widget operations
                current_point = self.annotations[self.drag_point_index]
                self.point_moved.emit(old_x, old_y, new_x, new_y, self.drag_point_index, current_point)
                self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to end dragging and panning."""
        if (event.button() == Qt.RightButton or event.button() == Qt.MiddleButton) and self.panning:
            self.panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
        elif event.button() == Qt.LeftButton and self.dragging:
            # PERFORMANCE: Emit drag end signal before cleanup - enhanced with index
            if self.drag_point_index >= 0 and self.drag_point_index < len(self.annotations):
                annotation = self.annotations[self.drag_point_index]
                self.point_drag_ended.emit(annotation[0], annotation[1], annotation[2], self.drag_point_index)
            
            self.dragging = False
            self.drag_point_index = -1
            self.last_mouse_pos = None
            self.drag_offset = None  # Clean up drag offset
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with zoom-toward-cursor behavior."""
        if not hasattr(self, 'original_pixmap') or not self.original_pixmap:
            return

        # Get scroll direction and amount
        delta = event.angleDelta().y()
        if delta == 0:
            return

        # Calculate zoom factor change (fine steps for precise control)
        # 1.08x per notch for ~8% increments
        zoom_step = 1.08

        # Use scroll delta for variable zoom speed (respect wheel sensitivity)
        # Most mice: 120 units per notch, but some have finer control
        steps = delta / 120.0
        if steps > 0:
            zoom_change = zoom_step ** steps
        else:
            zoom_change = 1.0 / (zoom_step ** abs(steps))

        # Calculate new zoom level
        old_zoom = self.zoom_factor
        new_zoom = self.zoom_factor * zoom_change
        new_zoom = max(self.min_zoom, min(new_zoom, self.max_zoom))

        # If zoom didn't actually change (hit limits), return early
        if new_zoom == old_zoom:
            return

        # Get cursor position in widget coordinates
        cursor_pos = event.pos()
        cursor_x = cursor_pos.x()
        cursor_y = cursor_pos.y()

        # Get current image display parameters
        widget_size = self.size()
        pixmap = self.scaled_pixmap if hasattr(self, 'scaled_pixmap') and self.scaled_pixmap else self.original_pixmap

        # Calculate current image position (center + pan offset)
        old_image_x = (widget_size.width() - pixmap.width()) // 2 + self.pan_offset_x
        old_image_y = (widget_size.height() - pixmap.height()) // 2 + self.pan_offset_y

        # Calculate cursor position relative to current image top-left
        cursor_rel_x = cursor_x - old_image_x
        cursor_rel_y = cursor_y - old_image_y

        # Apply zoom
        self.zoom_factor = new_zoom
        self.apply_zoom()

        # Get new image size after zoom
        new_pixmap = self.scaled_pixmap if hasattr(self, 'scaled_pixmap') and self.scaled_pixmap else self.original_pixmap

        # Calculate where image would be positioned with current pan offset
        new_image_x = (widget_size.width() - new_pixmap.width()) // 2 + self.pan_offset_x
        new_image_y = (widget_size.height() - new_pixmap.height()) // 2 + self.pan_offset_y

        # Calculate where the cursor would point to after zoom (in image coordinates)
        # We want to adjust pan so cursor still points to the same spot
        # The point that was at cursor_rel before should still be at cursor position
        scale_ratio = new_zoom / old_zoom
        new_cursor_rel_x = cursor_rel_x * scale_ratio
        new_cursor_rel_y = cursor_rel_y * scale_ratio

        # Adjust pan offset to keep cursor over the same image point
        # cursor_x should equal new_image_x + new_cursor_rel_x
        # cursor_x = (widget_width - new_pixmap_width) // 2 + new_pan_offset_x + new_cursor_rel_x
        # Solve for new_pan_offset_x:
        self.pan_offset_x += int(cursor_rel_x - new_cursor_rel_x)
        self.pan_offset_y += int(cursor_rel_y - new_cursor_rel_y)

        # Invalidate coordinate cache since zoom and pan changed
        self._cached_image_position = None

        # Update display
        self.update()
        self.view_changed.emit(self.zoom_factor, self.pan_offset_x, self.pan_offset_y)
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        from PyQt5.QtCore import Qt
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            # Spacebar pressed - disable point interaction only
            self.space_pressed = True
            # Clear any existing highlight
            if self.highlighted_point_index != -1:
                self.highlighted_point_index = -1
                self.update()
            event.accept()
            return
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle keyboard release events."""
        from PyQt5.QtCore import Qt
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = False
            event.accept()
        else:
            super().keyReleaseEvent(event)
    
    def leaveEvent(self, event):
        """Clear point highlighting when mouse leaves widget (matches functioning system)."""
        if self.highlighted_point_index != -1:
            self.highlighted_point_index = -1
            self.update()
        super().leaveEvent(event)

    def _push_undo(self, entry):
        """Push an (action, index, point) entry onto the undo stack."""
        self._undo_stack.append(entry)
        if len(self._undo_stack) > self._undo_max:
            self._undo_stack.pop(0)

    def undo_last_action(self):
        """Reverse the last add/remove action. Bound to Ctrl+Z."""
        if not self._undo_stack:
            return False
        action, idx, point = self._undo_stack.pop()
        if action == "add":
            # Reverse an add: remove the point at idx
            if 0 <= idx < len(self.annotations):
                removed = self.annotations.pop(idx)
                self._remove_from_spatial_index(idx)
                self._rebuild_spatial_index()
                self.highlighted_point_index = -1
                try:
                    self.point_removed.emit(removed[0], removed[1], idx, removed)
                except Exception:
                    pass
                self.update()
                return True
        elif action == "remove":
            # Reverse a remove: insert the point back at idx
            insert_idx = min(idx, len(self.annotations))
            self.annotations.insert(insert_idx, list(point))
            self._add_to_spatial_index(point[0], point[1], insert_idx)
            self._rebuild_spatial_index()
            try:
                self.point_added.emit(point[0], point[1], point[2], insert_idx)
            except Exception:
                pass
            self.update()
            return True
        return False

    def clear_undo_stack(self):
        """Clear the undo stack (e.g., on image switch)."""
        self._undo_stack.clear()

    def find_nearest_point(self, orig_x, orig_y, tolerance=5):
        """Find the nearest point to given coordinates within tolerance distance.
        PERFORMANCE: Uses spatial index for O(log n) search instead of O(n) linear search."""
        if not self.annotations:
            return -1

        # Disable snap-to-point when spacebar is held (ArcGIS-style behavior)
        # This allows placing points precisely next to existing points
        if self.space_pressed:
            return -1
        
        # OPTIMIZATION: Use spatial index if available for O(log n) performance
        if self._spatial_index and SPATIAL_INDEX_AVAILABLE:
            try:
                # Query spatial index for points within tolerance radius
                nearby_points = self._spatial_index.query_point(orig_x, orig_y, max_distance=tolerance)
                
                if not nearby_points:
                    return -1
                
                # Find the closest among nearby points (usually very few)
                min_dist_sq = float('inf')
                nearest_idx = -1
                
                for spatial_point in nearby_points:
                    # Calculate exact distance only for nearby candidates
                    dist_sq = (spatial_point.x - orig_x) ** 2 + (spatial_point.y - orig_y) ** 2
                    
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        nearest_idx = spatial_point.data  # data contains the annotation index

                # Validate the index is still within the current annotations
                # list (the spatial index can hold stale indices when the
                # annotations list shrinks).
                if nearest_idx >= len(self.annotations):
                    return -1

                return nearest_idx
                
            except Exception as e:
                # Fallback to linear search if spatial index fails
                logging.warning(f"Spatial index query failed, falling back to linear search: {e}")
        
        # FALLBACK: Linear search when spatial index not available
        min_dist_sq = tolerance * tolerance
        nearest_idx = -1
        
        for i, (x, y, _) in enumerate(self.annotations):
            dist_sq = (x - orig_x) ** 2 + (y - orig_y) ** 2
            
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_idx = i
                
                if dist_sq < 1.0:  # Early exit for very close points
                    break
        
        return nearest_idx
    
    def _rebuild_spatial_index(self):
        """Rebuild spatial index from current annotations for O(log n) searching."""
        if not self._spatial_index or not SPATIAL_INDEX_AVAILABLE:
            return
        
        try:
            # Clear existing index
            self._spatial_index.clear()
            self._spatial_points.clear()
            
            # Add all current annotations to spatial index
            for i, (x, y, class_id) in enumerate(self.annotations):
                spatial_point = SpatialPoint(
                    x=int(x), 
                    y=int(y), 
                    data=i  # Store annotation index as data
                )
                self._spatial_index.insert(spatial_point)
                self._spatial_points[i] = spatial_point
                
        except Exception as e:
            logging.warning(f"Failed to rebuild spatial index: {e}")
    
    def _add_to_spatial_index(self, x, y, index):
        """Add a single point to the spatial index."""
        if not self._spatial_index or not SPATIAL_INDEX_AVAILABLE:
            return
        
        try:
            spatial_point = SpatialPoint(
                x=int(x), 
                y=int(y), 
                data=index
            )
            self._spatial_index.insert(spatial_point)
            self._spatial_points[index] = spatial_point
        except Exception as e:
            logging.warning(f"Failed to add point to spatial index: {e}")
    
    def _remove_from_spatial_index(self, index):
        """Remove a point from the spatial index."""
        if not self._spatial_index or not SPATIAL_INDEX_AVAILABLE:
            return
        
        try:
            if index in self._spatial_points:
                spatial_point = self._spatial_points[index]
                self._spatial_index.remove(spatial_point)
                del self._spatial_points[index]
        except Exception as e:
            logging.warning(f"Failed to remove point from spatial index: {e}")
    
    def _update_spatial_index_point(self, index, new_x, new_y):
        """Update a point's position in the spatial index."""
        # Remove old position and add new one
        self._remove_from_spatial_index(index)
        self._add_to_spatial_index(new_x, new_y, index)
    
    def _get_visible_points(self, image_x: int, image_y: int, image_width: int, image_height: int):
        """Get annotation points that are visible in the current viewport using spatial indexing.
        
        VIEWPORT CULLING: This dramatically improves performance when zoomed in or working 
        with many annotations by only rendering points that are actually visible.
        
        Returns:
            List of tuples: [(index, x, y, class_id), ...] for visible points
        """
        if not self.annotations or not self.current_image:
            return []
        
        # Calculate the visible image region in image coordinates
        img_width = self.current_image.width()
        img_height = self.current_image.height()
        
        # Convert screen viewport bounds to image coordinates
        # Account for current zoom and pan to determine what part of image is visible
        scale_x = img_width / image_width if image_width > 0 else 1
        scale_y = img_height / image_height if image_height > 0 else 1
        
        # Calculate visible image region bounds
        # Add margin for points that are partially visible (point radius)
        margin = max(self.point_size * scale_x, self.point_size * scale_y, 10)
        
        # Convert screen viewport to image coordinates
        # When image_x is negative, we're panned to the right, so left edge of viewport shows image at -image_x
        viewport_left_in_image = (-image_x) * scale_x
        viewport_top_in_image = (-image_y) * scale_y
        viewport_right_in_image = (-image_x + self.width()) * scale_x
        viewport_bottom_in_image = (-image_y + self.height()) * scale_y
        
        # Apply margins and clamp to image bounds
        visible_left = max(0, viewport_left_in_image - margin)
        visible_top = max(0, viewport_top_in_image - margin)
        visible_right = min(img_width, viewport_right_in_image + margin)
        visible_bottom = min(img_height, viewport_bottom_in_image + margin)
        
        # Safety check: ensure valid bounds
        if visible_left >= visible_right or visible_top >= visible_bottom:
            logger.debug("Invalid viewport bounds, showing no points")
            return []
        
        # Use spatial index for efficient viewport culling if available
        if self._spatial_index and SPATIAL_INDEX_AVAILABLE:
            try:
                # Query spatial index for points in visible region
                visible_points = []
                
                # Create query bounding box for spatial index
                query_rect = BoundingBox(
                    min_x=float(visible_left),
                    min_y=float(visible_top), 
                    max_x=float(visible_right),
                    max_y=float(visible_bottom)
                )
                
                # Query spatial index for points in viewport
                spatial_results = self._spatial_index.query_region(query_rect)
                
                # Convert spatial results to annotation format
                for spatial_point in spatial_results:
                    annotation_index = spatial_point.data
                    if 0 <= annotation_index < len(self.annotations):
                        annotation = self.annotations[annotation_index]
                        x, y, class_id = annotation
                        visible_points.append((annotation_index, x, y, class_id))
                
                logger.debug(f"Viewport culling: {len(visible_points)}/{len(self.annotations)} points visible")
                return visible_points
                
            except Exception as e:
                logger.warning(f"Spatial index query failed, falling back to linear search: {e}")
        
        # Fallback: Linear search through all annotations (O(n) but still with culling)
        visible_points = []
        for i, (x, y, class_id) in enumerate(self.annotations):
            # Check if point is within visible bounds
            if (visible_left <= x <= visible_right and 
                visible_top <= y <= visible_bottom):
                visible_points.append((i, x, y, class_id))
        
        logger.debug(f"Viewport culling (linear): {len(visible_points)}/{len(self.annotations)} points visible")
        return visible_points
    
    # Public API methods for integration
    
    def set_current_class(self, class_id: int):
        """Set the current annotation class."""
        self.current_class = class_id
        logger.debug(f"Current class set to: {class_id}")
    
    def set_class_colors(self, class_colors: List[Tuple[int, int, int]]):
        """Set the class colors to match the control panel."""
        self.class_colors = class_colors
        logger.debug(f"Class colors updated: {len(class_colors)} colors")
        self.update()
    
    def set_point_size(self, size: int):
        """Set the annotation point size."""
        self.point_size = size
        self.update()
        logger.debug(f"Point size set to: {size}")
    
    def set_show_grid(self, show: bool):
        """Set grid visibility."""
        self.show_grid = show
        self.update()
        logger.debug(f"Grid visibility: {show}")
    
    def set_grid_size(self, size: int):
        """Set grid spacing."""
        self.grid_size = size
        if self.show_grid:
            self.update()
        logger.debug(f"Grid size set to: {size}")
    
    def clear_annotations(self):
        """Clear all annotations."""
        self.annotations.clear()
        self.update()
        logger.info("All annotations cleared")
    
    def get_current_state(self) -> Dict:
        """Get current canvas state."""
        return {
            'name': self.name,
            'version': self.version,
            'has_image': self.current_image is not None,
            'zoom_factor': self.zoom_factor,
            'pan_offset': (self.pan_offset_x, self.pan_offset_y),
            'rgb_channels': self.rgb_channel_mapping.copy(),
            'overlays': {
                'ground_truth': {'enabled': self.show_gt_overlay, 'opacity': self.gt_overlay_opacity},
                'prediction': {'enabled': self.show_prediction_overlay, 'opacity': self.prediction_overlay_opacity}
            },
            'annotations_count': len(self.annotations),
            'current_class': self.current_class,
            'point_size': self.point_size,
            'grid_enabled': self.show_grid
        }
    
    def get_statistics(self) -> Dict:
        """Get canvas statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'image_loaded': self.current_image is not None,
            'image_path': self.current_image_path or '',
            'zoom_factor': self.zoom_factor,
            'zoom_percentage': int(self.zoom_factor * 100),
            'rgb_channel_mapping': self.rgb_channel_mapping.copy(),
            'overlays_enabled': {
                'ground_truth': self.show_gt_overlay,
                'prediction': self.show_prediction_overlay
            },
            'annotations_count': len(self.annotations),
            'features': {
                'rgb_remapping': True,
                'overlays': True,
                'zoom_pan': True,
                'grid': True,
                'multi_class': True
            }
        }
    
    def set_pixel_info_enabled(self, enabled: bool):
        """Enable/disable pixel info display."""
        self.show_pixel_info = enabled
        if not enabled and hasattr(self, 'pixel_tooltip'):
            # Hide tooltip when disabled
            self.pixel_tooltip.hide()
        logger.debug(f"Pixel info {'enabled' if enabled else 'disabled'}")
    
    def show_pixel_tooltip(self, event, img_x: int, img_y: int):
        """Show pixel information tooltip with fixed-width formatting for stable display."""
        try:
            # Create sophisticated tooltip if it doesn't exist with fixed-width formatting
            if not hasattr(self, 'pixel_tooltip'):
                # Main tooltip container with shadow effect
                self.pixel_tooltip = QFrame(self)
                self.pixel_tooltip.setFrameStyle(QFrame.StyledPanel)
                self.pixel_tooltip.setStyleSheet("""
                    QFrame {
                        background: rgba(30, 35, 42, 0.95);
                        border: 1px solid #4a5568;
                        border-radius: 6px;
                        color: #e2e8f0;
                    }
                """)
                
                # Layout for tooltip content
                tooltip_layout = QVBoxLayout(self.pixel_tooltip)
                tooltip_layout.setContentsMargins(12, 10, 12, 10)
                tooltip_layout.setSpacing(8)
                
                # Coordinate section with fixed width
                coord_container = QFrame()
                coord_layout = QVBoxLayout(coord_container)
                coord_layout.setSpacing(2)
                
                coord_header = QLabel("Coordinates")
                coord_header.setStyleSheet("""
                    color: #60a5fa;
                    font-weight: bold;
                    font-size: 11px;
                    margin-bottom: 2px;
                """)
                coord_layout.addWidget(coord_header)
                
                self.coord_display = QLabel("X:---- Y:----")
                self.coord_display.setStyleSheet("""
                    color: #e2e8f0;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 10px;
                    font-weight: bold;
                    min-width: 100px;
                """)
                coord_layout.addWidget(self.coord_display)
                tooltip_layout.addWidget(coord_container)
                
                # RGB Values section with fixed width
                rgb_container = QFrame()
                rgb_layout = QVBoxLayout(rgb_container)
                rgb_layout.setSpacing(2)
                
                rgb_header = QLabel("RGB Values")
                rgb_header.setStyleSheet("""
                    color: #10b981;
                    font-weight: bold;
                    font-size: 11px;
                    margin-bottom: 2px;
                """)
                rgb_layout.addWidget(rgb_header)
                
                # Fixed-width RGB displays
                self.r_display = QLabel("R:---")
                self.g_display = QLabel("G:---")
                self.b_display = QLabel("B:---")
                
                rgb_values_layout = QHBoxLayout()
                rgb_values_layout.setSpacing(12)
                
                for display, color in [(self.r_display, "#ef4444"), (self.g_display, "#10b981"), (self.b_display, "#3b82f6")]:
                    display.setStyleSheet(f"""
                        color: {color}; 
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                        font-size: 10px; 
                        font-weight: bold; 
                        min-width: 45px;
                    """)
                
                rgb_values_layout.addWidget(self.r_display)
                rgb_values_layout.addWidget(self.g_display)
                rgb_values_layout.addWidget(self.b_display)
                
                rgb_layout.addLayout(rgb_values_layout)
                tooltip_layout.addWidget(rgb_container)
                
                # Ground Truth section with fixed width
                gt_container = QFrame()
                gt_layout = QVBoxLayout(gt_container)
                gt_layout.setSpacing(2)
                
                gt_header = QLabel("Ground Truth")
                gt_header.setStyleSheet("""
                    color: #f59e0b;
                    font-weight: bold;
                    font-size: 11px;
                    margin-bottom: 2px;
                """)
                gt_layout.addWidget(gt_header)
                
                self.gt_index_display = QLabel("Index: --")
                self.gt_name_display = QLabel("Class: ------------")
                
                for display in [self.gt_index_display, self.gt_name_display]:
                    display.setStyleSheet("""
                        color: #fbbf24;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                        font-size: 9px;
                        font-weight: bold;
                        min-width: 120px;
                    """)
                
                gt_layout.addWidget(self.gt_index_display)
                gt_layout.addWidget(self.gt_name_display)
                tooltip_layout.addWidget(gt_container)
                
                # Prediction section with fixed width
                pred_container = QFrame()
                pred_layout = QVBoxLayout(pred_container)
                pred_layout.setSpacing(2)
                
                pred_header = QLabel("Prediction")
                pred_header.setStyleSheet("""
                    color: #8b5cf6;
                    font-weight: bold;
                    font-size: 11px;
                    margin-bottom: 2px;
                """)
                pred_layout.addWidget(pred_header)
                
                self.pred_index_display = QLabel("Index: --")
                self.pred_name_display = QLabel("Class: ------------")
                
                for display in [self.pred_index_display, self.pred_name_display]:
                    display.setStyleSheet("""
                        color: #a78bfa;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                        font-size: 9px;
                        font-weight: bold;
                        min-width: 120px;
                    """)
                
                pred_layout.addWidget(self.pred_index_display)
                pred_layout.addWidget(self.pred_name_display)
                tooltip_layout.addWidget(pred_container)
                
                # Set minimum size for professional appearance
                self.pixel_tooltip.setMinimumSize(200, 140)
                self.pixel_tooltip.hide()
            
            # Get cursor position in widget coordinates
            cursor_pos = event.pos()
            
            # Get comprehensive pixel information
            pixel_info = self.get_pixel_info(img_x, img_y)
            
            # Update coordinate display with fixed width formatting
            self.coord_display.setText(f"X:{img_x:4d} Y:{img_y:4d}")
            
            # Update RGB values with fixed width formatting
            if pixel_info['rgb']:
                r, g, b = pixel_info['rgb']
                self.r_display.setText(f"R:{r:3d}")
                self.g_display.setText(f"G:{g:3d}")
                self.b_display.setText(f"B:{b:3d}")
            else:
                self.r_display.setText("R:---")
                self.g_display.setText("G:---")
                self.b_display.setText("B:---")
            
            # Update Ground Truth display with fixed width formatting
            if pixel_info['gt']:
                # Extract class index and name
                if pixel_info['gt'].startswith('Class'):
                    # Extract number from "Class123" format
                    try:
                        class_index = int(pixel_info['gt'][5:])
                        class_name = pixel_info['gt']
                    except ValueError:
                        class_index = 0
                        class_name = pixel_info['gt']
                else:
                    # Named class - find index
                    class_names = ["Impervious", "Building", "Low Veg", "Tree", "Car", "Clutter"]
                    try:
                        class_index = class_names.index(pixel_info['gt'])
                        class_name = pixel_info['gt']
                    except ValueError:
                        class_index = 0
                        class_name = pixel_info['gt']
                
                self.gt_index_display.setText(f"Index:{class_index:2d}")
                self.gt_name_display.setText(f"Class:{class_name:<12}")
            else:
                self.gt_index_display.setText("Index:--")
                self.gt_name_display.setText("Class:------------")
            
            # Update Prediction display with fixed width formatting
            if pixel_info['pred']:
                # Extract class index and name (same logic as GT)
                if pixel_info['pred'].startswith('Class'):
                    try:
                        pred_index = int(pixel_info['pred'][5:])
                        pred_name = pixel_info['pred']
                    except ValueError:
                        pred_index = 0
                        pred_name = pixel_info['pred']
                else:
                    # Named class - find index
                    class_names = ["Impervious", "Building", "Low Veg", "Tree", "Car", "Clutter"]
                    try:
                        pred_index = class_names.index(pixel_info['pred'])
                        pred_name = pixel_info['pred']
                    except ValueError:
                        pred_index = 0
                        pred_name = pixel_info['pred']
                
                self.pred_index_display.setText(f"Index:{pred_index:2d}")
                self.pred_name_display.setText(f"Class:{pred_name:<12}")
            else:
                self.pred_index_display.setText("Index:--")
                self.pred_name_display.setText("Class:------------")
            
            # Position tooltip near mouse cursor (ABILIUS-style with better positioning)
            widget_rect = self.rect()
            tooltip_x = cursor_pos.x() + 20  # Slightly more offset for sophistication
            tooltip_y = cursor_pos.y() - 15  # Slightly above cursor
            
            # Keep tooltip within widget bounds with padding
            tooltip_size = self.pixel_tooltip.size()
            
            if tooltip_x + tooltip_size.width() > widget_rect.width() - 10:
                tooltip_x = cursor_pos.x() - tooltip_size.width() - 10
            if tooltip_y < 10:
                tooltip_y = cursor_pos.y() + 25  # Below cursor if above doesn't fit
            if tooltip_y + tooltip_size.height() > widget_rect.height() - 10:
                tooltip_y = widget_rect.height() - tooltip_size.height() - 10
            
            self.pixel_tooltip.move(tooltip_x, tooltip_y)
            self.pixel_tooltip.show()
            
        except Exception as e:
            logger.error(f"Error in show_pixel_tooltip: {e}")
            # If pixel reading fails, show error state with fixed formatting
            if hasattr(self, 'pixel_tooltip'):
                # Show error state for all displays
                self.coord_display.setText("X:---- Y:----")
                self.r_display.setText("R:---")
                self.g_display.setText("G:---")
                self.b_display.setText("B:---")
                self.gt_index_display.setText("Index:--")
                self.gt_name_display.setText("Class:Error-------")
                self.pred_index_display.setText("Index:--")
                self.pred_name_display.setText("Class:Error-------")
                
                # Position tooltip (same sophisticated logic as above)
                cursor_pos = event.pos()
                tooltip_x = cursor_pos.x() + 20
                tooltip_y = cursor_pos.y() - 15
                
                widget_rect = self.rect()
                tooltip_size = self.pixel_tooltip.size()
                
                if tooltip_x + tooltip_size.width() > widget_rect.width() - 10:
                    tooltip_x = cursor_pos.x() - tooltip_size.width() - 10
                if tooltip_y < 10:
                    tooltip_y = cursor_pos.y() + 25
                if tooltip_y + tooltip_size.height() > widget_rect.height() - 10:
                    tooltip_y = widget_rect.height() - tooltip_size.height() - 10
                
                self.pixel_tooltip.move(tooltip_x, tooltip_y)
                self.pixel_tooltip.show()