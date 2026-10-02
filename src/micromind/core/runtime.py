"""Core runtime — platform-independent business logic."""

from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class Profile(Enum):
    """Execution profiles."""
    ULTRA_LOW = "ULTRA_LOW"
    LEGACY = "LEGACY"
    LOW = "LOW"
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    SERVER = "SERVER"


class Status(Enum):
    """Operation status."""
    OK = "OK"
    ERROR = "ERROR"
    WARNING = "WARNING"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


@dataclass
class SystemInfo:
    """System information."""
    os: str = ""
    cpu: str = ""
    ram_mb: int = 0
    storage_gb: int = 0
    cores: int = 0
    gui: bool = False
    networking: bool = False
    profile: Profile = Profile.ULTRA_LOW


@dataclass
class Contact:
    """Business contact."""
    id: str = ""
    name: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    timezone: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    call_permission: str = "denied"  # allowed, denied, confirm
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Task:
    """Business task."""
    id: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "pending"  # pending, in_progress, completed, cancelled
    owner: str = ""
    deadline: str = ""
    recurrence: str = ""
    history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Ticket:
    """Support ticket."""
    id: str = ""
    customer: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"
    status: str = "new"  # new, open, waiting, resolved, closed
    assignee: str = ""
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    history: list[dict] = field(default_factory=list)


@dataclass
class Offer:
    """Business offer."""
    id: str = ""
    customer_id: str = ""
    object: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    status: str = "new"  # new, review, accepted, rejected, expired
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CoreRuntime:
    """Core runtime — platform-independent business logic.

    Does NOT depend on:
    - LLM
    - Internet
    - GUI
    - Heavy database
    - Cloud
    - GPU
    """

    def __init__(self, config_dir: str = "./config", data_dir: str = "./data") -> None:
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._system_info = self._detect_system()
        self._profile = self._detect_profile()

    def _detect_system(self) -> SystemInfo:
        """Detect system capabilities."""
        info = SystemInfo()
        try:
            info.os = platform.system() + " " + platform.release()
            info.cpu = platform.processor() or "Unknown"
            info.cores = os.cpu_count() or 1
            # RAM detection would go here
            info.ram_mb = 0  # Placeholder
            info.gui = True  # Placeholder
            info.networking = True  # Placeholder
        except Exception:
            pass
        return info

    def _detect_profile(self) -> Profile:
        """Detect execution profile based on system capabilities."""
        # Simplified detection
        if self._system_info.ram_mb < 512:
            return Profile.ULTRA_LOW
        elif self._system_info.ram_mb < 2048:
            return Profile.LOW
        else:
            return Profile.STANDARD

    @property
    def system_info(self) -> SystemInfo:
        """Get system information."""
        return self._system_info

    @property
    def profile(self) -> Profile:
        """Get execution profile."""
        return self._profile

    def status(self) -> dict[str, Any]:
        """Get system status."""
        return {
            "core": Status.OK.value,
            "storage": Status.OK.value,
            "automation": Status.OK.value,
            "ai": "Gateway" if self._profile.value in ["STANDARD", "HIGH", "SERVER"] else "MicroAI",
            "telephony": "Gateway",
            "gateway": "Not configured",
            "security": "Legacy Safe" if self._profile in [Profile.ULTRA_LOW, Profile.LEGACY] else "Standard",
            "profile": self._profile.value,
        }

    def doctor(self) -> dict[str, Any]:
        """Run system diagnostics."""
        return {
            "os": self._system_info.os,
            "cpu": self._system_info.cpu,
            "ram": f"{self._system_info.ram_mb} MB",
            "storage": f"{self._system_info.storage_gb} GB",
            "gui": "Available" if self._system_info.gui else "Not available",
            "network": "Available" if self._system_info.networking else "Not available",
            "profile": self._profile.value,
            "ai": "MicroAI" if self._profile in [Profile.ULTRA_LOW, Profile.LEGACY] else "Gateway",
            "gateway": "Not configured",
            "telephony": "Gateway",
            "security": "Legacy Safe" if self._profile in [Profile.ULTRA_LOW, Profile.LEGACY] else "Standard",
            "database": "FlatFile",
        }
