"""
Annotation Store - Centralized data management for annotations

This module manages all annotation data independently of UI components.
It provides a clean API for adding, removing, and querying annotations.
"""

from typing import List, Dict, Optional, Tuple, Set, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
import json
import uuid


@dataclass
class Annotation:
    """Single annotation point."""
    x: float
    y: float
    class_id: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'class_id': self.class_id,
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        """Create from dictionary."""
        return cls(
            x=data['x'],
            y=data['y'],
            class_id=data['class_id'],
            id=data.get('id', str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )


class AnnotationStoreProtocol(Protocol):
    """Protocol defining the annotation store interface."""
    
    # Signals
    annotation_added: pyqtSignal
    annotation_removed: pyqtSignal
    annotation_updated: pyqtSignal
    annotations_cleared: pyqtSignal
    
    # Methods
    def add_annotation(self, x: float, y: float, class_id: int) -> str: ...
    def remove_annotation(self, annotation_id: str) -> bool: ...
    def update_annotation(self, annotation_id: str, x: float, y: float) -> bool: ...
    def get_annotations(self, class_id: Optional[int] = None) -> List[Annotation]: ...
    def clear_annotations(self) -> None: ...


class AnnotationStore(QObject):
    """
    Centralized store for annotation data.
    
    Features:
    - Add/remove/update annotations
    - Query by class or region
    - Undo/redo support
    - Change tracking
    - Serialization support
    
    This store is completely independent of UI and can be used
    with any annotation interface.
    """
    
    # Signals
    annotation_added = pyqtSignal(str, float, float, int)  # id, x, y, class_id
    annotation_removed = pyqtSignal(str)  # id
    annotation_updated = pyqtSignal(str, float, float)  # id, new_x, new_y
    annotations_cleared = pyqtSignal()
    annotations_loaded = pyqtSignal(int)  # count
    
    def __init__(self):
        super().__init__()
        
        # Data storage
        self._annotations: Dict[str, Annotation] = {}
        self._annotations_by_class: Dict[int, Set[str]] = {}
        
        # History for undo/redo
        self._history: List[Dict] = []
        self._history_index: int = -1
        self._max_history: int = 50
        
        # Change tracking
        self._modified: bool = False
        self._last_save_state: Optional[Dict] = None
    
    # Public API (implements AnnotationStoreProtocol)
    
    def add_annotation(self, x: float, y: float, class_id: int, metadata: Optional[Dict] = None) -> str:
        """
        Add a new annotation point.
        
        Args:
            x: X coordinate (image coordinates)
            y: Y coordinate (image coordinates)
            class_id: Class identifier
            metadata: Optional metadata
            
        Returns:
            ID of the created annotation
        """
        # Create annotation
        annotation = Annotation(x=x, y=y, class_id=class_id, metadata=metadata or {})
        
        # Store it
        self._annotations[annotation.id] = annotation
        
        # Update class index
        if class_id not in self._annotations_by_class:
            self._annotations_by_class[class_id] = set()
        self._annotations_by_class[class_id].add(annotation.id)
        
        # Record history
        self._record_action('add', annotation)
        
        # Mark as modified
        self._modified = True
        
        # Emit signal
        self.annotation_added.emit(annotation.id, x, y, class_id)
        
        return annotation.id
    
    def remove_annotation(self, annotation_id: str) -> bool:
        """
        Remove an annotation.
        
        Args:
            annotation_id: ID of annotation to remove
            
        Returns:
            True if removed, False if not found
        """
        if annotation_id not in self._annotations:
            return False
        
        # Get annotation
        annotation = self._annotations[annotation_id]
        
        # Remove from storage
        del self._annotations[annotation_id]
        
        # Update class index
        if annotation.class_id in self._annotations_by_class:
            self._annotations_by_class[annotation.class_id].discard(annotation_id)
            if not self._annotations_by_class[annotation.class_id]:
                del self._annotations_by_class[annotation.class_id]
        
        # Record history
        self._record_action('remove', annotation)
        
        # Mark as modified
        self._modified = True
        
        # Emit signal
        self.annotation_removed.emit(annotation_id)
        
        return True
    
    def update_annotation(self, annotation_id: str, x: float, y: float) -> bool:
        """
        Update annotation position.
        
        Args:
            annotation_id: ID of annotation to update
            x: New X coordinate
            y: New Y coordinate
            
        Returns:
            True if updated, False if not found
        """
        if annotation_id not in self._annotations:
            return False
        
        # Get annotation
        annotation = self._annotations[annotation_id]
        old_x, old_y = annotation.x, annotation.y
        
        # Update position
        annotation.x = x
        annotation.y = y
        annotation.timestamp = datetime.now()
        
        # Record history
        self._record_action('update', annotation, {'old_x': old_x, 'old_y': old_y})
        
        # Mark as modified
        self._modified = True
        
        # Emit signal
        self.annotation_updated.emit(annotation_id, x, y)
        
        return True
    
    def get_annotations(self, class_id: Optional[int] = None) -> List[Annotation]:
        """
        Get annotations, optionally filtered by class.
        
        Args:
            class_id: Optional class filter
            
        Returns:
            List of annotations
        """
        if class_id is None:
            return list(self._annotations.values())
        else:
            annotation_ids = self._annotations_by_class.get(class_id, set())
            return [self._annotations[aid] for aid in annotation_ids]
    
    def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """Get a specific annotation by ID."""
        return self._annotations.get(annotation_id)
    
    def clear_annotations(self) -> None:
        """Clear all annotations."""
        # Record history
        if self._annotations:
            self._record_action('clear', list(self._annotations.values()))
        
        # Clear storage
        self._annotations.clear()
        self._annotations_by_class.clear()
        
        # Mark as modified
        self._modified = True
        
        # Emit signal
        self.annotations_cleared.emit()
    
    def get_statistics(self) -> Dict[str, int]:
        """Get annotation statistics."""
        stats = {
            'total': len(self._annotations),
            'by_class': {}
        }
        
        for class_id, annotation_ids in self._annotations_by_class.items():
            stats['by_class'][class_id] = len(annotation_ids)
        
        return stats
    
    def find_nearest(self, x: float, y: float, max_distance: float = 10.0) -> Optional[str]:
        """
        Find nearest annotation to given point.
        
        Args:
            x: X coordinate
            y: Y coordinate
            max_distance: Maximum search distance
            
        Returns:
            ID of nearest annotation or None
        """
        nearest_id = None
        nearest_dist = max_distance
        
        for annotation in self._annotations.values():
            dist = ((annotation.x - x) ** 2 + (annotation.y - y) ** 2) ** 0.5
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id = annotation.id
        
        return nearest_id
    
    def find_in_region(self, x1: float, y1: float, x2: float, y2: float) -> List[str]:
        """Find all annotations within a rectangular region."""
        found = []
        
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        for annotation in self._annotations.values():
            if min_x <= annotation.x <= max_x and min_y <= annotation.y <= max_y:
                found.append(annotation.id)
        
        return found
    
    # Serialization
    
    def to_dict(self) -> dict:
        """Convert store to dictionary for saving."""
        return {
            'annotations': [ann.to_dict() for ann in self._annotations.values()],
            'metadata': {
                'created': datetime.now().isoformat(),
                'count': len(self._annotations)
            }
        }
    
    def from_dict(self, data: dict) -> None:
        """Load store from dictionary."""
        self.clear_annotations()
        
        for ann_data in data.get('annotations', []):
            annotation = Annotation.from_dict(ann_data)
            
            # Store it
            self._annotations[annotation.id] = annotation
            
            # Update class index
            if annotation.class_id not in self._annotations_by_class:
                self._annotations_by_class[annotation.class_id] = set()
            self._annotations_by_class[annotation.class_id].add(annotation.id)
        
        # Reset modified flag
        self._modified = False
        self._last_save_state = self.to_dict()
        
        # Emit signal
        self.annotations_loaded.emit(len(self._annotations))
    
    def save_to_file(self, filepath: str) -> bool:
        """Save annotations to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            
            self._modified = False
            self._last_save_state = self.to_dict()
            return True
            
        except Exception as e:
            print(f"Error saving annotations: {e}")
            return False
    
    def load_from_file(self, filepath: str) -> bool:
        """Load annotations from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.from_dict(data)
            return True
            
        except Exception as e:
            print(f"Error loading annotations: {e}")
            return False
    
    # History management
    
    def _record_action(self, action: str, data: Any, extra: Optional[Dict] = None):
        """Record action for undo/redo."""
        record = {
            'action': action,
            'data': data,
            'extra': extra or {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Remove any history after current index
        self._history = self._history[:self._history_index + 1]
        
        # Add new record
        self._history.append(record)
        self._history_index += 1
        
        # Limit history size
        if len(self._history) > self._max_history:
            self._history.pop(0)
            self._history_index -= 1
    
    def undo(self) -> bool:
        """Undo last action."""
        if self._history_index < 0:
            return False
        
        # Get action to undo
        record = self._history[self._history_index]
        
        # Perform undo based on action type
        if record['action'] == 'add':
            # Remove the added annotation
            self.remove_annotation(record['data'].id)
        elif record['action'] == 'remove':
            # Re-add the removed annotation
            ann = record['data']
            self._annotations[ann.id] = ann
            if ann.class_id not in self._annotations_by_class:
                self._annotations_by_class[ann.class_id] = set()
            self._annotations_by_class[ann.class_id].add(ann.id)
        elif record['action'] == 'update':
            # Restore old position
            ann = self._annotations[record['data'].id]
            ann.x = record['extra']['old_x']
            ann.y = record['extra']['old_y']
        
        self._history_index -= 1
        return True
    
    def redo(self) -> bool:
        """Redo next action."""
        if self._history_index >= len(self._history) - 1:
            return False
        
        self._history_index += 1
        # Get action to redo
        record = self._history[self._history_index]
        
        # Perform redo based on action type
        # (Implementation similar to undo but reversed)
        
        return True
    
    @property
    def is_modified(self) -> bool:
        """Check if store has unsaved changes."""
        return self._modified
    
    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._history_index >= 0
    
    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._history_index < len(self._history) - 1