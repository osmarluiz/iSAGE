#!/usr/bin/env python3
"""
Demo Annotation System - Demonstrates the complete modular annotation system

This script shows how to use the annotation builder and active learning preset
to create a complete annotation system for active learning workflows.
"""

import sys
import os
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from annotation_modules.builders.annotation_builder import AnnotationBuilder
from annotation_modules.builders.active_learning_preset import ActiveLearningPreset


def demo_basic_annotation_system():
    """Demo: Basic annotation system with simple point tool."""
    print("=== Demo: Basic Annotation System ===")
    
    # Create builder
    builder = AnnotationBuilder()
    
    # Initialize with basic configuration
    builder.initialize(
        preset_name='basic_annotation',
        window_title='Basic Annotation Demo',
        window_size=(1200, 800),
        theme='light'
    )
    
    # Set preset
    builder.set_preset('basic_annotation')
    
    # Build system
    main_window = builder.build()
    
    if main_window:
        print("✓ Basic annotation system created successfully")
        print(f"  Components: {len(builder.get_components())}")
        print(f"  Tools: {len(builder.get_tools())}")
        print(f"  Build progress: {builder.get_build_progress()['progress_percent']:.1f}%")
        
        # Show window
        main_window.show()
        return main_window
    else:
        print("✗ Failed to create basic annotation system")
        return None


def demo_active_learning_system():
    """Demo: Active learning annotation system with full features."""
    print("\n=== Demo: Active Learning System ===")
    
    # Create active learning preset
    preset = ActiveLearningPreset()
    
    # Initialize with active learning configuration
    preset.initialize(
        model_integration_enabled=True,
        uncertainty_sampling=True,
        batch_size=10,
        confidence_threshold=0.7,
        annotation_mode='sparse',
        point_budget=100,
        class_balance_enabled=True,
        real_time_prediction=True,
        auto_save_interval=300.0,
        preload_images=True,
        cache_predictions=True
    )
    
    # Create annotation system
    main_window = preset.create_annotation_system(
        window_title='Active Learning Demo',
        window_size=(1600, 1000),
        theme='dark'
    )
    
    if main_window:
        print("✓ Active learning system created successfully")
        
        # Get statistics
        stats = preset.get_statistics()
        print(f"  Model integration: {stats['model_integration_enabled']}")
        print(f"  Annotation mode: {stats['annotation_mode']}")
        print(f"  Point budget: {stats['point_budget']}")
        print(f"  Batch size: {stats['batch_size']}")
        print(f"  Confidence threshold: {stats['confidence_threshold']}")
        
        # Show window
        main_window.show()
        
        # Simulate starting a session (would normally use real image directory)
        print("\n  Starting demo session...")
        demo_image_dir = "/tmp/demo_images"  # Mock directory
        os.makedirs(demo_image_dir, exist_ok=True)
        
        # Create a few demo image files
        for i in range(3):
            demo_file = os.path.join(demo_image_dir, f"demo_image_{i}.jpg")
            with open(demo_file, 'w') as f:
                f.write(f"# Demo image {i}")
        
        # Start session (this would normally load real images)
        session_started = preset.start_active_learning_session(
            image_directory=demo_image_dir,
            model_path=None  # No model for demo
        )
        
        if session_started:
            print("  ✓ Active learning session started")
            
            # Get annotation candidates
            candidates = preset.get_next_annotation_candidates(count=5)
            print(f"  ✓ Got {len(candidates)} annotation candidates")
            
            # Show annotation statistics
            annotation_stats = preset.get_annotation_statistics()
            print(f"  Current iteration: {annotation_stats['current_iteration']}")
            print(f"  Total annotations: {annotation_stats['total_points']}")
            
        else:
            print("  ✗ Failed to start active learning session")
        
        return main_window
    else:
        print("✗ Failed to create active learning system")
        return None


def demo_advanced_annotation_system():
    """Demo: Advanced annotation system with all features."""
    print("\n=== Demo: Advanced Annotation System ===")
    
    # Create builder
    builder = AnnotationBuilder()
    
    # Initialize with advanced configuration
    builder.initialize(
        preset_name='advanced_annotation',
        window_title='Advanced Annotation Demo',
        window_size=(1800, 1200),
        theme='dark',
        validation_enabled=True,
        component_configs={
            'canvas': {
                'enable_zoom': True,
                'enable_pan': True,
                'crosshair_enabled': True,
                'grid_enabled': True,
                'background_color': '#2b2b2b'
            },
            'point_tool': {
                'point_size': 12,
                'show_confidence': True,
                'show_point_labels': True,
                'click_tolerance': 15.0
            },
            'prediction_overlay': {
                'confidence_threshold': 0.6,
                'color_scheme': 'red_blue',
                'show_uncertainty': True
            },
            'session_manager': {
                'auto_save_enabled': True,
                'recovery_enabled': True,
                'session_directory': '/tmp/annotation_sessions'
            }
        }
    )
    
    # Set preset
    builder.set_preset('advanced_annotation')
    
    # Build system
    main_window = builder.build()
    
    if main_window:
        print("✓ Advanced annotation system created successfully")
        
        # Get build progress
        build_progress = builder.get_build_progress()
        print(f"  Build stages completed: {build_progress['current_stage']}/{build_progress['total_stages']}")
        print(f"  Build progress: {build_progress['progress_percent']:.1f}%")
        
        # Get statistics
        stats = builder.get_statistics()
        print(f"  Components configured: {stats['components_configured']}")
        print(f"  Components created: {stats['components_created']}")
        print(f"  Tools: {stats['tools_count']}")
        print(f"  Overlays: {stats['overlays_count']}")
        print(f"  Validation errors: {stats['validation_errors']}")
        
        # Show available components
        print("\n  Available components:")
        for comp_name, component in builder._components.items():
            print(f"    - {comp_name}: {component.__class__.__name__}")
        
        # Show window
        main_window.show()
        return main_window
    else:
        print("✗ Failed to create advanced annotation system")
        return None


def demo_component_modularity():
    """Demo: Component modularity and customization."""
    print("\n=== Demo: Component Modularity ===")
    
    # Create builder
    builder = AnnotationBuilder()
    
    # Initialize with basic setup
    builder.initialize(
        preset_name='custom',
        window_title='Custom Annotation System',
        window_size=(1400, 900),
        theme='light'
    )
    
    # Add custom components one by one
    from annotation_modules.canvas.annotation_canvas import AnnotationCanvas
    from annotation_modules.tools.point_tool import PointTool
    from annotation_modules.tools.point_manager import PointManager
    from annotation_modules.overlays.prediction_overlay import PredictionOverlay
    from annotation_modules.ui.control_panel import ControlPanel
    from annotation_modules.ui.status_panel import StatusPanel
    from annotation_modules.io.json_saver import JsonSaver
    from annotation_modules.io.session_manager import SessionManager
    
    print("  Adding custom components...")
    
    # Add canvas with custom configuration
    builder.add_component('canvas', AnnotationCanvas, {
        'enable_zoom': True,
        'enable_pan': True,
        'crosshair_enabled': False,
        'background_color': '#f8f8f8'
    })
    
    # Add point tool with custom settings
    builder.add_component('point_tool', PointTool, {
        'point_size': 8,
        'click_tolerance': 12.0,
        'show_point_labels': True,
        'show_confidence': False
    })
    
    # Add point manager
    builder.add_component('point_manager', PointManager, {
        'max_history_size': 50
    })
    
    # Add prediction overlay
    builder.add_component('prediction_overlay', PredictionOverlay, {
        'confidence_threshold': 0.5,
        'color_scheme': 'red_blue',
        'use_confidence_mapping': True
    })
    
    # Add UI panels
    builder.add_component('control_panel', ControlPanel, {
        'panel_width': 280,
        'collapsible': True,
        'theme': 'light'
    })
    
    builder.add_component('status_panel', StatusPanel, {
        'panel_width': 350,
        'log_enabled': True,
        'auto_scroll': True
    })
    
    # Add I/O components
    builder.add_component('json_saver', JsonSaver, {
        'pretty_print': True,
        'backup_enabled': True
    })
    
    builder.add_component('session_manager', SessionManager, {
        'auto_save_enabled': True,
        'recovery_enabled': False
    })
    
    print(f"  ✓ Added {len(builder._component_configs)} custom components")
    
    # Build system
    main_window = builder.build()
    
    if main_window:
        print("✓ Custom annotation system created successfully")
        
        # Demonstrate component access
        canvas = builder.get_component('canvas')
        point_tool = builder.get_component('point_tool')
        control_panel = builder.get_component('control_panel')
        
        print(f"  Canvas: {canvas.__class__.__name__ if canvas else 'None'}")
        print(f"  Point tool: {point_tool.__class__.__name__ if point_tool else 'None'}")
        print(f"  Control panel: {control_panel.__class__.__name__ if control_panel else 'None'}")
        
        # Show window
        main_window.show()
        return main_window
    else:
        print("✗ Failed to create custom annotation system")
        return None


def main():
    """Main demo function."""
    print("Annotation System Demo")
    print("=" * 50)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # List to keep windows alive
    windows = []
    
    try:
        # Demo 1: Basic annotation system
        basic_window = demo_basic_annotation_system()
        if basic_window:
            windows.append(basic_window)
        
        # Demo 2: Active learning system
        active_window = demo_active_learning_system()
        if active_window:
            windows.append(active_window)
        
        # Demo 3: Advanced annotation system
        advanced_window = demo_advanced_annotation_system()
        if advanced_window:
            windows.append(advanced_window)
        
        # Demo 4: Component modularity
        custom_window = demo_component_modularity()
        if custom_window:
            windows.append(custom_window)
        
        print(f"\n=== Demo Complete ===")
        print(f"Created {len(windows)} annotation systems")
        print("All windows are now open. Close them to exit.")
        
        # Set up timer to close after 30 seconds (for automated testing)
        if len(sys.argv) > 1 and sys.argv[1] == '--auto-close':
            timer = QTimer()
            timer.timeout.connect(app.quit)
            timer.start(30000)  # 30 seconds
            print("Auto-close enabled: windows will close in 30 seconds")
        
        # Run application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Error running demo: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()