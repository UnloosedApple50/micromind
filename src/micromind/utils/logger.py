"""
MicroMind Logger
================

A structured logging utility with support for ERROR, WARN, INFO, DEBUG,
and AUDIT levels.  The logger automatically redacts sensitive fields
(passwords, API keys, tokens, secrets) to prevent accidental credential
leaks in log files.

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * Sensitive data is NEVER logged.
"""

from __future__ import annotations

import logging
import re
import sys
from enum import IntEnum
from typing import Any, Dict, List, Optional, Pattern, TextIO, Union


# ---------------------------------------------------------------------------
# Log levels
# ---------------------------------------------------------------------------


class LogLevel(IntEnum):
    """Custom log levels including AUDIT."""

    ERROR = logging.ERROR       # 40
    WARN = logging.WARNING     # 30
    INFO = logging.INFO       # 20
    DEBUG = logging.DEBUG     # 10
    AUDIT = 25                # Between INFO and WARNING – audit trail


# Register the custom AUDIT level with the standard logging module
logging.addLevelName(LogLevel.AUDIT.value, "AUDIT")


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_DEFAULT_SENSITIVE_KEYS: List[str] = [
    "password",
    "passwd",
    "pwd",
    "api_key",
    "apikey",
    "secret",
    "token",
    "auth_token",
    "access_token",
    "refresh_token",
    "private_key",
    "credential",
    "credentials",
]

_REDACTED_PLACEHOLDER: str = "***REDACTED***"


def _build_sensitive_pattern(keys: List[str]) -> Pattern[str]:
    """Build a regex pattern that matches sensitive key names."""
    escaped = [re.escape(k) for k in keys]
    # Match key=value, "key": "value", key: value, etc.
    pattern = r'(?i)(["\']?(?:' + "|".join(escaped) + r')["\']?\s*[:=]\s*["\']?)([^"\'\s,;}]+)'
    return re.compile(pattern)


# ---------------------------------------------------------------------------
# Logger class
# ---------------------------------------------------------------------------


class Logger:
    """
    Structured logger with secret redaction and AUDIT level support.

    Parameters
    ----------
    name:
        Logger name (typically ``__name__``).
    level:
        Minimum log level to emit.
    stream:
        Output stream.  Defaults to ``sys.stderr``.
    sensitive_keys:
        Additional key names to treat as sensitive beyond the defaults.
    """

    def __init__(
        self,
        name: str,
        level: Union[int, LogLevel] = LogLevel.INFO,
        stream: Optional[TextIO] = None,
        sensitive_keys: Optional[List[str]] = None,
    ) -> None:
        self._name = name
        self._level = int(level)
        self._stream = stream or sys.stderr
        self._sensitive_keys = list(_DEFAULT_SENSITIVE_KEYS)
        if sensitive_keys:
            self._sensitive_keys.extend(sensitive_keys)
        self._pattern = _build_sensitive_pattern(self._sensitive_keys)

        # Create the underlying standard logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._level)

        # Avoid adding duplicate handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler(self._stream)
            handler.setLevel(self._level)
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    @property
    def name(self) -> str:
        """Return the logger name."""
        return self._name

    @property
    def level(self) -> int:
        """Return the current log level."""
        return self._level

    def set_level(self, level: Union[int, LogLevel]) -> None:
        """Set the minimum log level."""
        self._level = int(level)
        self._logger.setLevel(self._level)
        for handler in self._logger.handlers:
            handler.setLevel(self._level)

    # -- redaction ---------------------------------------------------------

    def redact(self, message: str) -> str:
        """
        Redact sensitive values from *message*.

        Replaces values associated with sensitive keys with
        ``"***REDACTED***"``.
        """
        return self._pattern.sub(r"\1" + _REDACTED_PLACEHOLDER, message)

    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a copy of *data* with sensitive values redacted.
        """
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in [k.lower() for k in self._sensitive_keys]:
                result[key] = _REDACTED_PLACEHOLDER
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, str):
                result[key] = self.redact(value)
            else:
                result[key] = value
        return result

    # -- logging methods ---------------------------------------------------

    def log(self, level: Union[int, LogLevel], message: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the specified level with redaction applied."""
        redacted = self.redact(str(message))
        self._logger.log(int(level), redacted, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR message."""
        self.log(LogLevel.ERROR, message, *args, **kwargs)

    def warn(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a WARN message."""
        self.log(LogLevel.WARN, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Alias for :meth:`warn`."""
        self.warn(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an INFO message."""
        self.log(LogLevel.INFO, message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a DEBUG message."""
        self.log(LogLevel.DEBUG, message, *args, **kwargs)

    def audit(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an AUDIT message (security/compliance trail)."""
        self.log(LogLevel.AUDIT, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR message with exception information."""
        redacted = self.redact(str(message))
        self._logger.exception(redacted, *args, **kwargs)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_loggers: Dict[str, Logger] = {}


def get_logger(
    name: str,
    level: Union[int, LogLevel] = LogLevel.INFO,
    stream: Optional[TextIO] = None,
    sensitive_keys: Optional[List[str]] = None,
) -> Logger:
    """
    Get or create a :class:`Logger` instance.

    Parameters
    ----------
    name:
        Logger name.
    level:
        Minimum log level.
    stream:
        Output stream.
    sensitive_keys:
        Additional sensitive key names.
    """
    if name not in _loggers:
        _loggers[name] = Logger(
            name=name,
            level=level,
            stream=stream,
            sensitive_keys=sensitive_keys,
        )
    return _loggers[name]
