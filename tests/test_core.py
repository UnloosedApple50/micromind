"""Tests for CoreRuntime, SystemInfo, Contact, Task, Ticket, Offer."""
from __future__ import annotations

import pytest

from micromind.core.runtime import (
    Contact,
    CoreRuntime,
    Offer,
    Profile,
    Status,
    SystemInfo,
    Task,
    Ticket,
)


# ---------------------------------------------------------------------------
# SystemInfo
# ---------------------------------------------------------------------------


class TestSystemInfo:
    def test_defaults(self) -> None:
        info = SystemInfo()
        assert info.os == ""
        assert info.cpu == ""
        assert info.ram_mb == 0
        assert info.storage_gb == 0
        assert info.cores == 0
        assert info.gui is False
        assert info.networking is False
        assert info.profile == Profile.ULTRA_LOW

    def test_custom_values(self) -> None:
        info = SystemInfo(
            os="Linux 5.15",
            cpu="ARM Cortex-A72",
            ram_mb=512,
            storage_gb=4,
            cores=4,
            gui=False,
            networking=False,
            profile=Profile.LEGACY,
        )
        assert info.os == "Linux 5.15"
        assert info.cpu == "ARM Cortex-A72"
        assert info.ram_mb == 512
        assert info.storage_gb == 4
        assert info.cores == 4
        assert info.gui is False
        assert info.networking is False
        assert info.profile == Profile.LEGACY


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------


class TestContact:
    def test_defaults(self) -> None:
        c = Contact()
        assert c.id == ""
        assert c.name == ""
        assert c.company == ""
        assert c.email == ""
        assert c.phone == ""
        assert c.country == ""
        assert c.timezone == ""
        assert c.tags == []
        assert c.notes == ""
        assert c.call_permission == "denied"
        assert c.created_at != ""

    def test_call_permission_values(self) -> None:
        for perm in ("allowed", "denied", "confirm"):
            c = Contact(call_permission=perm)
            assert c.call_permission == perm

    def test_tags_list(self) -> None:
        c = Contact(tags=["vip", "enterprise"])
        assert c.tags == ["vip", "enterprise"]


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class TestTask:
    def test_defaults(self) -> None:
        t = Task()
        assert t.id == ""
        assert t.title == ""
        assert t.description == ""
        assert t.priority == "medium"
        assert t.status == "pending"
        assert t.owner == ""
        assert t.deadline == ""
        assert t.recurrence == ""
        assert t.history == []
        assert t.created_at != ""

    def test_priority_values(self) -> None:
        for prio in ("low", "medium", "high", "urgent"):
            t = Task(priority=prio)
            assert t.priority == prio

    def test_status_values(self) -> None:
        for st in ("pending", "in_progress", "completed", "cancelled"):
            t = Task(status=st)
            assert t.status == st


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------


class TestTicket:
    def test_defaults(self) -> None:
        t = Ticket()
        assert t.id == ""
        assert t.customer == ""
        assert t.title == ""
        assert t.description == ""
        assert t.priority == "medium"
        assert t.status == "new"
        assert t.assignee == ""
        assert t.created != ""
        assert t.updated != ""
        assert t.history == []

    def test_status_values(self) -> None:
        for st in ("new", "open", "waiting", "resolved", "closed"):
            t = Ticket(status=st)
            assert t.status == st


# ---------------------------------------------------------------------------
# Offer
# ---------------------------------------------------------------------------


class TestOffer:
    def test_defaults(self) -> None:
        o = Offer()
        assert o.id == ""
        assert o.customer_id == ""
        assert o.object == ""
        assert o.amount == 0.0
        assert o.currency == "EUR"
        assert o.status == "new"
        assert o.source == ""
        assert o.created_at != ""

    def test_status_values(self) -> None:
        for st in ("new", "review", "accepted", "rejected", "expired"):
            o = Offer(status=st)
            assert o.status == st


# ---------------------------------------------------------------------------
# CoreRuntime
# ---------------------------------------------------------------------------


class TestCoreRuntime:
    def test_init_creates_dirs(self, tmp_path: Any) -> None:
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        rt = CoreRuntime(config_dir=str(config_dir), data_dir=str(data_dir))
        assert config_dir.exists()
        assert data_dir.exists()

    def test_system_info_property(self, tmp_path: Any) -> None:
        rt = CoreRuntime(
            config_dir=str(tmp_path / "c"), data_dir=str(tmp_path / "d")
        )
        info = rt.system_info
        assert isinstance(info, SystemInfo)
        assert info.os != ""

    def test_profile_property(self, tmp_path: Any) -> None:
        rt = CoreRuntime(
            config_dir=str(tmp_path / "c"), data_dir=str(tmp_path / "d")
        )
        assert isinstance(rt.profile, Profile)

    def test_status_returns_dict(self, tmp_path: Any) -> None:
        rt = CoreRuntime(
            config_dir=str(tmp_path / "c"), data_dir=str(tmp_path / "d")
        )
        status = rt.status()
        assert isinstance(status, dict)
        assert status["core"] == Status.OK.value
        assert "profile" in status
        assert "ai" in status
        assert "telephony" in status
        assert "gateway" in status
        assert "security" in status

    def test_doctor_returns_dict(self, tmp_path: Any) -> None:
        rt = CoreRuntime(
            config_dir=str(tmp_path / "c"), data_dir=str(tmp_path / "d")
        )
        info = rt.doctor()
        assert isinstance(info, dict)
        assert "os" in info
        assert "cpu" in info
        assert "ram" in info
        assert "storage" in info
        assert "gui" in info
        assert "network" in info
        assert "profile" in info
        assert "ai" in info
        assert "gateway" in info
        assert "telephony" in info
        assert "security" in info
        assert "database" in info

    def test_doctor_database_is_flatfile(self, tmp_path: Any) -> None:
        rt = CoreRuntime(
            config_dir=str(tmp_path / "c"), data_dir=str(tmp_path / "d")
        )
        info = rt.doctor()
        assert info["database"] == "FlatFile"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runtime(tmp_path: Any) -> CoreRuntime:
    return CoreRuntime(
        config_dir=str(tmp_path / "config"),
        data_dir=str(tmp_path / "data"),
    )
