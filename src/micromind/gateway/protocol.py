"""
MicroMind Gateway Protocol
===========================

Defines the wire protocol for gateway communication between clients and
the MicroMind core.  Every request and response is a self-describing
message that carries versioning, authentication, an operation identifier,
a payload, and a timestamp.

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * Protocol is transport-agnostic (works over TCP, Unix socket, stdio, …).
  * All messages are JSON-serialisable for easy debugging and interop.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Protocol version
# ---------------------------------------------------------------------------

PROTOCOL_VERSION: str = "1.0.0"
"""Current protocol version string (semver)."""


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Operation(str, Enum):
    """Supported gateway operations."""

    PING = "ping"
    EXECUTE = "execute"
    QUERY = "query"
    CONFIG_GET = "config.get"
    CONFIG_SET = "config.set"
    PLUGIN_LIST = "plugin.list"
    PLUGIN_LOAD = "plugin.load"
    PLUGIN_UNLOAD = "plugin.unload"
    STATUS = "status"
    SHUTDOWN = "shutdown"


class StatusCode(str, Enum):
    """Standard status codes returned in every :class:`Response`."""

    OK = "ok"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


@dataclass
class Request:
    """
    A single gateway request.

    Attributes
    ----------
    operation:
        The operation to perform (see :class:`Operation`).
    payload:
        Operation-specific data.  Must be JSON-serialisable.
    request_id:
        Unique identifier for this request.  Auto-generated if omitted.
    auth_token:
        Opaque authentication token.  The core never interprets it; it is
        forwarded to the configured authenticator.
    timestamp:
        Unix epoch (seconds) when the request was created.  Auto-set if
        omitted.
    version:
        Protocol version string.  Defaults to :data:`PROTOCOL_VERSION`.
    """

    operation: Operation
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    auth_token: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    version: str = PROTOCOL_VERSION

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        return {
            "version": self.version,
            "request_id": self.request_id,
            "auth_token": self.auth_token,
            "operation": self.operation.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Request":
        """Reconstruct a :class:`Request` from a dict.

        Raises
        ------
        ValueError
            If the dict is missing required fields or contains invalid data.
        """
        try:
            return cls(
                operation=Operation(data["operation"]),
                payload=data.get("payload", {}),
                request_id=data.get("request_id", uuid.uuid4().hex),
                auth_token=data.get("auth_token"),
                timestamp=data.get("timestamp", time.time()),
                version=data.get("version", PROTOCOL_VERSION),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid request dict: {exc}") from exc

    @classmethod
    def from_json(cls, raw: str) -> "Request":
        """Reconstruct a :class:`Request` from a JSON string."""
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass
class Response:
    """
    A single gateway response.

    Attributes
    ----------
    request_id:
        Echoes the :attr:`Request.request_id` that triggered this response.
    status:
        Outcome of the operation (see :class:`StatusCode`).
    result:
        Operation-specific result data.  ``None`` when ``status`` is not
        ``OK``.
    error_code:
        Machine-readable error identifier (e.g. ``"auth_failed"``).
        ``None`` on success.
    error_message:
        Human-readable error description.  ``None`` on success.
    timestamp:
        Unix epoch (seconds) when the response was created.
    version:
        Protocol version string.
    """

    request_id: str
    status: StatusCode
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    version: str = PROTOCOL_VERSION

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        return {
            "version": self.version,
            "request_id": self.request_id,
            "status": self.status.value,
            "result": self.result,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Response":
        """Reconstruct a :class:`Response` from a dict."""
        try:
            return cls(
                request_id=data["request_id"],
                status=StatusCode(data["status"]),
                result=data.get("result"),
                error_code=data.get("error_code"),
                error_message=data.get("error_message"),
                timestamp=data.get("timestamp", time.time()),
                version=data.get("version", PROTOCOL_VERSION),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid response dict: {exc}") from exc

    @classmethod
    def from_json(cls, raw: str) -> "Response":
        """Reconstruct a :class:`Response` from a JSON string."""
        return cls.from_dict(json.loads(raw))

    # -- convenience constructors -----------------------------------------

    @classmethod
    def ok(
        cls,
        request_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> "Response":
        """Build a successful response."""
        return cls(
            request_id=request_id,
            status=StatusCode.OK,
            result=result,
        )

    @classmethod
    def error(
        cls,
        request_id: str,
        status: StatusCode = StatusCode.ERROR,
        error_code: str = "unknown",
        error_message: str = "An unknown error occurred",
    ) -> "Response":
        """Build an error response."""
        return cls(
            request_id=request_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def validate_version(version: str) -> bool:
    """Return *True* if *version* is compatible with the current protocol.

    Compatibility rule: the major version must match.
    """
    try:
        major = version.split(".")[0]
        current_major = PROTOCOL_VERSION.split(".")[0]
        return major == current_major
    except (IndexError, AttributeError):
        return False
