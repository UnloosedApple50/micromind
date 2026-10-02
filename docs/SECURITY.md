# MicroMind Security Model

## Overview

MicroMind implements a **defense-in-depth** security model with multiple layers of protection. The system is designed to be safe by default, with explicit permission required for dangerous operations.

## Permission Levels

MicroMind defines five permission levels, from most to least privileged:

| Level | Description | Use Case |
|-------|-------------|----------|
| **ADMIN** | Full system access | System administrators |
| **MANAGER** | Manage users and data | Team leads, managers |
| **USER** | Standard user access | Regular users |
| **READ_ONLY** | Read-only access | Auditors, viewers |
| **SERVICE** | Service account | Automated processes, APIs |

## Permission Matrix

Each permission level grants specific actions:

```
ADMIN:       email.read, email.send, contacts.read, contacts.write,
             tasks.read, tasks.write, tickets.read, tickets.write,
             offers.read, offers.write, calls.read, calls.place,
             calls.configure, ai.use, system.execute

MANAGER:     email.read, email.send, contacts.read, contacts.write,
             tasks.read, tasks.write, tickets.read, tickets.write,
             offers.read, offers.write, calls.read, ai.use

USER:        email.read, contacts.read, tasks.read, tasks.write,
             tickets.read, tickets.write, offers.read

READ_ONLY:   email.read, contacts.read, tasks.read, tickets.read,
             offers.read, calls.read

SERVICE:     email.read, email.send, contacts.read, contacts.write,
             tasks.read, tasks.write, tickets.read, tickets.write,
             offers.read, offers.write, calls.read, calls.place, ai.use
```

## Safe Mode

When safe mode is enabled (`SecurityEngine(safe_mode=True)`), the following actions are **blocked for all users**, including ADMIN:

- `calls.place` — Placing phone calls
- `email.send` — Sending emails
- `system.execute` — Executing system commands

Safe mode is recommended for:
- ULTRA_LOW and LEGACY profiles
- Untrusted environments
- Testing and development
- Compliance requirements

## Input Validation

### Email Validation

```python
engine.validate_email("user@example.com")  # True
engine.validate_email("not-an-email")       # False
```

Pattern: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

### Phone Validation

```python
engine.validate_phone("+351912345678")   # True
engine.validate_phone("912345678")        # True
engine.validate_phone("abc123")           # False
```

- Removes common separators: spaces, hyphens, parentheses, dots
- Validates: 7-15 digits, optional `+` prefix

### Path Validation

```python
engine.validate_path("/data/file.txt", "/data")  # True
engine.validate_path("/etc/passwd", "/data")     # False
```

- Resolves symlinks and relative paths
- Prevents path traversal attacks
- Ensures target is within allowed base directory

### Input Sanitization

```python
engine.sanitize_input("hello\x00world")  # "helloworld"
engine.sanitize_input("a" * 20000)       # Truncated to 10000 chars
```

- Removes null bytes
- Truncates to maximum length (default: 10000 characters)

## Audit Logging

All security-relevant actions are logged:

```python
engine.audit("email.send", "admin", {"to": "user@example.com", "subject": "Hello"})
```

Audit log entries contain:
- **timestamp**: ISO 8601 UTC timestamp
- **action**: Action performed
- **user**: Permission level of the actor
- **details**: Additional context

The audit log is an append-only in-memory list. For production use, persist to disk or forward to a SIEM.

## Telephony Safety

The CallManager implements multiple safety checks before placing calls:

| Check | Description | Failure Result |
|-------|-------------|----------------|
| Missing phone | Phone number is empty | `MISSING_PHONE` |
| Blocklist | Number is in blocklist | `BLOCKED_NUMBER` |
| Allowlist | Number not in allowlist (if configured) | `NOT_IN_ALLOWLIST` |
| Business hours | Current time outside business hours | `OUTSIDE_BUSINESS_HOURS` |
| Hourly limit | Too many calls this hour | `HOURLY_LIMIT_EXCEEDED` |
| Daily limit | Too many calls today | `DAILY_LIMIT_EXCEEDED` |
| Cooldown | Too soon since last call | `COOLDOWN_ACTIVE` |
| Daily budget | Daily call budget exhausted | `DAILY_BUDGET_EXCEEDED` |

### Default Limits

| Limit | Default Value |
|-------|---------------|
| Max calls per hour | 10 |
| Max calls per day | 50 |
| Cooldown period | 300 seconds (5 minutes) |
| Business hours | 9 AM – 6 PM UTC |
| Daily call budget | 100.0 (currency units) |
| Monthly call budget | 2000.0 (currency units) |

## Risk Levels

Operations are classified by risk:

| Level | Description | Examples |
|-------|-------------|----------|
| **LOW** | Minimal risk | Reading contacts, listing tasks |
| **MEDIUM** | Moderate risk | Creating tickets, updating offers |
| **HIGH** | Significant risk | Sending emails, placing calls |
| **CRITICAL** | Critical risk | System configuration, data deletion |

## Data Protection

### At Rest

- **FlatFile**: JSON files with atomic writes (temp file + rename)
- **SQLite**: Single-file database with WAL mode support
- **Remote**: Encrypted transport via HTTPS

### In Transit

- All remote communication uses HTTPS/TLS
- API tokens are required for Gateway communication
- No plaintext credentials in configuration files

### In Memory

- Sensitive data (tokens, keys) stored in memory only
- No persistent credential storage in core runtime
- Audit log is in-memory (persist externally for production)

## Threat Model

### Addressed Threats

| Threat | Mitigation |
|--------|------------|
| Unauthorized access | Permission matrix, safe mode |
| Input injection | Input validation, sanitization |
| Path traversal | Path validation with resolve() |
| Rate limiting abuse | Call rate limits, cooldowns |
| Budget overruns | Daily/monthly call budgets |
| Audit tampering | Append-only audit log |
| Privilege escalation | Permission hierarchy, safe mode |

### Not Addressed (Out of Scope)

- Physical security of hardware
- Network-level attacks (DDoS, MITM)
- Side-channel attacks
- Social engineering

## Compliance Considerations

- **GDPR**: Data minimization, right to erasure (delete API)
- **SOC 2**: Audit logging, access controls
- **HIPAA**: Not recommended for PHI without additional controls
- **PCI DSS**: Not recommended for payment card data

## Security Checklist

Before deploying to production:

- [ ] Enable safe mode for untrusted environments
- [ ] Configure blocklist for known bad numbers
- [ ] Set up allowlist for approved numbers
- [ ] Adjust business hours to your timezone
- [ ] Set appropriate rate limits
- [ ] Configure daily/monthly budgets
- [ ] Enable audit logging to persistent storage
- [ ] Use HTTPS for all remote communication
- [ ] Rotate API tokens regularly
- [ ] Review permission assignments
- [ ] Test path validation with your directory structure
