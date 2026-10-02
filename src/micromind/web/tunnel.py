"""Tunnel API — start/stop Cloudflare Tunnel from web interface."""

from __future__ import annotations

import subprocess
import signal
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Global tunnel process
_tunnel_process: Optional[subprocess.Popen] = None
_tunnel_url: str = ""


class TunnelStart(BaseModel):
    """Tunnel start request."""
    port: int = 8081


@router.post("/api/tunnel/start")
async def start_tunnel(request: TunnelStart):
    """Start Cloudflare Tunnel."""
    global _tunnel_process, _tunnel_url

    if _tunnel_process and _tunnel_process.poll() is None:
        return {"status": "already_running", "url": _tunnel_url}

    try:
        # Start cloudflared tunnel
        log_file = open("./logs/tunnel.log", "w")
        _tunnel_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{request.port}"],
            stdout=log_file,
            stderr=log_file,
            preexec_fn=os.setsid if os.name != 'nt' else None,
        )

        # Wait a few seconds for the URL to appear
        import time
        time.sleep(5)

        # Read the log to get the URL
        log_path = Path("./logs/tunnel.log")
        if log_path.exists():
            content = log_path.read_text()
            # Extract URL from log
            for line in content.split("\n"):
                if "trycloudflare.com" in line:
                    # Extract URL
                    parts = line.split()
                    for part in parts:
                        if "trycloudflare.com" in part:
                            _tunnel_url = part.strip()
                            break
                    break

        return {
            "status": "started",
            "url": _tunnel_url,
            "pid": _tunnel_process.pid,
        }
    except Exception as e:
        return {"error": f"Failed to start tunnel: {str(e)}"}


@router.post("/api/tunnel/stop")
async def stop_tunnel():
    """Stop Cloudflare Tunnel."""
    global _tunnel_process, _tunnel_url

    if _tunnel_process and _tunnel_process.poll() is None:
        try:
            if os.name != 'nt':
                os.killpg(os.getpgid(_tunnel_process.pid), signal.SIGTERM)
            else:
                _tunnel_process.terminate()
            _tunnel_process.wait(timeout=5)
        except Exception:
            _tunnel_process.kill()

    _tunnel_process = None
    old_url = _tunnel_url
    _tunnel_url = ""

    return {"status": "stopped", "previous_url": old_url}


@router.get("/api/tunnel/status")
async def tunnel_status():
    """Get tunnel status."""
    global _tunnel_process, _tunnel_url

    is_running = _tunnel_process is not None and _tunnel_process.poll() is None

    return {
        "running": is_running,
        "url": _tunnel_url if is_running else "",
        "pid": _tunnel_process.pid if is_running else None,
    }
