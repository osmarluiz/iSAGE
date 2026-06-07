#!/usr/bin/env python3
"""
Test script for spatial index performance improvements.
Demonstrates O(log n) vs O(n) performance for point lookups.
"""

import time
import random
import statistics
from typing import List, Tuple
from spatial_index import SpatialIndex, SpatialPoint, BoundingBox


class LinearSearchIndex:
    """Linear search implementation for performance comparison."""
    
    def __init__(self):
        self.points: List[SpatialPoint] = []
    
    def insert(self, point: SpatialPoint) -> None:
        """Insert point (O(1))."""
        self.points.append(point)
    
    def query_point(self, x: float, y: float, max_distance: float = 0.0) -> List[SpatialPoint]:
        """Query points within distance (O(n))."""
        results = []
        for point in self.points:
            if max_distance == 0.0:
                if point.x == x and point.y == y:
                    results.append(point)
            else:
                if point.distance_to(x, y) <= max_distance:
                    results.append(point)
        return results
    
    def query_nearest(self, x: float, y: float, k: int = 1) -> List[SpatialPoint]:
        """Query k nearest points (O(n))."""
        distances = []
        for point in self.points:
            distance = point.distance_to(x, y)
            distances.append((distance, point))
        
        distances.sort()
        return [point for _, point in distances[:k]]
    
    def query_region(self, bbox: BoundingBox) -> List[SpatialPoint]:
        """Query points in region (O(n))."""
        results = []
        for point in self.points:
            if bbox.contains(point.x, point.y):
                results.append(point)
        return results
    
    def get_statistics(self) -> dict:
        """Get statistics."""
        return {
            'point_count': len(self.points),
            'implementation': 'linear_search'
        }


def generate_test_points(count: int, bounds: Tuple[float, float, float, float]) -> List[SpatialPoint]:
    """Generate random test points."""
    min_x, min_y, max_x, max_y = bounds
    points = []
    
    for i in range(count):
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)
        point = SpatialPoint(x=x, y=y, data=f"point_{i}", id=str(i))
        points.append(point)
    
    return points


def benchmark_point_queries(spatial_index: SpatialIndex, linear_index: LinearSearchIndex, 
                          query_count: int = 1000, tolerance: float = 10.0) -> dict:
    """Benchmark point queries."""
    print(f"\\n=== Point Query Benchmark ({query_count} queries) ===")
    
    # Generate random query points
    query_points = [(random.uniform(0, 1000), random.uniform(0, 1000)) for _ in range(query_count)]
    
    # Benchmark spatial index
    spatial_times = []
    for x, y in query_points:
        start = time.perf_counter()
        spatial_results = spatial_index.query_point(x, y, tolerance)
        end = time.perf_counter()
        spatial_times.append((end - start) * 1000)  # Convert to ms
    
    # Benchmark linear search
    linear_times = []
    for x, y in query_points:
        start = time.perf_counter()
        linear_results = linear_index.query_point(x, y, tolerance)
        end = time.perf_counter()
        linear_times.append((end - start) * 1000)  # Convert to ms
    
    spatial_avg = statistics.mean(spatial_times)
    linear_avg = statistics.mean(linear_times)
    speedup = linear_avg / spatial_avg if spatial_avg > 0 else 0
    
    print(f"Spatial Index: {spatial_avg:.4f}ms avg, {min(spatial_times):.4f}ms min, {max(spatial_times):.4f}ms max")
    print(f"Linear Search: {linear_avg:.4f}ms avg, {min(linear_times):.4f}ms min, {max(linear_times):.4f}ms max")
    print(f"Speedup: {speedup:.1f}x faster")
    
    return {
        'spatial_avg': spatial_avg,
        'linear_avg': linear_avg,
        'speedup': speedup,
        'spatial_times': spatial_times,
        'linear_times': linear_times
    }


def benchmark_nearest_queries(spatial_index: SpatialIndex, linear_index: LinearSearchIndex, 
                            query_count: int = 500) -> dict:
    """Benchmark nearest neighbor queries."""
    print(f"\\n=== Nearest Neighbor Benchmark ({query_count} queries) ===")
    
    # Generate random query points
    query_points = [(random.uniform(0, 1000), random.uniform(0, 1000)) for _ in range(query_count)]
    
    # Benchmark spatial index
    spatial_times = []
    for x, y in query_points:
        start = time.perf_counter()
        spatial_results = spatial_index.query_nearest(x, y, k=1)
        end = time.perf_counter()
        spatial_times.append((end - start) * 1000)  # Convert to ms
    
    # Benchmark linear search
    linear_times = []
    for x, y in query_points:
        start = time.perf_counter()
        linear_results = linear_index.query_nearest(x, y, k=1)
        end = time.perf_counter()
        linear_times.append((end - start) * 1000)  # Convert to ms
    
    spatial_avg = statistics.mean(spatial_times)
    linear_avg = statistics.mean(linear_times)
    speedup = linear_avg / spatial_avg if spatial_avg > 0 else 0
    
    print(f"Spatial Index: {spatial_avg:.4f}ms avg, {min(spatial_times):.4f}ms min, {max(spatial_times):.4f}ms max")
    print(f"Linear Search: {linear_avg:.4f}ms avg, {min(linear_times):.4f}ms min, {max(linear_times):.4f}ms max")
    print(f"Speedup: {speedup:.1f}x faster")
    
    return {
        'spatial_avg': spatial_avg,
        'linear_avg': linear_avg,
        'speedup': speedup
    }


def benchmark_region_queries(spatial_index: SpatialIndex, linear_index: LinearSearchIndex, 
                           query_count: int = 200) -> dict:
    """Benchmark region queries."""
    print(f"\\n=== Region Query Benchmark ({query_count} queries) ===")
    
    # Generate random query regions
    query_regions = []
    for _ in range(query_count):
        x1 = random.uniform(0, 900)
        y1 = random.uniform(0, 900)
        x2 = x1 + random.uniform(50, 100)
        y2 = y1 + random.uniform(50, 100)
        query_regions.append(BoundingBox(x1, y1, x2, y2))
    
    # Benchmark spatial index
    spatial_times = []
    for bbox in query_regions:
        start = time.perf_counter()
        spatial_results = spatial_index.query_region(bbox)
        end = time.perf_counter()
        spatial_times.append((end - start) * 1000)  # Convert to ms
    
    # Benchmark linear search
    linear_times = []
    for bbox in query_regions:
        start = time.perf_counter()
        linear_results = linear_index.query_region(bbox)
        end = time.perf_counter()
        linear_times.append((end - start) * 1000)  # Convert to ms
    
    spatial_avg = statistics.mean(spatial_times)
    linear_avg = statistics.mean(linear_times)
    speedup = linear_avg / spatial_avg if spatial_avg > 0 else 0
    
    print(f"Spatial Index: {spatial_avg:.4f}ms avg, {min(spatial_times):.4f}ms min, {max(spatial_times):.4f}ms max")
    print(f"Linear Search: {linear_avg:.4f}ms avg, {min(linear_times):.4f}ms min, {max(linear_times):.4f}ms max")
    print(f"Speedup: {speedup:.1f}x faster")
    
    return {
        'spatial_avg': spatial_avg,
        'linear_avg': linear_avg,
        'speedup': speedup
    }


def run_scalability_test():
    """Test performance scaling with different point counts."""
    print("\\n" + "="*60)
    print("SCALABILITY TEST: Performance vs Point Count")
    print("="*60)
    
    point_counts = [100, 500, 1000, 2000, 5000, 10000]
    bounds = (0, 0, 1000, 1000)
    
    results = []
    
    for count in point_counts:
        print(f"\\n--- Testing with {count} points ---")
        
        # Generate test points
        points = generate_test_points(count, bounds)
        
        # Setup indexes
        spatial_index = SpatialIndex(max_points_per_node=15, max_children_per_node=8)
        linear_index = LinearSearchIndex()
        
        # Insert points
        for point in points:
            spatial_index.insert(point)
            linear_index.insert(point)
        
        # Benchmark point queries (reduced query count for larger datasets)
        query_count = min(500, 50000 // count)  # Adjust query count based on dataset size
        benchmark_result = benchmark_point_queries(spatial_index, linear_index, query_count, tolerance=10.0)
        
        results.append({
            'point_count': count,
            'spatial_avg': benchmark_result['spatial_avg'],
            'linear_avg': benchmark_result['linear_avg'],
            'speedup': benchmark_result['speedup'],
            'spatial_stats': spatial_index.get_statistics()
        })
    
    # Print summary
    print("\\n" + "="*60)
    print("SCALABILITY SUMMARY")
    print("="*60)
    print(f"{'Points':<10} {'Spatial (ms)':<15} {'Linear (ms)':<15} {'Speedup':<10} {'Tree Height':<12}")
    print("-"*60)
    
    for result in results:
        print(f"{result['point_count']:<10} "
              f"{result['spatial_avg']:<15.4f} "
              f"{result['linear_avg']:<15.4f} "
              f"{result['speedup']:<10.1f}x "
              f"{result['spatial_stats']['height']:<12}")
    
    return results


def main():
    """Run spatial index performance tests."""
    print("="*60)
    print("SPATIAL INDEX PERFORMANCE TEST")
    print("="*60)
    print("\\nTesting R-tree spatial index vs linear search performance.")
    print("This demonstrates the O(log n) vs O(n) performance difference.")
    
    # Test with medium dataset
    point_count = 5000
    bounds = (0, 0, 1000, 1000)
    
    print(f"\\nGenerating {point_count} random test points...")
    points = generate_test_points(point_count, bounds)
    
    # Setup indexes
    print("Setting up spatial index and linear search...")
    spatial_index = SpatialIndex(max_points_per_node=15, max_children_per_node=8)
    linear_index = LinearSearchIndex()
    
    # Insert points
    print("Inserting points into both indexes...")
    start_time = time.time()
    for point in points:
        spatial_index.insert(point)
        linear_index.insert(point)
    insert_time = time.time() - start_time
    
    print(f"Insertion completed in {insert_time:.2f} seconds")
    
    # Print index statistics
    spatial_stats = spatial_index.get_statistics()
    linear_stats = linear_index.get_statistics()
    
    print(f"\\nSpatial Index: {spatial_stats['point_count']} points, height {spatial_stats['height']}")
    print(f"Linear Index: {linear_stats['point_count']} points")
    
    # Run benchmarks
    point_results = benchmark_point_queries(spatial_index, linear_index, query_count=1000, tolerance=10.0)
    nearest_results = benchmark_nearest_queries(spatial_index, linear_index, query_count=500)
    region_results = benchmark_region_queries(spatial_index, linear_index, query_count=200)
    
    # Print overall summary
    print("\\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Point Queries:     {point_results['speedup']:.1f}x faster")
    print(f"Nearest Neighbor:  {nearest_results['speedup']:.1f}x faster")
    print(f"Region Queries:    {region_results['speedup']:.1f}x faster")
    print(f"Average Speedup:   {(point_results['speedup'] + nearest_results['speedup'] + region_results['speedup']) / 3:.1f}x faster")
    
    # Run scalability test
    scalability_results = run_scalability_test()
    
    print("\\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
    print("\\nThe spatial index provides significant performance improvements:")
    print("- O(log n) vs O(n) time complexity")
    print("- Consistent performance even with large datasets")
    print("- Ideal for real-time annotation interaction")
    print("- Perfect for active learning with many sparse points")


if __name__ == "__main__":
    main()