"""MicroMind API — apenas JSON, sem HTML.

Este arquivo expõe o backend do MicroMind como API REST pura.
Não serve páginas, não tem templates, não tem CSS.

O frontend é SEU — crie onde quiser (pasta web/ ao lado) e
consuma estes endpoints via fetch() ou qualquer cliente HTTP.

Rodar:
    PYTHONPATH=src python3 -m uvicorn micromind.web.api:app --port 8081

Docs interativas automáticas:
    http://localhost:8081/docs
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from micromind.core.runtime import CoreRuntime
from micromind.storage.backends import FlatFileBackend
from micromind.security.engine import SecurityEngine
from micromind.ai.providers import (
    AIProvider, MicroAIProvider, ProviderError, build_provider,
)
from micromind.automation.engine import AutomationEngine
from micromind.telephony.calls import CallManager, DisabledTelephony

# ─────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="MicroMind API",
    description="Backend do MicroMind — só JSON. O frontend é seu.",
    version="1.1.0",
)

# CORS liberado: o frontend pode estar em qualquer origem (file://, outra porta)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# ESTADO GLOBAL
# ─────────────────────────────────────────────────────────────

runtime: Optional[CoreRuntime] = None
storage: Optional[FlatFileBackend] = None
security: Optional[SecurityEngine] = None
ai: AIProvider = MicroAIProvider()
automation: Optional[AutomationEngine] = None
telephony: Optional[CallManager] = None

# guarda a config do provider ativo para poder reconstruir
_ai_config: dict[str, Any] = {"provider": "microai"}


@app.on_event("startup")
async def startup() -> None:
    """Inicializa os componentes."""
    global runtime, storage, security, automation, telephony
    runtime = CoreRuntime()
    storage = FlatFileBackend()
    security = SecurityEngine(safe_mode=True)
    automation = AutomationEngine()
    telephony = CallManager(DisabledTelephony())


# ─────────────────────────────────────────────────────────────
# MODELOS DE ENTRADA
# ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    context: dict[str, Any] = Field(default_factory=dict)


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)


class ProviderRequest(BaseModel):
    """Troca o provider ativo.

    Exemplos:
        {"provider": "localllm", "model": "qwen2.5:7b"}
        {"provider": "remoteapi", "api_url": "...", "api_key": "...", "model": "..."}
    """
    provider: str
    model: Optional[str] = None
    host: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    gateway_url: Optional[str] = None
    token: Optional[str] = None
    timeout: Optional[float] = None


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = ""
    phone: str = ""
    company: str = ""


class TaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    priority: str = "medium"


class TicketRequest(BaseModel):
    title: str = Field(..., min_length=1)
    customer: str = ""
    priority: str = "medium"


# ─────────────────────────────────────────────────────────────
# ESTADO DO SISTEMA
# ─────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["sistema"])
async def health() -> dict[str, Any]:
    """Saúde geral do sistema."""
    return {
        "status": "ok",
        "core": "OK",
        "storage": "OK",
        "automation": "OK",
        "ai": type(ai).__name__,
        "ai_provider": ai.name,
        "telephony": "Disabled",
        "gateway": "Not configured",
        "security": "Safe Mode",
        "profile": runtime.profile.value if runtime else "Unknown",
    }


@app.get("/api/status", tags=["sistema"])
async def status() -> dict[str, Any]:
    """Status de cada componente."""
    if not runtime:
        raise HTTPException(503, "Runtime não inicializado")
    return runtime.status()


@app.get("/api/doctor", tags=["sistema"])
async def doctor() -> dict[str, Any]:
    """Diagnóstico completo."""
    if not runtime:
        raise HTTPException(503, "Runtime não inicializado")
    return runtime.doctor()


# ─────────────────────────────────────────────────────────────
# IA
# ─────────────────────────────────────────────────────────────

@app.get("/api/ai/providers", tags=["ia"])
async def list_providers() -> dict[str, Any]:
    """Lista os providers disponíveis e qual está ativo."""
    return {
        "active": ai.name,
        "config": _ai_config,
        "available": [
            {"name": "noai", "needs_network": False, "desc": "Sem IA"},
            {"name": "rulebased", "needs_network": False, "desc": "Regex"},
            {"name": "microai", "needs_network": False, "desc": "Palavras-chave"},
            {"name": "localllm", "needs_network": False, "desc": "Ollama local"},
            {"name": "remoteapi", "needs_network": True, "desc": "API OpenAI-compatível"},
            {"name": "gateway", "needs_network": True, "desc": "MicroMind Gateway"},
        ],
    }


@app.post("/api/ai/provider", tags=["ia"])
async def set_provider(req: ProviderRequest) -> dict[str, Any]:
    """Troca o provider ativo. Valida antes de aceitar."""
    global ai, _ai_config

    cfg = req.model_dump(exclude_none=True)
    try:
        novo = build_provider(cfg)
    except ProviderError as e:
        raise HTTPException(400, str(e))

    ai = novo
    _ai_config = cfg
    return {"status": "ok", "active": ai.name, "describe": ai.describe()}


@app.get("/api/ai/available", tags=["ia"])
async def ai_available() -> dict[str, Any]:
    """Verifica se o provider ativo está pronto para uso."""
    try:
        ok = await ai.is_available()
    except Exception as e:
        return {"available": False, "provider": ai.name, "error": str(e)}
    return {"available": ok, "provider": ai.name, "describe": ai.describe()}


@app.post("/api/ai/generate", tags=["ia"])
async def ai_generate(req: GenerateRequest) -> dict[str, Any]:
    """Gera texto com o provider ativo. Chamada REAL."""
    t0 = time.time()
    try:
        out = await ai.generate(req.prompt, req.context)
    except ProviderError as e:
        raise HTTPException(502, str(e))
    return {
        "provider": ai.name,
        "model": getattr(ai, "model", None),
        "response": out,
        "elapsed_seconds": round(time.time() - t0, 2),
    }


@app.post("/api/ai/classify", tags=["ia"])
async def ai_classify(req: ClassifyRequest) -> dict[str, Any]:
    """Classifica a intenção de um texto."""
    t0 = time.time()
    try:
        r = await ai.classify(req.text)
    except ProviderError as e:
        raise HTTPException(502, str(e))
    return {
        "intent": r.intent,
        "confidence": r.confidence,
        "proposed_action": r.proposed_action,
        "provider": ai.name,
        "elapsed_seconds": round(time.time() - t0, 2),
    }


# ─────────────────────────────────────────────────────────────
# DADOS
# ─────────────────────────────────────────────────────────────

@app.get("/api/contacts", tags=["dados"])
async def list_contacts() -> dict[str, Any]:
    if not storage:
        return {"contacts": []}
    return {"contacts": [k for k in storage.list_keys() if k.startswith("contact_")]}


@app.post("/api/contact", tags=["dados"])
async def create_contact(req: ContactRequest) -> dict[str, Any]:
    if not storage or not security:
        raise HTTPException(503, "Storage não inicializado")
    if req.email and not security.validate_email(req.email):
        raise HTTPException(400, "Email inválido")
    if req.phone and not security.validate_phone(req.phone):
        raise HTTPException(400, "Telefone inválido")

    cid = f"contact_{req.name.lower().replace(' ', '_')}"
    storage.set(cid, req.model_dump())
    return {"status": "ok", "contact_id": cid}


@app.get("/api/tasks", tags=["dados"])
async def list_tasks() -> dict[str, Any]:
    if not storage:
        return {"tasks": []}
    return {"tasks": [k for k in storage.list_keys() if k.startswith("task_")]}


@app.post("/api/task", tags=["dados"])
async def create_task(req: TaskRequest) -> dict[str, Any]:
    if not storage:
        raise HTTPException(503, "Storage não inicializado")
    tid = f"task_{req.title.lower().replace(' ', '_')}"
    d = req.model_dump()
    d["status"] = "pending"
    storage.set(tid, d)
    return {"status": "ok", "task_id": tid}


@app.get("/api/tickets", tags=["dados"])
async def list_tickets() -> dict[str, Any]:
    if not storage:
        return {"tickets": []}
    return {"tickets": [k for k in storage.list_keys() if k.startswith("ticket_")]}


@app.post("/api/ticket", tags=["dados"])
async def create_ticket(req: TicketRequest) -> dict[str, Any]:
    if not storage:
        raise HTTPException(503, "Storage não inicializado")
    tid = f"ticket_{req.title.lower().replace(' ', '_')}"
    d = req.model_dump()
    d["status"] = "new"
    storage.set(tid, d)
    return {"status": "ok", "ticket_id": tid}


@app.get("/api/automations", tags=["dados"])
async def list_automations() -> dict[str, Any]:
    if not automation:
        return {"automations": []}
    return {"automations": [
        {"id": r.id, "name": r.name, "enabled": r.enabled}
        for r in automation.list_rules()
    ]}


# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────

@app.get("/api/config", tags=["config"])
async def get_config() -> dict[str, Any]:
    """Configuração atual."""
    return {
        "ai": _ai_config,
        "profile": runtime.profile.value if runtime else None,
        "storage_backend": type(storage).__name__ if storage else None,
    }


@app.put("/api/config", tags=["config"])
async def put_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Grava configuração. Só aceita a chave 'ai' por enquanto."""
    global ai, _ai_config
    if "ai" in cfg:
        try:
            ai = build_provider(cfg["ai"])
            _ai_config = cfg["ai"]
        except ProviderError as e:
            raise HTTPException(400, str(e))
    return {"status": "ok", "config": await get_config()}


# ─────────────────────────────────────────────────────────────
# FRONTEND — serve a SUA pasta web/
# ─────────────────────────────────────────────────────────────

# Descobre a pasta web/ (irmã de backend/). Pode ser sobrescrita
# com a variável de ambiente MICROMIND_WEB.
_DEFAULT_WEB = Path(__file__).resolve().parents[4] / "web"
WEB_DIR = Path(os.environ.get("MICROMIND_WEB", _DEFAULT_WEB))


@app.get("/api/web/info", tags=["config"])
async def web_info() -> dict[str, Any]:
    """Onde está a pasta web/ e o que tem nela.

    Declarada ANTES do mount("/") — senão o mount engole esta rota.
    """
    if not WEB_DIR.is_dir():
        return {"exists": False, "path": str(WEB_DIR), "files": []}
    arquivos = sorted(
        str(p.relative_to(WEB_DIR))
        for p in WEB_DIR.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )
    return {
        "exists": True,
        "path": str(WEB_DIR),
        "has_index": (WEB_DIR / "index.html").is_file(),
        "files": arquivos,
        "url": "/",
    }


def _montar_frontend() -> None:
    """Monta a pasta web/ na raiz. Montado por ÚLTIMO para não
    engolir as rotas /api/* nem /docs."""
    if not WEB_DIR.is_dir():
        @app.get("/", include_in_schema=False)
        async def _sem_web() -> dict[str, Any]:
            return {
                "erro": "pasta web/ não encontrada",
                "procurei_em": str(WEB_DIR),
                "crie": "coloque um index.html nessa pasta",
                "api": "/docs",
            }
        return

    # Se existir index.html, a raiz serve ele
    index = WEB_DIR / "index.html"
    if index.is_file():
        from fastapi.responses import FileResponse

        @app.get("/", include_in_schema=False)
        async def _index() -> Any:
            return FileResponse(index)

    # Todo o resto (css, js, imagens) servido da pasta
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


_montar_frontend()
