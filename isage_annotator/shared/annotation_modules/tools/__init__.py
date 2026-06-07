"""
Annotation Tools - Different annotation methods

This module contains various annotation tools that can be used interchangeably:
- point_tool: Sparse point annotation for active learning
- enhanced_point_tool: Advanced point annotation with size adjustment
- point_manager: Point annotation management
- polygon_tool: Polygon drawing for dense annotation
- brush_tool: Brush painting for pixel-level annotation
- eraser_tool: Erasing annotations
- etc.

Each tool implements the same interface for seamless integration.
"""

from .base_tool import BaseTool, ToolProtocol
from .point_tool import PointTool
from .point_manager import PointManager

__all__ = [
    'BaseTool',
    'ToolProtocol',
    'PointTool',
    'PointManager'
]