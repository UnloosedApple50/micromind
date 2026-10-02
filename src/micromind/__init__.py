"""MicroMind — Agente empresarial ultraleve com capacidades de IA desacopladas.

Core local + MicroAI + LLM opcional + Gateway opcional + Telephony opcional + GUI opcional
"""

__version__ = "1.0.0"

# Execution profiles
PROFILES = {
    "ULTRA_LOW": {
        "cpu": "Pentium III",
        "ram_mb": 256,
        "storage_gb": 4,
        "os": "Windows 98 SE",
        "internet": False,
        "llm": False,
        "description": "Minimum hardware profile",
    },
    "LEGACY": {
        "cpu": "Pentium 4",
        "ram_mb": 512,
        "storage_gb": 10,
        "os": "Windows XP",
        "internet": False,
        "llm": False,
        "description": "Legacy hardware profile",
    },
    "LOW": {
        "cpu": "Intel Core 2",
        "ram_mb": 2048,
        "storage_gb": 50,
        "os": "Windows 7",
        "internet": True,
        "llm": False,
        "description": "Low-end modern hardware",
    },
    "STANDARD": {
        "cpu": "Intel i3",
        "ram_mb": 8192,
        "storage_gb": 256,
        "os": "Windows 10",
        "internet": True,
        "llm": True,
        "description": "Standard modern hardware",
    },
    "HIGH": {
        "cpu": "Intel i7",
        "ram_mb": 32768,
        "storage_gb": 1024,
        "os": "Windows 11",
        "internet": True,
        "llm": True,
        "description": "High-end hardware",
    },
    "SERVER": {
        "cpu": "Xeon",
        "ram_mb": 131072,
        "storage_gb": 4096,
        "os": "Linux Server",
        "internet": True,
        "llm": True,
        "description": "Server hardware",
    },
}

# Compatibility status
STATUS = {
    "SUPPORTED": "Tested and working",
    "EXPERIMENTAL": "In testing",
    "TESTED": "Tested on target",
    "UNTESTED": "Not yet tested",
    "NOT_SUPPORTED": "Not supported",
}

# AI Providers
AI_PROVIDERS = {
    "NoAIProvider": "No AI — rules only",
    "RuleBasedAI": "Rule-based classification",
    "MicroAIProvider": "Lightweight local AI",
    "LocalLLMProvider": "Local LLM (Ollama)",
    "RemoteAPIProvider": "Remote AI API",
    "GatewayProvider": "AI via Gateway",
}

# Telephony Providers
TELEPHONY_PROVIDERS = {
    "GatewayTelephony": "Calls via Gateway",
    "SIPTelephony": "Direct SIP",
    "CloudTelephony": "Cloud telephony API",
    "LocalPBX": "Local PBX",
    "DisabledTelephony": "Telephony disabled",
}

# Storage Backends
STORAGE_BACKENDS = {
    "FlatFileBackend": "Flat file storage (ULTRA_LOW)",
    "SQLiteBackend": "SQLite storage (LOW+)",
    "RemoteBackend": "Remote storage via Gateway",
}

# Permission levels
PERMISSIONS = {
    "ADMIN": "Full system access",
    "MANAGER": "Manage users and data",
    "USER": "Standard user access",
    "READ_ONLY": "Read-only access",
    "SERVICE": "Service account",
}

# Risk levels
RISK_LEVELS = {
    "LOW": "Low risk operation",
    "MEDIUM": "Medium risk operation",
    "HIGH": "High risk operation",
    "CRITICAL": "Critical risk operation",
}
