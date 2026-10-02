"""MicroMind benchmarks — startup time, idle RAM, peak RAM."""
from __future__ import annotations

import gc
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any


def _get_ram_mb() -> float:
    """Get current process RSS in MB (cross-platform)."""
    try:
        if platform.system() == "Linux":
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        elif platform.system() == "Darwin":
            import subprocess
            result = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(os.getpid())],
                capture_output=True,
                text=True,
            )
            return int(result.stdout.strip()) / 1024
        else:
            # Fallback: resource module
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        return 0.0


def _get_peak_ram_mb() -> float:
    """Get peak process RSS in MB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmHWM:"):
                        return int(line.split()[1]) / 1024
        elif platform.system() == "Darwin":
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        else:
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        return 0.0


def benchmark_startup() -> dict[str, Any]:
    """Benchmark MicroMind startup time."""
    # Force garbage collection before measurement
    gc.collect()

    start_time = time.perf_counter()
    start_ram = _get_ram_mb()

    # Import and initialize core runtime
    from micromind.core.runtime import CoreRuntime

    config_dir = os.environ.get("MICROMIND_CONFIG_DIR", "./config")
    data_dir = os.environ.get("MICROMIND_DATA_DIR", "./data")
    runtime = CoreRuntime(config_dir=config_dir, data_dir=data_dir)

    end_time = time.perf_counter()
    end_ram = _get_ram_mb()
    peak_ram = _get_peak_ram_mb()

    startup_ms = (end_time - start_time) * 1000
    idle_ram = end_ram - start_ram

    return {
        "startup_ms": round(startup_ms, 2),
        "idle_ram_mb": round(idle_ram, 2),
        "peak_ram_mb": round(peak_ram, 2),
        "profile": runtime.profile.value,
        "os": runtime.system_info.os,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }


def benchmark_storage() -> dict[str, Any]:
    """Benchmark storage backend performance."""
    import tempfile

    results: dict[str, Any] = {}

    # FlatFile benchmark
    with tempfile.TemporaryDirectory() as tmpdir:
        from micromind.storage.backends import FlatFileBackend

        gc.collect()
        start = time.perf_counter()
        backend = FlatFileBackend(data_dir=tmpdir)
        for i in range(100):
            backend.set(f"key_{i}", {"name": f"User {i}", "data": "x" * 100})
        write_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        for i in range(100):
            backend.get(f"key_{i}")
        read_time = (time.perf_counter() - start) * 1000

        results["flatfile"] = {
            "write_100_ms": round(write_time, 2),
            "read_100_ms": round(read_time, 2),
        }

    # SQLite benchmark
    with tempfile.TemporaryDirectory() as tmpdir:
        from micromind.storage.backends import SQLiteBackend

        gc.collect()
        start = time.perf_counter()
        backend = SQLiteBackend(db_path=os.path.join(tmpdir, "test.db"))
        for i in range(100):
            backend.set(f"key_{i}", {"name": f"User {i}", "data": "x" * 100})
        write_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        for i in range(100):
            backend.get(f"key_{i}")
        read_time = (time.perf_counter() - start) * 1000

        results["sqlite"] = {
            "write_100_ms": round(write_time, 2),
            "read_100_ms": round(read_time, 2),
        }

    return results


def benchmark_automation() -> dict[str, Any]:
    """Benchmark automation engine performance."""
    import asyncio
    from micromind.automation.engine import AutomationEngine, AutomationRule

    async def _run() -> dict[str, Any]:
        engine = AutomationEngine()
        for i in range(50):
            engine.add_rule(AutomationRule(
                name=f"Rule {i}",
                when="email.received",
                then_action="create_ticket",
            ))

        gc.collect()
        start = time.perf_counter()
        for _ in range(100):
            await engine.trigger("email.received", {"subject": "test"})
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "trigger_100_ms": round(elapsed, 2),
            "rules_count": 50,
            "executions_logged": len(engine.get_execution_log()),
        }

    return asyncio.run(_run())


def run_all() -> dict[str, Any]:
    """Run all benchmarks and return combined results."""
    print("Running MicroMind benchmarks...")
    print()

    print("1. Startup benchmark...")
    startup = benchmark_startup()
    print(f"   Startup: {startup['startup_ms']} ms")
    print(f"   Idle RAM: {startup['idle_ram_mb']} MB")
    print(f"   Peak RAM: {startup['peak_ram_mb']} MB")
    print(f"   Profile: {startup['profile']}")
    print()

    print("2. Storage benchmark...")
    storage = benchmark_storage()
    for backend, metrics in storage.items():
        print(f"   {backend}:")
        for metric, value in metrics.items():
            print(f"      {metric}: {value} ms")
    print()

    print("3. Automation benchmark...")
    automation = benchmark_automation()
    print(f"   Trigger 100x: {automation['trigger_100_ms']} ms")
    print(f"   Rules: {automation['rules_count']}")
    print(f"   Executions logged: {automation['executions_logged']}")
    print()

    return {
        "startup": startup,
        "storage": storage,
        "automation": automation,
    }


if __name__ == "__main__":
    results = run_all()
    print("Benchmark complete.")
