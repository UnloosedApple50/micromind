"""Web interface for MicroMind — simple dashboard for testing."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from micromind.core.runtime import CoreRuntime
from micromind.storage.backends import FlatFileBackend
from micromind.security.engine import SecurityEngine, Permission
from micromind.ai.providers import MicroAIProvider
from micromind.automation.engine import AutomationEngine
from micromind.telephony.calls import CallManager, DisabledTelephony
from micromind.web.settings import router as settings_router
from micromind.web.tunnel import router as tunnel_router

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "src" / "micromind" / "web" / "templates"
STATIC_DIR = BASE_DIR / "src" / "micromind" / "web" / "static"

# Initialize
app = FastAPI(title="MicroMind", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.include_router(settings_router)
app.include_router(tunnel_router)

# Global state
runtime: Optional[CoreRuntime] = None
storage: Optional[FlatFileBackend] = None
security: Optional[SecurityEngine] = None
ai: Optional[MicroAIProvider] = None
automation: Optional[AutomationEngine] = None
telephony: Optional[CallManager] = None


@app.on_event("startup")
async def startup():
    """Initialize all components."""
    global runtime, storage, security, ai, automation, telephony
    runtime = CoreRuntime()
    storage = FlatFileBackend()
    security = SecurityEngine(safe_mode=True)
    ai = MicroAIProvider()
    automation = AutomationEngine()
    telephony = CallManager(DisabledTelephony())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "runtime": runtime,
    })


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "core": "OK",
        "storage": "OK",
        "automation": "OK",
        "ai": "MicroAI",
        "telephony": "Disabled",
        "gateway": "Not configured",
        "security": "Safe Mode",
        "profile": runtime.profile.value if runtime else "Unknown",
    }


@app.get("/api/status")
async def status():
    """Get system status."""
    if not runtime:
        return {"error": "Runtime not initialized"}
    return runtime.status()


@app.get("/api/doctor")
async def doctor():
    """Run diagnostics."""
    if not runtime:
        return {"error": "Runtime not initialized"}
    return runtime.doctor()


@app.post("/api/chat")
async def chat(request: Request):
    """Send a message and get AI classification."""
    data = await request.json()
    message = data.get("message", "")

    if not message:
        return {"error": "Message is required"}

    # Classify with MicroAI
    result = await ai.classify(message)

    return {
        "intent": result.intent,
        "confidence": result.confidence,
        "proposed_action": result.proposed_action,
        "validation": result.validation,
        "permission": result.permission,
    }


@app.get("/api/contacts")
async def list_contacts():
    """List all contacts."""
    if not storage:
        return {"contacts": []}
    keys = storage.list_keys()
    contacts = [k for k in keys if k.startswith("contact_")]
    return {"contacts": contacts}


@app.post("/api/contact")
async def create_contact(request: Request):
    """Create a new contact."""
    data = await request.json()
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    company = data.get("company", "")

    if not name:
        return {"error": "Name is required"}

    # Validate
    if email and not security.validate_email(email):
        return {"error": "Invalid email format"}

    if phone and not security.validate_phone(phone):
        return {"error": "Invalid phone format"}

    contact_id = f"contact_{name.lower().replace(' ', '_')}"
    storage.set(contact_id, {
        "name": name,
        "email": email,
        "phone": phone,
        "company": company,
    })

    return {"status": "ok", "contact_id": contact_id}


@app.get("/api/tasks")
async def list_tasks():
    """List all tasks."""
    if not storage:
        return {"tasks": []}
    keys = storage.list_keys()
    tasks = [k for k in keys if k.startswith("task_")]
    return {"tasks": tasks}


@app.post("/api/task")
async def create_task(request: Request):
    """Create a new task."""
    data = await request.json()
    title = data.get("title", "")
    description = data.get("description", "")
    priority = data.get("priority", "medium")

    if not title:
        return {"error": "Title is required"}

    task_id = f"task_{title.lower().replace(' ', '_')}"
    storage.set(task_id, {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
    })

    return {"status": "ok", "task_id": task_id}


@app.get("/api/tickets")
async def list_tickets():
    """List all tickets."""
    if not storage:
        return {"tickets": []}
    keys = storage.list_keys()
    tickets = [k for k in keys if k.startswith("ticket_")]
    return {"tickets": tickets}


@app.post("/api/ticket")
async def create_ticket(request: Request):
    """Create a new ticket."""
    data = await request.json()
    title = data.get("title", "")
    customer = data.get("customer", "")
    priority = data.get("priority", "medium")

    if not title:
        return {"error": "Title is required"}

    ticket_id = f"ticket_{title.lower().replace(' ', '_')}"
    storage.set(ticket_id, {
        "title": title,
        "customer": customer,
        "priority": priority,
        "status": "new",
    })

    return {"status": "ok", "ticket_id": ticket_id}


@app.get("/api/automations")
async def list_automations():
    """List automation rules."""
    if not automation:
        return {"automations": []}
    rules = automation.list_rules()
    return {"automations": [{"id": r.id, "name": r.name, "enabled": r.enabled} for r in rules]}


@app.get("/api/call/simulate")
async def simulate_call():
    """Simulate a call (no real call)."""
    return {
        "status": "simulated",
        "result": "CALL_QUEUED",
        "message": "Call simulation successful. No real call was made.",
    }


# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
