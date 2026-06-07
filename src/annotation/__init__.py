"""
Annotation Tool Integration

Provides annotation tool launcher for the iSAGE active learning workflow.
Uses the SharedModulesAnnotationWidget from isage_annotator/.
"""

from .launcher import launch_annotation_tool

__all__ = ['launch_annotation_tool']
