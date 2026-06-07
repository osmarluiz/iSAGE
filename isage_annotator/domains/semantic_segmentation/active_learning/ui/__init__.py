"""
Active Learning UI Components

This module contains organized UI components for active learning functionality
within the semantic segmentation domain.

Directory Structure:
- session/: Session management, creation, and landing screens
- annotation/: Annotation interfaces and tools
- workflow/: Active learning workflow components
- components/: Reusable UI components
- navigation/: Navigation and layout components  
- integration/: External system integration
"""

# Don't automatically import widgets to avoid dependency chains
# Import them explicitly when needed

# For backward compatibility, keep the same exports
__all__ = ['ActiveLearningWidget']

# Lazy imports for backward compatibility
def _lazy_import():
    """Lazy import to maintain backward compatibility."""
    # These imports will be handled by the applications using the new paths
    pass