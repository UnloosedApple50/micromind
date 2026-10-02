"""
MicroMind Network Client
========================

A lightweight HTTP client with configurable timeouts and bounded retries.
It is designed for minimal resource usage and predictable behaviour – no
infinite retries, no unbounded buffering.

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * This module is optional; the core never imports it directly.
  * All network operations are bounded by timeouts and retry limits.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClientConfig:
    """
    Immutable network client configuration.

    Attributes
    ----------
    connect_timeout:
        Maximum seconds to wait for a TCP connection to be established.
    read_timeout:
        Maximum seconds to wait for a response after the connection is
        established.
    write_timeout:
        Maximum seconds to wait for a request body to be sent.
    retry_limit:
        Maximum number of retry attempts (0 = no retries).
    retry_backoff:
        Base delay in seconds between retries (exponential backoff).
    max_redirects:
        Maximum number of HTTP redirects to follow.
    user_agent:
        User-Agent header value.
    """

    connect_timeout: float = 5.0
    read_timeout: float = 10.0
    write_timeout: float = 5.0
    retry_limit: int = 3
    retry_backoff: float = 0.5
    max_redirects: int = 5
    user_agent: str = "MicroMind/1.0"


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass
class NetworkResponse:
    """A single network response."""

    status_code: int
    headers: Dict[str, str]
    body: bytes
    url: str
    elapsed: float

    @property
    def ok(self) -> bool:
        """Whether the response status code indicates success (2xx)."""
        return 200 <= self.status_code < 300

    def text(self, encoding: str = "utf-8") -> str:
        """Decode the response body as text."""
        return self.body.decode(encoding, errors="replace")

    def json(self) -> Any:
        """Decode the response body as JSON."""
        import json

        return json.loads(self.text())


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NetworkError(Exception):
    """Base exception for network client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TimeoutError(NetworkError):
    """Raised when a network operation exceeds its timeout."""


class RetryExhaustedError(NetworkError):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


# ---------------------------------------------------------------------------
# Network client
# ---------------------------------------------------------------------------


class NetworkClient:
    """
    Lightweight HTTP client with bounded retries and configurable timeouts.

    Parameters
    ----------
    config:
        Client configuration.  Defaults to :class:`ClientConfig` with
        sensible defaults.
    """

    def __init__(self, config: Optional[ClientConfig] = None) -> None:
        self._config = config or ClientConfig()

    @property
    def config(self) -> ClientConfig:
        """Return the client configuration."""
        return self._config

    # -- public API --------------------------------------------------------

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """Perform an HTTP GET request."""
        return self._request("GET", url, headers=headers)

    def post(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """Perform an HTTP POST request."""
        return self._request("POST", url, data=data, headers=headers)

    def put(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """Perform an HTTP PUT request."""
        return self._request("PUT", url, data=data, headers=headers)

    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """Perform an HTTP DELETE request."""
        return self._request("DELETE", url, headers=headers)

    # -- internal ----------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """
        Perform an HTTP request with bounded retries.

        Raises
        ------
        RetryExhaustedError
            If all retry attempts are exhausted.
        NetworkError
            If a non-retryable error occurs.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self._config.retry_limit + 1):
            try:
                return self._do_request(method, url, data, headers)
            except (urllib.error.URLError, OSError) as exc:
                last_error = exc
                if attempt < self._config.retry_limit:
                    delay = self._config.retry_backoff * (2 ** attempt)
                    logger.warning(
                        "Request %s %s failed (attempt %d/%d): %s – retrying in %.1fs",
                        method,
                        url,
                        attempt + 1,
                        self._config.retry_limit + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    break

        raise RetryExhaustedError(
            f"All {self._config.retry_limit + 1} attempts failed for {method} {url}: {last_error}",
            attempts=self._config.retry_limit + 1,
        )

    def _do_request(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> NetworkResponse:
        """Execute a single HTTP request."""
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
        )

        # Set headers
        req.add_header("User-Agent", self._config.user_agent)
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)

        start = time.monotonic()
        try:
            response = urllib.request.urlopen(
                req,
                timeout=self._config.connect_timeout,
            )
        except urllib.error.HTTPError as exc:
            # HTTPError is a valid response (has status code, headers, body)
            elapsed = time.monotonic() - start
            body = exc.read()
            return NetworkResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()),
                body=body,
                url=exc.url,
                elapsed=elapsed,
            )
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError(f"Connection to {url} timed out") from exc
            raise

        elapsed = time.monotonic() - start
        body = response.read()
        return NetworkResponse(
            status_code=response.status,
            headers=dict(response.headers.items()),
            body=body,
            url=response.url,
            elapsed=elapsed,
        )
