# MicroMind Telephony

## Overview

MicroMind's telephony system provides **outbound call automation** with comprehensive safety checks. It is designed to be safe by default, with multiple layers of protection against accidental or unauthorized calls.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CallManager                           │
│                                                          │
│  Safety Checks:                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. Missing phone validation                      │    │
│  │ 2. Blocklist enforcement                         │    │
│  │ 3. Allowlist enforcement                         │    │
│  │ 4. Business hours check                          │    │
│  │ 5. Hourly rate limit                             │    │
│  │ 6. Daily rate limit                              │    │
│  │ 7. Cooldown period                               │    │
│  │ 8. Daily budget limit                            │    │
│  └─────────────────────────────────────────────────┘    │
│                          ↓                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │           TelephonyProvider                      │    │
│  │                                                  │    │
│  │  • GatewayTelephony (via Gateway)               │    │
│  │  • DisabledTelephony (default, safe)            │    │
│  │  • SIPTelephony (planned)                       │    │
│  │  • CloudTelephony (planned)                     │    │
│  │  • LocalPBX (planned)                           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Call Lifecycle

```
QUEUED → DIALING → RINGING → ANSWERED → COMPLETED
                    ↓           ↓
                  BUSY      NO_ANSWER
                    ↓           ↓
                  FAILED ←── VOICEMAIL
                    ↓
                CANCELLED
```

## Call Statuses

| Status | Description |
|--------|-------------|
| `QUEUED` | Call is queued, waiting to be placed |
| `DIALING` | Call is being dialed |
| `RINGING` | Phone is ringing |
| `ANSWERED` | Call was answered |
| `BUSY` | Line was busy |
| `NO_ANSWER` | No answer received |
| `FAILED` | Call failed (see result for reason) |
| `VOICEMAIL` | Voicemail detected |
| `CANCELLED` | Call was cancelled |
| `COMPLETED` | Call completed successfully |

## Call Policies

| Policy | Description |
|--------|-------------|
| `AUTO_CALL` | Place call automatically |
| `CONFIRM_CALL` | Require confirmation before placing |
| `BLOCK_CALL` | Block the call entirely |

## Safety Checks

### 1. Missing Phone Validation

```python
request = await manager.request_call(contact_id="c1", phone="")
# Result: FAILED, "MISSING_PHONE"
```

### 2. Blocklist

```python
manager._blocklist.append("+351912345678")
request = await manager.request_call(contact_id="c1", phone="+351912345678")
# Result: FAILED, "BLOCKED_NUMBER"
```

### 3. Allowlist

```python
manager._allowlist.append("+351999999999")
request = await manager.request_call(contact_id="c1", phone="+351912345678")
# Result: FAILED, "NOT_IN_ALLOWLIST"
```

### 4. Business Hours

```python
manager._business_hours = (9, 18)  # 9 AM to 6 PM UTC
# Calls outside this window will fail with "OUTSIDE_BUSINESS_HOURS"
```

### 5. Hourly Rate Limit

```python
manager._max_calls_per_hour = 10
# After 10 calls in one hour, further calls fail with "HOURLY_LIMIT_EXCEEDED"
```

### 6. Daily Rate Limit

```python
manager._max_calls_per_day = 50
# After 50 calls in one day, further calls fail with "DAILY_LIMIT_EXCEEDED"
```

### 7. Cooldown Period

```python
manager._cooldown_seconds = 300  # 5 minutes
# Calls within 5 minutes of the last call fail with "COOLDOWN_ACTIVE"
```

### 8. Daily Budget

```python
manager._call_budget_daily = 100.0
manager._daily_spent = 100.0
# Further calls fail with "DAILY_BUDGET_EXCEEDED"
```

## Usage Examples

### Basic Call

```python
from micromind.telephony.calls import CallManager, GatewayTelephony

provider = GatewayTelephony(
    gateway_url="https://gateway.example.com",
    token="your-token",
)
manager = CallManager(provider)

# Configure for testing
manager._business_hours = (0, 24)  # Always allow
manager._cooldown_seconds = 0  # No cooldown

request = await manager.request_call(
    contact_id="contact_123",
    phone="+351912345678",
    offer_id="offer_456",
    amount=1500.0,
    currency="EUR",
    object="Enterprise License",
)

print(f"Call status: {request.status}")
print(f"Call result: {request.result}")
```

### With Safety Checks

```python
# Default configuration (safe)
manager = CallManager(GatewayTelephony("https://gw.example.com", "tok"))

# These will fail with appropriate error messages:
await manager.request_call(contact_id="c1", phone="")  # MISSING_PHONE
await manager.request_call(contact_id="c1", phone="+351912345678")  # OUTSIDE_BUSINESS_HOURS (if outside 9-18 UTC)
```

### Check Call Status

```python
call = manager.get_call(call_id)
if call:
    print(f"Status: {call.status}")
    print(f"Duration: {call.duration}s")
    print(f"Result: {call.result}")
```

### List All Calls

```python
calls = manager.list_calls()
for call in calls:
    print(f"{call.id}: {call.status} - {call.phone}")
```

### Get Statistics

```python
stats = manager.get_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"Daily count: {stats['daily_count']}")
print(f"Hourly count: {stats['hourly_count']}")
print(f"Daily budget: {stats['daily_budget']}")
print(f"Daily spent: {stats['daily_spent']}")
```

## Configuration

### Default Configuration

```python
manager = CallManager(provider)

# Defaults:
# _max_calls_per_hour = 10
# _max_calls_per_day = 50
# _cooldown_seconds = 300
# _business_hours = (9, 18)  # UTC
# _timezone = "UTC"
# _call_budget_daily = 100.0
# _call_budget_monthly = 2000.0
```

### Custom Configuration

```python
manager = CallManager(provider)
manager._max_calls_per_hour = 20
manager._max_calls_per_day = 100
manager._cooldown_seconds = 60
manager._business_hours = (8, 20)  # 8 AM to 8 PM
manager._call_budget_daily = 500.0
manager._call_budget_monthly = 5000.0
```

## Telephony Providers

### DisabledTelephony (Default)

```python
from micromind.telephony.calls import DisabledTelephony

provider = DisabledTelephony()
manager = CallManager(provider)

# All calls will fail with "Telephony disabled"
```

### GatewayTelephony

```python
from micromind.telephony.calls import GatewayTelephony

provider = GatewayTelephony(
    gateway_url="https://gateway.example.com",
    token="your-api-token",
)
manager = CallManager(provider)
```

### SIPTelephony (Planned)

```python
# from micromind.telephony.calls import SIPTelephony
# provider = SIPTelephony(
#     server="sip.example.com",
#     username="user",
#     password="pass",
# )
```

### CloudTelephony (Planned)

```python
# from micromind.telephony.calls import CloudTelephony
# provider = CloudTelephony(
#     provider="twilio",
#     account_sid="...",
#     auth_token="...",
# )
```

## Integration with Automation

```python
from micromind.automation.engine import AutomationEngine, AutomationRule

engine = AutomationEngine()
engine.add_rule(AutomationRule(
    name="Auto-call on offer accepted",
    when="offer.accepted",
    if_condition="amount > 1000",
    then_action="place_call",
))

# When an offer is accepted:
results = await engine.trigger("offer.accepted", {
    "offer_id": "offer_123",
    "amount": 1500.0,
    "customer_id": "customer_456",
})
```

## Best Practices

1. **Always use DisabledTelephony in testing**
2. **Configure blocklist for known bad numbers**
3. **Set up allowlist for approved numbers**
4. **Adjust business hours to your timezone**
5. **Set appropriate rate limits for your use case**
6. **Monitor daily/monthly budgets**
7. **Review call logs regularly**
8. **Use dry_run mode for automation testing**
9. **Enable safe mode in untrusted environments**
10. **Persist call logs for compliance**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| All calls fail with "Telephony disabled" | Use GatewayTelephony instead of DisabledTelephony |
| Calls fail with "OUTSIDE_BUSINESS_HOURS" | Adjust `_business_hours` or set to `(0, 24)` |
| Calls fail with "HOURLY_LIMIT_EXCEEDED" | Increase `_max_calls_per_hour` or wait |
| Calls fail with "COOLDOWN_ACTIVE" | Reduce `_cooldown_seconds` or wait |
| Calls fail with "DAILY_BUDGET_EXCEEDED" | Increase `_call_budget_daily` or reset `_daily_spent` |
| Calls fail with "BLOCKED_NUMBER" | Remove number from `_blocklist` |
| Calls fail with "NOT_IN_ALLOWLIST" | Add number to `_allowlist` or clear allowlist |
