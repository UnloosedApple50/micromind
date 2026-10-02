# MicroMind

**Agente empresarial ultraleve com capacidades de IA desacopladas.**

Core local + MicroAI + LLM opcional + Gateway opcional + Telephony opcional + GUI opcional

---

## Overview

MicroMind is an **ultra-lightweight enterprise agent** designed to run on hardware ranging from a Pentium III with 256 MB RAM to modern servers. It provides business automation capabilities with **decoupled AI** — meaning AI is an optional provider, not a core dependency.

### Key Features

- **Ultra-lightweight**: Runs on 256 MB RAM, 4 GB storage
- **Offline-capable**: Full functionality without internet
- **Decoupled AI**: Optional AI providers (NoAI, RuleBased, MicroAI, LocalLLM, RemoteAPI, Gateway)
- **Profile-aware**: Automatically adapts to hardware capabilities
- **Safety by default**: Comprehensive permission system and audit logging
- **Automation**: WHEN/IF/THEN rule engine with recursion guard
- **Telephony**: Outbound call management with rate limits and budgets
- **Storage**: FlatFile (ULTRA_LOW) or SQLite (LOW+) backends

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/micromind/micromind.git
cd micromind

# Install (ULTRA_LOW / LEGACY — no dependencies)
pip install .

# Install (STANDARD — with CLI and remote capabilities)
pip install ".[standard]"

# Install (HIGH — with local LLM)
pip install ".[high]"

# Install (SERVER — with Gateway)
pip install ".[server]"

# Install (development)
pip install ".[dev]"
```

### Basic Usage

```bash
# Run setup wizard
python -m micromind.cli setup

# Check system status
python -m micromind.cli status

# Run diagnostics
python -m micromind.cli doctor

# Add a contact
python -m micromind.cli contact-add "Alice" --email alice@example.com

# Search contacts
python -m micromind.cli contact-search "Alice"

# Add a task
python -m micromind.cli task-add "Follow up" --priority high

# List tasks
python -m micromind.cli task-list

# Create a ticket
python -m micromind.cli ticket-create "Bug report" --customer Alice

# Create an offer
python -m micromind.cli offer-create customer_123 --object "License" --amount 1500
```

### Python API

```python
from micromind.core.runtime import CoreRuntime

# Initialize
runtime = CoreRuntime(config_dir="./config", data_dir="./data")

# Check profile
print(f"Profile: {runtime.profile.value}")
print(f"OS: {runtime.system_info.os}")

# Get status
status = runtime.status()
print(f"AI: {status['ai']}")
print(f"Security: {status['security']}")
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MicroMind                              │
├─────────────────────────────────────────────────────────────┤
│  Core Runtime  │  Security Engine  │  Automation Engine     │
│  • SystemInfo  │  • Permissions    │  • WHEN/IF/THEN        │
│  • Contact     │  • Validation     │  • Event triggers      │
│  • Task        │  • Audit log      │  • Recursion guard     │
│  • Ticket      │  • Safe mode      │  • Dry run mode        │
│  • Offer       │                   │                        │
├─────────────────────────────────────────────────────────────┤
│                    Storage Layer                             │
│  FlatFileBackend (ULTRA_LOW) │ SQLiteBackend (LOW+)         │
├─────────────────────────────────────────────────────────────┤
│              Optional Providers                              │
│  AI: NoAI │ RuleBased │ MicroAI │ LocalLLM │ RemoteAPI     │
│  Telephony: Disabled │ Gateway │ SIP │ Cloud │ LocalPBX    │
└─────────────────────────────────────────────────────────────┘
```

## Execution Profiles

| Profile | CPU | RAM | Storage | OS | Internet | LLM |
|---------|-----|-----|---------|----|----------|-----|
| ULTRA_LOW | Pentium III | 256 MB | 4 GB | Windows 98 SE | No | No |
| LEGACY | Pentium 4 | 512 MB | 10 GB | Windows XP | No | No |
| LOW | Intel Core 2 | 2 GB | 50 GB | Windows 7 | Yes | No |
| STANDARD | Intel i3 | 8 GB | 256 GB | Windows 10 | Yes | Yes |
| HIGH | Intel i7 | 32 GB | 1 TB | Windows 11 | Yes | Yes |
| SERVER | Xeon | 128 GB | 4 TB | Linux Server | Yes | Yes |

## AI Providers

| Provider | Profile | Description |
|----------|---------|-------------|
| NoAIProvider | ULTRA_LOW | No AI, rules only |
| RuleBasedAI | ULTRA_LOW | Keyword matching with regex |
| MicroAIProvider | LEGACY | TF-IDF-like scoring with keyword patterns |
| LocalLLMProvider | STANDARD+ | Local LLM via Ollama |
| RemoteAPIProvider | STANDARD+ | Remote AI API |
| GatewayProvider | Any | AI via Gateway |

## Security

MicroMind implements a **defense-in-depth** security model:

- **Permission levels**: ADMIN, MANAGER, USER, READ_ONLY, SERVICE
- **Permission matrix**: Granular action-based permissions
- **Safe mode**: Blocks dangerous operations
- **Input validation**: Email, phone, path validation
- **Audit logging**: Immutable audit trail

```python
from micromind.security.engine import SecurityEngine, Permission

engine = SecurityEngine(safe_mode=True)
engine.check_permission(Permission.ADMIN, "email.send")  # False (safe mode)
engine.check_permission(Permission.ADMIN, "email.read")  # True
```

## Automation

WHEN/IF/THEN rule engine:

```python
from micromind.automation.engine import AutomationEngine, AutomationRule

engine = AutomationEngine()
engine.add_rule(AutomationRule(
    name="Auto-ticket on urgent email",
    when="email.received",
    if_condition="subject contains 'urgent'",
    then_action="create_ticket",
))

# Trigger
results = await engine.trigger("email.received", {"subject": "Urgent: Server down"})
```

## Telephony

Outbound call management with safety checks:

```python
from micromind.telephony.calls import CallManager, GatewayTelephony

provider = GatewayTelephony("https://gateway.example.com", "token")
manager = CallManager(provider)

# Configure
manager._business_hours = (9, 18)
manager._max_calls_per_hour = 10
manager._max_calls_per_day = 50

# Place call
request = await manager.request_call(
    contact_id="contact_123",
    phone="+351912345678",
    offer_id="offer_456",
    amount=1500.0,
)
```

## Storage

```python
# FlatFile (ULTRA_LOW / LEGACY)
from micromind.storage.backends import FlatFileBackend
backend = FlatFileBackend(data_dir="./data")
backend.set("contact_123", {"name": "Alice", "email": "alice@example.com"})
contact = backend.get("contact_123")

# SQLite (LOW+)
from micromind.storage.backends import SQLiteBackend
backend = SQLiteBackend(db_path="./data/micromind.db")
backend.set("contact_123", {"name": "Alice", "email": "alice@example.com"})
contact = backend.get("contact_123")
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MICROMIND_PROFILE` | auto | Execution profile |
| `MICROMIND_CONFIG_DIR` | ./config | Configuration directory |
| `MICROMIND_DATA_DIR` | ./data | Data directory |
| `MICROMIND_AI_PROVIDER` | micro_ai | AI provider |
| `MICROMIND_TELEPHONY_ENABLED` | false | Enable telephony |
| `MICROMIND_GATEWAY_URL` | | Gateway URL |
| `MICROMIND_GATEWAY_TOKEN` | | Gateway API token |

## Benchmarks

```bash
# Run all benchmarks
python -m benchmarks.startup

# Run specific benchmark
python -c "from benchmarks.startup import benchmark_startup; print(benchmark_startup())"
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=micromind --cov-report=term-missing

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and components
- [Security](docs/SECURITY.md) — Security model and permissions
- [Compatibility](docs/COMPATIBILITY.md) — Hardware and software compatibility
- [Telephony](docs/TELEPHONY.md) — Call management and safety
- [Legacy](docs/LEGACY.md) — Legacy hardware support

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING](CONTRIBUTING.md) guide for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/micromind/micromind/issues)
- **Discussions**: [GitHub Discussions](https://github.com/micromind/micromind/discussions)
- **Documentation**: [GitHub Wiki](https://github.com/micromind/micromind/wiki)
