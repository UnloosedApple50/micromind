"""Storage backends — FlatFile, SQLite, Remote."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    def get(self, key: str) -> Optional[dict[str, Any]]:
        pass

    @abstractmethod
    def set(self, key: str, data: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        pass

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        pass


class FlatFileBackend(StorageBackend):
    """Flat file storage — for ULTRA_LOW profile.

    Stores data in JSON files, one per entity.
    Designed for 2GB total storage with thousands of entities.
    """

    def __init__(self, data_dir: str = "./data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = {}

    def _get_path(self, key: str) -> Path:
        """Get file path for a key."""
        # Sanitize key for filesystem
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_")
        return self.data_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get data by key."""
        if key in self._cache:
            return self._cache[key]

        path = self._get_path(key)
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self._cache[key] = data
                return data
            except Exception:
                return None
        return None

    def set(self, key: str, data: dict[str, Any]) -> bool:
        """Set data by key with atomic write."""
        data["_updated"] = datetime.utcnow().isoformat()
        data["_size_kb"] = len(json.dumps(data)) / 1024

        path = self._get_path(key)
        try:
            # Atomic write using temp file
            with tempfile.NamedTemporaryFile(mode='w', dir=self.data_dir, delete=False) as f:
                json.dump(data, f, indent=2)
                temp_path = f.name

            # Atomic rename
            os.replace(temp_path, path)
            self._cache[key] = data
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete data by key."""
        path = self._get_path(key)
        if path.exists():
            try:
                path.unlink()
                self._cache.pop(key, None)
                return True
            except Exception:
                return False
        return False

    def list_keys(self) -> list[str]:
        """List all keys."""
        keys = []
        for f in self.data_dir.glob("*.json"):
            keys.append(f.stem)
        return keys

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search data."""
        results = []
        query_lower = query.lower()

        for key in self.list_keys():
            data = self.get(key)
            if data:
                for field, value in data.items():
                    if isinstance(value, str) and query_lower in value.lower():
                        results.append({"key": key, "field": field, "value": value})
                        break

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        total_size = 0
        count = 0
        for f in self.data_dir.glob("*.json"):
            total_size += f.stat().st_size
            count += 1

        return {
            "count": count,
            "total_size_kb": total_size / 1024,
            "cache_size": len(self._cache),
        }


class SQLiteBackend(StorageBackend):
    """SQLite storage — for LOW profile and above."""

    def __init__(self, db_path: str = "./data/micromind.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_key ON entities(key)
            """)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get data by key."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM entities WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def set(self, key: str, data: dict[str, Any]) -> bool:
        """Set data by key."""
        data["_updated"] = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO entities (key, data, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(data), datetime.utcnow().isoformat())
            )
            conn.commit()
        return True

    def delete(self, key: str) -> bool:
        """Delete data by key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM entities WHERE key = ?", (key,))
            conn.commit()
        return True

    def list_keys(self) -> list[str]:
        """List all keys."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key FROM entities").fetchall()
            return [row[0] for row in rows]

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search data."""
        results = []
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, data FROM entities WHERE data LIKE ?",
                (f"%{query}%",)
            ).fetchall()
            for key, data_str in rows:
                data = json.loads(data_str)
                results.append({"key": key, "data": data})
        return results


class RemoteBackend(StorageBackend):
    """Remote storage via Gateway."""

    def __init__(self, gateway_url: str, token: str) -> None:
        self.gateway_url = gateway_url
        self.token = token

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get data from remote."""
        # Implementation would use httpx to call Gateway API
        pass

    def set(self, key: str, data: dict[str, Any]) -> bool:
        """Set data to remote."""
        pass

    def delete(self, key: str) -> bool:
        """Delete data from remote."""
        pass

    def list_keys(self) -> list[str]:
        """List keys from remote."""
        pass

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search remote data."""
        pass
