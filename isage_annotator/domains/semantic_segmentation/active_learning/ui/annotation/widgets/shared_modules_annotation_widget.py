"""
Shared Modules Annotation Widget

Wrapper widget that uses the shared annotation modules system
for comparison with the standalone annotation system.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

# Import simplified shared annotation modules directly
# Initialize logger and PyQt5 imports first
logger = logging.getLogger(__name__)

# PyQt5 is already imported above, no need for duplicate import

# Simple and direct import approach
try:
    import sys
    from pathlib import Path
    
    # Setup paths - more robust path detection
    current_file = Path(__file__).resolve()
    
    # Navigate up to find the project root (look for the 'shared' directory)
    project_root = current_file
    for _ in range(10):  # Max 10 levels up
        project_root = project_root.parent
        if (project_root / 'shared' / 'annotation_modules').exists():
            break
    else:
        # Fallback: assume we're in the standard structure
        project_root = current_file.parent.parent.parent.parent.parent
    
    shared_modules_path = str(project_root / 'shared' / 'annotation_modules')
    
    logger.info(f"Current file: {current_file}")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Shared modules path: {shared_modules_path}")
    logger.info(f"Shared modules exists: {Path(shared_modules_path).exists()}")
    
    if shared_modules_path not in sys.path:
        sys.path.insert(0, shared_modules_path)
    
    # Import the modules with absolute imports
    import importlib.util
    
    # Import layout utilities for safe layout management
    layout_utils_path = str(project_root / 'shared' / 'annotation_modules' / 'ui' / 'layout_utils.py')
    layout_utils_spec = importlib.util.spec_from_file_location("layout_utils", layout_utils_path)
    if layout_utils_spec is None:
        raise ImportError(f"Could not create spec for layout_utils from {layout_utils_path}")
    layout_utils = importlib.util.module_from_spec(layout_utils_spec)
    layout_utils_spec.loader.exec_module(layout_utils)
    
    # Make layout utilities available
    safe_set_layout = layout_utils.safe_set_layout
    init_widget_layout = layout_utils.init_widget_layout
    logger.info("✅ Layout utilities imported successfully")
    
    # Helper function to import module from path
    def import_module_from_path(module_name, file_path):
        try:
            if not Path(file_path).exists():
                raise ImportError(f"Module file does not exist: {file_path}")
            
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                raise ImportError(f"Could not create spec for {module_name} from {file_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info(f"Successfully imported {module_name} from {file_path}")
            return module
        except Exception as e:
            logger.error(f"Failed to import {module_name} from {file_path}: {e}")
            raise
    
    # Import each module directly from its file path with detailed error handling
    logger.info("Starting module imports...")
    
    try:
        control_panel = import_module_from_path(
            "advanced_control_panel",
            str(project_root / 'shared' / 'annotation_modules' / 'advanced_control_panel.py')
        )
        SharedControlPanel = control_panel.AdvancedControlPanel
        logger.info("✅ AdvancedControlPanel imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import ControlPanel: {e}")
        raise
    
    try:
        status_panel = import_module_from_path(
            "status_panel",
            str(project_root / 'shared' / 'annotation_modules' / 'status_panel.py')
        )
        SharedStatusPanel = status_panel.StatusPanel
        logger.info("✅ StatusPanel imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import StatusPanel: {e}")
        raise
    
    try:
        rgb_overlay_canvas = import_module_from_path(
            "rgb_overlay_canvas",
            str(project_root / 'shared' / 'annotation_modules' / 'canvas' / 'rgb_overlay_canvas.py')
        )
        AnnotationCanvas = rgb_overlay_canvas.RGBOverlayCanvas
        logger.info("✅ RGBOverlayCanvas imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import RGBOverlayCanvas: {e}")
        raise
    
    try:
        canvas_controls_bar = import_module_from_path(
            "canvas_controls_bar",
            str(project_root / 'shared' / 'annotation_modules' / 'canvas' / 'canvas_controls_bar.py')
        )
        CanvasControlsBar = canvas_controls_bar.CanvasControlsBar
        logger.info("✅ CanvasControlsBar imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import CanvasControlsBar: {e}")
        raise
    
    try:
        header_bar = import_module_from_path(
            "header_bar",
            str(project_root / 'shared' / 'annotation_modules' / 'ui' / 'header_bar.py')
        )
        HeaderBar = header_bar.HeaderBar
        logger.info("✅ HeaderBar imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import HeaderBar: {e}")
        raise
    
    try:
        bottom_navigation_panel = import_module_from_path(
            "bottom_navigation_panel",
            str(project_root / 'shared' / 'annotation_modules' / 'navigation' / 'bottom_navigation_panel.py')
        )
        BottomNavigationPanel = bottom_navigation_panel.BottomNavigationPanel
        logger.info("✅ BottomNavigationPanel imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import BottomNavigationPanel: {e}")
        raise
    
    SHARED_MODULES_AVAILABLE = True
    logger.info("Shared annotation modules imported successfully")
    
except ImportError as e:
    SHARED_MODULES_AVAILABLE = False
    logger.warning(f"Shared annotation modules not available: {e}")
    
    # Create fallback dummy classes and functions
    class AnnotationCanvas: 
        pass
    class SharedControlPanel: 
        pass  
    class SharedStatusPanel: 
        pass
    class HeaderBar:
        pass
    class BottomNavigationPanel:
        pass
    class CanvasControlsBar:
        pass
    
    # Fallback layout utilities
    def safe_set_layout(widget, layout): 
        return False
    def init_widget_layout(widget, layout_class, *args, **kwargs):
        return layout_class(widget, *args, **kwargs)
    
except Exception as e:
    SHARED_MODULES_AVAILABLE = False
    logger.error(f"Failed to import shared modules: {e}")
    
    # Create fallback dummy classes and functions 
    class AnnotationCanvas: 
        pass
    class SharedControlPanel: 
        pass
    class SharedStatusPanel: 
        pass
    class HeaderBar:
        pass
    class BottomNavigationPanel:
        pass
    class CanvasControlsBar:
        pass

# Fallback classes are already created above in the except blocks

# Import header and footer from current system for consistency
from .annotation_widget import AnnotationHeaderBar, FooterBar


class SharedModulesAnnotationWidget(QWidget):
    """
    Annotation widget using shared modules architecture.
    
    Provides identical functionality to the current system but uses
    modular shared components for comparison and testing.
    """
    
    # Required signals for integration
    modeExitRequested = pyqtSignal()
    annotationChanged = pyqtSignal(str, dict)  # image_name, annotation_data
    classConfigChanged = pyqtSignal(dict)  # class_data - notify all components of class changes
    sessionUpdated = pyqtSignal(dict)  # session_stats
    
    def __init__(self, parent=None, session_path=None, iteration=None):
        logger.info("SharedModulesAnnotationWidget.__init__ called")
        logger.info(f"Parameters: parent={parent}, session_path={session_path}, iteration={iteration}")
        logger.info(f"SHARED_MODULES_AVAILABLE: {SHARED_MODULES_AVAILABLE}")

        super().__init__(parent)
        logger.info("QWidget.__init__ completed")

        if not SHARED_MODULES_AVAILABLE:
            logger.error("Shared modules not available - showing unavailable message")
            self.show_unavailable_message()
            return

        # State
        self.image_list = []
        self.current_image_index = 0
        self.current_annotations = []

        # Session count cache for efficient total tracking
        self.session_total = 0
        self.session_class_totals = {}  # {class_id: count}
        self.per_image_counts = {}  # {image_stem: {'total': N, 'classes': {class_id: count}}}
        self._current_iteration = iteration if iteration is not None else 0  # Use provided or detect dynamically

        # Dynamic class configuration (loaded from dataset_metadata.json)
        self.class_names = []
        self.class_colors = []
        self.ignore_index = None
        self.num_classes = 0
        # Direct session path - prefer this over session_manager
        self.session_path = Path(session_path) if session_path else None
        
        # Shared module components
        self.annotation_canvas = None
        self.control_panel = None
        self.status_panel = None
        self.bottom_navigation = None
        self.canvas_controls = None
        
        try:
            logger.info("Starting UI setup...")
            self.setup_ui()
            logger.info("UI setup completed")
            
            logger.info("Starting shared modules setup...")
            self.setup_shared_modules()
            logger.info("Shared modules setup completed")
            
            logger.info("Starting signal connections...")
            self.setup_connections()
            logger.info("Signal connections completed")
            
            logger.info("Starting session initialization...")
            logger.info("=== ABOUT TO CALL initialize_session ===")
            self.initialize_session()
            logger.info("=== initialize_session COMPLETED ===")
            logger.info("Session initialization completed")
            
            logger.info("Setting up keyboard shortcuts...")
            self.setup_keyboard_shortcuts()
            logger.info("Keyboard shortcuts setup completed")
            
            logger.info("Shared modules annotation widget initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize shared modules annotation widget: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't show error message that might close widget - just log it
            logger.error("Widget initialization failed - widget may not function properly")
    
    def get_current_classes(self):
        """Get current class configuration from JSON - single source of truth."""
        if not self.session_path:
            return None

        # First get current iteration from session config
        import json
        session_config_path = self.session_path / "config" / "session_config.json"
        current_iteration = 0

        if session_config_path.exists():
            try:
                with open(session_config_path, 'r') as f:
                    session_config = json.load(f)
                    current_iteration = session_config.get('current_iteration', 0)
            except Exception:
                current_iteration = 0

        # Try iteration-specific metadata first, fallback to session
        possible_metadata_paths = [
            self.session_path / f"iteration_{current_iteration}" / "config" / "dataset_metadata.json",
            self.session_path / "iterations" / f"iteration_{current_iteration}" / "config" / "dataset_metadata.json",
            self.session_path / "config" / "dataset_metadata.json",
        ]

        metadata_path = None
        for path in possible_metadata_paths:
            if path.exists():
                metadata_path = path
                break

        if not metadata_path:
            logger.warning(f"No dataset_metadata.json found in {self.session_path}")
            return None

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        classes_info = metadata['classes']
        class_info = classes_info['class_info']
        
        # Extract class data
        names = []
        colors = []
        
        for i in range(classes_info['num_classes']):
            class_data = class_info[str(i)]
            names.append(class_data['name'])
            
            # Parse hex color to RGB tuple
            color_hex = class_data['color']
            if color_hex.startswith('#'):
                color_hex = color_hex[1:]
            rgb = tuple(int(color_hex[j:j+2], 16) for j in (0, 2, 4))
            colors.append(rgb)
        
        return {
            'names': names,
            'colors': colors,
            'num_classes': classes_info['num_classes'],
            'ignore_index': classes_info['ignore_index']
        }
    
    def update_classes(self, new_class_data):
        """Update class configuration everywhere - single update method."""
        if not self.session_path:
            return

        # 1. Write to JSON immediately
        self._write_classes_to_json(new_class_data)

        # 2. Update our own memory
        self._apply_class_config(new_class_data)

        # 3. Reconfigure keyboard shortcuts
        self.setup_keyboard_shortcuts()

        # 4. Configure overlay paths (canvas needs class info)
        if hasattr(self, 'annotation_canvas') and self.annotation_canvas:
            self._configure_overlay_paths()
            # Propagate class colors so points render with the legend color
            # (without this, the canvas keeps its initial palette and new
            # classes fall back to white).
            if hasattr(self.annotation_canvas, 'set_class_colors'):
                self.annotation_canvas.set_class_colors(new_class_data['colors'])

        # 5. Notify all components of class changes
        self.classConfigChanged.emit(new_class_data)

        logger.info(f"Classes updated: {len(new_class_data['names'])} classes")
    
    def _write_classes_to_json(self, class_data):
        """Write class data to JSON file."""
        import json
        metadata_path = self.session_path / "config" / "dataset_metadata.json"
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Update only the class_info while preserving other fields
        if 'classes' not in metadata:
            metadata['classes'] = {}
            
        # Build new class_info
        class_info = {}
        for i, (name, color) in enumerate(zip(class_data['names'], class_data['colors'])):
            # Convert RGB tuple to hex string
            hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            
            # Preserve extra fields if they exist (pixel_count, frequency, etc.)
            old_info = metadata['classes'].get('class_info', {}).get(str(i), {})
            class_info[str(i)] = {
                'name': name,
                'color': hex_color,
                'pixel_count': old_info.get('pixel_count', 0),
                'frequency': old_info.get('frequency', 0)
            }
        
        # Update only what we need to change
        metadata['classes']['num_classes'] = class_data['num_classes']
        metadata['classes']['ignore_index'] = class_data['ignore_index']
        metadata['classes']['class_info'] = class_info
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _apply_class_config(self, class_data):
        """Apply class configuration to our memory."""
        self.class_names = class_data['names']
        self.class_colors = class_data['colors']
        self.num_classes = class_data['num_classes']
        self.ignore_index = class_data['ignore_index']

        # Initialize status panel class counts display
        if self.status_panel and hasattr(self.status_panel, 'initialize_class_counts'):
            self.status_panel.initialize_class_counts(self.class_names, self.class_colors)
    
    def _configure_overlay_paths(self):
        """Configure ground truth and prediction mask paths from session metadata."""
        if not self.session_path or not self.annotation_canvas:
            return

        # Get current class data which also reads the metadata
        current_classes = self.get_current_classes()
        if not current_classes:
            return

        # Read paths from same metadata
        import json
        metadata_path = self.session_path / "config" / "dataset_metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        # Configure ground truth mask directory
        train_masks_path = metadata.get('paths', {}).get('train_masks', '')
        if train_masks_path:
            gt_mask_dir = Path(train_masks_path)
            # Handle relative paths - they're relative to project root (session's grandparent)
            if not gt_mask_dir.is_absolute():
                gt_mask_dir = self.session_path.parent.parent / gt_mask_dir

            if hasattr(self.annotation_canvas, 'set_gt_mask_directory'):
                self.annotation_canvas.set_gt_mask_directory(str(gt_mask_dir))
                logger.info(f"Ground truth masks configured: {gt_mask_dir}")

        # Configure prediction directory from previous iteration
        current_iteration = self._current_iteration
        if current_iteration > 0:
            prediction_iteration = current_iteration - 1
            prediction_dir = self.session_path / f"iteration_{prediction_iteration}" / "predictions"

            if prediction_dir.exists():
                if hasattr(self.annotation_canvas, 'set_prediction_directory'):
                    self.annotation_canvas.set_prediction_directory(str(prediction_dir))
                    logger.info(f"Prediction masks configured: {prediction_dir}")
            else:
                logger.warning(f"Prediction directory not found: {prediction_dir}")
        else:
            logger.info("Iteration 0 - no predictions available from previous iteration")

    def show_unavailable_message(self):
        """Show message when shared modules are not available."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QVBoxLayout(self)
        
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt
        
        message = QLabel(
            "🧩 Shared Modules System Unavailable\n\n"
            "The shared annotation modules could not be loaded.\n"
            "This might be due to:\n"
            "• Import path issues\n" 
            "• Missing dependencies\n"
            "• Module structure changes\n\n"
            "Please check the shared modules directory:\n"
            "/shared/annotation_modules/\n\n"
            "Falling back to current system..."
        )
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("""
            QLabel {
                color: #f59e0b;
                font-size: 16px;
                background: #1e293b;
                border: 2px dashed #f59e0b;
                border-radius: 8px;
                padding: 40px;
            }
        """)
        layout.addWidget(message)
        
        # Don't auto-close - let user dismiss manually
        # The unavailable message should stay visible for debugging
        logger.warning("Shared modules unavailable message displayed - widget will remain open")
    
    def show_error_message(self, error_msg: str):
        """Show error message in the widget."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QVBoxLayout(self)
        
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt
        
        message = QLabel(
            f"❌ Shared Modules Error\n\n"
            f"An error occurred while setting up the shared modules system:\n\n"
            f"{error_msg}\n\n"
            f"Please check the logs for more details."
        )
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-size: 14px;
                background: #1e293b;
                border: 2px solid #ef4444;
                border-radius: 8px;
                padding: 30px;
            }
        """)
        layout.addWidget(message)
    
    def setup_ui(self):
        """Setup the main UI layout using shared modules."""
        # Use safe layout initialization to prevent QLayout errors
        if SHARED_MODULES_AVAILABLE and 'safe_set_layout' in globals():
            logger.info("Using safe layout utilities for SharedModulesAnnotationWidget")
            layout = init_widget_layout(self, QVBoxLayout)
        else:
            # Fallback to manual layout clearing
            existing_layout = self.layout()
            if existing_layout is not None:
                # Clear existing layout
                while existing_layout.count():
                    child = existing_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                existing_layout.deleteLater()
            
            layout = QVBoxLayout(self)
        
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Enhanced header bar with shared modules
        if SHARED_MODULES_AVAILABLE:
            try:
                self.header = HeaderBar(
                    name="annotation_header",
                    version="1.0.0",
                    parent=self
                )
                layout.addWidget(self.header)
                logger.info("HeaderBar created successfully")
            except Exception as e:
                logger.warning(f"Failed to create HeaderBar: {e}")
                # Fallback to original header
                try:
                    self.header = AnnotationHeaderBar()
                    layout.addWidget(self.header)
                    logger.info("Using original AnnotationHeaderBar fallback")
                except Exception as e2:
                    logger.warning(f"Original header also failed: {e2}")
                    self.header = self.create_simple_header()
                    layout.addWidget(self.header)
                    logger.info("Using simple fallback header")
        else:
            # Use simple header when shared modules not available
            self.header = self.create_simple_header()
            layout.addWidget(self.header)
            logger.info("Using simple header (shared modules not available)")
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left control panel (shared module)
        if SHARED_MODULES_AVAILABLE:
            try:
                self.control_panel = SharedControlPanel(
                    name="advanced_annotation_control_panel",
                    version="2.0.0",
                    parent=self
                )
                
                # Initialize the advanced control panel with our theme and exact sizing
                self.control_panel.initialize(
                    panel_width=384,
                    panel_height=800,
                    theme='dark'
                )
                
                # Add annotation tools
                self.control_panel.add_tool("point_tool", {
                    "name": "Point Tool",
                    "description": "Add annotation points",
                    "icon": "📍",
                    "active": True
                })
                
                main_splitter.addWidget(self.control_panel)
                
            except Exception as e:
                logger.error(f"Failed to create shared control panel: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fallback to simple widget
                fallback = self.create_fallback_panel("Control Panel\n(Shared Module)", 384)
                main_splitter.addWidget(fallback)
        else:
            fallback = self.create_fallback_panel("Control Panel\n(Modules Not Available)", 384)
            main_splitter.addWidget(fallback)
        
        # Central canvas area
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(5, 5, 5, 5)
        
        # Professional canvas controls bar (shared module)
        if SHARED_MODULES_AVAILABLE:
            try:
                self.canvas_controls = CanvasControlsBar(
                    name="annotation_canvas_controls",
                    version="1.0.0",
                    parent=canvas_widget
                )
                canvas_layout.addWidget(self.canvas_controls)
                logger.info("CanvasControlsBar created successfully")
            except Exception as e:
                logger.warning(f"Failed to create CanvasControlsBar: {e}")
                # Fallback to simple controls bar
                fallback_controls = self.create_simple_canvas_controls()
                canvas_layout.addWidget(fallback_controls)
                logger.info("Using simple fallback canvas controls")
        else:
            # Use simple controls when shared modules not available
            fallback_controls = self.create_simple_canvas_controls()
            canvas_layout.addWidget(fallback_controls)
            logger.info("Using simple canvas controls (shared modules not available)")
        
        # RGB & Overlay enhanced annotation canvas (shared module)
        if SHARED_MODULES_AVAILABLE:
            try:
                # Create RGB & overlay enhanced canvas
                self.annotation_canvas = AnnotationCanvas(
                    name="rgb_overlay_annotation_canvas",
                    version="2.0.0",
                    parent=canvas_widget
                )
                canvas_layout.addWidget(self.annotation_canvas)
                
            except Exception as e:
                logger.error(f"Failed to create shared annotation canvas: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fallback to informative widget
                fallback = self.create_canvas_fallback()
                canvas_layout.addWidget(fallback)
        else:
            fallback = self.create_canvas_fallback()
            canvas_layout.addWidget(fallback)
        
        main_splitter.addWidget(canvas_widget)
        
        # Right status panel (shared module)  
        if SHARED_MODULES_AVAILABLE:
            try:
                self.status_panel = SharedStatusPanel(
                    name="enhanced_annotation_status_panel",
                    version="2.0.0",
                    parent=self
                )
                
                # Initialize enhanced status panel
                self.status_panel.initialize(
                    panel_width=384,
                    theme='dark'
                )
                
                main_splitter.addWidget(self.status_panel)
                
            except Exception as e:
                logger.error(f"Failed to create shared status panel: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fallback to simple widget
                fallback = self.create_fallback_panel("Status Panel\n(Shared Module)", 384)
                main_splitter.addWidget(fallback)
        else:
            fallback = self.create_fallback_panel("Status Panel\n(Modules Not Available)", 384)
            main_splitter.addWidget(fallback)
        
        # Set splitter proportions
        main_splitter.setSizes([384, 552, 384])
        layout.addWidget(main_splitter)
        
        # Bottom navigation panel (shared module) - matches functioning system exactly
        if SHARED_MODULES_AVAILABLE:
            try:
                self.bottom_navigation = BottomNavigationPanel(
                    name="annotation_bottom_nav",
                    version="1.0.0",
                    parent=self
                )
                layout.addWidget(self.bottom_navigation)
                logger.info("BottomNavigationPanel created successfully")
            except Exception as e:
                logger.warning(f"Failed to create BottomNavigationPanel: {e}")
                # Fallback to simple navigation bar
                fallback_nav = self.create_simple_navigation()
                layout.addWidget(fallback_nav)
                logger.info("Using simple fallback navigation")
        else:
            # Use simple navigation when shared modules not available
            fallback_nav = self.create_simple_navigation()
            layout.addWidget(fallback_nav)
            logger.info("Using simple navigation (shared modules not available)")
        
        # Footer bar - create simple footer to avoid dependency issues
        try:
            self.footer = FooterBar()
            layout.addWidget(self.footer)
            logger.info("Original FooterBar created successfully")
        except Exception as e:
            logger.warning(f"Failed to create FooterBar: {e}")
            # Fallback to simple footer
            self.footer = self.create_simple_footer()
            layout.addWidget(self.footer)
            logger.info("Using simple fallback footer")
        
        # Apply global styling
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #ffffff;
            }
        """)
    
    def create_fallback_panel(self, text: str, width: int):
        """Create fallback panel when shared modules fail."""
        from PyQt5.QtWidgets import QLabel
        fallback = QLabel(text)
        fallback.setFixedWidth(width)
        fallback.setStyleSheet("""
            QLabel {
                background: #1f2937; 
                color: #f59e0b; 
                padding: 20px;
                font-size: 14px;
                border: 1px dashed #f59e0b;
                text-align: center;
            }
        """)
        fallback.setAlignment(Qt.AlignCenter)
        return fallback
    
    def create_canvas_fallback(self):
        """Create fallback canvas when shared modules fail."""
        from PyQt5.QtWidgets import QLabel
        fallback = QLabel(
            "🧩 Shared Modules Canvas\n\n"
            "Status: Unable to load\n\n"
            "The shared annotation modules could not be initialized.\n"
            "Please check:\n"
            "• Module imports\n"
            "• Dependencies\n"
            "• Module structure\n\n"
            "This is the comparison system - the current system\n"
            "continues to work perfectly!"
        )
        fallback.setStyleSheet("""
            QLabel {
                background: #2d3748; 
                color: #ffffff; 
                font-size: 14px;
                border: 2px dashed #f59e0b;
                padding: 30px;
                text-align: center;
            }
        """)
        fallback.setAlignment(Qt.AlignCenter)
        return fallback
    
    def create_simple_header(self):
        """Create a simple header widget as fallback."""
        from PyQt5.QtWidgets import QLabel, QHBoxLayout
        
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                border-bottom: 2px solid #374151;
            }
        """)
        
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Title
        title_label = QLabel("🧩 Shared Modules Annotation System")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Status
        self.header_status = QLabel("Ready")
        self.header_status.setStyleSheet("""
            QLabel {
                color: #10b981;
                font-size: 14px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(self.header_status)
        
        return header_widget
    
    def create_simple_footer(self):
        """Create a simple footer widget as fallback."""
        from PyQt5.QtWidgets import QLabel, QHBoxLayout
        
        footer_widget = QWidget()
        footer_widget.setFixedHeight(30)
        footer_widget.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                border-top: 1px solid #374151;
            }
        """)
        
        layout = QHBoxLayout(footer_widget)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Status label
        self.footer_status = QLabel("Ready")
        self.footer_status.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(self.footer_status)
        
        layout.addStretch()
        
        # Version label
        version_label = QLabel("Shared Modules v1.0.0")
        version_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 11px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(version_label)
        
        return footer_widget
    
    def create_simple_navigation(self):
        """Create a simple navigation widget as fallback."""
        from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
        
        nav_widget = QFrame()
        nav_widget.setFixedHeight(40)
        nav_widget.setStyleSheet("background: #374151; border: 1px solid #4b5563;")
        
        # Check for existing layout before creating new one
        existing_layout = nav_widget.layout()
        if existing_layout is not None:
            logger.warning("Navigation widget already has layout, clearing it")
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(nav_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Left spacer
        layout.addStretch()
        
        # Navigation info
        nav_label = QLabel("🧩 Bottom Navigation (Fallback)")
        nav_label.setStyleSheet("""
            QLabel {
                color: #f59e0b;
                font-size: 14px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(nav_label)
        
        # Right spacer
        layout.addStretch()
        
        return nav_widget
    
    def create_simple_canvas_controls(self):
        """Create simplified canvas controls bar as fallback."""
        from PyQt5.QtWidgets import QFrame, QLabel, QHBoxLayout
        
        controls_bar = QFrame()
        controls_bar.setFixedHeight(40)
        controls_bar.setStyleSheet("background: #374151; border: 1px solid #4b5563;")
        
        # Check for existing layout before creating new one
        existing_layout = controls_bar.layout()
        if existing_layout is not None:
            logger.warning("Controls bar already has layout, clearing it")
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        controls_layout = QHBoxLayout(controls_bar)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        # Info label
        info_label = QLabel("🧩 Canvas Controls (Fallback)")
        info_label.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 14px;")
        controls_layout.addWidget(info_label)
        
        controls_layout.addStretch()
        
        # Status label
        status_label = QLabel("Ready")
        status_label.setStyleSheet("color: #10b981; font-size: 12px;")
        controls_layout.addWidget(status_label)
        
        return controls_bar
    
    def setup_shared_modules(self):
        """Initialize shared module components."""
        if not SHARED_MODULES_AVAILABLE:
            logger.info("Shared modules not available, using fallback components")
            return
        
        try:
            logger.info("Setting up simplified shared modules...")
            
            # The components are already created in setup_ui()
            # Here we can add any additional configuration
            if self.annotation_canvas:
                logger.info("Annotation canvas ready")
            
            if self.control_panel:
                logger.info("Control panel ready")
                # Configure class names for VAIHINGEN dataset
                self.configure_control_panel_classes()
                
            if self.status_panel:
                logger.info("Status panel ready")
                
            logger.info("Simplified shared modules setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup shared modules: {e}")
    
    def setup_connections(self):
        """Setup signal connections between components."""
        if not SHARED_MODULES_AVAILABLE:
            logger.info("No shared modules available for signal connections")
            return
        
        try:
            # Connect enhanced header bar signals
            if hasattr(self.header, 'backRequested'):
                self.header.backRequested.connect(self.on_back_requested)
            if hasattr(self.header, 'helpRequested'):
                self.header.helpRequested.connect(self.on_help_requested)
            if hasattr(self.header, 'previousImageRequested'):
                self.header.previousImageRequested.connect(self.on_previous_image_requested)
            if hasattr(self.header, 'nextImageRequested'):
                self.header.nextImageRequested.connect(self.on_next_image_requested)
            if hasattr(self.header, 'gotoImageRequested'):
                self.header.gotoImageRequested.connect(self.on_goto_image_requested)
            
            # Connect RGB & overlay enhanced canvas signals
            if self.annotation_canvas:
                # Connect annotation events
                if hasattr(self.annotation_canvas, 'point_added'):
                    self.annotation_canvas.point_added.connect(self.on_annotation_added)
                if hasattr(self.annotation_canvas, 'point_removed'):
                    self.annotation_canvas.point_removed.connect(self.on_annotation_removed)
                if hasattr(self.annotation_canvas, 'point_moved'):
                    self.annotation_canvas.point_moved.connect(self.on_annotation_moved)
                if hasattr(self.annotation_canvas, 'point_drag_ended'):
                    self.annotation_canvas.point_drag_ended.connect(self.on_annotation_drag_ended)
                if hasattr(self.annotation_canvas, 'image_loaded'):
                    self.annotation_canvas.image_loaded.connect(self.on_image_loaded)
                if hasattr(self.annotation_canvas, 'view_changed'):
                    self.annotation_canvas.view_changed.connect(self.on_view_changed)
                if hasattr(self.annotation_canvas, 'mouse_coordinates'):
                    self.annotation_canvas.mouse_coordinates.connect(self.on_mouse_coordinates)
                # Connect RGB channel mapping signals
                if hasattr(self.annotation_canvas, 'rgb_channels_changed'):
                    self.annotation_canvas.rgb_channels_changed.connect(self.on_canvas_rgb_channels_changed)
                # Connect overlay signals
                if hasattr(self.annotation_canvas, 'overlay_toggled'):
                    self.annotation_canvas.overlay_toggled.connect(self.on_canvas_overlay_toggled)
            
            # Connect advanced control panel signals
            if self.control_panel:
                if hasattr(self.control_panel, 'classChanged'):
                    self.control_panel.classChanged.connect(self.on_class_changed)
                if hasattr(self.control_panel, 'clearRequested'):
                    self.control_panel.clearRequested.connect(self.on_clear_requested)
                if hasattr(self.control_panel, 'actionTriggered'):
                    self.control_panel.actionTriggered.connect(
                        lambda action, _payload=None: self.on_undo_requested()
                        if action == "undo" else None
                    )
                if hasattr(self.control_panel, 'toolChanged'):
                    self.control_panel.toolChanged.connect(self.on_tool_changed)
                if hasattr(self.control_panel, 'pointSizeChanged'):
                    self.control_panel.pointSizeChanged.connect(self.on_point_size_changed)
                if hasattr(self.control_panel, 'gridToggled'):
                    self.control_panel.gridToggled.connect(self.on_grid_toggled)
                if hasattr(self.control_panel, 'gridSizeChanged'):
                    self.control_panel.gridSizeChanged.connect(self.on_grid_size_changed)
                if hasattr(self.control_panel, 'rgbChannelChanged'):
                    self.control_panel.rgbChannelChanged.connect(self.on_rgb_channel_changed)
                if hasattr(self.control_panel, 'overlayToggled'):
                    self.control_panel.overlayToggled.connect(self.on_overlay_toggled)
                if hasattr(self.control_panel, 'overlayOpacityChanged'):
                    self.control_panel.overlayOpacityChanged.connect(self.on_overlay_opacity_changed)
                if hasattr(self.control_panel, 'pixelInfoToggled'):
                    self.control_panel.pixelInfoToggled.connect(self.on_pixel_info_toggled)
                if hasattr(self.control_panel, 'haloToggled'):
                    self.control_panel.haloToggled.connect(self.on_halo_toggled)
                if hasattr(self.control_panel, 'renderModeChanged'):
                    self.control_panel.renderModeChanged.connect(self.on_render_mode_changed)
                from PyQt5.QtCore import Qt as _Qt
                if hasattr(self.control_panel, 'classAdded'):
                    try:
                        self.control_panel.classAdded.connect(
                            self.on_class_added, _Qt.UniqueConnection
                        )
                    except TypeError:
                        pass  # already connected
                if hasattr(self.control_panel, 'classRemoved'):
                    try:
                        self.control_panel.classRemoved.connect(
                            self.on_class_removed, _Qt.UniqueConnection
                        )
                    except TypeError:
                        pass
                
                # Connect our class config changes to control panel
                self.classConfigChanged.connect(self.on_control_panel_class_refresh)
            
            # Connect enhanced status panel signals
            if self.status_panel:
                if hasattr(self.status_panel, 'statusChanged'):
                    self.status_panel.statusChanged.connect(self.on_status_changed)
                if hasattr(self.status_panel, 'minimapNavigated'):
                    self.status_panel.minimapNavigated.connect(self.on_minimap_navigated)
                if hasattr(self.status_panel, 'minimapClicked'):
                    self.status_panel.minimapClicked.connect(self.on_minimap_clicked)
            
            # Connect bottom navigation signals
            if self.bottom_navigation:
                if hasattr(self.bottom_navigation, 'previousRequested'):
                    self.bottom_navigation.previousRequested.connect(self.on_previous_image_requested)
                if hasattr(self.bottom_navigation, 'nextRequested'):
                    self.bottom_navigation.nextRequested.connect(self.on_next_image_requested)
                if hasattr(self.bottom_navigation, 'navigationChanged'):
                    self.bottom_navigation.navigationChanged.connect(self.on_navigation_changed)
            
            # Connect canvas controls signals
            if self.canvas_controls:
                if hasattr(self.canvas_controls, 'zoomInRequested'):
                    self.canvas_controls.zoomInRequested.connect(self.on_zoom_in_requested)
                if hasattr(self.canvas_controls, 'zoomOutRequested'):
                    self.canvas_controls.zoomOutRequested.connect(self.on_zoom_out_requested)
                if hasattr(self.canvas_controls, 'zoomResetRequested'):
                    self.canvas_controls.zoomResetRequested.connect(self.on_zoom_reset_requested)
                if hasattr(self.canvas_controls, 'goToImageRequested'):
                    self.canvas_controls.goToImageRequested.connect(self.on_goto_image_requested)
                if hasattr(self.canvas_controls, 'canvasToolChanged'):
                    self.canvas_controls.canvasToolChanged.connect(self.on_canvas_tool_changed)
            
            logger.info("Signal connections established for simplified shared modules")
            
        except Exception as e:
            logger.error(f"Failed to setup connections: {e}")
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts (matches functioning annotation system)."""
        try:
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence
            
            logger.info("Setting up keyboard shortcuts...")

            # Clear ALL previously created shortcuts to avoid duplicates across
            # repeated calls (this method is invoked on every Add Class).
            if hasattr(self, '_class_shortcuts'):
                for shortcut in self._class_shortcuts:
                    shortcut.deleteLater()
            self._class_shortcuts = []
            if hasattr(self, '_static_shortcuts'):
                for shortcut in self._static_shortcuts:
                    shortcut.deleteLater()
            self._static_shortcuts = []

            # Class selection shortcuts (dynamic based on num_classes)
            num_shortcuts = min(len(self.class_names), 9)  # Max 9 shortcuts (1-9 keys)
            for i in range(1, num_shortcuts + 1):  # Dynamic range based on actual classes
                if i <= len(self.class_names):
                    shortcut = QShortcut(QKeySequence(str(i)), self)
                    # Create lambda with default parameter to capture current i
                    shortcut.activated.connect(lambda i=i-1: self.on_class_shortcut(i))
                    self._class_shortcuts.append(shortcut)  # Track for later cleanup
                    logger.debug(f"Added class shortcut: {i} -> {self.class_names[i-1]}")

            def _mk(seq, slot):
                sc = QShortcut(QKeySequence(seq), self)
                sc.activated.connect(slot)
                self._static_shortcuts.append(sc)
                return sc

            _mk("Escape", self.on_exit_requested)
            _mk("Ctrl++", self.on_zoom_in_requested)
            _mk("Ctrl+-", self.on_zoom_out_requested)
            _mk("Ctrl+0", self.on_zoom_reset_requested)
            _mk("F1", self.on_help_requested)
            _mk("Right", self.on_next_image_requested)
            _mk("Left", self.on_previous_image_requested)
            _mk("Ctrl+Z", self.on_undo_requested)
            _mk("Ctrl+z", self.on_undo_requested)

            # Overlay shortcuts (G and P) are handled by keyPressEvent/keyReleaseEvent
            # for hold-to-preview behavior

            logger.info("✅ Keyboard shortcuts setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup keyboard shortcuts: {e}")
    
    def add_status_message_with_bottom_sync(self, category: str, message: str, msg_type: str = "info"):
        """Add status message to both status panel and bottom navigation."""
        # Add to status panel
        if self.status_panel:
            self.status_panel.add_status_message(category, message, msg_type)
        
        # Also update bottom navigation action display
        if self.bottom_navigation and hasattr(self.bottom_navigation, 'update_from_status_message'):
            # Format message for bottom display
            formatted_message = f"{category}: {message}"
            self.bottom_navigation.update_from_status_message(formatted_message, msg_type)
    
    def on_class_shortcut(self, class_index: int):
        """Handle class selection shortcut (1-6 keys)."""
        if 0 <= class_index < len(self.class_names):
            logger.info(f"Class shortcut pressed: {class_index + 1} -> {self.class_names[class_index]}")

            # Update control panel class selection
            if self.control_panel and hasattr(self.control_panel, 'select_class'):
                self.control_panel.select_class(class_index)
            elif self.control_panel and hasattr(self.control_panel, '_current_class'):
                self.control_panel._current_class = class_index
                if hasattr(self.control_panel, 'update_statistics'):
                    self.control_panel.update_statistics()

            # Update canvas current class
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_current_class'):
                self.annotation_canvas.set_current_class(class_index)
                # Set focus on canvas so keyboard shortcuts work immediately
                self.annotation_canvas.setFocus()

            # Update status panel
            if self.status_panel:
                self.status_panel.add_status_message("Class", f"Selected: {self.class_names[class_index]}", "info")
    
    def on_undo_requested(self):
        """Handle Ctrl+Z - undo last add/remove action on canvas."""
        try:
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'undo_last_action'):
                ok = self.annotation_canvas.undo_last_action()
                if not ok and self.status_panel:
                    self.status_panel.add_status_message("Undo", "Nothing to undo", "info")
        except Exception as e:
            logger.error(f"Undo failed: {e}")

    def on_exit_requested(self):
        """Handle Escape key - return to mode grid."""
        logger.info("Exit requested via Escape key")
        if self.status_panel:
            self.status_panel.add_status_message("Navigation", "Returning to mode grid...", "info")
        
        # Emit back request if header supports it
        if self.header and hasattr(self.header, 'backRequested'):
            self.header.backRequested.emit()
        else:
            # Fallback: close widget or return to parent
            self.close()
    
    def initialize_session(self):
        """Initialize session data using direct session path."""
        logger.info("=== initialize_session START ===")
        
        # Check if session path is available
        if not self.session_path or not self.session_path.exists():
            logger.warning("❌ No valid session path available")
            if self.status_panel:
                self.status_panel.update_status("No Session", "No session path provided", "warning")
            return
        
        logger.info(f"✅ Using session path: {self.session_path}")
        session_name = self.session_path.name
        
        try:
            # Now we have a valid session_path, continue with initialization
            logger.info(f"Session path: {self.session_path}")
            logger.info(f"Session name: {session_name}")
            
            # Load class configuration from dataset metadata
            class_data = self.get_current_classes()
            if class_data:
                self._apply_class_config(class_data)

                # Initialize control panel with class data
                if self.control_panel and hasattr(self.control_panel, 'update_class_config'):
                    self.control_panel.update_class_config(
                        class_names=class_data['names'],
                        class_colors=class_data['colors']
                    )
                    logger.info("Control panel initialized with session classes")

                # Sync canvas colors so points are drawn with the same palette
                # the control panel shows.
                if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_class_colors'):
                    self.annotation_canvas.set_class_colors(class_data['colors'])
                    logger.info(f"Canvas class_colors synced from metadata ({len(class_data['colors'])} classes)")
            
            # Configure overlay mask paths for ground truth and predictions
            self._configure_overlay_paths()
            
            # Try to get session summary for additional info
            session_summary = None
            if self.session_path:
                try:
                    # Try to read session config for summary info
                    session_config_path = self.session_path / 'config' / 'session_config.json'
                    if session_config_path.exists():
                        import json
                        with open(session_config_path, 'r') as f:
                            session_data = json.load(f)

                        # Create a summary from session config
                        # Use self._current_iteration which was passed to widget constructor
                        session_summary = {
                            'session_name': session_data.get('session_metadata', {}).get('name', session_name),
                            'description': session_data.get('session_metadata', {}).get('description', ''),
                            'created_at': session_data.get('session_metadata', {}).get('created_at', ''),
                            'current_iteration': self._current_iteration
                        }

                        if session_summary.get('session_name'):
                            session_name = session_summary.get('session_name', session_name)
                            logger.info(f"Session summary retrieved from config: {session_summary}")
                    else:
                        # No session config, still create summary with current iteration
                        session_summary = {
                            'current_iteration': self._current_iteration
                        }
                except Exception as e:
                    logger.warning(f"Could not get session summary from config: {e}")
                    # Still set the iteration even if config fails
                    session_summary = {
                        'current_iteration': self._current_iteration
                    }
            
            # Update UI components
            # Update enhanced header with session info
            try:
                self.update_header_session_info(session_name, session_summary)
            except Exception as e:
                logger.warning(f"Could not update enhanced header: {e}")
                
            # Also update header navigation with placeholder info  
            try:
                # For now, use placeholder values since we don't have image navigation yet
                self.update_header_navigation(0, 0, [])
            except Exception as e:
                logger.warning(f"Could not update header navigation: {e}")
            
            # Update status panel
            if self.status_panel:
                self.status_panel.update_status("Session Ready", f"Session: {session_name}", "success")
            # Show session load in both panels
            self.add_status_message_with_bottom_sync("Session", f"Loaded session: {session_name}", "info")
            
            # Add session details if available
            if session_summary:
                status = session_summary.get('status', 'unknown')
                iteration = session_summary.get('current_iteration', 0)
                total_samples = session_summary.get('total_samples', 0)
                if self.status_panel:
                    self.status_panel.add_status_message("Details", f"Status: {status}, Iteration: {iteration}, Samples: {total_samples}", "info")
            
            # CRITICAL: Load image list and first image (same as functioning widget)
            logger.info("Loading image list from session...")
            self.load_image_list()
            
            # Load first image if available
            if self.image_list:
                logger.info(f"Loading first image from {len(self.image_list)} total images")
                self.load_image_by_index(0)
                
                # Update status with image count
                if self.status_panel:
                    self.status_panel.add_status_message("Images", f"Loaded {len(self.image_list)} images", "success")
            else:
                logger.warning("No images found in session")
                if self.status_panel:
                    self.status_panel.add_status_message("Images", "No images found", "warning")
                # Show empty state in canvas
                if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_empty_state'):
                    self.annotation_canvas.show_empty_state("No images available in this session")
            
            logger.info(f"Session initialization completed successfully: {session_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if self.status_panel:
                self.status_panel.update_status("Session Error", f"Failed to initialize: {str(e)}", "error")
                self.status_panel.add_status_message("Error", f"Session init failed: {str(e)}", "error")
    
    def on_annotation_added(self, x: float, y: float, class_id: int, index: int):
        """Handle annotation added event - O(1) operation using canvas-provided data."""
        logger.info(f"Annotation added at ({x}, {y}) with class {class_id}, index {index}")

        # O(1) operation: Canvas provides exact data, no searching needed
        annotation = [int(round(x)), int(round(y)), int(class_id)]

        # Simply append to list - canvas manages its own ordering
        # The index parameter is informational (canvas's internal index)
        self.current_annotations.append(annotation)

        # Update session count cache incrementally
        self.session_total += 1
        if class_id not in self.session_class_totals:
            self.session_class_totals[class_id] = 0
        self.session_class_totals[class_id] += 1

        # Update per-image counts
        if hasattr(self, 'current_image_path') and self.current_image_path:
            image_stem = Path(self.current_image_path).stem
            if image_stem not in self.per_image_counts:
                self.per_image_counts[image_stem] = {'total': 0, 'classes': {}}
            self.per_image_counts[image_stem]['total'] += 1
            if class_id not in self.per_image_counts[image_stem]['classes']:
                self.per_image_counts[image_stem]['classes'][class_id] = 0
            self.per_image_counts[image_stem]['classes'][class_id] += 1

        # Update control panel with cached counts
        self._update_count_display()
        
        # Update both status panel and bottom navigation 
        class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"Class {class_id}"
        self.add_status_message_with_bottom_sync("Canvas", f"Added {class_name} at ({x:.0f}, {y:.0f})", "success")
        
        # Emit signal for backend integration - STANDARDIZED: Array format
        self.annotationChanged.emit("current_image", {"action": "add", "point": annotation})
        
        # CRITICAL FIX: Save annotations immediately
        self.save_current_annotations()
    
    def on_annotation_changed_internal(self, annotation_data: dict):
        """Handle internal annotation changes."""
        logger.info(f"Annotation changed: {annotation_data}")
        self.annotationChanged.emit("current_image", annotation_data)
    
    def on_class_changed(self, class_id: int):
        """Handle class selection change."""
        logger.info(f"Class changed to: {class_id}")
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_current_class'):
            self.annotation_canvas.set_current_class(class_id)
            # Set focus on canvas so keyboard shortcuts work immediately
            self.annotation_canvas.setFocus()
        if self.status_panel:
            self.status_panel.update_component_status("Tools", f"Class {class_id} selected", "info")
    
    def on_clear_requested(self):
        """Handle clear annotations request."""
        logger.info("Clear annotations requested")

        # Update session cache before clearing - subtract current image's counts
        if hasattr(self, 'current_image_path') and self.current_image_path:
            image_stem = Path(self.current_image_path).stem
            if image_stem in self.per_image_counts:
                # Subtract from session totals
                old_counts = self.per_image_counts[image_stem]
                self.session_total = max(0, self.session_total - old_counts['total'])
                for class_id, count in old_counts['classes'].items():
                    if class_id in self.session_class_totals:
                        self.session_class_totals[class_id] = max(0, self.session_class_totals[class_id] - count)
                # Reset per-image counts
                self.per_image_counts[image_stem] = {'total': 0, 'classes': {}}

        # Clear canvas annotations
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'clear_annotations'):
            self.annotation_canvas.clear_annotations()

        # Clear internal annotations list
        self.current_annotations.clear()

        # Update control panel with cached counts
        self._update_count_display()

        # Update status panel
        if self.status_panel:
            self.status_panel.update_status("Ready", "Annotations cleared", "info")
            self.status_panel.add_status_message("System", "All annotations cleared", "info")

        # CRITICAL FIX: Save empty annotations immediately
        self.save_current_annotations()
    
    def on_tool_changed(self, tool_name: str):
        """Handle tool change."""
        logger.info(f"Tool changed to: {tool_name}")
        if self.status_panel:
            self.status_panel.update_component_status("Tools", f"{tool_name} active", "info")
    
    def on_point_size_changed(self, size: int):
        """Handle point size change."""
        logger.info(f"Point size changed to: {size}")
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_point_size'):
            self.annotation_canvas.set_point_size(size)
        if self.status_panel:
            self.status_panel.add_status_message("Display", f"Point size: {size}px", "info")
    
    def on_grid_toggled(self, show_grid: bool):
        """Handle grid toggle."""
        logger.info(f"Grid toggled: {show_grid}")
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_show_grid'):
            self.annotation_canvas.set_show_grid(show_grid)
        if self.status_panel:
            status = "enabled" if show_grid else "disabled"
            self.status_panel.add_status_message("Display", f"Grid {status}", "info")
    
    def on_grid_size_changed(self, grid_size: int):
        """Handle grid size change."""
        logger.info(f"Grid size changed: {grid_size}px")
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_grid_size'):
            self.annotation_canvas.set_grid_size(grid_size)
        if self.status_panel:
            self.status_panel.add_status_message("Display", f"Grid size: {grid_size}px", "info")
    
    def on_image_loaded(self):
        """Handle image loaded event (matches working annotation widget)."""
        # Get current image path from canvas or current state
        current_image_path = ""
        if hasattr(self, 'current_image_path') and self.current_image_path:
            current_image_path = self.current_image_path
        elif (self.annotation_canvas and 
              hasattr(self.annotation_canvas, 'current_image_path') and 
              self.annotation_canvas.current_image_path):
            current_image_path = self.annotation_canvas.current_image_path
        
        logger.info(f"Image loaded: {current_image_path}")
        
        # Update canvas controls with image info
        if self.canvas_controls and current_image_path:
            from pathlib import Path
            filename = Path(current_image_path).name
            self.canvas_controls.update_image_info(filename, self.current_image_index, len(self.image_list))
        
        # Update minimap with new image
        if (self.status_panel and 
            hasattr(self.status_panel, 'update_minimap_image') and 
            self.annotation_canvas and 
            hasattr(self.annotation_canvas, 'original_pixmap')):
            # Get the original pixmap from canvas (not the PIL image)
            original_pixmap = getattr(self.annotation_canvas, 'original_pixmap', None)
            if original_pixmap:
                self.status_panel.update_minimap_image(original_pixmap)
        
        if self.status_panel and current_image_path:
            from pathlib import Path
            filename = Path(current_image_path).name
            
            # Update image info in status panel
            if hasattr(self.status_panel, 'update_image_info'):
                # Try to get image dimensions if available
                if (self.annotation_canvas and 
                    hasattr(self.annotation_canvas, 'current_image') and 
                    self.annotation_canvas.current_image):
                    img = self.annotation_canvas.current_image
                    # Handle both PIL Image and QPixmap
                    if hasattr(img, 'size'):  # PIL Image
                        try:
                            # Try as property first (PIL Image)
                            if callable(img.size):
                                width, height = img.size()
                            else:
                                width, height = img.size
                        except (TypeError, AttributeError):
                            width = height = 0
                    elif hasattr(img, 'width'):  # QPixmap
                        width = img.width()
                        height = img.height()
                    else:
                        width = height = 0
                    
                    self.status_panel.update_image_info(
                        filename, 
                        width, 
                        height, 
                        "PNG/JPG",  # Default format
                        0.0  # Size not calculated
                    )
                else:
                    self.status_panel.update_image_info(filename)
            
            self.status_panel.update_status("Image Loaded", f"Loaded: {filename}", "success")
            self.status_panel.update_component_status("Canvas", "Image ready", "info")
    
    def on_status_changed(self, status_type: str, message: str):
        """Handle status panel changes."""
        logger.info(f"Status changed: {status_type} - {message}")
    
    def on_annotation_removed(self, x: float, y: float, index: int, point_data: list):
        """Handle annotation removed event - O(1) operation using canvas-provided data."""
        logger.info(f"Annotation removed at ({x}, {y}), index {index}, data {point_data}")

        # Get class_id before removing for cache update
        class_id = None
        if 0 <= index < len(self.current_annotations):
            removed = self.current_annotations.pop(index)
            logger.info(f"Removed annotation: {removed}")
            if len(removed) >= 3:
                class_id = int(removed[2])
        else:
            logger.warning(f"Invalid index {index} for removal, list length: {len(self.current_annotations)}")
            # Try to get class_id from point_data if available
            if point_data and len(point_data) >= 3:
                class_id = int(point_data[2])

        # Update session count cache incrementally
        if class_id is not None:
            self.session_total = max(0, self.session_total - 1)
            if class_id in self.session_class_totals:
                self.session_class_totals[class_id] = max(0, self.session_class_totals[class_id] - 1)

            # Update per-image counts
            if hasattr(self, 'current_image_path') and self.current_image_path:
                image_stem = Path(self.current_image_path).stem
                if image_stem in self.per_image_counts:
                    self.per_image_counts[image_stem]['total'] = max(0, self.per_image_counts[image_stem]['total'] - 1)
                    if class_id in self.per_image_counts[image_stem]['classes']:
                        self.per_image_counts[image_stem]['classes'][class_id] = max(0, self.per_image_counts[image_stem]['classes'][class_id] - 1)

        # Update control panel with cached counts
        self._update_count_display()
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Canvas", f"Point removed at ({x:.0f}, {y:.0f})", "info")
        
        # Emit signal for backend integration
        self.annotationChanged.emit("current_image", {"action": "remove", "x": x, "y": y})
        
        # CRITICAL FIX: Save annotations immediately
        self.save_current_annotations()
    
    def on_annotation_moved(self, old_x: float, old_y: float, new_x: float, new_y: float, index: int, point_data: list):
        """Handle annotation moved event - O(1) operation using canvas-provided data."""
        logger.debug(f"Annotation moved from ({old_x}, {old_y}) to ({new_x}, {new_y}), index {index}")
        
        # O(1) operation: Canvas provides exact index and data, no searching needed
        if 0 <= index < len(self.current_annotations):
            self.current_annotations[index][0] = int(round(new_x))  # Update x
            self.current_annotations[index][1] = int(round(new_y))  # Update y
            # Class stays the same: self.current_annotations[index][2] unchanged
        else:
            logger.warning(f"Invalid index {index} for move, list length: {len(self.current_annotations)}")
        
        # Emit signal for backend integration (real-time updates)
        self.annotationChanged.emit("current_image", {"action": "move", "old_x": old_x, "old_y": old_y, "new_x": new_x, "new_y": new_y})
        
        # No saving here - wait for drag end signal
    
    def on_annotation_drag_ended(self, x: float, y: float, class_id: int, index: int):
        """Handle annotation drag ended event - O(1) operation, save when complete."""
        logger.info(f"Drag completed for point at ({x}, {y}) class {class_id}, index {index}")
        
        # Update status panel with completion message
        if self.status_panel:
            self.status_panel.add_status_message("Canvas", f"Point moved to ({x:.0f}, {y:.0f})", "success")
        
        # PERFORMANCE: Save annotations only once when drag is complete 
        self.save_current_annotations()
    
    def save_current_annotations(self):
        """Save current annotations to JSON file immediately."""
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            logger.warning("No current image path for saving annotations")
            return
            
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            # Get image info
            image_path = Path(self.current_image_path)
            image_stem = image_path.stem
            
            # Determine save location - use detected iteration
            if hasattr(self, 'session_path') and self.session_path:
                # Use the dynamically detected iteration
                current_iteration = getattr(self, '_current_iteration', 0)

                # Try actual structure first, then fallback
                possible_dirs = [
                    Path(self.session_path) / f"iteration_{current_iteration}" / "annotations",
                    Path(self.session_path) / "iterations" / f"iteration_{current_iteration}" / "annotations" / "json",
                ]

                annotations_dir = None
                for dir_path in possible_dirs:
                    if dir_path.exists():
                        annotations_dir = dir_path
                        break

                # If none exist, create with the correct structure
                if not annotations_dir:
                    annotations_dir = Path(self.session_path) / f"iteration_{current_iteration}" / "annotations"
            else:
                # Fallback to annotations folder next to image
                annotations_dir = image_path.parent / "annotations"
                current_iteration = 0

            annotations_dir.mkdir(parents=True, exist_ok=True)
            annotation_file = annotations_dir / f"{image_stem}.json"


            # Direct conversion to unified format - 2x more efficient
            annotations = [[int(round(ann[0])), int(round(ann[1])), int(ann[2])]
                          for ann in self.current_annotations]

            # Get image info for metadata
            image_info = self._get_current_image_info()

            # Create annotation data in unified format (without annotations for custom formatting)
            annotation_data = {
                "format_version": "1.0",
                "image": {
                    "name": f"{image_stem}.png",
                    "width": image_info["width"],
                    "height": image_info["height"]
                },
                "iteration": current_iteration,
                "created_at": datetime.now().isoformat() + "Z"
            }

            # Custom JSON formatting to keep each annotation on a single line
            json_str = json.dumps(annotation_data, indent=2)
            # Remove closing brace and add annotations array
            json_str = json_str.rstrip('\n}')
            json_str += ',\n  "annotations": [\n'
            for i, annotation in enumerate(annotations):
                comma = ',' if i < len(annotations) - 1 else ''
                json_str += f'    {json.dumps(annotation)}{comma}\n'
            json_str += '  ]\n}'

            # Save to file
            with open(annotation_file, 'w') as f:
                f.write(json_str)
                
            logger.info(f"Saved {len(annotations)} annotations to {annotation_file} in unified format")
            
            # Update status if available
            if hasattr(self, 'status_panel') and self.status_panel:
                self.status_panel.add_status_message("Save", f"Saved {len(annotations)} points to {annotation_file.name}", "success")
            
        except Exception as e:
            logger.error(f"Failed to save annotations: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Show error in status if available
            if hasattr(self, 'status_panel') and self.status_panel:
                self.status_panel.add_status_message("Save", f"Failed to save annotations: {str(e)}", "error")
    
    def _get_current_image_info(self):
        """Get current image dimensions for annotation metadata."""
        try:
            # Try to get dimensions from canvas first
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'get_image_size'):
                width, height = self.annotation_canvas.get_image_size()
                return {"width": width, "height": height}
            elif hasattr(self, 'current_image_path') and self.current_image_path:
                # Fallback: read from image file
                import imageio
                img = imageio.imread(self.current_image_path)
                height, width = img.shape[:2]
                return {"width": int(width), "height": int(height)}
            else:
                # Last fallback: use session default (most images are 512x512)
                logger.warning("Could not get image dimensions, using default 512x512")
                return {"width": 512, "height": 512}
        except Exception as e:
            logger.warning(f"Error getting image info: {e}, using default 512x512")
            return {"width": 512, "height": 512}

    def on_view_changed(self, zoom: float, pan_x: float, pan_y: float):
        """Handle view changes (zoom/pan)."""
        logger.debug(f"View changed: zoom={zoom:.2f}, pan=({pan_x:.1f}, {pan_y:.1f})")
        
        # Update canvas controls bar zoom display
        if self.canvas_controls:
            self.canvas_controls.update_zoom_display(zoom)
        
        # Update minimap view rectangle
        if (self.status_panel and 
            hasattr(self.status_panel, 'update_minimap_view') and 
            self.annotation_canvas):
            canvas_size = self.annotation_canvas.size()
            self.status_panel.update_minimap_view(canvas_size, zoom, int(pan_x), int(pan_y))
        
        # Update status panel with zoom info
        if self.status_panel:
            zoom_percent = int(zoom * 100)
            self.status_panel.add_status_message("View", f"Zoom: {zoom_percent}%", "info")
    
    def on_mouse_coordinates(self, x: int, y: int):
        """Handle mouse coordinate updates with enhanced pixel information."""
        # Get additional pixel information if available
        rgb_values = None
        gt_value = None  
        pred_value = None
        
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'get_pixel_info'):
            try:
                logger.debug(f"Calling get_pixel_info({x}, {y}) on canvas")
                pixel_info = self.annotation_canvas.get_pixel_info(x, y)
                logger.debug(f"Got pixel info: {pixel_info}")
                if pixel_info:
                    rgb_values = pixel_info.get('rgb')
                    gt_value = pixel_info.get('gt')
                    pred_value = pixel_info.get('pred')
                    logger.debug(f"Extracted values - RGB: {rgb_values}, GT: {gt_value}, Pred: {pred_value}")
            except Exception as e:
                logger.error(f"Could not get enhanced pixel info: {e}")
        else:
            logger.debug(f"Canvas: {self.annotation_canvas}, has method: {hasattr(self.annotation_canvas, 'get_pixel_info') if self.annotation_canvas else False}")
        
        # Update bottom navigation with enhanced pixel display
        if self.bottom_navigation and hasattr(self.bottom_navigation, 'update_pixel_info'):
            self.bottom_navigation.update_pixel_info(x, y, rgb_values, gt_value, pred_value)
        elif self.bottom_navigation and hasattr(self.bottom_navigation, 'update_coordinates'):
            # Fallback to simple coordinates if enhanced method not available
            self.bottom_navigation.update_coordinates(x, y)
        
        # Update status panel or footer with current coordinates
        if hasattr(self, 'footer_status'):
            self.footer_status.setText(f"Coordinates: ({x}, {y})")
        
        # Could also update header status
        if hasattr(self, 'header_status'):
            self.header_status.setText(f"Mouse: ({x}, {y})")
    
    def on_navigation_changed(self, current_index: int, total_count: int):
        """Handle navigation state changes."""
        logger.debug(f"Navigation changed: {current_index + 1} of {total_count}")
        
        # Update current navigation state
        self.current_image_index = current_index
        
        # Update header navigation if available
        self.update_header_navigation(current_index, total_count, self.image_list)
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Navigation", f"Image {current_index + 1} of {total_count}", "info")
    
    def on_rgb_channel_changed(self, channel: str, mapping: int):
        """Handle RGB channel mapping changes."""
        logger.info(f"RGB channel {channel} mapped to channel {mapping}")
        
        # Update canvas RGB channel mapping if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_rgb_channel_mapping'):
            self.annotation_canvas.set_rgb_channel_mapping(channel, mapping)
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Display", f"RGB {channel.upper()} → Channel {mapping}", "info")
    
    def on_overlay_toggled(self, overlay_type: str, enabled: bool):
        """Handle overlay toggle changes."""
        logger.info(f"Overlay {overlay_type} {'enabled' if enabled else 'disabled'}")
        
        # Update canvas overlay if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_overlay_enabled'):
            self.annotation_canvas.set_overlay_enabled(overlay_type, enabled)
        
        # Update status panel
        if self.status_panel:
            status = "enabled" if enabled else "disabled"
            self.status_panel.add_status_message("Display", f"{overlay_type} overlay {status}", "info")
    
    def on_overlay_opacity_changed(self, overlay_type: str, opacity: float):
        """Handle overlay opacity changes (matches functioning system)."""
        logger.info(f"Overlay {overlay_type} opacity changed to {opacity:.2f}")
        
        # Update canvas overlay opacity if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_overlay_opacity'):
            self.annotation_canvas.set_overlay_opacity(overlay_type, opacity)
        
        # Update status panel
        if self.status_panel:
            percentage = int(opacity * 100)
            self.status_panel.add_status_message("Display", f"{overlay_type} opacity: {percentage}%", "info")
    
    def on_pixel_info_toggled(self, enabled: bool):
        """Handle pixel info toggle changes."""
        logger.info(f"Pixel info {'enabled' if enabled else 'disabled'}")

        # Update canvas pixel info if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_pixel_info_enabled'):
            self.annotation_canvas.set_pixel_info_enabled(enabled)

        # Update status panel
        if self.status_panel:
            status = "enabled" if enabled else "disabled"
            self.status_panel.add_status_message("Display", f"Pixel info {status}", "info")

    def on_halo_toggled(self, enabled: bool):
        """Handle halo (highlight new points) toggle."""
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_show_new_halo'):
            self.annotation_canvas.set_show_new_halo(enabled)

    def on_render_mode_changed(self, mode: str):
        """Handle render mode combobox change."""
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_render_mode'):
            self.annotation_canvas.set_render_mode(mode)
    
    def on_class_added(self, class_name: str, color: tuple):
        """Handle class addition from control panel."""
        logger.info(f"Class added: {class_name} with color {color}")
        
        # Get current classes and add new one
        current_classes = self.get_current_classes()
        if current_classes:
            current_classes['names'].append(class_name)
            current_classes['colors'].append(color)
            current_classes['num_classes'] += 1
            
            # Update everything through centralized method
            self.update_classes(current_classes)
            
            # Update status panel
            if self.status_panel:
                self.status_panel.add_status_message("Classes", f"Added class: {class_name}", "success")
    
    def on_class_removed(self, class_id: int):
        """Handle class removal from control panel."""
        logger.info(f"Class removed: ID {class_id}")
        
        # Get current classes and remove specified one
        current_classes = self.get_current_classes()
        if current_classes and 0 <= class_id < len(current_classes['names']):
            removed_name = current_classes['names'][class_id]
            
            # Remove from lists
            current_classes['names'].pop(class_id)
            current_classes['colors'].pop(class_id)
            current_classes['num_classes'] -= 1
            
            # Update everything through centralized method
            self.update_classes(current_classes)
            
            # Update status panel
            if self.status_panel:
                self.status_panel.add_status_message("Classes", f"Removed class: {removed_name}", "warning")
    
    def on_control_panel_class_refresh(self, class_data):
        """Handle control panel refresh when classes change."""
        if self.control_panel and hasattr(self.control_panel, 'update_class_config'):
            self.control_panel.update_class_config(
                class_names=class_data['names'],
                class_colors=class_data['colors']
            )
            logger.info("Control panel class list refreshed")
    
    def on_zoom_in_requested(self):
        """Handle zoom in request from canvas controls."""
        logger.debug("Zoom in requested from canvas controls")
        
        # Apply zoom to canvas if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'zoom_in'):
            success = self.annotation_canvas.zoom_in()
            if success and hasattr(self.annotation_canvas, 'zoom_factor'):
                # Update controls bar zoom display
                if self.canvas_controls:
                    self.canvas_controls.update_zoom_display(self.annotation_canvas.zoom_factor)
                
                # Update status panel
                if self.status_panel:
                    zoom_percent = int(self.annotation_canvas.zoom_factor * 100)
                    self.status_panel.add_status_message("Canvas", f"Zoomed in to {zoom_percent}%", "info")
    
    def on_zoom_out_requested(self):
        """Handle zoom out request from canvas controls."""
        logger.debug("Zoom out requested from canvas controls")
        
        # Apply zoom to canvas if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'zoom_out'):
            success = self.annotation_canvas.zoom_out()
            if success and hasattr(self.annotation_canvas, 'zoom_factor'):
                # Update controls bar zoom display
                if self.canvas_controls:
                    self.canvas_controls.update_zoom_display(self.annotation_canvas.zoom_factor)
                
                # Update status panel
                if self.status_panel:
                    zoom_percent = int(self.annotation_canvas.zoom_factor * 100)
                    self.status_panel.add_status_message("Canvas", f"Zoomed out to {zoom_percent}%", "info")
    
    def on_zoom_reset_requested(self):
        """Handle zoom reset (fit) request from canvas controls."""
        logger.debug("Zoom reset (fit) requested from canvas controls")
        
        # Apply zoom reset to canvas if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'reset_zoom'):
            success = self.annotation_canvas.reset_zoom()
            if success and hasattr(self.annotation_canvas, 'zoom_factor'):
                # Update controls bar zoom display
                if self.canvas_controls:
                    self.canvas_controls.update_zoom_display(self.annotation_canvas.zoom_factor)
                
                # Update status panel
                if self.status_panel:
                    zoom_percent = int(self.annotation_canvas.zoom_factor * 100)
                    self.status_panel.add_status_message("Canvas", f"Zoom reset to fit ({zoom_percent}%)", "info")
    
    def on_canvas_tool_changed(self, tool_name: str):
        """Handle canvas tool change from controls."""
        logger.info(f"Canvas tool changed to: {tool_name}")
        
        # Update canvas tool if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_current_tool'):
            self.annotation_canvas.set_current_tool(tool_name)
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Tools", f"Canvas tool: {tool_name}", "info")
    
    def on_minimap_navigated(self, pan_x: int, pan_y: int):
        """Handle minimap navigation from status panel."""
        logger.info(f"Minimap navigation: pan=({pan_x}, {pan_y})")
        
        # Update canvas pan if available
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_pan_offset'):
            self.annotation_canvas.set_pan_offset(pan_x, pan_y)
            
            # Force canvas update
            if hasattr(self.annotation_canvas, 'update'):
                self.annotation_canvas.update()
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Navigation", f"Minimap navigation: ({pan_x}, {pan_y})", "info")
    
    def on_minimap_clicked(self, image_x: float, image_y: float):
        """Handle minimap click navigation."""
        logger.info(f"Minimap clicked at image coordinates: ({image_x:.0f}, {image_y:.0f})")
        
        # Navigate canvas to clicked position
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_pan_offset'):
            # Calculate pan offset to center on clicked position
            # Get current widget/viewport size
            widget_rect = self.annotation_canvas.rect()
            center_x = widget_rect.width() // 2
            center_y = widget_rect.height() // 2
            
            # Calculate pan offset needed to center clicked point
            pan_x = int(image_x - center_x)
            pan_y = int(image_y - center_y)
            
            logger.info(f"Navigating to pan offset: ({pan_x}, {pan_y})")
            self.annotation_canvas.set_pan_offset(pan_x, pan_y)
            
            # Force canvas update
            if hasattr(self.annotation_canvas, 'update'):
                self.annotation_canvas.update()
        
        # Update status panel with navigation feedback
        if self.status_panel:
            self.status_panel.add_status_message("Navigation", f"Navigated to ({image_x:.0f}, {image_y:.0f})", "info")
    
    def on_canvas_rgb_channels_changed(self, r: int, g: int, b: int):
        """Handle RGB channel mapping changes from canvas."""
        logger.info(f"Canvas RGB channels changed: R={r}, G={g}, B={b}")
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Display", f"RGB channels: R→{r}, G→{g}, B→{b}", "info")
    
    def on_canvas_overlay_toggled(self, overlay_type: str, enabled: bool):
        """Handle overlay toggle from canvas."""
        logger.info(f"Canvas overlay {overlay_type} {'enabled' if enabled else 'disabled'}")
        
        # Update status panel
        if self.status_panel:
            status = "enabled" if enabled else "disabled"
            self.status_panel.add_status_message("Display", f"{overlay_type} overlay {status}", "info")
    
    def load_image(self, image_path: str):
        """Load image using shared modules."""
        if not SHARED_MODULES_AVAILABLE or not self.annotation_canvas:
            logger.warning("Cannot load image - shared modules not available")
            return False
        
        try:
            success = self.annotation_canvas.load_image(image_path)
            if success:
                logger.info(f"Image loaded successfully: {Path(image_path).name}")
                # CRITICAL FIX: Set current_image_path for annotation saving
                self.current_image_path = image_path
                logger.info(f"Set current_image_path = {self.current_image_path}")
                # Clear undo stack so Ctrl+Z only affects current image edits
                if hasattr(self.annotation_canvas, 'clear_undo_stack'):
                    self.annotation_canvas.clear_undo_stack()
            return success
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return False
    
    def showMaximized(self):
        """Show widget maximized."""
        try:
            logger.info("showMaximized() called")
            super().showMaximized()
            logger.info(f"Widget maximized - visible: {self.isVisible()}, geometry: {self.geometry()}")
            
            # Simple status update without complex logic
            if hasattr(self, 'status_panel') and self.status_panel:
                self.status_panel.update_status("Widget Shown", "Interface ready for use", "success")
                logger.info("Status panel updated successfully")
            
            # Update header status if available
            if hasattr(self, 'header_status'):
                self.header_status.setText("Active")
                logger.info("Header status updated")
                
            # Update footer status if available
            if hasattr(self, 'footer_status'):
                self.footer_status.setText("Shared Modules Ready")
                logger.info("Footer status updated")
                
            logger.info("showMaximized() completed successfully")
            
        except Exception as e:
            logger.error(f"Error in showMaximized(): {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Still try to show the widget
            try:
                super().showMaximized()
            except:
                logger.error("Failed to show widget even with fallback")
    
    # Enhanced Header Bar event handlers
    
    def on_back_requested(self):
        """Handle back button request from header."""
        logger.info("Back button requested - emitting modeExitRequested")
        self.modeExitRequested.emit()
    
    def on_help_requested(self):
        """Handle help button request from header - show comprehensive help dialog."""
        logger.info("Help requested from header")
        self.show_help_dialog()
    
    def on_previous_image_requested(self):
        """Handle previous image request from navigation."""
        if not self.image_list:
            logger.warning("No images available for navigation")
            return
            
        # Circular navigation - wrap to last image if at beginning
        new_index = self.current_image_index - 1
        if new_index < 0:
            new_index = len(self.image_list) - 1
            
        logger.info(f"Previous image requested: {new_index + 1}/{len(self.image_list)}")
        self.load_image_by_index(new_index)
    
    def on_next_image_requested(self):
        """Handle next image request from navigation."""
        if not self.image_list:
            logger.warning("No images available for navigation")
            return
            
        # Circular navigation - wrap to first image if at end
        new_index = self.current_image_index + 1
        if new_index >= len(self.image_list):
            new_index = 0
            
        logger.info(f"Next image requested: {new_index + 1}/{len(self.image_list)}")
        self.load_image_by_index(new_index)

    def keyPressEvent(self, event):
        """Handle key press events for overlay toggle shortcuts."""
        from PyQt5.QtCore import Qt
        key = event.key()

        # P key - temporarily toggle prediction overlay while held
        if key == Qt.Key_P and not event.isAutoRepeat():
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_prediction_overlay'):
                if not hasattr(self, '_pred_overlay_original_state'):
                    self._pred_overlay_original_state = self.annotation_canvas.show_prediction_overlay
                    new_state = not self._pred_overlay_original_state
                    self.annotation_canvas.set_overlay_enabled("prediction", new_state)
                    logger.info(f"Prediction overlay preview: {new_state}")
            return

        # G key - temporarily toggle ground truth overlay while held
        if key == Qt.Key_G and not event.isAutoRepeat():
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_gt_overlay'):
                if not hasattr(self, '_gt_overlay_original_state'):
                    self._gt_overlay_original_state = self.annotation_canvas.show_gt_overlay
                    new_state = not self._gt_overlay_original_state
                    self.annotation_canvas.set_overlay_enabled("ground_truth", new_state)
                    logger.info(f"Ground truth overlay preview: {new_state}")
            return

        # Pass other keys to parent
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Handle key release events to restore overlay states."""
        from PyQt5.QtCore import Qt
        key = event.key()

        # P key released - restore prediction overlay to original state
        if key == Qt.Key_P and not event.isAutoRepeat():
            if hasattr(self, '_pred_overlay_original_state'):
                self.annotation_canvas.set_overlay_enabled("prediction", self._pred_overlay_original_state)
                logger.info(f"Prediction overlay restored: {self._pred_overlay_original_state}")
                delattr(self, '_pred_overlay_original_state')
            return

        # G key released - restore ground truth overlay to original state
        if key == Qt.Key_G and not event.isAutoRepeat():
            if hasattr(self, '_gt_overlay_original_state'):
                self.annotation_canvas.set_overlay_enabled("ground_truth", self._gt_overlay_original_state)
                logger.info(f"Ground truth overlay restored: {self._gt_overlay_original_state}")
                delattr(self, '_gt_overlay_original_state')
            return

        # Pass other keys to parent
        super().keyReleaseEvent(event)

    def on_goto_image_requested(self, target_index=None):
        """Handle go-to image request from navigation."""
        if not self.image_list:
            logger.warning("No images available for navigation")
            return
            
        if target_index is None:
            # Show input dialog
            from PyQt5.QtWidgets import QInputDialog
            max_num = len(self.image_list)
            current_num = self.current_image_index + 1
            
            num, ok = QInputDialog.getInt(
                self, 
                "Go to Image", 
                f"Enter image number (1-{max_num}):",
                current_num,
                1, 
                max_num
            )
            
            if not ok:
                return
                
            target_index = num - 1  # Convert to 0-based index
        
        if 0 <= target_index < len(self.image_list):
            logger.info(f"Go-to image requested: {target_index + 1}/{len(self.image_list)}")
            self.load_image_by_index(target_index)
        else:
            logger.warning(f"Invalid go-to image index: {target_index}")
    
    def update_header_session_info(self, session_name: str, session_data: dict = None):
        """Update header with session information."""
        if hasattr(self.header, 'update_session_info'):
            self.header.update_session_info(session_name, session_data)
            logger.debug(f"Header session info updated: {session_name}")
    
    def update_header_navigation(self, current_index: int, total_images: int, image_list: list = None):
        """Update header with navigation state."""
        if hasattr(self.header, 'update_navigation_state'):
            self.header.update_navigation_state(current_index, total_images, image_list)
            logger.debug(f"Header navigation updated: {current_index + 1} of {total_images}")
    
    def closeEvent(self, event):
        """Handle close event."""
        logger.info("Shared modules annotation widget close event received")
        logger.info(f"Event type: {event.type()}")
        logger.info("Widget is being closed - emitting modeExitRequested signal")
        self.modeExitRequested.emit()
        event.accept()
    
    # CRITICAL: Add missing image loading methods from functioning system
    def load_image_list(self):
        """Load the list of images from session - CRITICAL METHOD MISSING FROM MODULAR SYSTEM."""
        logger.info(f"session_path is None: {self.session_path is None}")
        
        # Ensure overlay paths are configured when loading images
        if self.session_path and hasattr(self, 'annotation_canvas') and self.annotation_canvas:
            self._configure_overlay_paths()
        
        if not self.session_path:
            logger.warning("No session path available for loading images")
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_empty_state'):
                self.annotation_canvas.show_empty_state("No session loaded")
            return
        
        logger.info(f"Session path type: {type(self.session_path)}")
        logger.info(f"Session path exists: {self.session_path.exists()}")

        # Try to read image path from metadata first
        images_dir = None
        metadata_path = self.session_path / "config" / "dataset_metadata.json"
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                train_images_path = metadata.get('paths', {}).get('train_images', '')
                if train_images_path:
                    # Path could be relative to project root
                    images_dir = Path(train_images_path)
                    if not images_dir.is_absolute():
                        # Try relative to project root (parent of session path's parent)
                        project_root = self.session_path.parent.parent
                        images_dir = project_root / train_images_path
                    logger.info(f"Got images path from metadata: {images_dir}")
            except Exception as e:
                logger.warning(f"Failed to read metadata: {e}")

        # Fallback to hardcoded paths
        if not images_dir or not images_dir.exists():
            fallback_paths = [
                self.session_path / "data" / "dataset" / "train" / "images",
                self.session_path / "images",
            ]
            for path in fallback_paths:
                if path.exists():
                    images_dir = path
                    break
            else:
                images_dir = fallback_paths[0]  # Use first for error message

        logger.info(f"Looking for images in: {images_dir}")
        logger.info(f"Images directory exists: {images_dir.exists()}")

        if not images_dir.exists():
            logger.warning(f"Images directory not found: {images_dir}")

            if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_empty_state'):
                self.annotation_canvas.show_empty_state("No images found in session")
            return
            
        # Get all image files (PNG, TIF, TIFF) and sort numerically
        image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.tif")) + list(images_dir.glob("*.tiff"))

        # Sort by numeric value of filename (0.png, 1.png, ..., 10.png, etc.)
        def numeric_sort_key(path):
            try:
                return int(path.stem)
            except ValueError:
                return float('inf')  # Put non-numeric files at the end

        image_files.sort(key=numeric_sort_key)

        # Optional filter: if env var FILTER_FRAMES_FILE points to a text file
        # listing frame stems (one per line), keep only those frames.
        # No-op when env var is unset → preserves default behavior.
        import os as _os
        ff = _os.environ.get('FILTER_FRAMES_FILE')
        if ff and Path(ff).exists():
            keep = set(Path(ff).read_text().split())
            n_before = len(image_files)
            image_files = [p for p in image_files if p.stem in keep]
            logger.info(f"FILTER_FRAMES_FILE active: kept {len(image_files)}/{n_before} frames")

        self.image_list = [str(path) for path in image_files]
        logger.info(f"Loaded {len(self.image_list)} images from session")
        
        if self.image_list:
            logger.info(f"First image: {Path(self.image_list[0]).name}")
            logger.info(f"Last image: {Path(self.image_list[-1]).name}")
            
            # NOTE: First image loading is now handled by initialize_session to avoid duplication
            # self.load_image_by_index(0)  # Removed to prevent duplicate loading
            
            # Update all navigation components
            if self.bottom_navigation:
                self.bottom_navigation.update_navigation_state(0, len(self.image_list), self.image_list)
            
            if self.canvas_controls:
                self.canvas_controls.update_navigation_state(0, len(self.image_list), self.image_list)
                
            if self.header and hasattr(self.header, 'update_navigation_state'):
                self.header.update_navigation_state(0, len(self.image_list), self.image_list)
                
            # Update progress tracking
            if self.status_panel and hasattr(self.status_panel, 'update_progress'):
                self.status_panel.update_progress(0, len(self.image_list))

            # Initialize session count cache
            self._initialize_session_counts()
        else:
            logger.warning("No images found in session")
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'show_empty_state'):
                self.annotation_canvas.show_empty_state("No images found in session")

    def _get_current_iteration_and_annotations_dir(self):
        """Find the current iteration and its annotations directory.

        Uses self._current_iteration if set, otherwise detects the latest.

        Returns:
            Tuple[int, Path or None]: (iteration_number, annotations_dir_path)
        """
        if not self.session_path:
            return 0, None

        # Use the iteration set in __init__ if provided (including 0).
        if hasattr(self, '_current_iteration') and self._current_iteration is not None and self._current_iteration >= 0:
            current_iteration = self._current_iteration
            iteration_path = self.session_path / f"iteration_{current_iteration}"
            if iteration_path.exists():
                logger.info(f"Using provided iteration {current_iteration}")
            else:
                logger.warning(f"Provided iteration {current_iteration} not found, detecting latest")
                current_iteration = None
        else:
            current_iteration = None

        # Auto-detect if not set or not found
        if current_iteration is None:
            # Find all iteration folders
            iteration_dirs = []
            for item in self.session_path.iterdir():
                if item.is_dir() and item.name.startswith('iteration_'):
                    try:
                        iter_num = int(item.name.split('_')[1])
                        iteration_dirs.append((iter_num, item))
                    except (ValueError, IndexError):
                        continue

            if not iteration_dirs:
                logger.warning(f"No iteration folders found in {self.session_path}")
                return 0, None

            # Get the latest (highest numbered) iteration
            iteration_dirs.sort(key=lambda x: x[0], reverse=True)
            current_iteration, iteration_path = iteration_dirs[0]
        else:
            iteration_path = self.session_path / f"iteration_{current_iteration}"

        # Find annotations directory within the iteration
        possible_annotation_paths = [
            iteration_path / "annotations",  # Your actual structure
            iteration_path / "annotations" / "json",  # Alternative structure
        ]

        annotations_dir = None
        for path in possible_annotation_paths:
            if path.exists():
                annotations_dir = path
                break

        if not annotations_dir:
            logger.warning(f"No annotations directory found in {iteration_path}")

        logger.info(f"Using iteration {current_iteration}, annotations dir: {annotations_dir}")
        return current_iteration, annotations_dir

    def _initialize_session_counts(self):
        """Initialize session count cache by scanning all annotation JSON files.

        This is called once at startup and provides O(1) access to counts thereafter.
        """
        if not self.session_path:
            return

        # Reset counts
        self.session_total = 0
        self.session_class_totals = {i: 0 for i in range(self.num_classes)} if self.num_classes > 0 else {}
        self.per_image_counts = {}

        # Get current iteration and annotations directory
        self._current_iteration, annotations_dir = self._get_current_iteration_and_annotations_dir()

        if not annotations_dir:
            logger.warning(f"No annotations directory found in {self.session_path}")
            return

        logger.info(f"Initializing session counts from: {annotations_dir}")

        # Scan all JSON files
        json_files = list(annotations_dir.glob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                annotations = data.get("annotations", [])
                image_stem = json_file.stem

                image_total = len(annotations)
                image_classes = {}

                for ann in annotations:
                    if len(ann) >= 3:
                        class_id = int(ann[2])
                        # Update session totals
                        if class_id not in self.session_class_totals:
                            self.session_class_totals[class_id] = 0
                        self.session_class_totals[class_id] += 1
                        # Update per-image counts
                        image_classes[class_id] = image_classes.get(class_id, 0) + 1

                self.session_total += image_total
                self.per_image_counts[image_stem] = {
                    'total': image_total,
                    'classes': image_classes
                }

            except Exception as e:
                logger.warning(f"Failed to load annotation counts from {json_file}: {e}")

        logger.info(f"Session counts initialized: {self.session_total} total points across {len(json_files)} files")
        logger.info(f"Per-class totals: {self.session_class_totals}")

        # Update control panel with initial counts (no current image yet, so empty)
        if self.control_panel:
            if hasattr(self.control_panel, 'update_class_statistics'):
                self.control_panel.update_class_statistics({}, self.session_class_totals)

    def _update_count_display(self):
        """Update the control panel and status panel with current counts from cache."""
        current_count = len(self.current_annotations) if self.current_annotations else 0

        # Update control panel point counts
        if self.control_panel and hasattr(self.control_panel, 'update_point_counts'):
            self.control_panel.update_point_counts(current_count, self.session_total)

        # Calculate current image class counts
        current_class_counts = {}
        if self.current_annotations:
            for ann in self.current_annotations:
                if len(ann) >= 3:
                    class_id = int(ann[2])
                    current_class_counts[class_id] = current_class_counts.get(class_id, 0) + 1

        # Update control panel class statistics
        if self.control_panel and hasattr(self.control_panel, 'update_class_statistics'):
            self.control_panel.update_class_statistics(current_class_counts, self.session_class_totals)

        # Update status panel class counts (right side panel with Img/Total columns)
        if self.status_panel and hasattr(self.status_panel, 'update_class_counts'):
            self.status_panel.update_class_counts(current_class_counts, self.session_class_totals)

        # Update status panel overall counts
        if self.status_panel:
            if hasattr(self.status_panel, 'current_image_count_label') and self.status_panel.current_image_count_label:
                self.status_panel.current_image_count_label.setText(f"📍 {current_count}")
            if hasattr(self.status_panel, 'annotation_count_label') and self.status_panel.annotation_count_label:
                self.status_panel.annotation_count_label.setText(f"🎯 {self.session_total}")

    def load_image_by_index(self, index: int):
        """Load image by index - CRITICAL METHOD MISSING FROM MODULAR SYSTEM."""
        logger.info(f"self.image_list = {self.image_list}")
        logger.info(f"len(self.image_list) = {len(self.image_list) if self.image_list else 'image_list is None'}")
        logger.info(f"self.annotation_canvas = {self.annotation_canvas}")
        logger.info(f"canvas has load_image: {hasattr(self.annotation_canvas, 'load_image') if self.annotation_canvas else 'canvas is None'}")
        
        if not self.image_list or not (0 <= index < len(self.image_list)):
            logger.warning(f"Invalid image index: {index} (total images: {len(self.image_list)})")
            return False
            
        self.current_image_index = index
        image_path = self.image_list[index]
        
        logger.info(f"Loading image by index {index}: {Path(image_path).name}")
        logger.info(f"Full image path: {image_path}")
        logger.info(f"Image path exists: {Path(image_path).exists()}")
        
        # Load image in canvas (same as functioning system)
        success = False
        if self.annotation_canvas and hasattr(self.annotation_canvas, 'load_image'):
            logger.info("Calling annotation_canvas.load_image...")
            success = self.annotation_canvas.load_image(image_path)
            logger.info(f"Canvas load_image result: {success}")
        else:
            logger.warning("Cannot load image - annotation_canvas not available or missing load_image method")
        
        if success:
            logger.info(f"Image loaded successfully: {Path(image_path).name}")
            
            # CRITICAL FIX: Set current_image_path for annotation saving
            self.current_image_path = image_path
            logger.info(f"Set current_image_path = {self.current_image_path}")
            
            # Update control panel (same as functioning system) 
            if self.control_panel and hasattr(self.control_panel, 'update_navigation_state'):
                self.control_panel.update_navigation_state(index, len(self.image_list), self.image_list)
                
            # Update status panel with progress (same as functioning system)
            if self.status_panel and hasattr(self.status_panel, 'update_progress'):
                self.status_panel.update_progress(index, len(self.image_list))
            
            # Update modular navigation components (same as functioning system)
            if self.bottom_navigation:
                self.bottom_navigation.update_navigation_state(index, len(self.image_list), self.image_list)
                
            if self.canvas_controls:
                # Update both navigation and image info
                self.canvas_controls.update_navigation_state(index, len(self.image_list), self.image_list)
                filename = Path(image_path).name
                self.canvas_controls.update_image_info(filename, index, len(self.image_list))
            
            # Get and update image info (same as functioning system)
            filename = Path(image_path).name
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    format_str = img.format
                    
                if self.status_panel and hasattr(self.status_panel, 'update_image_info'):
                    # Calculate file size
                    import os
                    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
                    self.status_panel.update_image_info(filename, width, height, format_str, file_size_mb)
                    
            except Exception as e:
                logger.warning(f"Could not get image info: {e}")
                if self.status_panel and hasattr(self.status_panel, 'update_image_info'):
                    self.status_panel.update_image_info(filename)
                    
            # Update header navigation
            if self.header and hasattr(self.header, 'update_navigation_state'):
                self.header.update_navigation_state(index, len(self.image_list), self.image_list)
                
            # Load annotations for this image (same as functioning system)
            image_stem = Path(image_path).stem  
            self.load_image_annotations(image_stem)
            
            # Status update to both panels
            self.add_status_message_with_bottom_sync("Navigation", f"Loaded image {index + 1}/{len(self.image_list)}: {filename}", "success")
                
            logger.info(f"Successfully loaded and updated UI for image: {filename}")
            return True
        else:
            logger.error(f"Failed to load image: {Path(image_path).name}")
            if self.status_panel:
                self.status_panel.add_status_message("Error", f"Failed to load image: {Path(image_path).name}", "error")
            return False
    
    def load_image_annotations(self, image_stem: str):
        """Load annotations for a specific image (same as functioning system)."""
        if not self.session_path:
            return

        # Use the detected current iteration
        current_iteration = getattr(self, '_current_iteration', 0)

        # Try multiple path structures to find annotations file
        possible_paths = [
            self.session_path / f"iteration_{current_iteration}" / "annotations" / f"{image_stem}.json",
            self.session_path / "iterations" / f"iteration_{current_iteration}" / "annotations" / "json" / f"{image_stem}.json",
        ]

        annotations_file = None
        for path in possible_paths:
            if path.exists():
                annotations_file = path
                break

        if not annotations_file:
            # No file found in any location
            logger.debug(f"No annotations file found for {image_stem}")
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'clear_annotations'):
                self.annotation_canvas.clear_annotations()
            self.current_annotations = []
            self._update_count_display()
            return

        # File exists, load it
        try:
            with open(annotations_file, 'r') as f:
                data = json.load(f)

            # Try unified format first (Option B)
            if "annotations" in data:
                # New unified format: direct [x, y, class] array - optimized loading
                annotations = data.get("annotations", [])
                self.current_annotations = [[int(ann[0]), int(ann[1]), int(ann[2])]
                                          for ann in annotations if len(ann) >= 3]
                logger.info(f"Loaded unified format annotations")

            elif "coordinates" in data and "class" in data:
                # Backward compatibility: old separated format
                coordinates = data.get("coordinates", [])
                classes = data.get("class", [])

                if len(coordinates) != len(classes):
                    logger.error(f"Coordinates/classes length mismatch: {len(coordinates)} vs {len(classes)}")
                    return

                # Optimized legacy format conversion
                self.current_annotations = [[int(coord[0]), int(coord[1]), int(class_id)]
                                          for coord, class_id in zip(coordinates, classes) if len(coord) >= 2]
                logger.info(f"Loaded legacy format annotations (converted to unified)")

            else:
                logger.error(f"Unknown annotation format in {annotations_file}")
                self.current_annotations = []
                return

            logger.info(f"Loaded {len(self.current_annotations)} annotations from {annotations_file}")

            # Load into canvas using internal format
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'load_annotations'):
                self.annotation_canvas.load_annotations(self.current_annotations)
                logger.info(f"Annotations loaded into canvas for {image_stem}")

                # Tell canvas which points came from PRIOR iterations (so the halo
                # only highlights points added in the current iteration).
                if hasattr(self.annotation_canvas, 'set_prior_annotations'):
                    prior_pts = []
                    if current_iteration > 0:
                        prev_path = self.session_path / f"iteration_{current_iteration - 1}" / "annotations" / f"{image_stem}.json"
                        if prev_path.exists():
                            try:
                                prev_data = json.loads(prev_path.read_text())
                                prior_pts = prev_data.get("annotations", [])
                            except Exception as e:
                                logger.warning(f"Failed to load prior annotations from {prev_path}: {e}")
                    self.annotation_canvas.set_prior_annotations(prior_pts)

            # Update control panel statistics with cached session totals
            self._update_count_display()

        except Exception as e:
            logger.warning(f"Failed to load annotations for {image_stem}: {e}")
            # CRITICAL FIX: Clear annotations on load failure
            self.current_annotations = []
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'clear_annotations'):
                self.annotation_canvas.clear_annotations()
            # Update display with zero current count
            self._update_count_display()
    
    def configure_control_panel_classes(self):
        """Configure the control panel with VAIHINGEN class names."""
        if not self.control_panel:
            return
            
        logger.info("Configuring control panel with VAIHINGEN classes")
        
        # Use the new update_class_config method if available
        if hasattr(self.control_panel, 'update_class_config'):
            self.control_panel.update_class_config(self.class_names, self.class_colors)
            logger.info(f"Updated control panel with {len(self.class_names)} VAIHINGEN classes")
            
            # Also update the canvas colors to match the sidebar
            if self.annotation_canvas and hasattr(self.annotation_canvas, 'set_class_colors'):
                self.annotation_canvas.set_class_colors(self.class_colors)
                logger.info(f"Updated canvas with {len(self.class_colors)} class colors")
            
            return
        
        # Fallback to legacy approach for compatibility
        if hasattr(self.control_panel, 'class_selection_widget') and self.control_panel.class_selection_widget:
            widget = self.control_panel.class_selection_widget
            
            # Update each class with proper names and colors
            for i, (name, color) in enumerate(zip(self.class_names, self.class_colors)):
                # Convert color tuple to hex string
                color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                
                # Set class name
                if hasattr(widget, 'set_class_name'):
                    widget.set_class_name(i + 1, name)  # Widget uses 1-based indexing
                    logger.info(f"Set class {i+1} name to: {name}")
                
                # Set class color
                if hasattr(widget, 'set_class_color'):
                    widget.set_class_color(i + 1, color_hex)
                    logger.info(f"Set class {i+1} color to: {color_hex}")
            
            # Update the display
            if hasattr(widget, 'update_active_button'):
                widget.update_active_button()
            if hasattr(widget, 'update_current_class_display'):
                widget.update_current_class_display()
                
        logger.info("Class configuration completed")
    
    def show_help_dialog(self):
        """Show comprehensive help dialog matching functioning system exactly."""
        from PyQt5.QtWidgets import QMessageBox
        
        help_text = """
        🎯 ABILIUS ANNOTATION TOOL - KEYBOARD SHORTCUTS
        
        📂 Navigation:
        • Q / E - Previous / Next image
        • R - Random image selection
        • Ctrl+G - Go to specific image number
        
        🎨 Annotation Classes (VAIHINGEN Dataset):
        • 1 - Impervious surfaces (White)
        • 2 - Building (Blue)
        • 3 - Low vegetation (Cyan)
        • 4 - Tree (Green)
        • 5 - Car (Yellow)
        • 6 - Clutter (Red)
        
        🖱️ Point Annotation:
        • Left Click - Add annotation point
        • Left Click + Drag - Move existing point
        • Right Click - Remove nearest point
        • Space + Click - Force new point placement
        
        🔍 Zoom & View:
        • Mouse Wheel - Zoom in/out at cursor
        • Ctrl + Plus - Zoom in
        • Ctrl + Minus - Zoom out
        • Ctrl + 0 - Reset zoom to fit image
        • Middle Click + Drag - Pan around image
        
        ⚙️ Display Controls:
        • Toggle grid overlay for precise placement
        • RGB channel remapping (R/G/B → any channel)
        • Ground truth and prediction overlays
        • Pixel info tooltips for RGB values
        • Point size adjustment (3-20 pixels)
        
        ⌨️ System:
        • ESC - Return to Mode Grid
        • F1 - Show this help dialog
        • Ctrl+S - Save annotations (auto-saved)
        
        💡 Tips:
        • Hover over points to highlight them
        • Use space bar to override smart point detection
        • Mini-map shows full image overview
        • Status panel displays current statistics
        • Professional dark theme for reduced eye strain
        
        🚀 Advanced Features:
        • Session-based workflow with 1754 images
        • Real-time coordinate tracking
        • Sophisticated mouse interactions
        • Multi-class color-coded annotations
        • Professional overlay system
        """
        
        # Create enhanced message box with custom styling
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🎯 ABILIUS Annotation Tool - Help")
        msg_box.setText(help_text.strip())
        msg_box.setIcon(QMessageBox.Information)
        
        # Apply professional dark theme styling to match the application
        msg_box.setStyleSheet("""
            QMessageBox {
                background: #1a202c;
                color: #e2e8f0;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox QLabel {
                color: #e2e8f0;
                font-size: 11px;
                line-height: 1.4;
            }
            QMessageBox QPushButton {
                background: #3182ce;
                color: white;
                border: 1px solid #2c5aa0;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background: #2c5aa0;
            }
            QMessageBox QPushButton:pressed {
                background: #2a4d8a;
            }
        """)
        
        # Show dialog and update status
        msg_box.exec_()
        
        # Update status panel
        if self.status_panel:
            self.status_panel.add_status_message("Help", "Help dialog displayed", "info")
        
        logger.info("Comprehensive help dialog displayed")