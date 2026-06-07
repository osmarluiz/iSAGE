"""
Composition Example - How modular components work together

This example shows how independent modules are composed into
a working annotation system while maintaining clean separation.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt

# Import our modular components
from display.minimap_widget import MinimapWidget
from data.annotation_store import AnnotationStore
from simple_canvas import SimpleAnnotationCanvas
from simple_control_panel import SimpleControlPanel
from simple_status_panel import SimpleStatusPanel


class AnnotationSystem(QWidget):
    """
    Example of composing modular components into a complete system.
    
    Key principles:
    1. Components don't know about each other
    2. All communication through signals
    3. This class just wires them together
    4. Each component can be tested/replaced independently
    """
    
    def __init__(self):
        super().__init__()
        
        # Create independent components
        self._create_components()
        
        # Wire up signal connections
        self._connect_signals()
        
        # Create layout
        self._setup_layout()
    
    def _create_components(self):
        """Create all modular components."""
        
        # Data layer (no UI dependencies)
        self.annotation_store = AnnotationStore()
        
        # Display components
        self.minimap = MinimapWidget(config={
            'size': (200, 150),
            'style': {
                'background': '#1f2937',
                'view_rect_color': '#3b82f6'
            }
        })
        
        # UI components
        self.canvas = SimpleAnnotationCanvas()
        self.control_panel = SimpleControlPanel()
        self.status_panel = SimpleStatusPanel()
        
        # Initialize components
        self.control_panel.initialize(panel_width=384, theme='dark')
        self.status_panel.initialize(panel_width=384, theme='dark')
        self.canvas.initialize(
            background_color='#2d3748',
            enable_optimized_rendering=True
        )
    
    def _connect_signals(self):
        """
        Wire up all signal connections between components.
        
        This is the ONLY place where components are connected.
        Each connection is one-way and clearly documented.
        """
        
        # Canvas → Data Store
        self.canvas.annotationAdded.connect(
            lambda x, y, cls: self.annotation_store.add_annotation(x, y, cls)
        )
        
        # Data Store → Canvas (to update display)
        self.annotation_store.annotation_added.connect(
            self._on_annotation_added_to_store
        )
        self.annotation_store.annotation_removed.connect(
            self._on_annotation_removed_from_store
        )
        
        # Control Panel → Canvas
        self.control_panel.classChanged.connect(
            self.canvas.set_current_class
        )
        self.control_panel.clearRequested.connect(
            self.annotation_store.clear_annotations
        )
        
        # Data Store → Status Panel (statistics)
        self.annotation_store.annotation_added.connect(
            lambda *args: self._update_statistics()
        )
        self.annotation_store.annotation_removed.connect(
            lambda *args: self._update_statistics()
        )
        self.annotation_store.annotations_cleared.connect(
            self._update_statistics
        )
        
        # Canvas → Minimap (view updates)
        # Note: In full implementation, canvas would emit view_changed signal
        # self.canvas.view_changed.connect(self.minimap.update_view_rect)
        
        # Minimap → Canvas (navigation)
        self.minimap.view_clicked.connect(self._navigate_to_position)
        
        # Canvas → Status Panel (image info)
        self.canvas.imageLoaded.connect(
            lambda path: self.status_panel.add_status_message(
                "Canvas", f"Image loaded: {path}", "info"
            )
        )
    
    def _setup_layout(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main splitter for 3-panel layout
        splitter = QSplitter(Qt.Horizontal)
        
        # Add components
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.status_panel)
        
        # Set sizes
        splitter.setSizes([384, 600, 384])
        
        layout.addWidget(splitter)
        
        # Add minimap to status panel if possible
        # This shows how components can be nested while maintaining independence
        self._add_minimap_to_status_panel()
    
    def _add_minimap_to_status_panel(self):
        """Example of adding one component to another's layout."""
        # This is done externally - status panel doesn't know about minimap
        
        # Find a suitable place in status panel's layout
        # In real implementation, status panel might expose a method like:
        # self.status_panel.add_widget_to_section('top', self.minimap)
        
        # For now, we'll just note this as a TODO
        pass
    
    # Bridge methods (connecting signals to components)
    
    def _on_annotation_added_to_store(self, ann_id: str, x: float, y: float, class_id: int):
        """When annotation is added to store, update canvas display."""
        # In full implementation, canvas would maintain its own visual representation
        # synchronized with the data store
        current_count = len(self.annotation_store.get_annotations())
        self.status_panel.add_status_message(
            "Store", f"Annotation added. Total: {current_count}", "info"
        )
    
    def _on_annotation_removed_from_store(self, ann_id: str):
        """When annotation is removed from store, update canvas display."""
        current_count = len(self.annotation_store.get_annotations())
        self.status_panel.add_status_message(
            "Store", f"Annotation removed. Total: {current_count}", "info"
        )
    
    def _update_statistics(self):
        """Update statistics display in control panel."""
        stats = self.annotation_store.get_statistics()
        
        # Update control panel point counts
        if hasattr(self.control_panel, 'update_point_counts'):
            self.control_panel.update_point_counts(
                stats['total'],
                stats['total']  # In real system, would track session total
            )
        
        # Update status panel
        self.status_panel.update_component_status(
            "Annotations", f"Total: {stats['total']}", "info"
        )
    
    def _navigate_to_position(self, norm_x: float, norm_y: float):
        """Handle minimap click navigation."""
        # In full implementation, would calculate proper pan offset
        # and update canvas view
        self.status_panel.add_status_message(
            "Navigation", f"Navigate to ({norm_x:.2f}, {norm_y:.2f})", "info"
        )
    
    # Public API for the composed system
    
    def load_image(self, image_path: str):
        """Load an image into the system."""
        # Load into canvas
        if self.canvas.load_image(image_path):
            # Update minimap
            self.minimap.set_image(image_path)
            
            # Clear previous annotations
            self.annotation_store.clear_annotations()
            
            # Load annotations if they exist
            annotation_path = image_path.replace('.png', '_annotations.json')
            self.annotation_store.load_from_file(annotation_path)
    
    def save_annotations(self, filepath: str):
        """Save current annotations."""
        return self.annotation_store.save_to_file(filepath)
    
    def get_annotation_count(self) -> int:
        """Get total annotation count."""
        return len(self.annotation_store.get_annotations())


def create_annotation_widget_from_config(config: dict) -> AnnotationSystem:
    """
    Factory function showing how different configurations can create
    different annotation systems using the same modular components.
    """
    
    system = AnnotationSystem()
    
    # Apply configuration to components
    if 'minimap' in config:
        system.minimap.set_config(config['minimap'])
    
    if 'canvas' in config:
        # In full implementation, canvas would have set_config method
        pass
    
    if 'theme' in config:
        theme = config['theme']
        system.control_panel.initialize(theme=theme)
        system.status_panel.initialize(theme=theme)
    
    return system


# Example usage showing modularity benefits
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Create system with custom configuration
    config = {
        'minimap': {
            'size': (250, 180),
            'behavior': {
                'click_to_navigate': True,
                'show_crosshair': True
            }
        },
        'theme': 'dark'
    }
    
    widget = create_annotation_widget_from_config(config)
    widget.setWindowTitle("Modular Annotation System")
    widget.resize(1400, 800)
    widget.show()
    
    sys.exit(app.exec_())