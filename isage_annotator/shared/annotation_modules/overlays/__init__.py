"""
Overlay Components - Visual overlays for annotations

This module contains overlay components:
- prediction_overlay: Model prediction visualization
- ground_truth_overlay: Dense ground truth overlay
- mistake_overlay: Prediction vs ground truth comparison
- grid_overlay: Grid lines for alignment
- channel_mapper: Multi-spectral channel mapping
"""

from .base_overlay import BaseOverlay, OverlayProtocol

__all__ = [
    'BaseOverlay',
    'OverlayProtocol'
]