"""Tests for AutomationEngine."""
from __future__ import annotations

import pytest

from micromind.automation.engine import AutomationEngine, AutomationRule


# ---------------------------------------------------------------------------
# AutomationRule
# ---------------------------------------------------------------------------


class TestAutomationRule:
    def test_defaults(self) -> None:
        rule = AutomationRule()
        assert rule.id != ""
        assert rule.name == ""
        assert rule.enabled is True
        assert rule.dry_run is False
        assert rule.when == ""
        assert rule.if_condition == ""
        assert rule.then_action == ""
        assert rule.max_depth == 5
        assert rule.execution_count == 0
        assert rule.last_executed == ""
        assert rule.created_at != ""

    def test_custom_values(self) -> None:
        rule = AutomationRule(
            name="Test Rule",
            when="email.received",
            if_condition="subject contains 'urgent'",
            then_action="create_ticket",
            dry_run=True,
        )
        assert rule.name == "Test Rule"
        assert rule.when == "email.received"
        assert rule.if_condition == "subject contains 'urgent'"
        assert rule.then_action == "create_ticket"
        assert rule.dry_run is True


# ---------------------------------------------------------------------------
# AutomationEngine — rule management
# ---------------------------------------------------------------------------


class TestRuleManagement:
    def test_add_rule(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(name="Test", when="event", then_action="action")
        rule_id = engine.add_rule(rule)
        assert rule_id == rule.id
        assert len(engine.list_rules()) == 1

    def test_remove_rule(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(name="Test")
        rule_id = engine.add_rule(rule)
        assert engine.remove_rule(rule_id) is True
        assert len(engine.list_rules()) == 0

    def test_remove_nonexistent_rule(self) -> None:
        engine = AutomationEngine()
        assert engine.remove_rule("nonexistent") is False

    def test_enable_rule(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(name="Test", enabled=False)
        rule_id = engine.add_rule(rule)
        assert engine.enable_rule(rule_id) is True
        assert engine.list_rules()[0].enabled is True

    def test_enable_nonexistent_rule(self) -> None:
        engine = AutomationEngine()
        assert engine.enable_rule("nonexistent") is False

    def test_disable_rule(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(name="Test", enabled=True)
        rule_id = engine.add_rule(rule)
        assert engine.disable_rule(rule_id) is True
        assert engine.list_rules()[0].enabled is False

    def test_disable_nonexistent_rule(self) -> None:
        engine = AutomationEngine()
        assert engine.disable_rule("nonexistent") is False

    def test_list_rules_empty(self) -> None:
        engine = AutomationEngine()
        assert engine.list_rules() == []

    def test_list_rules_multiple(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(name="Rule 1"))
        engine.add_rule(AutomationRule(name="Rule 2"))
        engine.add_rule(AutomationRule(name="Rule 3"))
        assert len(engine.list_rules()) == 3


# ---------------------------------------------------------------------------
# AutomationEngine — trigger
# ---------------------------------------------------------------------------


class TestTrigger:
    @pytest.mark.asyncio
    async def test_trigger_matching_event(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        results = await engine.trigger("email.received", {})
        assert len(results) == 1
        assert results[0]["rule_name"] == "Test Rule"
        assert results[0]["action"] == "create_ticket"
        assert results[0]["status"] == "executed"

    @pytest.mark.asyncio
    async def test_trigger_non_matching_event(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        results = await engine.trigger("call.completed", {})
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_trigger_disabled_rule(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
            enabled=False,
        ))
        results = await engine.trigger("email.received", {})
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_trigger_dry_run(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
            dry_run=True,
        ))
        results = await engine.trigger("email.received", {})
        assert len(results) == 1
        assert results[0]["status"] == "dry_run"

    @pytest.mark.asyncio
    async def test_trigger_increments_execution_count(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        )
        engine.add_rule(rule)
        await engine.trigger("email.received", {})
        assert rule.execution_count == 1
        await engine.trigger("email.received", {})
        assert rule.execution_count == 2

    @pytest.mark.asyncio
    async def test_trigger_updates_last_executed(self) -> None:
        engine = AutomationEngine()
        rule = AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        )
        engine.add_rule(rule)
        assert rule.last_executed == ""
        await engine.trigger("email.received", {})
        assert rule.last_executed != ""

    @pytest.mark.asyncio
    async def test_trigger_max_depth(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        # Depth 6 should return empty (max is 5)
        results = await engine.trigger("email.received", {}, depth=6)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_trigger_at_max_depth(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        # Depth 5 should still work
        results = await engine.trigger("email.received", {}, depth=5)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# AutomationEngine — condition evaluation
# ---------------------------------------------------------------------------


class TestConditionEvaluation:
    @pytest.mark.asyncio
    async def test_condition_contains_match(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            if_condition="subject contains 'urgent'",
            then_action="create_ticket",
        ))
        results = await engine.trigger("email.received", {"subject": "This is urgent"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_condition_contains_no_match(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            if_condition="subject contains 'urgent'",
            then_action="create_ticket",
        ))
        results = await engine.trigger("email.received", {"subject": "Normal email"})
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_condition_always_true(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            if_condition="",
            then_action="create_ticket",
        ))
        results = await engine.trigger("email.received", {})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_unknown_condition_returns_true(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            if_condition="some unknown condition",
            then_action="create_ticket",
        ))
        results = await engine.trigger("email.received", {})
        assert len(results) == 1


# ---------------------------------------------------------------------------
# AutomationEngine — execution log
# ---------------------------------------------------------------------------


class TestExecutionLog:
    def test_empty_log(self) -> None:
        engine = AutomationEngine()
        assert engine.get_execution_log() == []

    @pytest.mark.asyncio
    async def test_log_after_trigger(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        await engine.trigger("email.received", {})
        log = engine.get_execution_log()
        assert len(log) == 1
        assert log[0]["rule_name"] == "Test Rule"
        assert log[0]["action"] == "create_ticket"
        assert "timestamp" in log[0]
        assert "execution_id" in log[0]

    @pytest.mark.asyncio
    async def test_log_copies(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        await engine.trigger("email.received", {})
        log = engine.get_execution_log()
        log.clear()
        # Original should be unaffected
        assert len(engine.get_execution_log()) == 1

    @pytest.mark.asyncio
    async def test_multiple_executions_logged(self) -> None:
        engine = AutomationEngine()
        engine.add_rule(AutomationRule(
            name="Test Rule",
            when="email.received",
            then_action="create_ticket",
        ))
        await engine.trigger("email.received", {})
        await engine.trigger("email.received", {})
        await engine.trigger("email.received", {})
        log = engine.get_execution_log()
        assert len(log) == 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> AutomationEngine:
    return AutomationEngine()
