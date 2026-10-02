"""
MicroMind Platform Common Package
=================================

Shared platform-agnostic utilities.
"""

from .filesystem import (
    AtomicWriteError,
    Filesystem,
    FilesystemError,
    PathTraversalError,
)

__all__ = [
    "AtomicWriteError",
    "Filesystem",
    "FilesystemError",
    "PathTraversalError",
]
