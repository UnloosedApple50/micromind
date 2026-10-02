"""Telephony — Outbound Call Agent with policies and safety."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CallStatus(Enum):
    """Call status."""
    QUEUED = "QUEUED"
    DIALING = "DIALING"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    BUSY = "BUSY"
    NO_ANSWER = "NO_ANSWER"
    FAILED = "FAILED"
    VOICEMAIL = "VOICEMAIL"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class CallPolicy(Enum):
    """Call policy."""
    AUTO_CALL = "AUTO_CALL"
    CONFIRM_CALL = "CONFIRM_CALL"
    BLOCK_CALL = "BLOCK_CALL"


@dataclass
class CallRequest:
    """Call request."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contact_id: str = ""
    phone: str = ""
    destination: str = ""
    status: CallStatus = CallStatus.QUEUED
    policy: CallPolicy = CallPolicy.CONFIRM_CALL
    offer_id: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    object: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: str = ""
    ended_at: str = ""
    duration: int = 0
    result: str = ""
    automation_id: str = ""
    provider: str = ""
    gateway: str = ""


class TelephonyProvider:
    """Abstract telephony provider."""

    async def place_call(self, request: CallRequest) -> CallRequest:
        """Place a call."""
        raise NotImplementedError

    async def cancel_call(self, call_id: str) -> bool:
        """Cancel a call."""
        raise NotImplementedError

    async def get_status(self, call_id: str) -> CallStatus:
        """Get call status."""
        raise NotImplementedError


class GatewayTelephony(TelephonyProvider):
    """Telephony via Gateway."""

    def __init__(self, gateway_url: str, token: str) -> None:
        self.gateway_url = gateway_url
        self.token = token

    async def place_call(self, request: CallRequest) -> CallRequest:
        """Place call via Gateway."""
        request.status = CallStatus.QUEUED
        return request

    async def cancel_call(self, call_id: str) -> bool:
        """Cancel call via Gateway."""
        return True

    async def get_status(self, call_id: str) -> CallStatus:
        """Get call status from Gateway."""
        return CallStatus.QUEUED


class DisabledTelephony(TelephonyProvider):
    """Telephony disabled."""

    async def place_call(self, request: CallRequest) -> CallRequest:
        request.status = CallStatus.FAILED
        request.result = "Telephony disabled"
        return request

    async def cancel_call(self, call_id: str) -> bool:
        return False

    async def get_status(self, call_id: str) -> CallStatus:
        return CallStatus.FAILED


class CallManager:
    """Call manager with policies, rate limits, and safety."""

    def __init__(self, provider: TelephonyProvider) -> None:
        self.provider = provider
        self._calls: dict[str, CallRequest] = {}
        self._daily_count = 0
        self._hourly_count = 0
        self._last_call_time: Optional[datetime] = None
        self._max_calls_per_hour = 10
        self._max_calls_per_day = 50
        self._cooldown_seconds = 300  # 5 minutes
        self._business_hours = (9, 18)  # 9 AM to 6 PM
        self._timezone = "UTC"
        self._allowlist: list[str] = []
        self._blocklist: list[str] = []
        self._call_budget_daily = 100.0
        self._call_budget_monthly = 2000.0
        self._daily_spent = 0.0
        self._monthly_spent = 0.0

    async def request_call(
        self,
        contact_id: str,
        phone: str,
        offer_id: str = "",
        amount: float = 0.0,
        currency: str = "EUR",
        object: str = "",
    ) -> CallRequest:
        """Request a call with all safety checks."""

        request = CallRequest(
            contact_id=contact_id,
            phone=phone,
            destination=phone,
            offer_id=offer_id,
            amount=amount,
            currency=currency,
            object=object,
        )

        # Check phone exists
        if not phone:
            request.status = CallStatus.FAILED
            request.result = "MISSING_PHONE"
            return request

        # Check blocklist
        if phone in self._blocklist:
            request.status = CallStatus.FAILED
            request.result = "BLOCKED_NUMBER"
            return request

        # Check allowlist (if configured)
        if self._allowlist and phone not in self._allowlist:
            request.status = CallStatus.FAILED
            request.result = "NOT_IN_ALLOWLIST"
            return request

        # Check business hours
        now = datetime.utcnow()
        if not (self._business_hours[0] <= now.hour < self._business_hours[1]):
            request.status = CallStatus.FAILED
            request.result = "OUTSIDE_BUSINESS_HOURS"
            return request

        # Check rate limits first
        if self._hourly_count >= self._max_calls_per_hour:
            request.status = CallStatus.FAILED
            request.result = "HOURLY_LIMIT_EXCEEDED"
            return request

        if self._daily_count >= self._max_calls_per_day:
            request.status = CallStatus.FAILED
            request.result = "DAILY_LIMIT_EXCEEDED"
            return request

        # Check cooldown
        if self._last_call_time:
            elapsed = (now - self._last_call_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                request.status = CallStatus.FAILED
                request.result = "COOLDOWN_ACTIVE"
                return request

        # Check budget
        if self._daily_spent >= self._call_budget_daily:
            request.status = CallStatus.FAILED
            request.result = "DAILY_BUDGET_EXCEEDED"
            return request

        # All checks passed — place call
        request = await self.provider.place_call(request)
        self._calls[request.id] = request
        self._daily_count += 1
        self._hourly_count += 1
        self._last_call_time = now

        return request

    def reset_counters(self) -> None:
        """Reset hourly/daily counters (for testing)."""
        self._hourly_count = 0
        self._daily_count = 0
        self._last_call_time = None

    def get_call(self, call_id: str) -> Optional[CallRequest]:
        """Get call by ID."""
        return self._calls.get(call_id)

    def list_calls(self) -> list[CallRequest]:
        """List all calls."""
        return list(self._calls.values())

    def get_stats(self) -> dict[str, Any]:
        """Get call statistics."""
        return {
            "total_calls": len(self._calls),
            "daily_count": self._daily_count,
            "hourly_count": self._hourly_count,
            "daily_budget": self._call_budget_daily,
            "monthly_budget": self._call_budget_monthly,
            "daily_spent": self._daily_spent,
            "monthly_spent": self._monthly_spent,
        }
