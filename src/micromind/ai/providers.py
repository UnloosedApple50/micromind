"""AI providers — NoAI, RuleBased, MicroAI, LocalLLM, RemoteAPI, Gateway.

PROVIDERS REAIS vs SIMULADOS
============================
- NoAIProvider       → sem IA, responde o mínimo
- RuleBasedAI        → regex, não precisa de rede
- MicroAIProvider    → contagem de palavras-chave, não precisa de rede
- LocalLLMProvider   → **fala de verdade** com o Ollama (HTTP local)
- RemoteAPIProvider  → **fala de verdade** com API OpenAI-compatível
- GatewayProvider    → **fala de verdade** com o MicroMind Gateway

Os três últimos fazem chamadas HTTP reais. Se o serviço estiver fora do ar,
levantam ProviderError com a mensagem do erro — nunca devolvem texto falso.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import httpx
    _HTTPX_OK = True
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore
    _HTTPX_OK = False


class ProviderError(RuntimeError):
    """Erro ao falar com um provider de IA externo."""


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

    name: str = "unknown"
    needs_network: bool = False

    @abstractmethod
    async def classify(self, text: str) -> AIResult:
        """Classify text and extract intent."""

    @abstractmethod
    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        """Generate response."""

    async def is_available(self) -> bool:
        """Se o provider está pronto para uso. Providers locais: sempre True."""
        return True

    def describe(self) -> dict[str, Any]:
        """Metadados para a API web."""
        return {
            "name": self.name,
            "needs_network": self.needs_network,
            "class": type(self).__name__,
        }


# ─────────────────────────────────────────────────────────────
# PROVIDERS QUE NÃO USAM REDE
# ─────────────────────────────────────────────────────────────

class NoAIProvider(AIProvider):
    """No AI — rules only."""

    name = "noai"

    async def classify(self, text: str) -> AIResult:
        return AIResult(intent="unknown", confidence=0.0, proposed_action="none")

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "AI is disabled. Using rule-based processing."


class RuleBasedAI(AIProvider):
    """Rule-based classification using keyword matching."""

    name = "rulebased"

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
    """Classificador leve por palavras-chave (sem rede, sem modelo).

    Nota: NÃO usa TF-IDF nem Naive Bayes — é contagem ponderada de palavras.
    Para subir de nível sem depender de rede, é o mais barato que existe.
    """

    name = "microai"

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


# ─────────────────────────────────────────────────────────────
# PROVIDERS REAIS (HTTP)
# ─────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """Classifique o texto abaixo em UMA destas intenções:
offer, email, call, ticket, task, contact, unknown

Responda APENAS com JSON neste formato, sem explicação:
{{"intent": "...", "confidence": 0.0}}

Texto: {text}"""


def _parse_json_response(raw: str) -> Optional[dict]:
    """Extrai o primeiro objeto JSON de uma resposta de LLM."""
    if not raw:
        return None
    # tenta direto
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # tenta achar {...} no meio
    m = re.search(r"\{.*?\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


class _HTTPProvider(AIProvider):
    """Base para providers que falam HTTP. Centraliza o tratamento de erro."""

    needs_network = True

    def __init__(self, timeout: float = 120.0) -> None:
        self.timeout = timeout

    def _require_httpx(self) -> None:
        if not _HTTPX_OK:
            raise ProviderError(
                "httpx não está instalado. Rode: pip install httpx"
            )

    async def _post_json(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        """POST que devolve JSON, com erro claro em caso de falha."""
        self._require_httpx()
        assert httpx is not None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers or {})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"{self.name}: HTTP {e.response.status_code} em {url} — "
                f"{e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise ProviderError(
                f"{self.name}: não consegui falar com {url} — {type(e).__name__}: {e}"
            ) from e

    async def _get_json(self, url: str, headers: dict | None = None) -> dict:
        self._require_httpx()
        assert httpx is not None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers or {})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"{self.name}: HTTP {e.response.status_code} em {url}"
            ) from e
        except httpx.RequestError as e:
            raise ProviderError(
                f"{self.name}: não consegui falar com {url} — {type(e).__name__}: {e}"
            ) from e


class LocalLLMProvider(_HTTPProvider):
    """LLM local via Ollama — chamadas HTTP reais.

    Endpoint usado: POST {host}/api/generate
    Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    name = "localllm"
    needs_network = False  # é local, mas usa HTTP

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout: float = 600.0,
        keep_alive: str = "2h",
    ) -> None:
        super().__init__(timeout=timeout)
        self.host = host.rstrip("/")
        self.model = model
        self.keep_alive = keep_alive

    def describe(self) -> dict[str, Any]:
        d = super().describe()
        d.update({"host": self.host, "model": self.model})
        return d

    async def is_available(self) -> bool:
        """Verifica se o Ollama responde e se o modelo existe."""
        try:
            data = await self._get_json(f"{self.host}/api/tags")
        except ProviderError:
            return False
        nomes = {m.get("name", "") for m in data.get("models", [])}
        return any(n == self.model or n.startswith(self.model + ":") for n in nomes)

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        """Gera texto com o modelo local. Chamada real ao Ollama."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": 0.3, "num_predict": 300},
        }
        # contexto opcional vira parte do prompt
        if context:
            extra = "\n".join(f"{k}: {v}" for k, v in context.items())
            payload["prompt"] = f"{prompt}\n\nContexto:\n{extra}"

        data = await self._post_json(f"{self.host}/api/generate", payload)
        return data.get("response", "")

    async def classify(self, text: str) -> AIResult:
        """Classifica usando o modelo local, pedindo JSON de volta."""
        prompt = CLASSIFY_PROMPT.format(text=text[:1500])
        raw = await self.generate(prompt, {})
        parsed = _parse_json_response(raw)

        if not parsed or "intent" not in parsed:
            return AIResult(
                intent="unknown",
                confidence=0.0,
                proposed_action="none",
                response=raw,
            )

        try:
            conf = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0

        return AIResult(
            intent=str(parsed["intent"]),
            confidence=max(0.0, min(1.0, conf)),
            proposed_action="process",
            validation="pending",
            response=raw,
        )


class RemoteAPIProvider(_HTTPProvider):
    """API de IA remota (OpenAI-compatível) — chamadas HTTP reais.

    Funciona com OpenAI, Groq, DeepSeek, OpenRouter, Together, etc.
    Basta apontar `api_url` para o /v1/chat/completions do serviço.
    """

    name = "remoteapi"

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def describe(self) -> dict[str, Any]:
        d = super().describe()
        d.update({"api_url": self.api_url, "model": self.model})
        return d

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        """Chama a API remota de verdade."""
        messages = [{"role": "user", "content": prompt}]
        if context:
            extra = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.insert(0, {"role": "system", "content": f"Contexto:\n{extra}"})

        data = await self._post_json(
            self.api_url,
            {"model": self.model, "messages": messages, "temperature": 0.3},
            headers=self._headers(),
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(
                f"{self.name}: resposta inesperada da API — {str(data)[:200]}"
            ) from e

    async def classify(self, text: str) -> AIResult:
        prompt = CLASSIFY_PROMPT.format(text=text[:1500])
        raw = await self.generate(prompt, {})
        parsed = _parse_json_response(raw)
        if not parsed or "intent" not in parsed:
            return AIResult(intent="unknown", confidence=0.0, response=raw)
        try:
            conf = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        return AIResult(
            intent=str(parsed["intent"]),
            confidence=max(0.0, min(1.0, conf)),
            proposed_action="process",
            response=raw,
        )


class GatewayProvider(_HTTPProvider):
    """IA via MicroMind Gateway — chamadas HTTP reais.

    O Gateway é um serviço separado que expõe operações modernas
    (LLM, telefonia) para clientes em hardware fraco.
    """

    name = "gateway"

    def __init__(
        self,
        gateway_url: str,
        token: str = "",
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.gateway_url = gateway_url.rstrip("/")
        self.token = token

    def describe(self) -> dict[str, Any]:
        d = super().describe()
        d.update({"gateway_url": self.gateway_url})
        return d

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def is_available(self) -> bool:
        try:
            await self._get_json(f"{self.gateway_url}/health", headers=self._headers())
            return True
        except ProviderError:
            return False

    async def generate(self, prompt: str, context: dict[str, Any]) -> str:
        data = await self._post_json(
            f"{self.gateway_url}/ai/generate",
            {"prompt": prompt, "context": context or {}},
            headers=self._headers(),
        )
        return data.get("response", "")

    async def classify(self, text: str) -> AIResult:
        data = await self._post_json(
            f"{self.gateway_url}/ai/classify",
            {"text": text},
            headers=self._headers(),
        )
        return AIResult(
            intent=data.get("intent", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            proposed_action=data.get("proposed_action", "process"),
        )


# ─────────────────────────────────────────────────────────────
# FÁBRICA
# ─────────────────────────────────────────────────────────────

PROVIDERS: dict[str, type[AIProvider]] = {
    "noai": NoAIProvider,
    "rulebased": RuleBasedAI,
    "microai": MicroAIProvider,
    "localllm": LocalLLMProvider,
    "remoteapi": RemoteAPIProvider,
    "gateway": GatewayProvider,
}


def build_provider(cfg: dict[str, Any]) -> AIProvider:
    """Cria um provider a partir de um dicionário de configuração.

    Exemplos:
        {"provider": "localllm", "model": "qwen2.5:7b"}
        {"provider": "remoteapi", "api_url": "...", "api_key": "...", "model": "..."}
        {"provider": "microai"}

    Levanta ProviderError se a config estiver incompleta.
    """
    kind = str(cfg.get("provider", "microai")).lower()
    cls = PROVIDERS.get(kind)
    if cls is None:
        raise ProviderError(
            f"provider desconhecido: {kind!r}. "
            f"Válidos: {', '.join(sorted(PROVIDERS))}"
        )

    if kind == "noai":
        return NoAIProvider()
    if kind == "rulebased":
        return RuleBasedAI()
    if kind == "microai":
        return MicroAIProvider()

    if kind == "localllm":
        return LocalLLMProvider(
            host=cfg.get("host", "http://localhost:11434"),
            model=cfg.get("model", "qwen2.5:7b"),
            timeout=float(cfg.get("timeout", 600.0)),
        )

    if kind == "remoteapi":
        url = cfg.get("api_url")
        key = cfg.get("api_key")
        if not url or not key:
            raise ProviderError("remoteapi precisa de 'api_url' e 'api_key'")
        return RemoteAPIProvider(
            api_url=url, api_key=key,
            model=cfg.get("model", "gpt-4o-mini"),
            timeout=float(cfg.get("timeout", 120.0)),
        )

    if kind == "gateway":
        url = cfg.get("gateway_url")
        if not url:
            raise ProviderError("gateway precisa de 'gateway_url'")
        return GatewayProvider(
            gateway_url=url,
            token=cfg.get("token", ""),
            timeout=float(cfg.get("timeout", 120.0)),
        )

    raise ProviderError(f"provider não implementado: {kind!r}")
