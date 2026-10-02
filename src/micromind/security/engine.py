"""Security — permissions, validation, and safety."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional


class Permission(Enum):
    """Permission levels."""
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"
    READ_ONLY = "READ_ONLY"
    SERVICE = "SERVICE"


class RiskLevel(Enum):
    """Risk levels for operations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Permission matrix
PERMISSION_MATRIX = {
    Permission.ADMIN: [
        "email.read", "email.send", "contacts.read", "contacts.write",
        "tasks.read", "tasks.write", "tickets.read", "tickets.write",
        "offers.read", "offers.write", "calls.read", "calls.place",
        "calls.configure", "ai.use", "system.execute",
    ],
    Permission.MANAGER: [
        "email.read", "email.send", "contacts.read", "contacts.write",
        "tasks.read", "tasks.write", "tickets.read", "tickets.write",
        "offers.read", "offers.write", "calls.read", "ai.use",
    ],
    Permission.USER: [
        "email.read", "contacts.read", "tasks.read", "tasks.write",
        "tickets.read", "tickets.write", "offers.read",
    ],
    Permission.READ_ONLY: [
        "email.read", "contacts.read", "tasks.read", "tickets.read",
        "offers.read", "calls.read",
    ],
    Permission.SERVICE: [
        "email.read", "email.send", "contacts.read", "contacts.write",
        "tasks.read", "tasks.write", "tickets.read", "tickets.write",
        "offers.read", "offers.write", "calls.read", "calls.place",
        "ai.use",
    ],
}


class SecurityEngine:
    """Security engine — permissions, validation, and safety."""

    def __init__(self, safe_mode: bool = False) -> None:
        self.safe_mode = safe_mode
        self._audit_log: list[dict[str, Any]] = []

    def check_permission(self, user: Permission, action: str) -> bool:
        """Check if user has permission for action."""
        if self.safe_mode and action in ["calls.place", "email.send", "system.execute"]:
            return False
        return action in PERMISSION_MATRIX.get(user, [])

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        # Basic validation: 7-15 digits, optional + prefix
        pattern = r'^\+?[0-9]{7,15}$'
        return bool(re.match(pattern, cleaned))

    def sanitize_input(self, text: str, max_length: int = 10000) -> str:
        """Sanitize user input."""
        if not text:
            return ""
        # Truncate
        text = text[:max_length]
        # Remove null bytes
        text = text.replace("\x00", "")
        return text

    def validate_path(self, path: str, allowed_base: str) -> bool:
        """Validate path is within allowed base."""
        try:
            # Normalize paths
            base = os.path.normpath(allowed_base)
            target = os.path.normpath(path)
            # Check if target is within base
            return target == base or target.startswith(base + os.sep)
        except Exception:
            return False

    def validate_path_exists(self, path: str, allowed_base: str) -> bool:
        """Validate path is within allowed base and exists."""
        if not self.validate_path(path, allowed_base):
            return False
        return Path(path).exists()

    def audit(self, action: str, user: str, details: dict[str, Any]) -> None:
        """Log audit event."""
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user": user,
            "details": details,
        })

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get audit log."""
        return self._audit_log.copy()


from datetime import datetime
