"""
Point Manager - Manages point annotations and operations

This module provides advanced point management functionality including
batch operations, filtering, and analysis.
"""

from typing import List, Dict, Any, Optional, Tuple, Callable
import time
import uuid
from ..base_protocols import BaseComponent, AnnotationPoint, QPointF, QColor


class PointManager(BaseComponent):
    """Manages point annotations with advanced operations."""
    
    # Manager-specific signals
    pointsChanged = pyqtSignal()
    batchOperationCompleted = pyqtSignal(str, int)  # operation_name, affected_count
    filterChanged = pyqtSignal(str)  # filter_name
    
    def __init__(self, name: str = "point_manager", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Point storage
        self._points: Dict[str, AnnotationPoint] = {}  # id -> point
        self._point_groups: Dict[str, List[str]] = {}  # group_name -> point_ids
        self._point_tags: Dict[str, List[str]] = {}  # point_id -> tags
        
        # Filtering and sorting
        self._active_filters: Dict[str, Callable[[AnnotationPoint], bool]] = {}
        self._sort_function: Optional[Callable[[List[AnnotationPoint]], List[AnnotationPoint]]] = None
        
        # Undo/Redo
        self._history: List[Dict[str, Any]] = []
        self._history_index: int = -1
        self._max_history_size: int = 100
        
        # Analysis cache
        self._analysis_cache: Dict[str, Any] = {}
        self._cache_dirty: bool = True
    
    def initialize(self, **kwargs) -> bool:
        """Initialize point manager."""
        self._max_history_size = kwargs.get('max_history_size', 100)
        return super().initialize(**kwargs)
    
    def add_point(self, point: AnnotationPoint, point_id: Optional[str] = None) -> str:
        """Add a point with optional ID."""
        if point_id is None:
            point_id = str(uuid.uuid4())
        
        # Save state for undo
        self._save_state("add_point", point_id)
        
        # Add point
        self._points[point_id] = point
        self._invalidate_cache()
        
        self.pointsChanged.emit()
        self.emit_state_changed({'points_count': len(self._points)})
        
        return point_id
    
    def remove_point(self, point_id: str) -> bool:
        """Remove a point by ID."""
        if point_id not in self._points:
            return False
        
        # Save state for undo
        self._save_state("remove_point", point_id)
        
        # Remove from groups
        for group_name, point_ids in self._point_groups.items():
            if point_id in point_ids:
                point_ids.remove(point_id)
        
        # Remove tags
        if point_id in self._point_tags:
            del self._point_tags[point_id]
        
        # Remove point
        del self._points[point_id]
        self._invalidate_cache()
        
        self.pointsChanged.emit()
        self.emit_state_changed({'points_count': len(self._points)})
        
        return True
    
    def get_point(self, point_id: str) -> Optional[AnnotationPoint]:
        """Get a point by ID."""
        return self._points.get(point_id)
    
    def get_all_points(self) -> List[AnnotationPoint]:
        """Get all points."""
        return list(self._points.values())
    
    def get_filtered_points(self) -> List[AnnotationPoint]:
        """Get points after applying active filters."""
        points = self.get_all_points()
        
        # Apply filters
        for filter_name, filter_func in self._active_filters.items():
            points = [p for p in points if filter_func(p)]
        
        # Apply sorting
        if self._sort_function:
            points = self._sort_function(points)
        
        return points
    
    def update_point(self, point_id: str, **kwargs) -> bool:
        """Update a point's properties."""
        if point_id not in self._points:
            return False
        
        # Save state for undo
        self._save_state("update_point", point_id)
        
        point = self._points[point_id]
        
        # Update properties
        if 'x' in kwargs:
            point.x = kwargs['x']
        if 'y' in kwargs:
            point.y = kwargs['y']
        if 'class_id' in kwargs:
            point.class_id = kwargs['class_id']
        if 'confidence' in kwargs:
            point.confidence = kwargs['confidence']
        if 'timestamp' in kwargs:
            point.timestamp = kwargs['timestamp']
        if 'source' in kwargs:
            point.source = kwargs['source']
        
        self._invalidate_cache()
        self.pointsChanged.emit()
        
        return True
    
    def move_point(self, point_id: str, new_pos: QPointF) -> bool:
        """Move a point to new position."""
        return self.update_point(point_id, x=new_pos.x(), y=new_pos.y())
    
    def change_point_class(self, point_id: str, new_class_id: int) -> bool:
        """Change point class."""
        return self.update_point(point_id, class_id=new_class_id)
    
    def set_point_confidence(self, point_id: str, confidence: float) -> bool:
        """Set point confidence."""
        return self.update_point(point_id, confidence=confidence)
    
    def clear_points(self) -> None:
        """Clear all points."""
        # Save state for undo
        self._save_state("clear_points")
        
        self._points.clear()
        self._point_groups.clear()
        self._point_tags.clear()
        self._invalidate_cache()
        
        self.pointsChanged.emit()
        self.emit_state_changed({'points_count': 0})
    
    # Group operations
    def create_group(self, group_name: str, point_ids: List[str] = None) -> bool:
        """Create a point group."""
        if point_ids is None:
            point_ids = []
        
        # Validate point IDs
        valid_ids = [pid for pid in point_ids if pid in self._points]
        
        self._point_groups[group_name] = valid_ids
        self.emit_state_changed({'groups_count': len(self._point_groups)})
        
        return True
    
    def add_to_group(self, group_name: str, point_id: str) -> bool:
        """Add point to group."""
        if point_id not in self._points:
            return False
        
        if group_name not in self._point_groups:
            self._point_groups[group_name] = []
        
        if point_id not in self._point_groups[group_name]:
            self._point_groups[group_name].append(point_id)
        
        return True
    
    def remove_from_group(self, group_name: str, point_id: str) -> bool:
        """Remove point from group."""
        if group_name not in self._point_groups:
            return False
        
        if point_id in self._point_groups[group_name]:
            self._point_groups[group_name].remove(point_id)
            return True
        
        return False
    
    def get_group_points(self, group_name: str) -> List[AnnotationPoint]:
        """Get points in a group."""
        if group_name not in self._point_groups:
            return []
        
        return [self._points[pid] for pid in self._point_groups[group_name] if pid in self._points]
    
    def delete_group(self, group_name: str) -> bool:
        """Delete a group."""
        if group_name in self._point_groups:
            del self._point_groups[group_name]
            self.emit_state_changed({'groups_count': len(self._point_groups)})
            return True
        return False
    
    def get_group_names(self) -> List[str]:
        """Get all group names."""
        return list(self._point_groups.keys())
    
    # Tagging operations
    def add_tag(self, point_id: str, tag: str) -> bool:
        """Add tag to point."""
        if point_id not in self._points:
            return False
        
        if point_id not in self._point_tags:
            self._point_tags[point_id] = []
        
        if tag not in self._point_tags[point_id]:
            self._point_tags[point_id].append(tag)
        
        return True
    
    def remove_tag(self, point_id: str, tag: str) -> bool:
        """Remove tag from point."""
        if point_id not in self._point_tags:
            return False
        
        if tag in self._point_tags[point_id]:
            self._point_tags[point_id].remove(tag)
            return True
        
        return False
    
    def get_point_tags(self, point_id: str) -> List[str]:
        """Get tags for a point."""
        return self._point_tags.get(point_id, [])
    
    def get_points_with_tag(self, tag: str) -> List[AnnotationPoint]:
        """Get points with specific tag."""
        points = []
        for point_id, tags in self._point_tags.items():
            if tag in tags and point_id in self._points:
                points.append(self._points[point_id])
        return points
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        for point_tags in self._point_tags.values():
            tags.update(point_tags)
        return sorted(list(tags))
    
    # Filtering operations
    def add_filter(self, filter_name: str, filter_func: Callable[[AnnotationPoint], bool]) -> None:
        """Add a filter function."""
        self._active_filters[filter_name] = filter_func
        self.filterChanged.emit(filter_name)
    
    def remove_filter(self, filter_name: str) -> bool:
        """Remove a filter."""
        if filter_name in self._active_filters:
            del self._active_filters[filter_name]
            self.filterChanged.emit(filter_name)
            return True
        return False
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        self._active_filters.clear()
        self.filterChanged.emit("all")
    
    def get_active_filters(self) -> List[str]:
        """Get names of active filters."""
        return list(self._active_filters.keys())
    
    def set_sort_function(self, sort_func: Optional[Callable[[List[AnnotationPoint]], List[AnnotationPoint]]]) -> None:
        """Set sort function."""
        self._sort_function = sort_func
    
    # Batch operations
    def batch_update_class(self, point_ids: List[str], new_class_id: int) -> int:
        """Update class for multiple points."""
        # Save state for undo
        self._save_state("batch_update_class", point_ids)
        
        updated_count = 0
        for point_id in point_ids:
            if self.change_point_class(point_id, new_class_id):
                updated_count += 1
        
        if updated_count > 0:
            self.pointsChanged.emit()
            self.batchOperationCompleted.emit("update_class", updated_count)
        
        return updated_count
    
    def batch_move_points(self, point_ids: List[str], offset: QPointF) -> int:
        """Move multiple points by offset."""
        # Save state for undo
        self._save_state("batch_move_points", point_ids)
        
        updated_count = 0
        for point_id in point_ids:
            if point_id in self._points:
                point = self._points[point_id]
                new_pos = QPointF(point.x + offset.x(), point.y + offset.y())
                if self.move_point(point_id, new_pos):
                    updated_count += 1
        
        if updated_count > 0:
            self.pointsChanged.emit()
            self.batchOperationCompleted.emit("move_points", updated_count)
        
        return updated_count
    
    def batch_delete_points(self, point_ids: List[str]) -> int:
        """Delete multiple points."""
        # Save state for undo
        self._save_state("batch_delete_points", point_ids)
        
        deleted_count = 0
        for point_id in point_ids:
            if self.remove_point(point_id):
                deleted_count += 1
        
        if deleted_count > 0:
            self.batchOperationCompleted.emit("delete_points", deleted_count)
        
        return deleted_count
    
    def batch_set_confidence(self, point_ids: List[str], confidence: float) -> int:
        """Set confidence for multiple points."""
        # Save state for undo
        self._save_state("batch_set_confidence", point_ids)
        
        updated_count = 0
        for point_id in point_ids:
            if self.set_point_confidence(point_id, confidence):
                updated_count += 1
        
        if updated_count > 0:
            self.pointsChanged.emit()
            self.batchOperationCompleted.emit("set_confidence", updated_count)
        
        return updated_count
    
    # Selection operations
    def select_points_by_class(self, class_id: int) -> List[str]:
        """Select points by class."""
        selected_ids = []
        for point_id, point in self._points.items():
            if point.class_id == class_id:
                selected_ids.append(point_id)
        return selected_ids
    
    def select_points_in_region(self, top_left: QPointF, bottom_right: QPointF) -> List[str]:
        """Select points in rectangular region."""
        selected_ids = []
        for point_id, point in self._points.items():
            if (top_left.x() <= point.x <= bottom_right.x() and
                top_left.y() <= point.y <= bottom_right.y()):
                selected_ids.append(point_id)
        return selected_ids
    
    def select_points_by_confidence(self, min_confidence: float, max_confidence: float = 1.0) -> List[str]:
        """Select points by confidence range."""
        selected_ids = []
        for point_id, point in self._points.items():
            if min_confidence <= point.confidence <= max_confidence:
                selected_ids.append(point_id)
        return selected_ids
    
    def select_points_by_source(self, source: str) -> List[str]:
        """Select points by source."""
        selected_ids = []
        for point_id, point in self._points.items():
            if point.source == source:
                selected_ids.append(point_id)
        return selected_ids
    
    # Analysis operations
    def get_class_distribution(self) -> Dict[int, int]:
        """Get distribution of points by class."""
        if self._cache_dirty:
            self._update_analysis_cache()
        return self._analysis_cache.get('class_distribution', {})
    
    def get_confidence_statistics(self) -> Dict[str, float]:
        """Get confidence statistics."""
        if self._cache_dirty:
            self._update_analysis_cache()
        return self._analysis_cache.get('confidence_stats', {})
    
    def get_spatial_bounds(self) -> Tuple[float, float, float, float]:
        """Get spatial bounds of all points."""
        if not self._points:
            return (0, 0, 0, 0)
        
        points = list(self._points.values())
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)
        
        return (min_x, min_y, max_x, max_y)
    
    def get_density_analysis(self, grid_size: int = 50) -> Dict[str, Any]:
        """Get density analysis."""
        if self._cache_dirty:
            self._update_analysis_cache()
        
        cache_key = f'density_{grid_size}'
        if cache_key not in self._analysis_cache:
            self._analysis_cache[cache_key] = self._calculate_density_analysis(grid_size)
        
        return self._analysis_cache[cache_key]
    
    def get_nearest_neighbors(self, point_id: str, k: int = 5) -> List[Tuple[str, float]]:
        """Get k nearest neighbors for a point."""
        if point_id not in self._points:
            return []
        
        target_point = self._points[point_id]
        distances = []
        
        for other_id, other_point in self._points.items():
            if other_id != point_id:
                distance = ((target_point.x - other_point.x) ** 2 + 
                           (target_point.y - other_point.y) ** 2) ** 0.5
                distances.append((other_id, distance))
        
        # Sort by distance and return top k
        distances.sort(key=lambda x: x[1])
        return distances[:k]
    
    # Undo/Redo operations
    def undo(self) -> bool:
        """Undo last operation."""
        if self._history_index < 0:
            return False
        
        state = self._history[self._history_index]
        self._restore_state(state)
        self._history_index -= 1
        
        self.pointsChanged.emit()
        self.emit_state_changed({'can_undo': self.can_undo(), 'can_redo': self.can_redo()})
        
        return True
    
    def redo(self) -> bool:
        """Redo last undone operation."""
        if self._history_index >= len(self._history) - 1:
            return False
        
        self._history_index += 1
        state = self._history[self._history_index]
        self._restore_state(state)
        
        self.pointsChanged.emit()
        self.emit_state_changed({'can_undo': self.can_undo(), 'can_redo': self.can_redo()})
        
        return True
    
    def can_undo(self) -> bool:
        """Check if can undo."""
        return self._history_index >= 0
    
    def can_redo(self) -> bool:
        """Check if can redo."""
        return self._history_index < len(self._history) - 1
    
    def clear_history(self) -> None:
        """Clear undo/redo history."""
        self._history.clear()
        self._history_index = -1
        self.emit_state_changed({'can_undo': False, 'can_redo': False})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get point manager statistics."""
        return {
            'total_points': len(self._points),
            'groups_count': len(self._point_groups),
            'tags_count': len(self.get_all_tags()),
            'active_filters': len(self._active_filters),
            'class_distribution': self.get_class_distribution(),
            'confidence_stats': self.get_confidence_statistics(),
            'spatial_bounds': self.get_spatial_bounds(),
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'history_size': len(self._history),
            'cache_dirty': self._cache_dirty
        }
    
    # Private methods
    def _save_state(self, operation: str, affected_ids: Any = None) -> None:
        """Save current state for undo."""
        state = {
            'operation': operation,
            'timestamp': time.time(),
            'points': {pid: self._serialize_point(point) for pid, point in self._points.items()},
            'groups': dict(self._point_groups),
            'tags': dict(self._point_tags),
            'affected_ids': affected_ids
        }
        
        # Remove any states after current index
        self._history = self._history[:self._history_index + 1]
        
        # Add new state
        self._history.append(state)
        self._history_index += 1
        
        # Limit history size
        if len(self._history) > self._max_history_size:
            self._history.pop(0)
            self._history_index -= 1
    
    def _restore_state(self, state: Dict[str, Any]) -> None:
        """Restore state from history."""
        # Restore points
        self._points.clear()
        for point_id, point_data in state['points'].items():
            self._points[point_id] = self._deserialize_point(point_data)
        
        # Restore groups and tags
        self._point_groups = dict(state['groups'])
        self._point_tags = dict(state['tags'])
        
        self._invalidate_cache()
    
    def _serialize_point(self, point: AnnotationPoint) -> Dict[str, Any]:
        """Serialize point for history."""
        return point.to_dict()
    
    def _deserialize_point(self, data: Dict[str, Any]) -> AnnotationPoint:
        """Deserialize point from history."""
        return AnnotationPoint.from_dict(data)
    
    def _invalidate_cache(self) -> None:
        """Invalidate analysis cache."""
        self._cache_dirty = True
        self._analysis_cache.clear()
    
    def _update_analysis_cache(self) -> None:
        """Update analysis cache."""
        points = list(self._points.values())
        
        # Class distribution
        class_dist = {}
        for point in points:
            class_dist[point.class_id] = class_dist.get(point.class_id, 0) + 1
        
        # Confidence statistics
        confidences = [p.confidence for p in points]
        if confidences:
            conf_stats = {
                'mean': sum(confidences) / len(confidences),
                'min': min(confidences),
                'max': max(confidences),
                'std': (sum((c - sum(confidences) / len(confidences)) ** 2 for c in confidences) / len(confidences)) ** 0.5
            }
        else:
            conf_stats = {'mean': 0, 'min': 0, 'max': 0, 'std': 0}
        
        self._analysis_cache.update({
            'class_distribution': class_dist,
            'confidence_stats': conf_stats
        })
        
        self._cache_dirty = False
    
    def _calculate_density_analysis(self, grid_size: int) -> Dict[str, Any]:
        """Calculate density analysis."""
        if not self._points:
            return {'grid_size': grid_size, 'density': [], 'bounds': (0, 0, 0, 0)}
        
        # Get bounds
        min_x, min_y, max_x, max_y = self.get_spatial_bounds()
        
        # Create grid
        cell_width = (max_x - min_x) / grid_size if max_x > min_x else 1
        cell_height = (max_y - min_y) / grid_size if max_y > min_y else 1
        
        density = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Count points in each cell
        for point in self._points.values():
            grid_x = int((point.x - min_x) / cell_width)
            grid_y = int((point.y - min_y) / cell_height)
            
            # Clamp to grid bounds
            grid_x = max(0, min(grid_size - 1, grid_x))
            grid_y = max(0, min(grid_size - 1, grid_y))
            
            density[grid_y][grid_x] += 1
        
        return {
            'grid_size': grid_size,
            'density': density,
            'bounds': (min_x, min_y, max_x, max_y),
            'cell_size': (cell_width, cell_height)
        }