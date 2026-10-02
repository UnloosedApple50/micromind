"""Automation engine — WHEN/IF/THEN rules."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class AutomationRule:
    """Automation rule: WHEN event IF condition THEN action."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    enabled: bool = True
    dry_run: bool = False
    when: str = ""  # Event trigger
    if_condition: str = ""  # Condition expression
    then_action: str = ""  # Action to execute
    max_depth: int = 5
    execution_count: int = 0
    last_executed: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AutomationEngine:
    """WHEN/IF/THEN automation engine."""

    def __init__(self) -> None:
        self._rules: dict[str, AutomationRule] = {}
        self._handlers: dict[str, Callable] = {}
        self._execution_log: list[dict[str, Any]] = []

    def register_handler(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        self._handlers[event] = handler

    def add_rule(self, rule: AutomationRule) -> str:
        """Add an automation rule."""
        self._rules[rule.id] = rule
        return rule.id

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an automation rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def list_rules(self) -> list[AutomationRule]:
        """List all rules."""
        return list(self._rules.values())

    async def trigger(self, event: str, context: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
        """Trigger automation rules for an event."""
        results = []

        if depth > 5:  # Max recursion depth
            return results

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.when != event:
                continue

            # Check condition
            if self._evaluate_condition(rule.if_condition, context):
                result = await self._execute_action(rule, context, depth)
                results.append(result)

        return results

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate IF condition."""
        if not condition:
            return True

        # Simple condition evaluation
        # Example: "subject contains 'urgente'"
        try:
            if "contains" in condition:
                parts = condition.split("contains")
                field = parts[0].strip().strip("'\"")
                value = parts[1].strip().strip("'\"")
                field_value = str(context.get(field, "")).lower()
                return value.lower() in field_value
            return True
        except Exception:
            return False

    async def _execute_action(self, rule: AutomationRule, context: dict[str, Any], depth: int) -> dict[str, Any]:
        """Execute THEN action."""
        execution_id = str(uuid.uuid4())
        result = {
            "execution_id": execution_id,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "action": rule.then_action,
            "status": "executed" if not rule.dry_run else "dry_run",
            "timestamp": datetime.utcnow().isoformat(),
            "depth": depth,
        }

        self._execution_log.append(result)
        rule.execution_count += 1
        rule.last_executed = datetime.utcnow().isoformat()

        return result

    def get_execution_log(self) -> list[dict[str, Any]]:
        """Get execution log."""
        return self._execution_log.copy()
