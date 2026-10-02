"""
MicroMind Gateway Package
=========================

Transport-agnostic gateway protocol for client ↔ core communication.
"""

from .protocol import (
    PROTOCOL_VERSION,
    Operation,
    Request,
    Response,
    StatusCode,
    validate_version,
)

__all__ = [
    "PROTOCOL_VERSION",
    "Operation",
    "Request",
    "Response",
    "StatusCode",
    "validate_version",
]
