"""
MicroMind Filesystem Abstraction
================================

Provides a safe, platform-agnostic filesystem interface with:
  * Path normalisation and validation.
  * Atomic writes (write-to-temp + rename).
  * Path traversal protection (reject paths that escape a base directory).

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * All filesystem operations are safe by default.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import BinaryIO, Optional, TextIO, Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FilesystemError(Exception):
    """Base exception for filesystem errors."""


class PathTraversalError(FilesystemError):
    """Raised when a path attempts to escape the allowed base directory."""


class AtomicWriteError(FilesystemError):
    """Raised when an atomic write operation fails."""


# ---------------------------------------------------------------------------
# Filesystem abstraction
# ---------------------------------------------------------------------------


class Filesystem:
    """
    Platform-agnostic filesystem abstraction with safety guarantees.

    Parameters
    ----------
    base_dir:
        Optional base directory.  When set, all path operations are
        resolved relative to this directory and path traversal outside
        it is blocked.
    """

    def __init__(self, base_dir: Optional[PathLike] = None) -> None:
        self._base_dir: Optional[Path] = None
        if base_dir is not None:
            self._base_dir = Path(base_dir).resolve()

    @property
    def base_dir(self) -> Optional[Path]:
        """Return the configured base directory, or ``None`` if unrestricted."""
        return self._base_dir

    # -- path resolution ---------------------------------------------------

    def resolve(self, path: PathLike) -> Path:
        """
        Resolve *path* to an absolute path.

        If a base directory is configured, *path* is resolved relative to
        it and the result is checked for path traversal.

        Raises
        ------
        PathTraversalError
            If the resolved path escapes the base directory.
        """
        p = Path(path)
        if self._base_dir is not None:
            if not p.is_absolute():
                p = self._base_dir / p
            resolved = p.resolve()
            try:
                resolved.relative_to(self._base_dir)
            except ValueError as exc:
                raise PathTraversalError(
                    f"Path {path!r} escapes base directory {self._base_dir}"
                ) from exc
            return resolved
        return p.resolve()

    def join(self, *parts: PathLike) -> Path:
        """Join path parts and resolve the result."""
        return self.resolve(Path(*parts))

    # -- existence checks --------------------------------------------------

    def exists(self, path: PathLike) -> bool:
        """Return ``True`` if *path* exists."""
        return self.resolve(path).exists()

    def is_file(self, path: PathLike) -> bool:
        """Return ``True`` if *path* exists and is a regular file."""
        return self.resolve(path).is_file()

    def is_dir(self, path: PathLike) -> bool:
        """Return ``True`` if *path* exists and is a directory."""
        return self.resolve(path).is_dir()

    # -- reading -----------------------------------------------------------

    def read_bytes(self, path: PathLike) -> bytes:
        """Read and return the entire contents of *path* as bytes."""
        resolved = self.resolve(path)
        return resolved.read_bytes()

    def read_text(self, path: PathLike, encoding: str = "utf-8") -> str:
        """Read and return the entire contents of *path* as text."""
        resolved = self.resolve(path)
        return resolved.read_text(encoding=encoding)

    def open_read(self, path: PathLike, mode: str = "r") -> Union[TextIO, BinaryIO]:
        """
        Open *path* for reading.

        Parameters
        ----------
        path:
            File path to open.
        mode:
            File mode (``"r"`` for text, ``"rb"`` for binary).
        """
        resolved = self.resolve(path)
        return open(resolved, mode)

    # -- writing -----------------------------------------------------------

    def write_bytes(self, path: PathLike, data: bytes) -> None:
        """Write *data* to *path* atomically."""
        self._atomic_write(path, data)

    def write_text(
        self,
        path: PathLike,
        data: str,
        encoding: str = "utf-8",
    ) -> None:
        """Write *data* to *path* atomically."""
        self._atomic_write(path, data.encode(encoding))

    def _atomic_write(self, path: PathLike, data: bytes) -> None:
        """
        Perform an atomic write to *path*.

        The data is first written to a temporary file in the same
        directory, then renamed to the target path.  This ensures that
        the target file is never in a partially-written state.

        Raises
        ------
        AtomicWriteError
            If the write or rename operation fails.
        """
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)

        tmp_path: Optional[Path] = None
        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=str(resolved.parent),
                prefix=f".{resolved.name}.",
                suffix=".tmp",
            )
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, resolved)
            tmp_path = None
        except OSError as exc:
            raise AtomicWriteError(
                f"Failed to atomically write {path}: {exc}"
            ) from exc
        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def open_write(self, path: PathLike, mode: str = "w") -> Union[TextIO, BinaryIO]:
        """
        Open *path* for writing.

        Note: this is NOT atomic.  Use :meth:`write_bytes` or
        :meth:`write_text` for atomic writes.
        """
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return open(resolved, mode)

    # -- deletion ----------------------------------------------------------

    def delete(self, path: PathLike) -> bool:
        """
        Delete *path* if it exists.

        Returns
        -------
        bool
            ``True`` if the file was deleted, ``False`` if it did not exist.
        """
        resolved = self.resolve(path)
        if not resolved.exists():
            return False
        if resolved.is_dir():
            resolved.rmdir()
        else:
            resolved.unlink()
        return True

    # -- directory listing -------------------------------------------------

    def list_dir(self, path: PathLike = ".") -> list[Path]:
        """
        List the contents of the directory at *path*.

        Returns a list of :class:`Path` objects for each entry.
        """
        resolved = self.resolve(path)
        if not resolved.is_dir():
            raise FilesystemError(f"{path!r} is not a directory")
        return list(resolved.iterdir())

    def glob(self, pattern: str, path: PathLike = ".") -> list[Path]:
        """
        Return paths matching *pattern* relative to *path*.
        """
        resolved = self.resolve(path)
        return list(resolved.glob(pattern))

    # -- path traversal protection ----------------------------------------

    def safe_path(self, path: PathLike) -> Path:
        """
        Return a safe path, raising if it would escape the base directory.

        This is an alias for :meth:`resolve` with a name that makes the
        intent explicit at call sites.
        """
        return self.resolve(path)

    def is_safe(self, path: PathLike) -> bool:
        """
        Return ``True`` if *path* is within the base directory.

        Always returns ``True`` when no base directory is configured.
        """
        if self._base_dir is None:
            return True
        try:
            self.resolve(path)
            return True
        except PathTraversalError:
            return False
