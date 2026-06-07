"""
Navigation Components - Image navigation and minimap

This module contains navigation components:
- image_navigator: Navigate through image datasets with thumbnail support
- minimap: Overview navigation widget with viewport visualization
- navigation_controller: Coordinate navigation between components
"""

from .base_navigator import BaseNavigator, NavigatorProtocol
from .image_navigator import ImageNavigator
from .minimap import Minimap
from .navigation_controller import NavigationController

__all__ = [
    'BaseNavigator',
    'NavigatorProtocol',
    'ImageNavigator',
    'Minimap',
    'NavigationController'
]