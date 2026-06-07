"""
Spatial Index for Efficient Point Lookup
Implements R-tree spatial indexing for fast annotation point queries.
Based on the legacy ABILIUS optimization roadmap.
"""

import math
import threading
from typing import List, Tuple, Optional, Any, Dict, Set
from dataclasses import dataclass, field


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside bounding box."""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this box intersects with another."""
        return not (self.max_x < other.min_x or self.min_x > other.max_x or
                   self.max_y < other.min_y or self.min_y > other.max_y)
    
    def distance_to_point(self, x: float, y: float) -> float:
        """Calculate minimum distance from point to bounding box."""
        dx = max(0, max(self.min_x - x, x - self.max_x))
        dy = max(0, max(self.min_y - y, y - self.max_y))
        return math.sqrt(dx * dx + dy * dy)
    
    def area(self) -> float:
        """Calculate area of bounding box."""
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)
    
    def expand(self, margin: float) -> 'BoundingBox':
        """Expand bounding box by margin."""
        return BoundingBox(
            self.min_x - margin, self.min_y - margin,
            self.max_x + margin, self.max_y + margin
        )
    
    def union(self, other: 'BoundingBox') -> 'BoundingBox':
        """Create union of two bounding boxes."""
        return BoundingBox(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y)
        )


@dataclass
class SpatialPoint:
    """Point with spatial coordinates and associated data."""
    x: float
    y: float
    data: Any
    id: Optional[str] = None
    
    def distance_to(self, x: float, y: float) -> float:
        """Calculate distance to another point."""
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
    
    def bounding_box(self, margin: float = 0.0) -> BoundingBox:
        """Get bounding box for this point."""
        return BoundingBox(
            self.x - margin, self.y - margin,
            self.x + margin, self.y + margin
        )


@dataclass
class SpatialNode:
    """Node in the spatial index tree."""
    bbox: BoundingBox
    is_leaf: bool = False
    points: List[SpatialPoint] = field(default_factory=list)
    children: List['SpatialNode'] = field(default_factory=list)
    parent: Optional['SpatialNode'] = None
    
    def add_point(self, point: SpatialPoint) -> None:
        """Add point to this node."""
        if self.is_leaf:
            self.points.append(point)
        else:
            # Find best child to insert into
            best_child = self._choose_child(point)
            best_child.add_point(point)
    
    def _choose_child(self, point: SpatialPoint) -> 'SpatialNode':
        """Choose best child node for insertion."""
        best_child = None
        min_enlargement = float('inf')
        
        for child in self.children:
            # Calculate enlargement needed
            point_bbox = point.bounding_box()
            union_bbox = child.bbox.union(point_bbox)
            enlargement = union_bbox.area() - child.bbox.area()
            
            if enlargement < min_enlargement:
                min_enlargement = enlargement
                best_child = child
        
        return best_child or self.children[0]
    
    def update_bbox(self) -> None:
        """Update bounding box based on children/points."""
        if self.is_leaf and self.points:
            # Calculate bbox from points
            min_x = min(p.x for p in self.points)
            min_y = min(p.y for p in self.points)
            max_x = max(p.x for p in self.points)
            max_y = max(p.y for p in self.points)
            self.bbox = BoundingBox(min_x, min_y, max_x, max_y)
        elif self.children:
            # Calculate bbox from children
            child_bboxes = [child.bbox for child in self.children]
            min_x = min(bbox.min_x for bbox in child_bboxes)
            min_y = min(bbox.min_y for bbox in child_bboxes)
            max_x = max(bbox.max_x for bbox in child_bboxes)
            max_y = max(bbox.max_y for bbox in child_bboxes)
            self.bbox = BoundingBox(min_x, min_y, max_x, max_y)


class SpatialIndex:
    """R-tree spatial index for efficient point queries."""
    
    def __init__(self, max_points_per_node: int = 10, max_children_per_node: int = 4):
        """
        Initialize spatial index.
        
        Args:
            max_points_per_node: Maximum points per leaf node before splitting
            max_children_per_node: Maximum children per internal node before splitting
        """
        self.max_points_per_node = max_points_per_node
        self.max_children_per_node = max_children_per_node
        self.root: Optional[SpatialNode] = None
        self.point_count = 0
        self.height = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance tracking
        self.query_count = 0
        self.total_nodes_visited = 0
        self.insertion_count = 0
        self.deletion_count = 0
    
    def insert(self, point: SpatialPoint) -> None:
        """Insert point into spatial index."""
        with self._lock:
            try:
                if self.root is None:
                    # Create root node
                    self.root = SpatialNode(
                        bbox=point.bounding_box(),
                        is_leaf=True
                    )
                    self.height = 1
                
                # Insert point
                self._insert_point(self.root, point)
                self.point_count += 1
                self.insertion_count += 1
                
            except Exception as e:
                raise RuntimeError(f"Error inserting point: {str(e)}")
    
    def _insert_point(self, node: SpatialNode, point: SpatialPoint) -> None:
        """Insert point into specific node."""
        if node.is_leaf:
            # Add to leaf node
            node.points.append(point)
            node.update_bbox()
            
            # Split if necessary
            if len(node.points) > self.max_points_per_node:
                self._split_leaf_node(node)
        else:
            # Find best child
            best_child = node._choose_child(point)
            self._insert_point(best_child, point)
            
            # Update bbox
            node.update_bbox()
            
            # Split if necessary
            if len(node.children) > self.max_children_per_node:
                self._split_internal_node(node)
    
    def _split_leaf_node(self, node: SpatialNode) -> None:
        """Split leaf node when it has too many points."""
        if node.parent is None:
            # Create new root
            new_root = SpatialNode(bbox=node.bbox, is_leaf=False)
            new_root.children.append(node)
            node.parent = new_root
            self.root = new_root
            self.height += 1
        
        # Create new leaf node
        new_node = SpatialNode(bbox=BoundingBox(0, 0, 0, 0), is_leaf=True)
        new_node.parent = node.parent
        
        # Simple split: divide points roughly in half
        mid_point = len(node.points) // 2
        new_node.points = node.points[mid_point:]
        node.points = node.points[:mid_point]
        
        # Update bounding boxes
        node.update_bbox()
        new_node.update_bbox()
        
        # Add new node to parent
        node.parent.children.append(new_node)
    
    def _split_internal_node(self, node: SpatialNode) -> None:
        """Split internal node when it has too many children."""
        if node.parent is None:
            # Create new root
            new_root = SpatialNode(bbox=node.bbox, is_leaf=False)
            new_root.children.append(node)
            node.parent = new_root
            self.root = new_root
            self.height += 1
        
        # Create new internal node
        new_node = SpatialNode(bbox=BoundingBox(0, 0, 0, 0), is_leaf=False)
        new_node.parent = node.parent
        
        # Simple split: divide children roughly in half
        mid_point = len(node.children) // 2
        new_node.children = node.children[mid_point:]
        node.children = node.children[:mid_point]
        
        # Update parent references
        for child in new_node.children:
            child.parent = new_node
        
        # Update bounding boxes
        node.update_bbox()
        new_node.update_bbox()
        
        # Add new node to parent
        node.parent.children.append(new_node)
    
    def query_point(self, x: float, y: float, max_distance: float = 0.0) -> List[SpatialPoint]:
        """
        Query points within distance of given coordinates.
        
        Args:
            x: Query x coordinate
            y: Query y coordinate
            max_distance: Maximum distance (0.0 for exact match)
            
        Returns:
            List of points within distance
        """
        with self._lock:
            if self.root is None:
                return []
            
            self.query_count += 1
            results = []
            nodes_visited = 0
            
            # Create query bounding box
            query_bbox = BoundingBox(
                x - max_distance, y - max_distance,
                x + max_distance, y + max_distance
            )
            
            def _query_node(node: SpatialNode) -> None:
                nonlocal nodes_visited
                nodes_visited += 1
                
                # Check if node bbox intersects query bbox
                if not node.bbox.intersects(query_bbox):
                    return
                
                if node.is_leaf:
                    # Check points in leaf node
                    for point in node.points:
                        if max_distance == 0.0:
                            # Exact match
                            if point.x == x and point.y == y:
                                results.append(point)
                        else:
                            # Distance check
                            if point.distance_to(x, y) <= max_distance:
                                results.append(point)
                else:
                    # Recurse into children
                    for child in node.children:
                        _query_node(child)
            
            _query_node(self.root)
            self.total_nodes_visited += nodes_visited
            
            return results
    
    def query_nearest(self, x: float, y: float, k: int = 1) -> List[SpatialPoint]:
        """
        Query k nearest points to given coordinates.
        
        Args:
            x: Query x coordinate
            y: Query y coordinate
            k: Number of nearest points to return
            
        Returns:
            List of k nearest points, sorted by distance
        """
        if self.root is None:
            return []
        
        self.query_count += 1
        candidates = []
        nodes_visited = 0
        
        def _query_node(node: SpatialNode) -> None:
            nonlocal nodes_visited
            nodes_visited += 1
            
            if node.is_leaf:
                # Add all points as candidates
                for point in node.points:
                    distance = point.distance_to(x, y)
                    candidates.append((distance, point))
            else:
                # Add children with their minimum distances
                child_distances = []
                for child in node.children:
                    min_distance = child.bbox.distance_to_point(x, y)
                    child_distances.append((min_distance, child))
                
                # Sort by distance and recurse
                child_distances.sort(key=lambda x: x[0])
                for _, child in child_distances:
                    _query_node(child)
        
        _query_node(self.root)
        self.total_nodes_visited += nodes_visited
        
        # Sort candidates by distance and return top k
        candidates.sort()
        return [point for _, point in candidates[:k]]
    
    def query_region(self, bbox: BoundingBox) -> List[SpatialPoint]:
        """
        Query all points within a bounding box region.
        
        Args:
            bbox: Query bounding box
            
        Returns:
            List of points within the region
        """
        if self.root is None:
            return []
        
        self.query_count += 1
        results = []
        nodes_visited = 0
        
        def _query_node(node: SpatialNode) -> None:
            nonlocal nodes_visited
            nodes_visited += 1
            
            # Check if node bbox intersects query bbox
            if not node.bbox.intersects(bbox):
                return
            
            if node.is_leaf:
                # Check points in leaf node
                for point in node.points:
                    if bbox.contains(point.x, point.y):
                        results.append(point)
            else:
                # Recurse into children
                for child in node.children:
                    _query_node(child)
        
        _query_node(self.root)
        self.total_nodes_visited += nodes_visited
        
        return results
    
    def remove(self, point: SpatialPoint) -> bool:
        """
        Remove point from spatial index.
        
        Args:
            point: Point to remove
            
        Returns:
            True if point was removed, False if not found
        """
        with self._lock:
            if self.root is None:
                return False
            
            removed = self._remove_point(self.root, point)
            if removed:
                self.point_count -= 1
                self.deletion_count += 1
            
            return removed
    
    def _remove_point(self, node: SpatialNode, point: SpatialPoint) -> bool:
        """Remove point from specific node."""
        if node.is_leaf:
            # Try to remove from leaf node
            for i, p in enumerate(node.points):
                if p.x == point.x and p.y == point.y and p.data == point.data:
                    node.points.pop(i)
                    node.update_bbox()
                    return True
            return False
        else:
            # Try to remove from children
            for child in node.children:
                if child.bbox.contains(point.x, point.y):
                    if self._remove_point(child, point):
                        node.update_bbox()
                        return True
            return False
    
    def clear(self) -> None:
        """Clear all points from the index."""
        with self._lock:
            self.root = None
            self.point_count = 0
            self.height = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance and structure statistics."""
        return {
            'point_count': self.point_count,
            'height': self.height,
            'query_count': self.query_count,
            'insertion_count': self.insertion_count,
            'deletion_count': self.deletion_count,
            'total_nodes_visited': self.total_nodes_visited,
            'avg_nodes_per_query': self.total_nodes_visited / max(1, self.query_count),
            'max_points_per_node': self.max_points_per_node,
            'max_children_per_node': self.max_children_per_node
        }
    
    def validate(self) -> List[str]:
        """Validate index structure and return any errors."""
        errors = []
        
        if self.root is None:
            return errors
        
        def _validate_node(node: SpatialNode, level: int) -> None:
            # Check leaf node constraints
            if node.is_leaf:
                if len(node.points) > self.max_points_per_node:
                    errors.append(f"Leaf node at level {level} has {len(node.points)} points (max {self.max_points_per_node})")
                
                # Check all points are within bbox
                for point in node.points:
                    if not node.bbox.contains(point.x, point.y):
                        errors.append(f"Point ({point.x}, {point.y}) not within node bbox at level {level}")
            
            # Check internal node constraints
            else:
                if len(node.children) > self.max_children_per_node:
                    errors.append(f"Internal node at level {level} has {len(node.children)} children (max {self.max_children_per_node})")
                
                # Check all children bboxes are within parent bbox
                for child in node.children:
                    if not node.bbox.intersects(child.bbox):
                        errors.append(f"Child bbox not within parent bbox at level {level}")
                    
                    # Recurse
                    _validate_node(child, level + 1)
        
        _validate_node(self.root, 0)
        return errors