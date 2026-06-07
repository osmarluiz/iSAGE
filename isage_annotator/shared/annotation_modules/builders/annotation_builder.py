"""
Annotation Builder - Assembles complete annotation systems from components

This module provides a builder pattern for creating complete annotation systems
by combining tools, overlays, UI components, and navigation elements.
"""

from typing import Dict, Any, List, Optional, Type, Callable
from ..base_protocols import BaseComponent, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QSplitter
from ..canvas.annotation_canvas import AnnotationCanvas
from ..tools.point_tool import PointTool
from ..tools.point_manager import PointManager
from ..overlays.prediction_overlay import PredictionOverlay
from ..overlays.ground_truth_overlay import GroundTruthOverlay
from ..overlays.mistake_overlay import MistakeOverlay
from ..navigation.image_navigator import ImageNavigator
from ..navigation.minimap import Minimap
from ..navigation.navigation_controller import NavigationController
from ..ui.control_panel import ControlPanel
from ..ui.status_panel import StatusPanel
from ..ui.theme_manager import ThemeManager
from ..ui.dialog_manager import DialogManager
from ..io.json_saver import JsonSaver
from ..io.json_loader import JsonLoader
from ..io.auto_saver import AutoSaver
from ..io.session_manager import SessionManager
from ..io.data_validator import DataValidator
from .base_builder import BaseBuilder


class AnnotationBuilder(BaseBuilder):
    """Builder for creating complete annotation systems."""
    
    def __init__(self, name: str = "annotation_builder", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Builder configuration
        self._preset_name: Optional[str] = None
        self._window_title: str = "Annotation System"
        self._window_size: tuple = (1400, 900)
        self._theme: str = "light"
        
        # Component registry
        self._components: Dict[str, BaseComponent] = {}
        self._component_configs: Dict[str, Dict[str, Any]] = {}
        self._ui_layout: Optional[QWidget] = None
        
        # Main window
        self._main_window: Optional[QMainWindow] = None
        self._central_widget: Optional[QWidget] = None
        
        # Core components
        self._canvas: Optional[AnnotationCanvas] = None
        self._theme_manager: Optional[ThemeManager] = None
        self._session_manager: Optional[SessionManager] = None
        self._navigation_controller: Optional[NavigationController] = None
        
        # Tools
        self._tools: Dict[str, BaseComponent] = {}
        self._active_tool: Optional[str] = None
        
        # Overlays
        self._overlays: Dict[str, BaseComponent] = {}
        
        # UI panels
        self._control_panel: Optional[ControlPanel] = None
        self._status_panel: Optional[StatusPanel] = None
        self._minimap: Optional[Minimap] = None
        
        # I/O components
        self._json_saver: Optional[JsonSaver] = None
        self._json_loader: Optional[JsonLoader] = None
        self._auto_saver: Optional[AutoSaver] = None
        self._data_validator: Optional[DataValidator] = None
        
        # Build stages
        self._build_stages: List[str] = [
            'initialize_core',
            'create_theme_manager',
            'create_main_window',
            'create_canvas',
            'create_tools',
            'create_overlays',
            'create_navigation',
            'create_ui_panels',
            'create_io_components',
            'setup_connections',
            'apply_theme',
            'finalize_build'
        ]
        self._current_stage: int = 0
        
        # Validation
        self._validation_enabled: bool = True
        self._validation_errors: List[str] = []
    
    def initialize(self, **kwargs) -> bool:
        """Initialize annotation builder."""
        self._preset_name = kwargs.get('preset_name', None)
        self._window_title = kwargs.get('window_title', "Annotation System")
        self._window_size = kwargs.get('window_size', (1400, 900))
        self._theme = kwargs.get('theme', 'light')
        self._validation_enabled = kwargs.get('validation_enabled', True)
        
        # Update component configs
        self._component_configs = kwargs.get('component_configs', {})
        
        return super().initialize(**kwargs)
    
    def set_preset(self, preset_name: str) -> 'AnnotationBuilder':
        """Set preset configuration."""
        self._preset_name = preset_name
        
        # Apply preset-specific configurations
        if preset_name == 'active_learning':
            self._apply_active_learning_preset()
        elif preset_name == 'basic_annotation':
            self._apply_basic_annotation_preset()
        elif preset_name == 'advanced_annotation':
            self._apply_advanced_annotation_preset()
        
        self.emit_state_changed({'preset': preset_name})
        return self
    
    def add_component(self, component_name: str, component_class: Type[BaseComponent], config: Dict[str, Any]) -> 'AnnotationBuilder':
        """Add component to builder."""
        try:
            self._component_configs[component_name] = {
                'class': component_class,
                'config': config
            }
            
            self.emit_state_changed({'components_count': len(self._component_configs)})
            
        except Exception as e:
            self.emit_error(f"Error adding component: {str(e)}")
        
        return self
    
    def remove_component(self, component_name: str) -> 'AnnotationBuilder':
        """Remove component from builder."""
        try:
            if component_name in self._component_configs:
                del self._component_configs[component_name]
                
                if component_name in self._components:
                    del self._components[component_name]
                
                self.emit_state_changed({'components_count': len(self._component_configs)})
                
        except Exception as e:
            self.emit_error(f"Error removing component: {str(e)}")
        
        return self
    
    def configure_component(self, component_name: str, config: Dict[str, Any]) -> 'AnnotationBuilder':
        """Configure component settings."""
        try:
            if component_name in self._component_configs:
                self._component_configs[component_name]['config'].update(config)
                
                # Reconfigure if already created
                if component_name in self._components:
                    component = self._components[component_name]
                    component.initialize(**config)
                
        except Exception as e:
            self.emit_error(f"Error configuring component: {str(e)}")
        
        return self
    
    def build(self) -> Optional[QMainWindow]:
        """Build complete annotation system."""
        try:
            self._validation_errors.clear()
            self._current_stage = 0
            
            # Execute build stages
            for stage in self._build_stages:
                self.emit_state_changed({'build_stage': stage, 'stage_index': self._current_stage})
                
                stage_method = getattr(self, f'_{stage}', None)
                if stage_method:
                    success = stage_method()
                    if not success:
                        self.emit_error(f"Build failed at stage: {stage}")
                        return None
                
                self._current_stage += 1
            
            # Validate build
            if self._validation_enabled and not self._validate_build():
                self.emit_error("Build validation failed")
                return None
            
            self.emit_state_changed({'build_completed': True})
            return self._main_window
            
        except Exception as e:
            self.emit_error(f"Error building annotation system: {str(e)}")
            return None
    
    def get_component(self, component_name: str) -> Optional[BaseComponent]:
        """Get component by name."""
        return self._components.get(component_name)
    
    def get_main_window(self) -> Optional[QMainWindow]:
        """Get main window."""
        return self._main_window
    
    def get_canvas(self) -> Optional[AnnotationCanvas]:
        """Get annotation canvas."""
        return self._canvas
    
    def get_tools(self) -> Dict[str, BaseComponent]:
        """Get all tools."""
        return self._tools.copy()
    
    def get_overlays(self) -> Dict[str, BaseComponent]:
        """Get all overlays."""
        return self._overlays.copy()
    
    def get_build_progress(self) -> Dict[str, Any]:
        """Get build progress information."""
        return {
            'current_stage': self._current_stage,
            'total_stages': len(self._build_stages),
            'stage_name': self._build_stages[self._current_stage] if self._current_stage < len(self._build_stages) else 'completed',
            'progress_percent': (self._current_stage / len(self._build_stages)) * 100,
            'validation_errors': self._validation_errors.copy()
        }
    
    def _apply_active_learning_preset(self) -> None:
        """Apply active learning preset configuration."""
        try:
            # Canvas configuration
            self._component_configs['canvas'] = {
                'class': AnnotationCanvas,
                'config': {
                    'enable_zoom': True,
                    'enable_pan': True,
                    'background_color': '#ffffff',
                    'crosshair_enabled': True,
                    'grid_enabled': False
                }
            }
            
            # Point tool configuration
            self._component_configs['point_tool'] = {
                'class': PointTool,
                'config': {
                    'point_size': 8,
                    'click_tolerance': 10.0,
                    'show_point_labels': True,
                    'show_confidence': True
                }
            }
            
            # Point manager configuration
            self._component_configs['point_manager'] = {
                'class': PointManager,
                'config': {
                    'max_history_size': 100
                }
            }
            
            # Overlays configuration
            self._component_configs['prediction_overlay'] = {
                'class': PredictionOverlay,
                'config': {
                    'confidence_threshold': 0.5,
                    'color_scheme': 'red_blue',
                    'use_confidence_mapping': True
                }
            }
            
            self._component_configs['ground_truth_overlay'] = {
                'class': GroundTruthOverlay,
                'config': {
                    'show_boundaries': True,
                    'show_class_labels': True
                }
            }
            
            self._component_configs['mistake_overlay'] = {
                'class': MistakeOverlay,
                'config': {
                    'show_mistake_stats': True,
                    'highlight_confidence': True
                }
            }
            
            # Navigation configuration
            self._component_configs['image_navigator'] = {
                'class': ImageNavigator,
                'config': {
                    'thumbnail_size': (128, 128),
                    'cache_enabled': True,
                    'preload_enabled': True
                }
            }
            
            self._component_configs['minimap'] = {
                'class': Minimap,
                'config': {
                    'minimap_size': (200, 200),
                    'click_to_navigate': True,
                    'show_zoom_level': True
                }
            }
            
            # UI panels configuration
            self._component_configs['control_panel'] = {
                'class': ControlPanel,
                'config': {
                    'panel_width': 300,
                    'collapsible': True,
                    'theme': self._theme
                }
            }
            
            self._component_configs['status_panel'] = {
                'class': StatusPanel,
                'config': {
                    'panel_width': 400,
                    'log_enabled': True,
                    'auto_scroll': True
                }
            }
            
            # I/O components configuration
            self._component_configs['session_manager'] = {
                'class': SessionManager,
                'config': {
                    'auto_save_enabled': True,
                    'recovery_enabled': True
                }
            }
            
            self._component_configs['auto_saver'] = {
                'class': AutoSaver,
                'config': {
                    'save_interval': 300.0,
                    'change_detection': True
                }
            }
            
        except Exception as e:
            self.emit_error(f"Error applying active learning preset: {str(e)}")
    
    def _apply_basic_annotation_preset(self) -> None:
        """Apply basic annotation preset configuration."""
        try:
            # Simplified configuration for basic annotation
            self._component_configs['canvas'] = {
                'class': AnnotationCanvas,
                'config': {
                    'enable_zoom': True,
                    'enable_pan': True,
                    'background_color': '#ffffff'
                }
            }
            
            self._component_configs['point_tool'] = {
                'class': PointTool,
                'config': {
                    'point_size': 6,
                    'click_tolerance': 8.0,
                    'show_point_labels': False
                }
            }
            
            self._component_configs['control_panel'] = {
                'class': ControlPanel,
                'config': {
                    'panel_width': 250,
                    'collapsible': False
                }
            }
            
        except Exception as e:
            self.emit_error(f"Error applying basic annotation preset: {str(e)}")
    
    def _apply_advanced_annotation_preset(self) -> None:
        """Apply advanced annotation preset configuration."""
        try:
            # Full-featured configuration
            self._apply_active_learning_preset()
            
            # Add advanced features
            self._component_configs['data_validator'] = {
                'class': DataValidator,
                'config': {
                    'strict_mode': True,
                    'repair_mode': True
                }
            }
            
            # Enhanced UI
            self._component_configs['dialog_manager'] = {
                'class': DialogManager,
                'config': {
                    'remember_positions': True
                }
            }
            
        except Exception as e:
            self.emit_error(f"Error applying advanced annotation preset: {str(e)}")
    
    def _initialize_core(self) -> bool:
        """Initialize core components."""
        try:
            # Clear existing components
            self._components.clear()
            self._tools.clear()
            self._overlays.clear()
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error initializing core: {str(e)}")
            return False
    
    def _create_theme_manager(self) -> bool:
        """Create theme manager."""
        try:
            self._theme_manager = ThemeManager()
            self._theme_manager.initialize(default_theme=self._theme)
            self._components['theme_manager'] = self._theme_manager
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating theme manager: {str(e)}")
            return False
    
    def _create_main_window(self) -> bool:
        """Create main window."""
        try:
            self._main_window = QMainWindow()
            self._main_window.setWindowTitle(self._window_title)
            self._main_window.resize(*self._window_size)
            
            # Create central widget
            self._central_widget = QWidget()
            self._main_window.setCentralWidget(self._central_widget)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating main window: {str(e)}")
            return False
    
    def _create_canvas(self) -> bool:
        """Create annotation canvas."""
        try:
            if 'canvas' in self._component_configs:
                config = self._component_configs['canvas']
                self._canvas = config['class']()
                self._canvas.initialize(**config['config'])
                self._components['canvas'] = self._canvas
                
                return True
            
            return False
            
        except Exception as e:
            self.emit_error(f"Error creating canvas: {str(e)}")
            return False
    
    def _create_tools(self) -> bool:
        """Create annotation tools."""
        try:
            # Create tools based on configuration
            for comp_name, comp_config in self._component_configs.items():
                if comp_name.endswith('_tool') or comp_name.endswith('_manager'):
                    component = comp_config['class']()
                    component.initialize(**comp_config['config'])
                    
                    self._components[comp_name] = component
                    self._tools[comp_name] = component
                    
                    # Set first tool as active
                    if self._active_tool is None:
                        self._active_tool = comp_name
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating tools: {str(e)}")
            return False
    
    def _create_overlays(self) -> bool:
        """Create overlays."""
        try:
            # Create overlays based on configuration
            for comp_name, comp_config in self._component_configs.items():
                if comp_name.endswith('_overlay'):
                    component = comp_config['class']()
                    component.initialize(**comp_config['config'])
                    
                    self._components[comp_name] = component
                    self._overlays[comp_name] = component
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating overlays: {str(e)}")
            return False
    
    def _create_navigation(self) -> bool:
        """Create navigation components."""
        try:
            # Create navigation components
            nav_components = ['image_navigator', 'minimap']
            
            for comp_name in nav_components:
                if comp_name in self._component_configs:
                    comp_config = self._component_configs[comp_name]
                    component = comp_config['class']()
                    component.initialize(**comp_config['config'])
                    
                    self._components[comp_name] = component
                    
                    if comp_name == 'minimap':
                        self._minimap = component
            
            # Create navigation controller
            self._navigation_controller = NavigationController()
            self._navigation_controller.initialize()
            
            # Connect navigation components
            if 'image_navigator' in self._components:
                self._navigation_controller.set_image_navigator(self._components['image_navigator'])
            
            if 'minimap' in self._components:
                self._navigation_controller.set_minimap(self._components['minimap'])
            
            if self._canvas:
                self._navigation_controller.set_main_canvas(self._canvas)
            
            self._components['navigation_controller'] = self._navigation_controller
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating navigation: {str(e)}")
            return False
    
    def _create_ui_panels(self) -> bool:
        """Create UI panels."""
        try:
            # Create control panel
            if 'control_panel' in self._component_configs:
                comp_config = self._component_configs['control_panel']
                self._control_panel = comp_config['class']()
                self._control_panel.initialize(**comp_config['config'])
                
                # Add tools to control panel
                for tool_name, tool in self._tools.items():
                    tool_config = {
                        'display_name': tool_name.replace('_', ' ').title(),
                        'tooltip': f"Select {tool_name}"
                    }
                    self._control_panel.add_tool(tool_name, tool_config)
                
                self._components['control_panel'] = self._control_panel
            
            # Create status panel
            if 'status_panel' in self._component_configs:
                comp_config = self._component_configs['status_panel']
                self._status_panel = comp_config['class']()
                self._status_panel.initialize(**comp_config['config'])
                self._components['status_panel'] = self._status_panel
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating UI panels: {str(e)}")
            return False
    
    def _create_io_components(self) -> bool:
        """Create I/O components."""
        try:
            # Create I/O components
            io_components = ['json_saver', 'json_loader', 'session_manager', 'auto_saver', 'data_validator']
            
            for comp_name in io_components:
                if comp_name in self._component_configs:
                    comp_config = self._component_configs[comp_name]
                    component = comp_config['class']()
                    component.initialize(**comp_config['config'])
                    
                    self._components[comp_name] = component
                    
                    # Store references to commonly used components
                    if comp_name == 'session_manager':
                        self._session_manager = component
                    elif comp_name == 'auto_saver':
                        self._auto_saver = component
                    elif comp_name == 'json_saver':
                        self._json_saver = component
                    elif comp_name == 'json_loader':
                        self._json_loader = component
                    elif comp_name == 'data_validator':
                        self._data_validator = component
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error creating I/O components: {str(e)}")
            return False
    
    def _setup_connections(self) -> bool:
        """Setup component connections."""
        try:
            # Connect tools to canvas
            if self._canvas:
                for tool in self._tools.values():
                    if hasattr(tool, 'set_canvas'):
                        tool.set_canvas(self._canvas)
            
            # Connect overlays to canvas
            if self._canvas:
                for overlay in self._overlays.values():
                    if hasattr(overlay, 'set_canvas'):
                        overlay.set_canvas(self._canvas)
            
            # Connect control panel to tools
            if self._control_panel:
                self._control_panel.toolSelected.connect(self._on_tool_selected)
            
            # Connect status panel to components
            if self._status_panel:
                # Connect error signals
                for component in self._components.values():
                    if hasattr(component, 'errorOccurred'):
                        component.errorOccurred.connect(
                            lambda msg: self._status_panel.add_log_entry('error', msg)
                        )
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting up connections: {str(e)}")
            return False
    
    def _apply_theme(self) -> bool:
        """Apply theme to all components."""
        try:
            if self._theme_manager:
                # Register theme callbacks for all UI components
                ui_components = ['control_panel', 'status_panel', 'minimap']
                
                for comp_name in ui_components:
                    if comp_name in self._components:
                        component = self._components[comp_name]
                        if hasattr(component, 'set_theme'):
                            self._theme_manager.register_theme_callback(
                                lambda theme, comp=component: comp.set_theme(theme)
                            )
                
                # Apply current theme
                self._theme_manager.set_theme(self._theme)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error applying theme: {str(e)}")
            return False
    
    def _finalize_build(self) -> bool:
        """Finalize build process."""
        try:
            # Create main layout
            main_layout = QHBoxLayout()
            
            # Create splitter for main content
            main_splitter = QSplitter(1)  # Qt.Horizontal
            
            # Add control panel
            if self._control_panel:
                main_splitter.addWidget(self._control_panel)
            
            # Create center area
            center_widget = QWidget()
            center_layout = QVBoxLayout()
            
            # Add canvas
            if self._canvas:
                center_layout.addWidget(self._canvas)
            
            center_widget.setLayout(center_layout)
            main_splitter.addWidget(center_widget)
            
            # Add right panel (status + minimap)
            right_widget = QWidget()
            right_layout = QVBoxLayout()
            
            if self._minimap:
                right_layout.addWidget(self._minimap)
            
            if self._status_panel:
                right_layout.addWidget(self._status_panel)
            
            right_widget.setLayout(right_layout)
            main_splitter.addWidget(right_widget)
            
            # Set splitter proportions
            main_splitter.setSizes([300, 800, 300])
            
            # Add splitter to main layout
            main_layout.addWidget(main_splitter)
            
            # Set layout to central widget
            self._central_widget.setLayout(main_layout)
            
            # Show main window
            self._main_window.show()
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error finalizing build: {str(e)}")
            return False
    
    def _validate_build(self) -> bool:
        """Validate built system."""
        try:
            # Check required components
            required_components = ['canvas']
            
            for comp_name in required_components:
                if comp_name not in self._components:
                    self._validation_errors.append(f"Missing required component: {comp_name}")
            
            # Check component initialization
            for comp_name, component in self._components.items():
                if not hasattr(component, 'is_initialized') or not component.is_initialized():
                    self._validation_errors.append(f"Component not initialized: {comp_name}")
            
            # Check main window
            if not self._main_window:
                self._validation_errors.append("Main window not created")
            
            return len(self._validation_errors) == 0
            
        except Exception as e:
            self.emit_error(f"Error validating build: {str(e)}")
            return False
    
    def _on_tool_selected(self, tool_name: str) -> None:
        """Handle tool selection."""
        try:
            if tool_name in self._tools:
                # Deactivate current tool
                if self._active_tool and self._active_tool in self._tools:
                    old_tool = self._tools[self._active_tool]
                    if hasattr(old_tool, 'set_active'):
                        old_tool.set_active(False)
                
                # Activate new tool
                self._active_tool = tool_name
                new_tool = self._tools[tool_name]
                if hasattr(new_tool, 'set_active'):
                    new_tool.set_active(True)
                
                # Update canvas tool
                if self._canvas and hasattr(self._canvas, 'set_active_tool'):
                    self._canvas.set_active_tool(new_tool)
                
                self.emit_state_changed({'active_tool': tool_name})
                
        except Exception as e:
            self.emit_error(f"Error handling tool selection: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get builder statistics."""
        stats = super().get_statistics()
        stats.update({
            'preset_name': self._preset_name,
            'window_title': self._window_title,
            'window_size': self._window_size,
            'theme': self._theme,
            'components_configured': len(self._component_configs),
            'components_created': len(self._components),
            'tools_count': len(self._tools),
            'overlays_count': len(self._overlays),
            'active_tool': self._active_tool,
            'validation_enabled': self._validation_enabled,
            'validation_errors': len(self._validation_errors),
            'build_progress': self.get_build_progress()
        })
        return stats