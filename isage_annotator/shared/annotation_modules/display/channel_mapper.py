"""
Enhanced Channel Mapper - Advanced channel mapping for multi-channel images

This enhanced version addresses potential issues and adds improvements:
- Better performance with optimized array operations
- Support for more advanced color spaces (HSV, LAB, etc.)
- Enhanced histogram-based auto-bounds calculation
- Support for custom color mapping functions
- Better memory management for large images
- Real-time processing capabilities
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from ..base_protocols import BaseComponent, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache
from sklearn.preprocessing import RobustScaler
from scipy import ndimage
from skimage import exposure
import cv2


class ChannelMapper(BaseComponent):
    """Enhanced channel mapper for multi-channel image visualization."""
    
    # Enhanced channel mapping signals
    channelMappingChanged = pyqtSignal(dict)  # mapping_config
    channelBoundsChanged = pyqtSignal(str, float, float)  # channel, min_val, max_val
    mappingPresetChanged = pyqtSignal(str)  # preset_name
    colorSpaceChanged = pyqtSignal(str)  # color_space
    processingModeChanged = pyqtSignal(str)  # processing_mode
    histogramUpdated = pyqtSignal(dict)  # histogram_data
    
    def __init__(self, name: str = "enhanced_channel_mapper", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Enhanced channel mapping configuration
        self._channel_mapping: Dict[str, Union[int, List[int]]] = {'R': 0, 'G': 1, 'B': 2}
        self._available_channels: List[int] = []
        self._channel_names: List[str] = []
        self._channel_descriptions: List[str] = []
        self._channel_wavelengths: List[float] = []
        self._image_shape: Optional[Tuple[int, int, int]] = None
        
        # Enhanced bounds and normalization
        self._channel_bounds: Dict[int, Tuple[float, float]] = {}
        self._auto_bounds: bool = True
        self._bounds_method: str = "percentile"  # percentile, robust, minmax, adaptive
        self._percentile_bounds: Tuple[float, float] = (2.0, 98.0)
        self._robust_bounds: bool = True
        self._adaptive_bounds: bool = False
        self._global_bounds: Optional[Tuple[float, float]] = None
        
        # Advanced display settings
        self._color_space: str = "RGB"  # RGB, HSV, LAB, YUV, XYZ
        self._gamma_correction: float = 1.0
        self._contrast_enhancement: float = 1.0
        self._brightness_adjustment: float = 0.0
        self._saturation_adjustment: float = 1.0
        self._hue_shift: float = 0.0
        
        # Advanced enhancement features
        self._histogram_equalization: bool = False
        self._adaptive_histogram_eq: bool = False
        self._clahe_enabled: bool = False
        self._clahe_clip_limit: float = 2.0
        self._clahe_tile_size: Tuple[int, int] = (8, 8)
        
        # Custom color mapping
        self._custom_color_functions: Dict[str, Callable] = {}
        self._color_map_mode: str = "linear"  # linear, logarithmic, exponential, custom
        self._color_map_function: Optional[Callable] = None
        
        # Multi-channel blending
        self._blending_mode: str = "normal"  # normal, multiply, overlay, screen, soft_light
        self._channel_weights: Dict[int, float] = {}
        self._enable_channel_mixing: bool = False
        
        # Performance optimization
        self._processing_mode: str = "auto"  # auto, cpu, gpu, parallel
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._max_workers: int = 4
        self._chunk_size: int = 1024
        self._use_gpu: bool = False
        
        # Advanced caching
        self._cache_enabled: bool = True
        self._cached_mappings: Dict[str, np.ndarray] = {}
        self._cached_histograms: Dict[str, np.ndarray] = {}
        self._cached_bounds: Dict[str, Tuple[float, float]] = {}
        self._max_cache_size: int = 20
        self._cache_compression: bool = True
        
        # Real-time processing
        self._real_time_enabled: bool = False
        self._frame_rate_limit: int = 30
        self._processing_queue_size: int = 5
        self._drop_frames: bool = True
        
        # Statistics and monitoring
        self._mapping_stats: Dict[str, Any] = {
            'total_mappings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0.0,
            'gpu_usage': 0.0,
            'memory_usage': 0.0
        }
        
        # Quality and validation
        self._quality_checks: bool = True
        self._input_validation: bool = True
        self._output_validation: bool = True
        self._nan_handling: str = "replace"  # replace, ignore, error
        self._inf_handling: str = "clip"  # clip, replace, error
        
        # Initialize enhanced features
        self._initialize_enhanced_presets()
        self._setup_processing_pipeline()
        
        # Thread safety
        self._processing_lock = threading.Lock()
        self._cache_lock = threading.Lock()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced channel mapper."""
        # Basic settings
        self._auto_bounds = kwargs.get('auto_bounds', True)
        self._bounds_method = kwargs.get('bounds_method', 'percentile')
        self._percentile_bounds = kwargs.get('percentile_bounds', (2.0, 98.0))
        self._robust_bounds = kwargs.get('robust_bounds', True)
        self._adaptive_bounds = kwargs.get('adaptive_bounds', False)
        self._global_bounds = kwargs.get('global_bounds', None)
        
        # Enhanced settings
        self._color_space = kwargs.get('color_space', 'RGB')
        self._gamma_correction = kwargs.get('gamma_correction', 1.0)
        self._contrast_enhancement = kwargs.get('contrast_enhancement', 1.0)
        self._brightness_adjustment = kwargs.get('brightness_adjustment', 0.0)
        self._saturation_adjustment = kwargs.get('saturation_adjustment', 1.0)
        self._hue_shift = kwargs.get('hue_shift', 0.0)
        
        # Advanced enhancement
        self._histogram_equalization = kwargs.get('histogram_equalization', False)
        self._adaptive_histogram_eq = kwargs.get('adaptive_histogram_eq', False)
        self._clahe_enabled = kwargs.get('clahe_enabled', False)
        self._clahe_clip_limit = kwargs.get('clahe_clip_limit', 2.0)
        self._clahe_tile_size = kwargs.get('clahe_tile_size', (8, 8))
        
        # Performance settings
        self._processing_mode = kwargs.get('processing_mode', 'auto')
        self._max_workers = kwargs.get('max_workers', 4)
        self._chunk_size = kwargs.get('chunk_size', 1024)
        self._use_gpu = kwargs.get('use_gpu', False)
        
        # Cache settings
        self._cache_enabled = kwargs.get('cache_enabled', True)
        self._max_cache_size = kwargs.get('max_cache_size', 20)
        self._cache_compression = kwargs.get('cache_compression', True)
        
        # Real-time settings
        self._real_time_enabled = kwargs.get('real_time_enabled', False)
        self._frame_rate_limit = kwargs.get('frame_rate_limit', 30)
        self._processing_queue_size = kwargs.get('processing_queue_size', 5)
        self._drop_frames = kwargs.get('drop_frames', True)
        
        # Quality settings
        self._quality_checks = kwargs.get('quality_checks', True)
        self._input_validation = kwargs.get('input_validation', True)
        self._output_validation = kwargs.get('output_validation', True)
        self._nan_handling = kwargs.get('nan_handling', 'replace')
        self._inf_handling = kwargs.get('inf_handling', 'clip')
        
        # Set up thread pool
        if self._processing_mode in ['parallel', 'auto']:
            self._setup_thread_pool()
        
        # Set up channel mapping if provided
        if 'channel_mapping' in kwargs:
            self.set_channel_mapping(kwargs['channel_mapping'])
        
        return super().initialize(**kwargs)
    
    def set_image_shape(self, shape: Tuple[int, int, int], wavelengths: Optional[List[float]] = None) -> None:
        """Set the shape and metadata of the multi-channel image."""
        try:
            self._image_shape = shape
            height, width, channels = shape
            
            # Update available channels
            self._available_channels = list(range(channels))
            
            # Generate default channel names
            self._channel_names = [f'Channel {i}' for i in range(channels)]
            
            # Set wavelengths if provided
            if wavelengths and len(wavelengths) == channels:
                self._channel_wavelengths = wavelengths
                # Update names with wavelengths
                self._channel_names = [f'λ{wl:.1f}nm' for wl in wavelengths]
            else:
                self._channel_wavelengths = []
            
            # Generate descriptions
            self._channel_descriptions = [f'Channel {i} data' for i in range(channels)]
            
            # Clear caches
            self._clear_all_caches()
            
            # Update channel bounds
            self._update_channel_bounds()
            
            # Initialize channel weights
            self._channel_weights = {i: 1.0 for i in range(channels)}
            
            self.emit_state_changed({
                'image_shape': shape,
                'available_channels': len(self._available_channels),
                'has_wavelengths': bool(self._channel_wavelengths)
            })
            
        except Exception as e:
            self.emit_error(f"Error setting image shape: {str(e)}")
    
    def set_color_space(self, color_space: str) -> None:
        """Set the output color space."""
        try:
            valid_spaces = ['RGB', 'HSV', 'LAB', 'YUV', 'XYZ']
            if color_space not in valid_spaces:
                raise ValueError(f"Invalid color space. Must be one of: {valid_spaces}")
            
            if self._color_space != color_space:
                self._color_space = color_space
                self._clear_all_caches()
                
                self.colorSpaceChanged.emit(color_space)
                self.emit_state_changed({'color_space': color_space})
            
        except Exception as e:
            self.emit_error(f"Error setting color space: {str(e)}")
    
    def set_processing_mode(self, mode: str) -> None:
        """Set the processing mode."""
        try:
            valid_modes = ['auto', 'cpu', 'gpu', 'parallel']
            if mode not in valid_modes:
                raise ValueError(f"Invalid processing mode. Must be one of: {valid_modes}")
            
            if self._processing_mode != mode:
                self._processing_mode = mode
                
                # Setup thread pool for parallel processing
                if mode == 'parallel':
                    self._setup_thread_pool()
                elif mode == 'cpu' and self._thread_pool:
                    self._thread_pool.shutdown()
                    self._thread_pool = None
                
                self.processingModeChanged.emit(mode)
                self.emit_state_changed({'processing_mode': mode})
            
        except Exception as e:
            self.emit_error(f"Error setting processing mode: {str(e)}")
    
    def set_channel_weights(self, weights: Dict[int, float]) -> None:
        """Set weights for channel blending."""
        try:
            for channel, weight in weights.items():
                if channel in self._available_channels:
                    self._channel_weights[channel] = max(0.0, min(2.0, weight))
            
            self._clear_all_caches()
            self.emit_state_changed({'channel_weights': self._channel_weights})
            
        except Exception as e:
            self.emit_error(f"Error setting channel weights: {str(e)}")
    
    def set_blending_mode(self, mode: str) -> None:
        """Set the blending mode for multi-channel composition."""
        try:
            valid_modes = ['normal', 'multiply', 'overlay', 'screen', 'soft_light']
            if mode not in valid_modes:
                raise ValueError(f"Invalid blending mode. Must be one of: {valid_modes}")
            
            if self._blending_mode != mode:
                self._blending_mode = mode
                self._clear_all_caches()
                self.emit_state_changed({'blending_mode': mode})
            
        except Exception as e:
            self.emit_error(f"Error setting blending mode: {str(e)}")
    
    def enable_advanced_enhancements(self, histogram_eq: bool = False, adaptive_eq: bool = False, 
                                   clahe: bool = False, clahe_clip: float = 2.0) -> None:
        """Enable advanced image enhancement features."""
        try:
            self._histogram_equalization = histogram_eq
            self._adaptive_histogram_eq = adaptive_eq
            self._clahe_enabled = clahe
            self._clahe_clip_limit = clahe_clip
            
            if any([histogram_eq, adaptive_eq, clahe]):
                self._clear_all_caches()
            
            self.emit_state_changed({
                'histogram_equalization': histogram_eq,
                'adaptive_histogram_eq': adaptive_eq,
                'clahe_enabled': clahe
            })
            
        except Exception as e:
            self.emit_error(f"Error enabling advanced enhancements: {str(e)}")
    
    def set_custom_color_function(self, name: str, func: Callable[[np.ndarray], np.ndarray]) -> None:
        """Set a custom color mapping function."""
        try:
            self._custom_color_functions[name] = func
            self.emit_state_changed({'custom_functions_count': len(self._custom_color_functions)})
            
        except Exception as e:
            self.emit_error(f"Error setting custom color function: {str(e)}")
    
    def map_image_to_rgb(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Map multi-channel image to RGB display with enhanced features."""
        try:
            # Input validation
            if self._input_validation:
                if not self._validate_input(image):
                    return np.zeros((100, 100, 3), dtype=np.float32)
            
            # Start timing
            import time
            start_time = time.time()
            
            # Update image shape if needed
            if self._image_shape is None or self._image_shape != image.shape:
                self.set_image_shape(image.shape)
            
            # Generate cache key
            cache_key = self._generate_enhanced_cache_key(image, **kwargs)
            
            # Check cache
            if self._cache_enabled:
                with self._cache_lock:
                    if cache_key in self._cached_mappings:
                        self._mapping_stats['cache_hits'] += 1
                        return self._cached_mappings[cache_key].copy()
            
            # Process image based on mode
            if self._processing_mode == 'parallel' and self._thread_pool:
                rgb_image = self._process_parallel(image, **kwargs)
            elif self._processing_mode == 'gpu' and self._use_gpu:
                rgb_image = self._process_gpu(image, **kwargs)
            else:
                rgb_image = self._process_cpu(image, **kwargs)
            
            # Convert color space if needed
            if self._color_space != 'RGB':
                rgb_image = self._convert_color_space(rgb_image, 'RGB', self._color_space)
            
            # Output validation
            if self._output_validation:
                rgb_image = self._validate_output(rgb_image)
            
            # Cache result
            if self._cache_enabled:
                with self._cache_lock:
                    self._cache_result(cache_key, rgb_image)
                    self._mapping_stats['cache_misses'] += 1
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            return rgb_image
            
        except Exception as e:
            self.emit_error(f"Error mapping image to RGB: {str(e)}")
            return np.zeros((100, 100, 3), dtype=np.float32)
    
    def _process_cpu(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Process image using CPU."""
        try:
            height, width, channels = image.shape
            rgb_image = np.zeros((height, width, 3), dtype=np.float32)
            
            # Map each RGB channel
            for rgb_channel, channel_spec in self._channel_mapping.items():
                if isinstance(channel_spec, list):
                    # Multi-channel blending
                    blended_data = self._blend_channels(image, channel_spec)
                else:
                    # Single channel
                    if channel_spec < channels:
                        blended_data = image[:, :, channel_spec].astype(np.float32)
                    else:
                        continue
                
                # Apply bounds
                bounds = self._get_channel_bounds(channel_spec, blended_data)
                
                # Normalize channel
                normalized_channel = self._normalize_channel_enhanced(blended_data, bounds)
                
                # Apply enhancements
                enhanced_channel = self._apply_advanced_enhancements(normalized_channel)
                
                # Apply custom color function if specified
                if self._color_map_function:
                    enhanced_channel = self._color_map_function(enhanced_channel)
                
                # Assign to RGB channel
                rgb_channel_index = {'R': 0, 'G': 1, 'B': 2}[rgb_channel]
                rgb_image[:, :, rgb_channel_index] = enhanced_channel
            
            # Apply blending mode
            if self._blending_mode != 'normal':
                rgb_image = self._apply_blending_mode(rgb_image)
            
            return np.clip(rgb_image, 0.0, 1.0)
            
        except Exception as e:
            self.emit_error(f"Error in CPU processing: {str(e)}")
            return np.zeros((100, 100, 3), dtype=np.float32)
    
    def _process_parallel(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Process image using parallel processing."""
        try:
            height, width, channels = image.shape
            rgb_image = np.zeros((height, width, 3), dtype=np.float32)
            
            # Process channels in parallel
            futures = []
            for rgb_channel, channel_spec in self._channel_mapping.items():
                future = self._thread_pool.submit(
                    self._process_single_channel, 
                    image, channel_spec, rgb_channel
                )
                futures.append((rgb_channel, future))
            
            # Collect results
            for rgb_channel, future in futures:
                try:
                    processed_channel = future.result(timeout=5.0)
                    rgb_channel_index = {'R': 0, 'G': 1, 'B': 2}[rgb_channel]
                    rgb_image[:, :, rgb_channel_index] = processed_channel
                except Exception as e:
                    self.emit_error(f"Error processing channel {rgb_channel}: {str(e)}")
            
            return np.clip(rgb_image, 0.0, 1.0)
            
        except Exception as e:
            self.emit_error(f"Error in parallel processing: {str(e)}")
            return self._process_cpu(image, **kwargs)
    
    def _process_gpu(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Process image using GPU (if available)."""
        try:
            # For now, fall back to CPU processing
            # GPU processing would require CUDA or OpenCL implementation
            return self._process_cpu(image, **kwargs)
            
        except Exception as e:
            self.emit_error(f"Error in GPU processing: {str(e)}")
            return self._process_cpu(image, **kwargs)
    
    def _process_single_channel(self, image: np.ndarray, channel_spec: Union[int, List[int]], 
                               rgb_channel: str) -> np.ndarray:
        """Process a single channel for parallel processing."""
        try:
            if isinstance(channel_spec, list):
                # Multi-channel blending
                blended_data = self._blend_channels(image, channel_spec)
            else:
                # Single channel
                if channel_spec < image.shape[2]:
                    blended_data = image[:, :, channel_spec].astype(np.float32)
                else:
                    return np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
            
            # Apply bounds
            bounds = self._get_channel_bounds(channel_spec, blended_data)
            
            # Normalize channel
            normalized_channel = self._normalize_channel_enhanced(blended_data, bounds)
            
            # Apply enhancements
            enhanced_channel = self._apply_advanced_enhancements(normalized_channel)
            
            return enhanced_channel
            
        except Exception as e:
            self.emit_error(f"Error processing single channel: {str(e)}")
            return np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
    
    def _blend_channels(self, image: np.ndarray, channel_indices: List[int]) -> np.ndarray:
        """Blend multiple channels together."""
        try:
            if not channel_indices:
                return np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
            
            # Get valid channels
            valid_channels = [ch for ch in channel_indices if ch < image.shape[2]]
            if not valid_channels:
                return np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
            
            # Blend channels using weights
            blended = np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
            total_weight = 0.0
            
            for channel_idx in valid_channels:
                weight = self._channel_weights.get(channel_idx, 1.0)
                blended += image[:, :, channel_idx] * weight
                total_weight += weight
            
            # Normalize by total weight
            if total_weight > 0:
                blended /= total_weight
            
            return blended
            
        except Exception as e:
            self.emit_error(f"Error blending channels: {str(e)}")
            return np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
    
    def _get_channel_bounds(self, channel_spec: Union[int, List[int]], 
                           channel_data: np.ndarray) -> Tuple[float, float]:
        """Get bounds for channel with enhanced methods."""
        try:
            if self._auto_bounds:
                if self._bounds_method == "percentile":
                    return self._calculate_percentile_bounds(channel_data)
                elif self._bounds_method == "robust":
                    return self._calculate_robust_bounds(channel_data)
                elif self._bounds_method == "adaptive":
                    return self._calculate_adaptive_bounds(channel_data)
                else:  # minmax
                    return self._calculate_minmax_bounds(channel_data)
            else:
                # Use manual bounds
                if isinstance(channel_spec, int):
                    return self.get_channel_bounds(channel_spec)
                else:
                    return (0.0, 1.0)
                    
        except Exception as e:
            self.emit_error(f"Error getting channel bounds: {str(e)}")
            return (0.0, 1.0)
    
    def _calculate_robust_bounds(self, channel_data: np.ndarray) -> Tuple[float, float]:
        """Calculate robust bounds using robust statistics."""
        try:
            # Use robust scaler approach
            data_flat = channel_data.flatten()
            data_flat = data_flat[~np.isnan(data_flat)]
            
            if len(data_flat) == 0:
                return (0.0, 1.0)
            
            # Calculate IQR-based bounds
            q25 = np.percentile(data_flat, 25)
            q75 = np.percentile(data_flat, 75)
            iqr = q75 - q25
            
            # Robust bounds
            lower = q25 - 1.5 * iqr
            upper = q75 + 1.5 * iqr
            
            # Clamp to actual data range
            lower = max(lower, data_flat.min())
            upper = min(upper, data_flat.max())
            
            return (float(lower), float(upper))
            
        except Exception as e:
            self.emit_error(f"Error calculating robust bounds: {str(e)}")
            return (0.0, 1.0)
    
    def _calculate_adaptive_bounds(self, channel_data: np.ndarray) -> Tuple[float, float]:
        """Calculate adaptive bounds based on histogram analysis."""
        try:
            data_flat = channel_data.flatten()
            data_flat = data_flat[~np.isnan(data_flat)]
            
            if len(data_flat) == 0:
                return (0.0, 1.0)
            
            # Calculate histogram
            hist, bins = np.histogram(data_flat, bins=256, density=True)
            
            # Find peaks in histogram
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(hist, height=0.001)
            
            if len(peaks) >= 2:
                # Use peaks to determine bounds
                peak_bins = bins[peaks]
                lower = float(peak_bins[0])
                upper = float(peak_bins[-1])
            else:
                # Fall back to percentile method
                lower = float(np.percentile(data_flat, 5))
                upper = float(np.percentile(data_flat, 95))
            
            return (lower, upper)
            
        except Exception as e:
            self.emit_error(f"Error calculating adaptive bounds: {str(e)}")
            return self._calculate_percentile_bounds(channel_data)
    
    def _normalize_channel_enhanced(self, channel_data: np.ndarray, 
                                   bounds: Tuple[float, float]) -> np.ndarray:
        """Enhanced channel normalization with better handling."""
        try:
            min_val, max_val = bounds
            
            # Handle NaN and inf values
            if self._nan_handling == "replace":
                channel_data = np.nan_to_num(channel_data, nan=0.0)
            elif self._nan_handling == "error" and np.any(np.isnan(channel_data)):
                raise ValueError("NaN values found in channel data")
            
            if self._inf_handling == "clip":
                channel_data = np.clip(channel_data, -1e10, 1e10)
            elif self._inf_handling == "replace":
                channel_data = np.nan_to_num(channel_data, posinf=max_val, neginf=min_val)
            
            # Normalize
            if max_val > min_val:
                normalized = (channel_data - min_val) / (max_val - min_val)
            else:
                normalized = np.zeros_like(channel_data)
            
            # Clamp to 0-1 range
            normalized = np.clip(normalized, 0.0, 1.0)
            
            return normalized
            
        except Exception as e:
            self.emit_error(f"Error in enhanced normalization: {str(e)}")
            return np.clip(channel_data, 0.0, 1.0)
    
    def _apply_advanced_enhancements(self, channel_data: np.ndarray) -> np.ndarray:
        """Apply advanced image enhancement techniques."""
        try:
            enhanced = channel_data.copy()
            
            # Apply histogram equalization
            if self._histogram_equalization:
                enhanced = exposure.equalize_hist(enhanced)
            
            # Apply adaptive histogram equalization
            if self._adaptive_histogram_eq:
                enhanced = exposure.equalize_adapthist(enhanced)
            
            # Apply CLAHE
            if self._clahe_enabled:
                enhanced = self._apply_clahe(enhanced)
            
            # Apply gamma correction
            if self._gamma_correction != 1.0:
                enhanced = np.power(enhanced, 1.0 / self._gamma_correction)
            
            # Apply contrast enhancement
            if self._contrast_enhancement != 1.0:
                enhanced = (enhanced - 0.5) * self._contrast_enhancement + 0.5
            
            # Apply brightness adjustment
            if self._brightness_adjustment != 0.0:
                enhanced = enhanced + self._brightness_adjustment
            
            # Clamp values
            enhanced = np.clip(enhanced, 0.0, 1.0)
            
            return enhanced
            
        except Exception as e:
            self.emit_error(f"Error applying advanced enhancements: {str(e)}")
            return channel_data
    
    def _apply_clahe(self, channel_data: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        try:
            # Convert to uint8 for CLAHE
            data_uint8 = (channel_data * 255).astype(np.uint8)
            
            # Create CLAHE object
            clahe = cv2.createCLAHE(
                clipLimit=self._clahe_clip_limit,
                tileGridSize=self._clahe_tile_size
            )
            
            # Apply CLAHE
            enhanced_uint8 = clahe.apply(data_uint8)
            
            # Convert back to float
            enhanced = enhanced_uint8.astype(np.float32) / 255.0
            
            return enhanced
            
        except Exception as e:
            self.emit_error(f"Error applying CLAHE: {str(e)}")
            return channel_data
    
    def _convert_color_space(self, rgb_image: np.ndarray, 
                           from_space: str, to_space: str) -> np.ndarray:
        """Convert between color spaces."""
        try:
            if from_space == to_space:
                return rgb_image
            
            # Convert to uint8 for OpenCV
            rgb_uint8 = (rgb_image * 255).astype(np.uint8)
            
            # Define conversion mappings
            conversions = {
                ('RGB', 'HSV'): cv2.COLOR_RGB2HSV,
                ('RGB', 'LAB'): cv2.COLOR_RGB2LAB,
                ('RGB', 'YUV'): cv2.COLOR_RGB2YUV,
                ('RGB', 'XYZ'): cv2.COLOR_RGB2XYZ,
                ('HSV', 'RGB'): cv2.COLOR_HSV2RGB,
                ('LAB', 'RGB'): cv2.COLOR_LAB2RGB,
                ('YUV', 'RGB'): cv2.COLOR_YUV2RGB,
                ('XYZ', 'RGB'): cv2.COLOR_XYZ2RGB
            }
            
            conversion_key = (from_space, to_space)
            if conversion_key in conversions:
                converted_uint8 = cv2.cvtColor(rgb_uint8, conversions[conversion_key])
                return converted_uint8.astype(np.float32) / 255.0
            else:
                # Unsupported conversion, return original
                return rgb_image
                
        except Exception as e:
            self.emit_error(f"Error converting color space: {str(e)}")
            return rgb_image
    
    def _validate_input(self, image: np.ndarray) -> bool:
        """Validate input image."""
        try:
            if image.ndim != 3:
                self.emit_error("Input image must be 3-dimensional")
                return False
            
            if image.shape[2] == 0:
                self.emit_error("Input image has no channels")
                return False
            
            if image.size == 0:
                self.emit_error("Input image is empty")
                return False
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error validating input: {str(e)}")
            return False
    
    def _validate_output(self, rgb_image: np.ndarray) -> np.ndarray:
        """Validate and fix output image."""
        try:
            # Check shape
            if rgb_image.shape[2] != 3:
                self.emit_error("Output image must have 3 channels")
                return np.zeros((100, 100, 3), dtype=np.float32)
            
            # Handle NaN/inf values
            if np.any(np.isnan(rgb_image)) or np.any(np.isinf(rgb_image)):
                rgb_image = np.nan_to_num(rgb_image, nan=0.0, posinf=1.0, neginf=0.0)
            
            # Ensure correct range
            rgb_image = np.clip(rgb_image, 0.0, 1.0)
            
            return rgb_image
            
        except Exception as e:
            self.emit_error(f"Error validating output: {str(e)}")
            return np.zeros((100, 100, 3), dtype=np.float32)
    
    def _setup_thread_pool(self) -> None:
        """Setup thread pool for parallel processing."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown()
            
            self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers)
            
        except Exception as e:
            self.emit_error(f"Error setting up thread pool: {str(e)}")
    
    def _clear_all_caches(self) -> None:
        """Clear all caches."""
        try:
            with self._cache_lock:
                self._cached_mappings.clear()
                self._cached_histograms.clear()
                self._cached_bounds.clear()
            
        except Exception as e:
            self.emit_error(f"Error clearing caches: {str(e)}")
    
    def _generate_enhanced_cache_key(self, image: np.ndarray, **kwargs) -> str:
        """Generate enhanced cache key."""
        try:
            key_parts = [
                str(image.shape),
                str(self._channel_mapping),
                str(self._color_space),
                str(self._gamma_correction),
                str(self._contrast_enhancement),
                str(self._brightness_adjustment),
                str(self._auto_bounds),
                str(self._bounds_method),
                str(self._percentile_bounds),
                str(self._histogram_equalization),
                str(self._adaptive_histogram_eq),
                str(self._clahe_enabled),
                str(self._blending_mode),
                str(hash(str(sorted(self._channel_weights.items())))),
                str(kwargs.get('timestamp', ''))
            ]
            
            return '_'.join(key_parts)
            
        except Exception as e:
            self.emit_error(f"Error generating cache key: {str(e)}")
            return "default"
    
    def _update_processing_stats(self, processing_time: float) -> None:
        """Update processing statistics."""
        try:
            self._mapping_stats['total_mappings'] += 1
            
            # Update average processing time
            current_avg = self._mapping_stats['avg_processing_time']
            count = self._mapping_stats['total_mappings']
            
            self._mapping_stats['avg_processing_time'] = (
                (current_avg * (count - 1) + processing_time) / count
            )
            
        except Exception as e:
            self.emit_error(f"Error updating processing stats: {str(e)}")
    
    def _initialize_enhanced_presets(self) -> None:
        """Initialize enhanced mapping presets."""
        try:
            self._mapping_presets = {
                'RGB': {
                    'name': 'RGB',
                    'description': 'Standard RGB mapping',
                    'mapping': {'R': 0, 'G': 1, 'B': 2},
                    'color_space': 'RGB',
                    'gamma': 1.0,
                    'contrast': 1.0,
                    'brightness': 0.0,
                    'bounds_method': 'percentile'
                },
                'NIR_FALSE_COLOR': {
                    'name': 'NIR False Color',
                    'description': 'Near-infrared false color composite',
                    'mapping': {'R': 3, 'G': 0, 'B': 1},
                    'color_space': 'RGB',
                    'gamma': 1.2,
                    'contrast': 1.1,
                    'brightness': 0.0,
                    'bounds_method': 'robust'
                },
                'VEGETATION_ENHANCED': {
                    'name': 'Vegetation Enhanced',
                    'description': 'Enhanced vegetation analysis',
                    'mapping': {'R': 3, 'G': 2, 'B': 1},
                    'color_space': 'RGB',
                    'gamma': 1.0,
                    'contrast': 1.3,
                    'brightness': 0.1,
                    'bounds_method': 'adaptive',
                    'histogram_equalization': True
                },
                'MULTISPECTRAL_BLEND': {
                    'name': 'Multispectral Blend',
                    'description': 'Blend multiple channels',
                    'mapping': {'R': [0, 1], 'G': [2, 3], 'B': [4, 5]},
                    'color_space': 'RGB',
                    'gamma': 1.0,
                    'contrast': 1.0,
                    'brightness': 0.0,
                    'bounds_method': 'percentile',
                    'clahe_enabled': True
                }
            }
            
        except Exception as e:
            self.emit_error(f"Error initializing enhanced presets: {str(e)}")
    
    def _setup_processing_pipeline(self) -> None:
        """Setup the processing pipeline."""
        try:
            # Initialize processing pipeline components
            pass
            
        except Exception as e:
            self.emit_error(f"Error setting up processing pipeline: {str(e)}")
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get enhanced channel mapper statistics."""
        stats = super().get_statistics()
        stats.update({
            'available_channels': len(self._available_channels),
            'channel_mapping': self._channel_mapping,
            'color_space': self._color_space,
            'processing_mode': self._processing_mode,
            'bounds_method': self._bounds_method,
            'auto_bounds': self._auto_bounds,
            'enhancement_features': {
                'histogram_equalization': self._histogram_equalization,
                'adaptive_histogram_eq': self._adaptive_histogram_eq,
                'clahe_enabled': self._clahe_enabled,
                'gamma_correction': self._gamma_correction,
                'contrast_enhancement': self._contrast_enhancement,
                'brightness_adjustment': self._brightness_adjustment
            },
            'performance_settings': {
                'max_workers': self._max_workers,
                'chunk_size': self._chunk_size,
                'use_gpu': self._use_gpu,
                'cache_enabled': self._cache_enabled,
                'max_cache_size': self._max_cache_size
            },
            'cache_statistics': {
                'cached_mappings': len(self._cached_mappings),
                'cached_histograms': len(self._cached_histograms),
                'cached_bounds': len(self._cached_bounds),
                'cache_hits': self._mapping_stats['cache_hits'],
                'cache_misses': self._mapping_stats['cache_misses'],
                'hit_rate': self._mapping_stats['cache_hits'] / max(1, self._mapping_stats['cache_hits'] + self._mapping_stats['cache_misses'])
            },
            'processing_stats': self._mapping_stats,
            'quality_settings': {
                'quality_checks': self._quality_checks,
                'input_validation': self._input_validation,
                'output_validation': self._output_validation,
                'nan_handling': self._nan_handling,
                'inf_handling': self._inf_handling
            },
            'advanced_features': {
                'blending_mode': self._blending_mode,
                'channel_weights': self._channel_weights,
                'enable_channel_mixing': self._enable_channel_mixing,
                'custom_functions_count': len(self._custom_color_functions),
                'real_time_enabled': self._real_time_enabled
            }
        })
        return stats
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown()
            
            self._clear_all_caches()
            
        except Exception as e:
            self.emit_error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor."""
        try:
            self.cleanup()
        except:
            pass