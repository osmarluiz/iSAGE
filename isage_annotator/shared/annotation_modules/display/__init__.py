"""
Display Components - Image display and visualization utilities

This module contains display components:
- channel_mapper: Channel mapping for multi-channel images
- minimap_widget: Interactive minimap navigation widget
"""

try:
    from .channel_mapper import ChannelMapper
    channel_mapper_available = True
except ImportError:
    channel_mapper_available = False

try:
    from .minimap_widget import MinimapWidget
    minimap_available = True
except ImportError:
    minimap_available = False

__all__ = []
if channel_mapper_available:
    __all__.append('ChannelMapper')
if minimap_available:
    __all__.append('MinimapWidget')