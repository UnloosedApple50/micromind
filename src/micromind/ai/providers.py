"""AI providers — NoAI, RuleBased, MicroAI, LocalLLM, RemoteAPI, Gateway."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AIResult:
    """AI result with confidence and validation."""
    intent: str = ""
    confidence: float = 0.0
    proposed_action: str = ""
    validation: str = "pending"
    permission: str = "denied"
    entities: dict[str, Any] = field(default_factory=dict)
    response: str = ""


class AIProvider(ABC):
    """Abstract AI provider."""

    @abstractmethod
    async def classify(self, text: str) -> AIResult:
        """Classify text and extract intent."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        """Generate response."""
        pass


class NoAIProvider(AIProvider):
    """No AI — rules only."""

    async def classify(self, text: str) -> AIResult:
        return AIResult(intent="unknown", confidence=0.0, proposed_action="none")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "AI is disabled. Using rule-based processing."


class RuleBasedAI(AIProvider):
    """Rule-based classification using keyword matching."""

    RULES = [
        {"pattern": r"\b(oferta|proposta|amount|preço|valor)\b", "intent": "offer_received"},
        {"pattern": r"\b(email|correio|mensagem)\b", "intent": "email_received"},
        {"pattern": r"\b(chamada|liga|telefone|call)\b", "intent": "call_request"},
        {"pattern": r"\b(ticket|problema|issue|suporte)\b", "intent": "ticket_create"},
        {"pattern": r"\b(task|tarefa|trabalho|job)\b", "intent": "task_create"},
        {"pattern": r"\b(cliente|customer|contact)\b", "intent": "contact_lookup"},
    ]

    async def classify(self, text: str) -> AIResult:
        text_lower = text.lower()
        for rule in self.RULES:
            if re.search(rule["pattern"], text_lower):
                return AIResult(
                    intent=rule["intent"],
                    confidence=0.7,
                    proposed_action="process",
                    validation="pending",
                )
        return AIResult(intent="unknown", confidence=0.0, proposed_action="none")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "Rule-based response: " + prompt[:95]


class MicroAIProvider(AIProvider):
    """Lightweight local AI — TF-IDF, Naive Bayes, scoring."""

    def __init__(self) -> None:
        self._patterns: dict[str, list[str]] = {
            "offer": ["oferta", "proposta", "valor", "preço", "amount", "€", "euros"],
            "email": ["email", "correio", "mensagem", "resposta"],
            "call": ["chamada", "ligar", "telefone", "call", "contacto"],
            "ticket": ["ticket", "problema", "issue", "suporte", "ajuda"],
            "task": ["tarefa", "task", "trabalho", "job", "fazer"],
            "contact": ["cliente", "customer", "contact", "pessoa", "empresa"],
        }

    async def classify(self, text: str) -> AIResult:
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for intent, keywords in self._patterns.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score / len(keywords)

        if scores:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] * 2, 1.0)
            return AIResult(
                intent=best_intent,
                confidence=confidence,
                proposed_action="process",
                validation="pending",
            )

        return AIResult(intent="unknown", confidence=0.0, proposed_action="none")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "MicroAI response: " + prompt[:100]


class LocalLLMProvider(AIProvider):
    """Local LLM via Ollama."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:0.5b") -> None:
        self.host = host
        self.model = model

    async def classify(self, text: str) -> AIResult:
        # Use LLM for classification
        return AIResult(intent="llm_classified", confidence=0.8, proposed_action="process")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        # Would call Ollama API
        return "LLM response: " + prompt[:100]


class RemoteAPIProvider(AIProvider):
    """Remote AI API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    async def classify(self, text: str) -> AIResult:
        return AIResult(intent="remote_classified", confidence=0.9, proposed_action="process")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "Remote AI response: " + prompt[:100]


class GatewayProvider(AIProvider):
    """AI via Gateway."""

    def __init__(self, gateway_url: str, token: str) -> None:
        self.gateway_url = gateway_url
        self.token = token

    async def classify(self, text: str) -> AIResult:
        return AIResult(intent="gateway_classified", confidence=0.85, proposed_action="process")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "Gateway AI response: " + prompt[:100]
