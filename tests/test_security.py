"""Tests for SecurityEngine permissions and validation."""
from __future__ import annotations

import pytest

from micromind.security.engine import (
    PERMISSION_MATRIX,
    Permission,
    RiskLevel,
    SecurityEngine,
)


# ---------------------------------------------------------------------------
# Permission Matrix
# ---------------------------------------------------------------------------


class TestPermissionMatrix:
    def test_admin_has_all_permissions(self) -> None:
        admin_perms = PERMISSION_MATRIX[Permission.ADMIN]
        assert "email.read" in admin_perms
        assert "email.send" in admin_perms
        assert "contacts.read" in admin_perms
        assert "contacts.write" in admin_perms
        assert "tasks.read" in admin_perms
        assert "tasks.write" in admin_perms
        assert "tickets.read" in admin_perms
        assert "tickets.write" in admin_perms
        assert "offers.read" in admin_perms
        assert "offers.write" in admin_perms
        assert "calls.read" in admin_perms
        assert "calls.place" in admin_perms
        assert "calls.configure" in admin_perms
        assert "ai.use" in admin_perms
        assert "system.execute" in admin_perms

    def test_manager_permissions(self) -> None:
        mgr_perms = PERMISSION_MATRIX[Permission.MANAGER]
        assert "email.read" in mgr_perms
        assert "email.send" in mgr_perms
        assert "contacts.read" in mgr_perms
        assert "contacts.write" in mgr_perms
        assert "tasks.read" in mgr_perms
        assert "tasks.write" in mgr_perms
        assert "tickets.read" in mgr_perms
        assert "tickets.write" in mgr_perms
        assert "offers.read" in mgr_perms
        assert "offers.write" in mgr_perms
        assert "calls.read" in mgr_perms
        assert "ai.use" in mgr_perms
        # Manager should NOT have these
        assert "calls.place" not in mgr_perms
        assert "calls.configure" not in mgr_perms
        assert "system.execute" not in mgr_perms

    def test_user_permissions(self) -> None:
        user_perms = PERMISSION_MATRIX[Permission.USER]
        assert "email.read" in user_perms
        assert "contacts.read" in user_perms
        assert "tasks.read" in user_perms
        assert "tasks.write" in user_perms
        assert "tickets.read" in user_perms
        assert "tickets.write" in user_perms
        assert "offers.read" in user_perms
        # User should NOT have these
        assert "email.send" not in user_perms
        assert "contacts.write" not in user_perms
        assert "offers.write" not in user_perms
        assert "calls.read" not in user_perms
        assert "calls.place" not in user_perms
        assert "ai.use" not in user_perms

    def test_read_only_permissions(self) -> None:
        ro_perms = PERMISSION_MATRIX[Permission.READ_ONLY]
        assert "email.read" in ro_perms
        assert "contacts.read" in ro_perms
        assert "tasks.read" in ro_perms
        assert "tickets.read" in ro_perms
        assert "offers.read" in ro_perms
        assert "calls.read" in ro_perms
        # Read-only should NOT have write permissions
        assert "email.send" not in ro_perms
        assert "contacts.write" not in ro_perms
        assert "tasks.write" not in ro_perms
        assert "tickets.write" not in ro_perms
        assert "offers.write" not in ro_perms
        assert "calls.place" not in ro_perms
        assert "ai.use" not in ro_perms

    def test_service_permissions(self) -> None:
        svc_perms = PERMISSION_MATRIX[Permission.SERVICE]
        assert "email.read" in svc_perms
        assert "email.send" in svc_perms
        assert "contacts.read" in svc_perms
        assert "contacts.write" in svc_perms
        assert "tasks.read" in svc_perms
        assert "tasks.write" in svc_perms
        assert "tickets.read" in svc_perms
        assert "tickets.write" in svc_perms
        assert "offers.read" in svc_perms
        assert "offers.write" in svc_perms
        assert "calls.read" in svc_perms
        assert "calls.place" in svc_perms
        assert "ai.use" in svc_perms
        # Service should NOT have these
        assert "calls.configure" not in svc_perms
        assert "system.execute" not in svc_perms


# ---------------------------------------------------------------------------
# SecurityEngine — check_permission
# ---------------------------------------------------------------------------


class TestCheckPermission:
    def test_admin_can_do_everything(self) -> None:
        engine = SecurityEngine()
        for action in PERMISSION_MATRIX[Permission.ADMIN]:
            assert engine.check_permission(Permission.ADMIN, action) is True

    def test_user_cannot_send_email(self) -> None:
        engine = SecurityEngine()
        assert engine.check_permission(Permission.USER, "email.send") is False

    def test_read_only_cannot_write(self) -> None:
        engine = SecurityEngine()
        assert engine.check_permission(Permission.READ_ONLY, "tasks.write") is False

    def test_unknown_action_denied(self) -> None:
        engine = SecurityEngine()
        assert engine.check_permission(Permission.ADMIN, "nonexistent.action") is False

    def test_safe_mode_blocks_dangerous_actions(self) -> None:
        engine = SecurityEngine(safe_mode=True)
        assert engine.check_permission(Permission.ADMIN, "calls.place") is False
        assert engine.check_permission(Permission.ADMIN, "email.send") is False
        assert engine.check_permission(Permission.ADMIN, "system.execute") is False

    def test_safe_mode_allows_safe_actions(self) -> None:
        engine = SecurityEngine(safe_mode=True)
        assert engine.check_permission(Permission.ADMIN, "email.read") is True
        assert engine.check_permission(Permission.ADMIN, "contacts.read") is True
        assert engine.check_permission(Permission.ADMIN, "tasks.read") is True

    def test_non_safe_mode_allows_dangerous_actions(self) -> None:
        engine = SecurityEngine(safe_mode=False)
        assert engine.check_permission(Permission.ADMIN, "calls.place") is True
        assert engine.check_permission(Permission.ADMIN, "email.send") is True
        assert engine.check_permission(Permission.ADMIN, "system.execute") is True


# ---------------------------------------------------------------------------
# SecurityEngine — validate_email
# ---------------------------------------------------------------------------


class TestValidateEmail:
    @pytest.mark.parametrize("email", [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.com",
        "user@sub.domain.com",
        "user@example.co.uk",
        "a@b.cc",
    ])
    def test_valid_emails(self, email: str) -> None:
        engine = SecurityEngine()
        assert engine.validate_email(email) is True

    @pytest.mark.parametrize("email", [
        "",
        "notanemail",
        "@example.com",
        "user@",
        "user@.com",
        "user@com",
        "user name@example.com",
        "user@example..com",
    ])
    def test_invalid_emails(self, email: str) -> None:
        engine = SecurityEngine()
        assert engine.validate_email(email) is False


# ---------------------------------------------------------------------------
# SecurityEngine — validate_phone
# ---------------------------------------------------------------------------


class TestValidatePhone:
    @pytest.mark.parametrize("phone", [
        "+351912345678",
        "912345678",
        "+1-555-123-4567",
        "+44 20 7946 0958",
        "5551234567",
        "+34612345678",
    ])
    def test_valid_phones(self, phone: str) -> None:
        engine = SecurityEngine()
        assert engine.validate_phone(phone) is True

    @pytest.mark.parametrize("phone", [
        "",
        "abc",
        "123",
        "+",
        "12345678901234567890",  # too long
        "phone123",
    ])
    def test_invalid_phones(self, phone: str) -> None:
        engine = SecurityEngine()
        assert engine.validate_phone(phone) is False


# ---------------------------------------------------------------------------
# SecurityEngine — sanitize_input
# ---------------------------------------------------------------------------


class TestSanitizeInput:
    def test_empty_string(self) -> None:
        engine = SecurityEngine()
        assert engine.sanitize_input("") == ""

    def test_none_input(self) -> None:
        engine = SecurityEngine()
        assert engine.sanitize_input(None) == ""

    def test_truncation(self) -> None:
        engine = SecurityEngine()
        long_text = "a" * 20000
        result = engine.sanitize_input(long_text, max_length=100)
        assert len(result) == 100

    def test_null_byte_removal(self) -> None:
        engine = SecurityEngine()
        result = engine.sanitize_input("hello\x00world")
        assert result == "helloworld"

    def test_normal_text_unchanged(self) -> None:
        engine = SecurityEngine()
        result = engine.sanitize_input("Hello, World!")
        assert result == "Hello, World!"


# ---------------------------------------------------------------------------
# SecurityEngine — validate_path
# ---------------------------------------------------------------------------


class TestValidatePath:
    def test_valid_path(self, tmp_path: Any) -> None:
        engine = SecurityEngine()
        # Create the file so it exists
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        target_file = subdir / "file.txt"
        target_file.write_text("test")
        assert engine.validate_path(str(target_file), str(tmp_path)) is True

    def test_invalid_path(self, tmp_path: Any) -> None:
        engine = SecurityEngine()
        target = str(tmp_path.parent / "outside.txt")
        assert engine.validate_path(target, str(tmp_path)) is False

    def test_path_traversal(self, tmp_path: Any) -> None:
        engine = SecurityEngine()
        target = str(tmp_path / ".." / "etc" / "passwd")
        # After resolve, this should be outside tmp_path
        assert engine.validate_path(target, str(tmp_path)) is False


# ---------------------------------------------------------------------------
# SecurityEngine — audit
# ---------------------------------------------------------------------------


class TestAudit:
    def test_audit_log_entry(self) -> None:
        engine = SecurityEngine()
        engine.audit("test.action", "admin", {"detail": "value"})
        log = engine.get_audit_log()
        assert len(log) == 1
        assert log[0]["action"] == "test.action"
        assert log[0]["user"] == "admin"
        assert log[0]["details"] == {"detail": "value"}
        assert "timestamp" in log[0]

    def test_audit_log_copies(self) -> None:
        engine = SecurityEngine()
        engine.audit("test.action", "admin", {})
        log = engine.get_audit_log()
        log.clear()
        # Original should be unaffected
        assert len(engine.get_audit_log()) == 1

    def test_multiple_audit_entries(self) -> None:
        engine = SecurityEngine()
        engine.audit("action1", "admin", {})
        engine.audit("action2", "user", {})
        log = engine.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "action1"
        assert log[1]["action"] == "action2"


# ---------------------------------------------------------------------------
# RiskLevel
# ---------------------------------------------------------------------------


class TestRiskLevel:
    def test_risk_levels_exist(self) -> None:
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def security_engine() -> SecurityEngine:
    return SecurityEngine()


@pytest.fixture()
def safe_engine() -> SecurityEngine:
    return SecurityEngine(safe_mode=True)
