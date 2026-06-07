"""
Layout Utilities - Helper functions for safe Qt layout management

This module provides utilities to safely manage Qt layouts, avoiding the common
"QLayout: Attempting to add QLayout to QFrame which already has a layout" error.
"""

import logging
from PyQt5.QtWidgets import QWidget, QLayout

logger = logging.getLogger(__name__)


def safe_set_layout(widget: QWidget, new_layout: QLayout) -> bool:
    """
    Safely set a layout on a widget, clearing any existing layout first.
    
    Args:
        widget: The widget to set the layout on
        new_layout: The new layout to apply
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if widget already has a layout
        existing_layout = widget.layout()
        if existing_layout is not None:
            logger.debug(f"Clearing existing layout from {widget.__class__.__name__}")
            clear_layout(existing_layout)
            existing_layout.deleteLater()
        
        # Set the new layout
        widget.setLayout(new_layout)
        logger.debug(f"Successfully set new layout on {widget.__class__.__name__}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting layout on {widget.__class__.__name__}: {e}")
        return False


def clear_layout(layout: QLayout) -> None:
    """
    Recursively clear all items from a layout.
    
    Args:
        layout: The layout to clear
    """
    try:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                clear_layout(child.layout())
                child.layout().deleteLater()
                
    except Exception as e:
        logger.error(f"Error clearing layout: {e}")


def safe_add_widget(layout: QLayout, widget: QWidget) -> bool:
    """
    Safely add a widget to a layout with error handling.
    
    Args:
        layout: The layout to add the widget to
        widget: The widget to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        layout.addWidget(widget)
        return True
    except Exception as e:
        logger.error(f"Error adding widget {widget.__class__.__name__} to layout: {e}")
        return False


def safe_add_layout(parent_layout: QLayout, child_layout: QLayout) -> bool:
    """
    Safely add a child layout to a parent layout with error handling.
    
    Args:
        parent_layout: The parent layout
        child_layout: The child layout to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        parent_layout.addLayout(child_layout)
        return True
    except Exception as e:
        logger.error(f"Error adding child layout to parent layout: {e}")
        return False


def init_widget_layout(widget: QWidget, layout_class, *args, **kwargs) -> QLayout:
    """
    Initialize a layout for a widget safely.
    
    Args:
        widget: The widget to initialize the layout for
        layout_class: The layout class (e.g., QVBoxLayout, QHBoxLayout)
        *args: Arguments to pass to the layout constructor
        **kwargs: Keyword arguments to pass to the layout constructor
        
    Returns:
        QLayout: The initialized layout
    """
    # Clear any existing layout
    existing_layout = widget.layout()
    if existing_layout is not None:
        logger.debug(f"Clearing existing layout from {widget.__class__.__name__}")
        clear_layout(existing_layout)
        existing_layout.deleteLater()
    
    # Create new layout
    new_layout = layout_class(widget, *args, **kwargs)
    logger.debug(f"Initialized {layout_class.__name__} for {widget.__class__.__name__}")
    
    return new_layout