"""Tests for AI providers."""
from __future__ import annotations

import pytest

from micromind.ai.providers import (
    AIResult,
    GatewayProvider,
    LocalLLMProvider,
    MicroAIProvider,
    NoAIProvider,
    RemoteAPIProvider,
    RuleBasedAI,
)


# ---------------------------------------------------------------------------
# AIResult
# ---------------------------------------------------------------------------


class TestAIResult:
    def test_defaults(self) -> None:
        result = AIResult()
        assert result.intent == ""
        assert result.confidence == 0.0
        assert result.proposed_action == ""
        assert result.validation == "pending"
        assert result.permission == "denied"
        assert result.entities == {}
        assert result.response == ""

    def test_custom_values(self) -> None:
        result = AIResult(
            intent="offer",
            confidence=0.9,
            proposed_action="process",
            validation="approved",
            permission="allowed",
            entities={"amount": 100},
            response="Done",
        )
        assert result.intent == "offer"
        assert result.confidence == 0.9
        assert result.proposed_action == "process"
        assert result.validation == "approved"
        assert result.permission == "allowed"
        assert result.entities == {"amount": 100}
        assert result.response == "Done"


# ---------------------------------------------------------------------------
# NoAIProvider
# ---------------------------------------------------------------------------


class TestNoAIProvider:
    @pytest.mark.asyncio
    async def test_classify_returns_unknown(self) -> None:
        provider = NoAIProvider()
        result = await provider.classify("any text")
        assert result.intent == "unknown"
        assert result.confidence == 0.0
        assert result.proposed_action == "none"

    @pytest.mark.asyncio
    async def test_generate_returns_disabled_message(self) -> None:
        provider = NoAIProvider()
        response = await provider.generate("prompt", {})
        assert "disabled" in response.lower()
        assert "rule-based" in response.lower()


# ---------------------------------------------------------------------------
# RuleBasedAI
# ---------------------------------------------------------------------------


class TestRuleBasedAI:
    @pytest.mark.asyncio
    async def test_classify_offer(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Tenho uma oferta para você")
        assert result.intent == "offer_received"
        assert result.confidence == 0.7
        assert result.proposed_action == "process"

    @pytest.mark.asyncio
    async def test_classify_email(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Recebi um email novo")
        assert result.intent == "email_received"

    @pytest.mark.asyncio
    async def test_classify_call(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Preciso de fazer uma chamada")
        assert result.intent == "call_request"

    @pytest.mark.asyncio
    async def test_classify_ticket(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Há um problema com o ticket")
        assert result.intent == "ticket_create"

    @pytest.mark.asyncio
    async def test_classify_task(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Tenho uma tarefa para fazer")
        assert result.intent == "task_create"

    @pytest.mark.asyncio
    async def test_classify_contact(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("Procuro um cliente")
        assert result.intent == "contact_lookup"

    @pytest.mark.asyncio
    async def test_classify_unknown(self) -> None:
        provider = RuleBasedAI()
        result = await provider.classify("xyz qwerty 12345")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        provider = RuleBasedAI()
        response = await provider.generate("test prompt", {})
        assert "Rule-based response" in response
        assert "test prompt" in response

    @pytest.mark.asyncio
    async def test_generate_truncates_long_prompt(self) -> None:
        provider = RuleBasedAI()
        long_prompt = "a" * 200
        response = await provider.generate(long_prompt, {})
        assert len(response) <= 120  # "Rule-based response: " + 100 chars


# ---------------------------------------------------------------------------
# MicroAIProvider
# ---------------------------------------------------------------------------


class TestMicroAIProvider:
    @pytest.mark.asyncio
    async def test_classify_offer(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("oferta proposta valor preço")
        assert result.intent == "offer"
        assert result.confidence > 0.0
        assert result.proposed_action == "process"

    @pytest.mark.asyncio
    async def test_classify_email(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("email correio mensagem resposta")
        assert result.intent == "email"

    @pytest.mark.asyncio
    async def test_classify_call(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("chamada ligar telefone call")
        assert result.intent == "call"

    @pytest.mark.asyncio
    async def test_classify_ticket(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("ticket problema issue suporte ajuda")
        assert result.intent == "ticket"

    @pytest.mark.asyncio
    async def test_classify_task(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("tarefa task trabalho job fazer")
        assert result.intent == "task"

    @pytest.mark.asyncio
    async def test_classify_contact(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("cliente customer contact pessoa empresa")
        assert result.intent == "contact"

    @pytest.mark.asyncio
    async def test_classify_unknown(self) -> None:
        provider = MicroAIProvider()
        result = await provider.classify("xyz qwerty 12345")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_confidence_capped_at_1(self) -> None:
        provider = MicroAIProvider()
        # All keywords for "offer" should give confidence = 1.0
        result = await provider.classify("oferta proposta valor preço amount € euros")
        assert result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        provider = MicroAIProvider()
        response = await provider.generate("test prompt", {})
        assert "MicroAI response" in response
        assert "test prompt" in response


# ---------------------------------------------------------------------------
# LocalLLMProvider
# ---------------------------------------------------------------------------


class TestLocalLLMProvider:
    def test_init_defaults(self) -> None:
        provider = LocalLLMProvider()
        assert provider.host == "http://localhost:11434"
        assert provider.model == "qwen2.5:0.5b"

    def test_init_custom(self) -> None:
        provider = LocalLLMProvider(
            host="http://192.168.1.100:11434",
            model="llama3.2:1b",
        )
        assert provider.host == "http://192.168.1.100:11434"
        assert provider.model == "llama3.2:1b"

    @pytest.mark.asyncio
    async def test_classify(self) -> None:
        provider = LocalLLMProvider()
        result = await provider.classify("test")
        assert result.intent == "llm_classified"
        assert result.confidence == 0.8
        assert result.proposed_action == "process"

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        provider = LocalLLMProvider()
        response = await provider.generate("test prompt", {})
        assert "LLM response" in response
        assert "test prompt" in response


# ---------------------------------------------------------------------------
# RemoteAPIProvider
# ---------------------------------------------------------------------------


class TestRemoteAPIProvider:
    def test_init(self) -> None:
        provider = RemoteAPIProvider(
            api_url="https://api.example.com/v1",
            api_key="sk-test123",
        )
        assert provider.api_url == "https://api.example.com/v1"
        assert provider.api_key == "sk-test123"

    @pytest.mark.asyncio
    async def test_classify(self) -> None:
        provider = RemoteAPIProvider(
            api_url="https://api.example.com/v1",
            api_key="sk-test123",
        )
        result = await provider.classify("test")
        assert result.intent == "remote_classified"
        assert result.confidence == 0.9
        assert result.proposed_action == "process"

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        provider = RemoteAPIProvider(
            api_url="https://api.example.com/v1",
            api_key="sk-test123",
        )
        response = await provider.generate("test prompt", {})
        assert "Remote AI response" in response
        assert "test prompt" in response


# ---------------------------------------------------------------------------
# GatewayProvider
# ---------------------------------------------------------------------------


class TestGatewayProvider:
    def test_init(self) -> None:
        provider = GatewayProvider(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        assert provider.gateway_url == "https://gateway.example.com"
        assert provider.token == "gw-token-123"

    @pytest.mark.asyncio
    async def test_classify(self) -> None:
        provider = GatewayProvider(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        result = await provider.classify("test")
        assert result.intent == "gateway_classified"
        assert result.confidence == 0.85
        assert result.proposed_action == "process"

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        provider = GatewayProvider(
            gateway_url="https://gateway.example.com",
            token="gw-token-123",
        )
        response = await provider.generate("test prompt", {})
        assert "Gateway AI response" in response
        assert "test prompt" in response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def no_ai() -> NoAIProvider:
    return NoAIProvider()


@pytest.fixture()
def rule_based() -> RuleBasedAI:
    return RuleBasedAI()


@pytest.fixture()
def micro_ai() -> MicroAIProvider:
    return MicroAIProvider()
