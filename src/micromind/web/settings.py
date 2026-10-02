"""Settings API — full configuration via web interface."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from micromind import PROFILES, AI_PROVIDERS, TELEPHONY_PROVIDERS, STORAGE_BACKENDS

router = APIRouter()

# Config file path
CONFIG_FILE = Path("./config/micromind.json")


class ConfigUpdate(BaseModel):
    """Configuration update."""
    section: str
    data: dict[str, Any]


def load_config() -> dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "profile": "ULTRA_LOW",
        "ai": {
            "provider": "MicroAIProvider",
            "model": "qwen2.5:0.5b",
            "ollama_host": "http://localhost:11434",
            "temperature": 0.3,
            "max_tokens": 512,
        },
        "storage": {
            "backend": "FlatFileBackend",
            "data_dir": "./data",
            "max_storage_kb": 2048,
        },
        "security": {
            "safe_mode": True,
            "permissions": "USER",
            "telemetry": False,
            "auto_update": False,
        },
        "telephony": {
            "provider": "DisabledTelephony",
            "enabled": False,
            "policy": "CONFIRM_CALL",
            "business_hours": [9, 18],
            "timezone": "UTC",
            "max_calls_per_hour": 10,
            "max_calls_per_day": 50,
            "cooldown_seconds": 300,
            "call_budget_daily": 100.0,
            "call_budget_monthly": 2000.0,
            "allowlist": [],
            "blocklist": [],
        },
        "gateway": {
            "enabled": False,
            "url": "",
            "token": "",
            "protocol_version": "1.0",
        },
        "email": {
            "enabled": False,
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_pass": "",
            "email_from": "",
        },
        "networking": {
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,
            "max_retries": 3,
        },
        "logging": {
            "level": "INFO",
            "file": "./logs/micromind.log",
            "max_size_mb": 10,
            "redact_secrets": True,
        },
    }


def save_config(config: dict[str, Any]) -> bool:
    """Save configuration to file."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


@router.get("/api/config")
async def get_config():
    """Get full configuration."""
    return load_config()


@router.put("/api/config")
async def update_config(request: Request):
    """Update configuration."""
    data = await request.json()
    section = data.get("section", "")
    new_data = data.get("data", {})

    if not section:
        return {"error": "Section is required"}

    config = load_config()
    config[section] = new_data

    if save_config(config):
        return {"status": "ok", "message": f"Configuration '{section}' updated"}
    return {"error": "Failed to save configuration"}


@router.get("/api/config/profiles")
async def get_profiles():
    """Get available profiles."""
    return {"profiles": PROFILES}


@router.get("/api/config/ai-providers")
async def get_ai_providers():
    """Get available AI providers."""
    return {"providers": AI_PROVIDERS}


@router.get("/api/config/telephony-providers")
async def get_telephony_providers():
    """Get available telephony providers."""
    return {"providers": TELEPHONY_PROVIDERS}


@router.get("/api/config/storage-backends")
async def get_storage_backends():
    """Get available storage backends."""
    return {"backends": STORAGE_BACKENDS}


@router.post("/api/config/reset")
async def reset_config():
    """Reset configuration to defaults."""
    CONFIG_FILE.unlink(missing_ok=True)
    return {"status": "ok", "message": "Configuration reset to defaults"}
