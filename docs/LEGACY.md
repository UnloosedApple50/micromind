# MicroMind Legacy Target Documentation

## Overview

MicroMind is designed to run on legacy hardware, including systems from the late 1990s and early 2000s. This document details the legacy compatibility features and constraints.

## Legacy Hardware Targets

### ULTRA_LOW Profile

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Pentium III 500 MHz | Pentium III 800 MHz |
| RAM | 256 MB | 512 MB |
| Storage | 4 GB | 10 GB |
| OS | Windows 98 SE | Windows ME |
| Python | 3.8 | 3.8 |
| Internet | Not required | Not required |

### LEGACY Profile

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Pentium 4 1.6 GHz | Pentium 4 2.4 GHz |
| RAM | 512 MB | 1 GB |
| Storage | 10 GB | 20 GB |
| OS | Windows XP | Windows XP SP3 |
| Python | 3.8 | 3.8 |
| Internet | Not required | Not required |

## Legacy Constraints

### No External Dependencies

The ULTRA_LOW and LEGACY profiles use **only Python standard library**. No pip packages are required.

```python
# ✅ Allowed (stdlib)
import json
import os
import platform
import sqlite3
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ❌ Not allowed (external)
# import typer
# import rich
# import httpx
# import yaml
```

### FlatFile Storage Only

ULTRA_LOW and LEGACY profiles use FlatFileBackend (JSON files). SQLite is not available.

```python
# ✅ ULTRA_LOW / LEGACY
from micromind.storage.backends import FlatFileBackend
backend = FlatFileBackend(data_dir="./data")

# ❌ Not available on ULTRA_LOW / LEGACY
# from micromind.storage.backends import SQLiteBackend
```

### No GUI

Legacy profiles use CLI only. Rich formatting is not available.

```python
# ✅ ULTRA_LOW / LEGACY
print("Contact added: Alice")

# ❌ Not available on ULTRA_LOW / LEGACY
# from rich.console import Console
# console = Console()
# console.print("[green]Contact added: Alice[/green]")
```

### No Internet

Legacy profiles operate fully offline. No network connectivity is required or used.

```python
# ✅ ULTRA_LOW / LEGACY
# All functionality works offline

# ❌ Not available on ULTRA_LOW / LEGACY
# - RemoteBackend
# - GatewayTelephony
# - RemoteAPIProvider
# - GatewayProvider
```

### No LLM

Legacy profiles use rule-based AI only. No local or remote LLM.

```python
# ✅ ULTRA_LOW / LEGACY
from micromind.ai.providers import NoAIProvider, RuleBasedAI, MicroAIProvider

# ❌ Not available on ULTRA_LOW / LEGACY
# from micromind.ai.providers import LocalLLMProvider, RemoteAPIProvider
```

## Legacy Installation

### Windows 98 SE / Windows ME

1. Install Python 3.8 (last version supporting Windows 98)
2. Copy MicroMind source files to `C:\MicroMind\`
3. Run from command prompt:
   ```
   C:\MicroMind> python -m micromind.cli
   ```

### Windows XP

1. Install Python 3.8
2. Copy MicroMind source files to `C:\MicroMind\`
3. Run from command prompt:
   ```
   C:\MicroMind> python -m micromind.cli
   ```

## Legacy Configuration

### Minimal Configuration

```yaml
# config/config.yaml
profile: ULTRA_LOW
storage:
  backend: flatfile
  data_dir: ./data
ai:
  provider: rule_based
telephony:
  enabled: false
automation:
  enabled: true
  max_rules: 50
```

### Directory Structure

```
C:\MicroMind\
├── config\
│   └── config.yaml
├── data\
│   ├── contact_alice.json
│   ├── contact_bob.json
│   ├── task_001.json
│   └── ...
├── src\
│   └── micromind\
│       ├── __init__.py
│       ├── core\
│       ├── security\
│       ├── storage\
│       ├── ai\
│       ├── automation\
│       └── cli.py
└── micromind.py (launcher)
```

## Legacy CLI

### Basic Commands

```bash
# Show status
python -m micromind.cli status

# Add contact
python -m micromind.cli contact-add "Alice" --email alice@example.com

# Search contacts
python -m micromind.cli contact-search "Alice"

# Add task
python -m micromind.cli task-add "Follow up" --priority high

# List tasks
python -m micromind.cli task-list

# Complete task
python -m micromind.cli task-complete task_follow_up

# Create ticket
python -m micromind.cli ticket-create "Bug report" --customer Alice

# List tickets
python -m micromind.cli ticket-list

# Create offer
python -m micromind.cli offer-create customer_123 --object "License" --amount 1500

# Run diagnostics
python -m micromind.cli doctor
```

## Legacy Performance

### Startup Time

| Profile | Target | Typical |
|---------|--------|---------|
| ULTRA_LOW | < 500 ms | ~200 ms |
| LEGACY | < 300 ms | ~150 ms |

### Memory Usage

| Profile | Idle RAM | Peak RAM |
|---------|----------|----------|
| ULTRA_LOW | < 20 MB | < 50 MB |
| LEGACY | < 30 MB | < 80 MB |

### Storage

| Profile | 1000 Entities | 10000 Entities |
|---------|---------------|----------------|
| ULTRA_LOW | ~2 MB | ~20 MB |
| LEGACY | ~2 MB | ~20 MB |

## Legacy Limitations

### Not Available on ULTRA_LOW / LEGACY

| Feature | Reason |
|---------|--------|
| SQLite | Requires more RAM |
| Rich CLI | Requires more RAM |
| Local LLM | Requires more RAM |
| Remote API | Requires internet |
| Gateway | Requires internet |
| SIP Telephony | Requires internet |
| Cloud Telephony | Requires internet |
| GUI | Requires more RAM |

### Available on ULTRA_LOW / LEGACY

| Feature | Notes |
|---------|-------|
| FlatFile storage | JSON files |
| Rule-based AI | Keyword matching |
| MicroAI | TF-IDF-like scoring |
| Automation | WHEN/IF/THEN rules |
| Security | Permissions, audit |
| CLI | Basic text output |
| Contacts | Full CRUD |
| Tasks | Full CRUD |
| Tickets | Full CRUD |
| Offers | Full CRUD |

## Legacy Migration Path

When upgrading from legacy hardware:

```
ULTRA_LOW → LEGACY → LOW → STANDARD → HIGH → SERVER
```

### Migration Steps

1. **Backup data**: Copy `./data/` directory
2. **Upgrade hardware**: Install new system
3. **Install Python**: Python 3.8+ on new system
4. **Copy data**: Restore `./data/` directory
5. **Update config**: Change profile in `config.yaml`
6. **Test**: Run `python -m micromind.cli doctor`

### Data Compatibility

- FlatFile JSON files are **fully compatible** across all profiles
- No data migration required when upgrading
- All data preserved across profile changes

## Legacy Security

### Safe Mode

Safe mode is **recommended** for all legacy profiles:

```python
from micromind.security.engine import SecurityEngine

engine = SecurityEngine(safe_mode=True)
```

### Default Security

Legacy profiles use **Legacy Safe** security mode:
- All dangerous operations blocked
- Input validation enabled
- Audit logging enabled
- Path traversal protection

## Legacy Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Python not found" | Add Python to PATH |
| "Permission denied" | Run as administrator |
| "Disk full" | Clean up `./data/` directory |
| "Out of memory" | Reduce number of entities |
| "Slow startup" | Disable unused modules |

### Diagnostic Commands

```bash
# Check Python version
python --version

# Check available memory
python -c "import os; print(os.sysconf('PHYS_PAGES') * os.sysconf('PAGE_SIZE') / 1024 / 1024, 'MB')"

# Check disk space
python -c "import shutil; print(shutil.disk_usage('.').free / 1024 / 1024, 'MB free')"

# Run diagnostics
python -m micromind.cli doctor
```

## Legacy Support

- **Python 3.8**: Minimum supported version
- **Windows 98 SE**: Last supported Windows 9x
- **Windows XP**: Last supported Windows NT 5.x
- **Linux**: Any distribution with Python 3.8+
- **macOS**: Development only, not recommended for production
