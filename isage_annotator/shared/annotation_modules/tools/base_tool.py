"""
Base Tool - Foundation for all annotation tools

This module provides the base class for all annotation tools.
"""

from typing import List, Dict, Any, Optional
from ..base_protocols import BaseComponent, ToolProtocol, AnnotationPoint, QPointF, pyqtSignal


class BaseTool(BaseComponent):
    """Base class for all annotation tools."""
    
    # Tool-specific signals
    annotationAdded = pyqtSignal(object)  # AnnotationPoint
    annotationRemoved = pyqtSignal(object)  # AnnotationPoint
    annotationModified = pyqtSignal(object, object)  # old, new AnnotationPoint
    annotationsCleared = pyqtSignal()
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        self._annotations: List[AnnotationPoint] = []
        self._current_class_id = 0
        self._enabled = True
        self._active = False
    
    # ToolProtocol implementation
    def handle_mouse_press(self, pos: QPointF, button: int) -> bool:
        """Handle mouse press events. Override in subclasses."""
        return False
    
    def handle_mouse_release(self, pos: QPointF, button: int) -> bool:
        """Handle mouse release events. Override in subclasses."""
        return False
    
    def handle_mouse_move(self, pos: QPointF) -> bool:
        """Handle mouse move events. Override in subclasses."""
        return False
    
    def handle_key_press(self, key: int) -> bool:
        """Handle key press events. Override in subclasses."""
        return False
    
    def get_annotations(self) -> List[AnnotationPoint]:
        """Get current annotations from this tool."""
        return self._annotations.copy()
    
    def set_annotations(self, annotations: List[AnnotationPoint]) -> None:
        """Set annotations for this tool."""
        self._annotations = annotations.copy()
        self.emit_state_changed({'annotations': len(self._annotations)})
    
    def clear_annotations(self) -> None:
        """Clear all annotations from this tool."""
        self._annotations.clear()
        self.annotationsCleared.emit()
        self.emit_state_changed({'annotations': 0})
    
    # Tool-specific methods
    def set_current_class_id(self, class_id: int) -> None:
        """Set the current class ID for new annotations."""
        self._current_class_id = class_id
        self.emit_state_changed({'current_class_id': class_id})
    
    def get_current_class_id(self) -> int:
        """Get the current class ID."""
        return self._current_class_id
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the tool."""
        self._enabled = enabled
        self.emit_state_changed({'enabled': enabled})
    
    def is_enabled(self) -> bool:
        """Check if tool is enabled."""
        return self._enabled
    
    def set_active(self, active: bool) -> None:
        """Set tool as active/inactive."""
        self._active = active
        self.emit_state_changed({'active': active})
    
    def is_active(self) -> bool:
        """Check if tool is active."""
        return self._active
    
    def add_annotation(self, point: AnnotationPoint) -> None:
        """Add an annotation point."""
        self._annotations.append(point)
        self.annotationAdded.emit(point)
        self.emit_state_changed({'annotations': len(self._annotations)})
    
    def remove_annotation(self, point: AnnotationPoint) -> bool:
        """Remove an annotation point."""
        try:
            self._annotations.remove(point)
            self.annotationRemoved.emit(point)
            self.emit_state_changed({'annotations': len(self._annotations)})
            return True
        except ValueError:
            return False
    
    def find_annotation_at(self, pos: QPointF, tolerance: float = 5.0) -> Optional[AnnotationPoint]:
        """Find annotation at given position within tolerance."""
        for annotation in self._annotations:
            distance = ((annotation.x - pos.x()) ** 2 + (annotation.y - pos.y()) ** 2) ** 0.5
            if distance <= tolerance:
                return annotation
        return None
    
    def get_annotation_count(self) -> int:
        """Get total number of annotations."""
        return len(self._annotations)
    
    def get_annotation_count_by_class(self, class_id: int) -> int:
        """Get number of annotations for a specific class."""
        return sum(1 for ann in self._annotations if ann.class_id == class_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool statistics."""
        class_counts = {}
        for annotation in self._annotations:
            class_id = annotation.class_id
            class_counts[class_id] = class_counts.get(class_id, 0) + 1
        
        return {
            'total_annotations': len(self._annotations),
            'class_distribution': class_counts,
            'current_class_id': self._current_class_id,
            'enabled': self._enabled,
            'active': self._active
        }


# Re-export for convenience
ToolProtocol = ToolProtocol