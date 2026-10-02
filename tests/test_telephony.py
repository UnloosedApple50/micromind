"""Tests for CallManager with all safety checks."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from micromind.telephony.calls import (
    CallManager,
    CallPolicy,
    CallRequest,
    CallStatus,
    DisabledTelephony,
    GatewayTelephony,
    TelephonyProvider,
)


# ---------------------------------------------------------------------------
# CallRequest
# ---------------------------------------------------------------------------


class TestCallRequest:
    def test_defaults(self) -> None:
        req = CallRequest()
        assert req.id != ""
        assert req.contact_id == ""
        assert req.phone == ""
        assert req.destination == ""
        assert req.status == CallStatus.QUEUED
        assert req.policy == CallPolicy.CONFIRM_CALL
        assert req.offer_id == ""
        assert req.amount == 0.0
        assert req.currency == "EUR"
        assert req.object == ""
        assert req.created_at != ""
        assert req.started_at == ""
        assert req.ended_at == ""
        assert req.duration == 0
        assert req.result == ""
        assert req.automation_id == ""
        assert req.provider == ""
        assert req.gateway == ""

    def test_custom_values(self) -> None:
        req = CallRequest(
            contact_id="contact_123",
            phone="+351912345678",
            destination="+351912345678",
            offer_id="offer_456",
            amount=1500.0,
            currency="USD",
            object="Enterprise License",
        )
        assert req.contact_id == "contact_123"
        assert req.phone == "+351912345678"
        assert req.destination == "+351912345678"
        assert req.offer_id == "offer_456"
        assert req.amount == 1500.0
        assert req.currency == "USD"
        assert req.object == "Enterprise License"


# ---------------------------------------------------------------------------
# CallStatus / CallPolicy
# ---------------------------------------------------------------------------


class TestEnums:
    def test_call_status_values(self) -> None:
        assert CallStatus.QUEUED.value == "QUEUED"
        assert CallStatus.DIALING.value == "DIALING"
        assert CallStatus.RINGING.value == "RINGING"
        assert CallStatus.ANSWERED.value == "ANSWERED"
        assert CallStatus.BUSY.value == "BUSY"
        assert CallStatus.NO_ANSWER.value == "NO_ANSWER"
        assert CallStatus.FAILED.value == "FAILED"
        assert CallStatus.VOICEMAIL.value == "VOICEMAIL"
        assert CallStatus.CANCELLED.value == "CANCELLED"
        assert CallStatus.COMPLETED.value == "COMPLETED"

    def test_call_policy_values(self) -> None:
        assert CallPolicy.AUTO_CALL.value == "AUTO_CALL"
        assert CallPolicy.CONFIRM_CALL.value == "CONFIRM_CALL"
        assert CallPolicy.BLOCK_CALL.value == "BLOCK_CALL"


# ---------------------------------------------------------------------------
# DisabledTelephony
# ---------------------------------------------------------------------------


class TestDisabledTelephony:
    @pytest.mark.asyncio
    async def test_place_call_fails(self) -> None:
        provider = DisabledTelephony()
        req = CallRequest(phone="+351912345678")
        result = await provider.place_call(req)
        assert result.status == CallStatus.FAILED
        assert result.result == "Telephony disabled"

    @pytest.mark.asyncio
    async def test_cancel_call_fails(self) -> None:
        provider = DisabledTelephony()
        assert await provider.cancel_call("any_id") is False

    @pytest.mark.asyncio
    async def test_get_status_fails(self) -> None:
        provider = DisabledTelephony()
        status = await provider.get_status("any_id")
        assert status == CallStatus.FAILED


# ---------------------------------------------------------------------------
# GatewayTelephony
# ---------------------------------------------------------------------------


class TestGatewayTelephony:
    def test_init(self) -> None:
        provider = GatewayTelephony(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        assert provider.gateway_url == "https://gateway.example.com"
        assert provider.token == "gw-token-123"

    @pytest.mark.asyncio
    async def test_place_call_queued(self) -> None:
        provider = GatewayTelephony(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        req = CallRequest(phone="+351912345678")
        result = await provider.place_call(req)
        assert result.status == CallStatus.QUEUED

    @pytest.mark.asyncio
    async def test_cancel_call_succeeds(self) -> None:
        provider = GatewayTelephony(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        assert await provider.cancel_call("any_id") is True

    @pytest.mark.asyncio
    async def test_get_status_queued(self) -> None:
        provider = GatewayTelephony(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        status = await provider.get_status("any_id")
        assert status == CallStatus.QUEUED


# ---------------------------------------------------------------------------
# CallManager — safety checks
# ---------------------------------------------------------------------------


class TestCallManagerSafety:
    @pytest.mark.asyncio
    async def test_missing_phone(self) -> None:
        manager = CallManager(DisabledTelephony())
        req = await manager.request_call(contact_id="c1", phone="")
        assert req.status == CallStatus.FAILED
        assert req.result == "MISSING_PHONE"

    @pytest.mark.asyncio
    async def test_blocked_number(self) -> None:
        manager = CallManager(DisabledTelephony())
        manager._blocklist.append("+351912345678")
        req = await manager.request_call(
            contact_id="c1",
            phone="+351912345678",
        )
        assert req.status == CallStatus.FAILED
        assert req.result == "BLOCKED_NUMBER"

    @pytest.mark.asyncio
    async def test_not_in_allowlist(self) -> None:
        manager = CallManager(DisabledTelephony())
        manager._allowlist.append("+351999999999")
        req = await manager.request_call(
            contact_id="c1",
            phone="+351912345678",
        )
        assert req.status == CallStatus.FAILED
        assert req.result == "NOT_IN_ALLOWLIST"

    @pytest.mark.asyncio
    async def test_in_allowlist_passes(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._allowlist.append("+351912345678")
        # Override business hours to always pass
        manager._business_hours = (0, 24)
        req = await manager.request_call(
            contact_id="c1",
            phone="+351912345678",
        )
        assert req.status == CallStatus.QUEUED

    @pytest.mark.asyncio
    async def test_outside_business_hours(self) -> None:
        manager = CallManager(DisabledTelephony())
        # Set business hours to a window that doesn't include current time
        now = datetime.utcnow()
        # Use a window that's definitely not now
        if now.hour < 12:
            manager._business_hours = (13, 14)
        else:
            manager._business_hours = (0, 1)
        req = await manager.request_call(
            contact_id="c1",
            phone="+351912345678",
        )
        assert req.status == CallStatus.FAILED
        assert req.result == "OUTSIDE_BUSINESS_HOURS"

    @pytest.mark.asyncio
    async def test_hourly_limit(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._max_calls_per_hour = 2
        manager._cooldown_seconds = 0  # Disable cooldown for this test
        # Make 2 calls to hit the limit
        await manager.request_call(contact_id="c1", phone="+351****1111")
        await manager.request_call(contact_id="c2", phone="+351****2222")
        # Third call should fail
        req = await manager.request_call(contact_id="c3", phone="+351****3333")
        assert req.status == CallStatus.FAILED
        assert req.result == "HOURLY_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_daily_limit(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._max_calls_per_day = 1
        manager._max_calls_per_hour = 100
        # Make 1 call to hit the daily limit
        await manager.request_call(contact_id="c1", phone="+351911111111")
        # Second call should fail
        req = await manager.request_call(contact_id="c2", phone="+351922222222")
        assert req.status == CallStatus.FAILED
        assert req.result == "DAILY_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_cooldown_active(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._cooldown_seconds = 300
        manager._max_calls_per_hour = 100
        manager._max_calls_per_day = 100
        # First call
        await manager.request_call(contact_id="c1", phone="+351****1111")
        # Second call immediately should fail due to cooldown
        req = await manager.request_call(contact_id="c2", phone="+351****2222")
        assert req.status == CallStatus.FAILED
        assert req.result == "COOLDOWN_ACTIVE"

    @pytest.mark.asyncio
    async def test_cooldown_expired(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._cooldown_seconds = 0  # No cooldown
        # First call
        await manager.request_call(contact_id="c1", phone="+351911111111")
        # Second call should succeed
        req = await manager.request_call(contact_id="c2", phone="+351922222222")
        assert req.status == CallStatus.QUEUED

    @pytest.mark.asyncio
    async def test_daily_budget_exceeded(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._call_budget_daily = 100.0
        manager._daily_spent = 100.0
        req = await manager.request_call(
            contact_id="c1",
            phone="+351911111111",
            amount=50.0,
        )
        assert req.status == CallStatus.FAILED
        assert req.result == "DAILY_BUDGET_EXCEEDED"

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        req = await manager.request_call(
            contact_id="c1",
            phone="+351912345678",
            offer_id="offer_123",
            amount=1500.0,
            currency="EUR",
            object="Enterprise License",
        )
        assert req.status == CallStatus.QUEUED
        assert req.contact_id == "c1"
        assert req.phone == "+351912345678"
        assert req.offer_id == "offer_123"
        assert req.amount == 1500.0
        assert req.currency == "EUR"
        assert req.object == "Enterprise License"


# ---------------------------------------------------------------------------
# CallManager — call management
# ---------------------------------------------------------------------------


class TestCallManagement:
    @pytest.mark.asyncio
    async def test_get_call(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        req = await manager.request_call(contact_id="c1", phone="+351912345678")
        retrieved = manager.get_call(req.id)
        assert retrieved is not None
        assert retrieved.id == req.id

    @pytest.mark.asyncio
    async def test_get_call_nonexistent(self) -> None:
        manager = CallManager(DisabledTelephony())
        assert manager.get_call("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_calls(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        manager._cooldown_seconds = 0  # Disable cooldown for this test
        await manager.request_call(contact_id="c1", phone="+351****1111")
        await manager.request_call(contact_id="c2", phone="+351****2222")
        calls = manager.list_calls()
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_list_calls_empty(self) -> None:
        manager = CallManager(DisabledTelephony())
        assert manager.list_calls() == []

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))
        manager._business_hours = (0, 24)
        await manager.request_call(contact_id="c1", phone="+351911111111")
        stats = manager.get_stats()
        assert stats["total_calls"] == 1
        assert stats["daily_count"] == 1
        assert stats["hourly_count"] == 1
        assert stats["daily_budget"] == 100.0
        assert stats["monthly_budget"] == 2000.0
        assert stats["daily_spent"] == 0.0
        assert stats["monthly_spent"] == 0.0


# ---------------------------------------------------------------------------
# CallManager — configuration
# ---------------------------------------------------------------------------


class TestCallManagerConfig:
    def test_default_limits(self) -> None:
        manager = CallManager(DisabledTelephony())
        assert manager._max_calls_per_hour == 10
        assert manager._max_calls_per_day == 50
        assert manager._cooldown_seconds == 300
        assert manager._business_hours == (9, 18)
        assert manager._timezone == "UTC"
        assert manager._call_budget_daily == 100.0
        assert manager._call_budget_monthly == 2000.0

    def test_custom_limits(self) -> None:
        manager = CallManager(DisabledTelephony())
        manager._max_calls_per_hour = 5
        manager._max_calls_per_day = 20
        manager._cooldown_seconds = 60
        manager._business_hours = (8, 20)
        manager._call_budget_daily = 500.0
        manager._call_budget_monthly = 5000.0
        assert manager._max_calls_per_hour == 5
        assert manager._max_calls_per_day == 20
        assert manager._cooldown_seconds == 60
        assert manager._business_hours == (8, 20)
        assert manager._call_budget_daily == 500.0
        assert manager._call_budget_monthly == 5000.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def disabled_telephony() -> DisabledTelephony:
    return DisabledTelephony()


@pytest.fixture()
def gateway_telephony() -> GatewayTelephony:
    return GatewayTelephony(
        gateway_url="https://gateway.example.com",
        token="test-token",
    )


@pytest.fixture()
def call_manager(disabled_telephony: DisabledTelephony) -> CallManager:
    return CallManager(disabled_telephony)


@pytest.fixture()
def permissive_manager(gateway_telephony: GatewayTelephony) -> CallManager:
    """CallManager with all safety checks effectively disabled."""
    manager = CallManager(gateway_telephony)
    manager._business_hours = (0, 24)
    manager._cooldown_seconds = 0
    manager._max_calls_per_hour = 9999
    manager._max_calls_per_day = 9999
    manager._call_budget_daily = 999999.0
    return manager
