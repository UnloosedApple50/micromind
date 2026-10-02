# MicroMind Architecture

## Overview

MicroMind is an **ultra-lightweight enterprise agent** with decoupled AI capabilities. It is designed to run on hardware ranging from a Pentium III with 256 MB RAM to modern servers, with optional components that can be enabled or disabled based on available resources.

## Design Principles

1. **Core-first**: The core runtime has zero external dependencies beyond Python stdlib
2. **Decoupled AI**: AI capabilities are optional providers, not baked into the core
3. **Profile-aware**: The system adapts its behavior based on detected hardware profile
4. **Safety by default**: All dangerous operations require explicit permission
5. **Offline-capable**: Full functionality without internet connectivity

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        MicroMind                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Core      │  │  Security   │  │    Automation       │  │
│  │  Runtime    │  │   Engine    │  │     Engine          │  │
│  │             │  │             │  │                     │  │
│  │ • SystemInfo│  │ • Permissions│  │ • WHEN/IF/THEN     │  │
│  │ • Contact   │  │ • Validation │  │ • Event triggers   │  │
│  │ • Task      │  │ • Audit log  │  │ • Recursion guard  │  │
│  │ • Ticket    │  │ • Safe mode  │  │ • Dry run mode     │  │
│  │ • Offer     │  │             │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │              │
│         └────────────────┼─────────────────────┘              │
│                          │                                    │
│  ┌───────────────────────┴───────────────────────────────┐   │
│  │                    Storage Layer                       │   │
│  │                                                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │ FlatFile     │  │   SQLite     │  │   Remote    │ │   │
│  │  │ (ULTRA_LOW)  │  │   (LOW+)     │  │  (Gateway)  │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Optional Providers                         │   │
│  │                                                        │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │   │
│  │  │ AI         │  │ Telephony  │  │ Gateway        │   │   │
│  │  │ Providers  │  │ Providers  │  │ (Remote API)   │   │   │
│  │  │            │  │            │  │                │   │   │
│  │  │ • NoAI     │  │ • Gateway  │  │ • AI via GW    │   │   │
│  │  │ • RuleBased│  │ • SIP      │  │ • Storage      │   │   │
│  │  │ • MicroAI  │  │ • Cloud    │  │ • Telephony    │   │   │
│  │  │ • LocalLLM │  │ • LocalPBX │  │ • Email        │   │   │
│  │  │ • RemoteAPI│  │ • Disabled │  │                │   │   │
│  │  │ • Gateway  │  │            │  │                │   │   │
│  │  └────────────┘  └────────────┘  └────────────────┘   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                    CLI (Typer + Rich)                   │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Core Runtime (`micromind.core.runtime`)

The heart of MicroMind. Provides:

- **SystemInfo**: OS, CPU, RAM, storage, cores, GUI, networking detection
- **Contact**: Business contact with call permissions
- **Task**: Business task with priority, status, recurrence
- **Ticket**: Support ticket with workflow states
- **Offer**: Business offer with currency and status
- **Profile detection**: Automatically selects ULTRA_LOW, LEGACY, LOW, STANDARD, HIGH, or SERVER

**Zero dependencies** — uses only Python stdlib.

### Security Engine (`micromind.security.engine`)

- **Permission levels**: ADMIN, MANAGER, USER, READ_ONLY, SERVICE
- **Permission matrix**: Granular action-based permissions
- **Safe mode**: Blocks dangerous operations (calls.place, email.send, system.execute)
- **Input validation**: Email, phone, path validation
- **Input sanitization**: Null byte removal, length truncation
- **Audit logging**: Immutable audit trail

### Storage Layer (`micromind.storage.backends`)

Three backends selected by profile:

| Backend | Profile | Description |
|---------|---------|-------------|
| FlatFileBackend | ULTRA_LOW | JSON files, atomic writes, in-memory cache |
| SQLiteBackend | LOW+ | SQLite with JSON columns, indexed |
| RemoteBackend | Any | Via Gateway API (not yet implemented) |

### AI Providers (`micromind.ai.providers`)

Six providers in increasing order of capability:

| Provider | Profile | Description |
|----------|---------|-------------|
| NoAIProvider | ULTRA_LOW | No AI, rules only |
| RuleBasedAI | ULTRA_LOW | Keyword matching with regex |
| MicroAIProvider | LEGACY | TF-IDF-like scoring with keyword patterns |
| LocalLLMProvider | STANDARD+ | Local LLM via Ollama |
| RemoteAPIProvider | STANDARD+ | Remote AI API |
| GatewayProvider | Any | AI via Gateway |

### Telephony Providers (`micromind.telephony.calls`)

| Provider | Description |
|----------|-------------|
| GatewayTelephony | Calls via Gateway |
| DisabledTelephony | Telephony disabled (default) |
| SIPTelephony | Direct SIP (planned) |
| CloudTelephony | Cloud telephony API (planned) |
| LocalPBX | Local PBX (planned) |

**CallManager safety checks**:
- Missing phone validation
- Blocklist enforcement
- Allowlist enforcement
- Business hours check
- Hourly rate limit
- Daily rate limit
- Cooldown period
- Daily budget limit

### Automation Engine (`micromind.automation.engine`)

WHEN/IF/THEN rule engine:

- **WHEN**: Event trigger (e.g., `email.received`)
- **IF**: Condition expression (e.g., `subject contains 'urgent'`)
- **THEN**: Action to execute (e.g., `create_ticket`)
- **Recursion guard**: Max depth of 5
- **Dry run mode**: Test without executing
- **Execution log**: Full audit trail

## Execution Profiles

| Profile | CPU | RAM | Storage | OS | Internet | LLM |
|---------|-----|-----|---------|----|----------|-----|
| ULTRA_LOW | Pentium III | 256 MB | 4 GB | Windows 98 SE | No | No |
| LEGACY | Pentium 4 | 512 MB | 10 GB | Windows XP | No | No |
| LOW | Intel Core 2 | 2 GB | 50 GB | Windows 7 | Yes | No |
| STANDARD | Intel i3 | 8 GB | 256 GB | Windows 10 | Yes | Yes |
| HIGH | Intel i7 | 32 GB | 1 TB | Windows 11 | Yes | Yes |
| SERVER | Xeon | 128 GB | 4 TB | Linux Server | Yes | Yes |

## Data Flow

```
User Input → CLI → CoreRuntime → SecurityEngine (permission check)
                                    ↓
                              Storage Layer (persist)
                                    ↓
                              AutomationEngine (trigger rules)
                                    ↓
                              AI Provider (classify/generate)
                                    ↓
                              Telephony Provider (if call needed)
                                    ↓
                              Response → CLI → User
```

## Threading Model

- **Synchronous**: Core runtime, storage, security
- **Asynchronous**: AI providers, telephony providers
- **Event-driven**: Automation engine triggers

## Configuration

Configuration is stored in `./config/` directory:

- `config.yaml` — Main configuration
- `permissions.yaml` — Permission overrides
- `automation.yaml` — Automation rules
- `telephony.yaml` — Telephony settings

Data is stored in `./data/` directory:

- FlatFile: `./data/*.json`
- SQLite: `./data/micromind.db`

## Extension Points

1. **Custom AI Provider**: Inherit from `AIProvider`, implement `classify()` and `generate()`
2. **Custom Telephony Provider**: Inherit from `TelephonyProvider`, implement `place_call()`, `cancel_call()`, `get_status()`
3. **Custom Storage Backend**: Inherit from `StorageBackend`, implement `get()`, `set()`, `delete()`, `list_keys()`, `search()`
4. **Custom Automation Handler**: Register via `AutomationEngine.register_handler()`
