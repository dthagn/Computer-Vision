"""
Core image processing modules
"""

from .detection import detect_document
from .perspective import correct_perspective, apply_perspective_with_padding
from .enhancement import enhance_document
from .pipeline import (
    process_document,
    process_document_with_fallback,
    update_enhancement,
    get_default_enhancement_presets,
)


__all__ = [
    "detect_document",
    "correct_perspective",
    "apply_perspective_with_padding",
    "enhance_document",
    "process_document",
    "process_document_with_fallback",
    "update_enhancement",
    "get_default_enhancement_presets",
]
