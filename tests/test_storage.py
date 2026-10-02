"""Tests for FlatFileBackend and SQLiteBackend."""
from __future__ import annotations

import json

import pytest

from micromind.storage.backends import FlatFileBackend, SQLiteBackend


# ---------------------------------------------------------------------------
# FlatFileBackend
# ---------------------------------------------------------------------------


class TestFlatFileBackend:
    def test_init_creates_dir(self, tmp_path: Any) -> None:
        data_dir = tmp_path / "data"
        backend = FlatFileBackend(data_dir=str(data_dir))
        assert data_dir.exists()

    def test_set_and_get(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        assert backend.set("key1", {"name": "Alice", "age": 30}) is True
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "Alice"
        assert result["age"] == 30
        assert "_updated" in result
        assert "_size_kb" in result

    def test_get_nonexistent(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        assert backend.get("nonexistent") is None

    def test_set_overwrites(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        backend.set("key1", {"name": "Bob"})
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "Bob"

    def test_delete(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        assert backend.delete("key1") is True
        assert backend.get("key1") is None

    def test_delete_nonexistent(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        assert backend.delete("nonexistent") is False

    def test_list_keys(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        backend.set("key2", {"name": "Bob"})
        keys = backend.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_search(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice", "company": "Acme"})
        backend.set("key2", {"name": "Bob", "company": "Globex"})
        results = backend.search("Alice")
        assert len(results) == 1
        assert results[0]["key"] == "key1"
        assert results[0]["field"] == "name"

    def test_search_no_match(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        results = backend.search("Zebra")
        assert results == []

    def test_get_stats(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        backend.set("key2", {"name": "Bob"})
        stats = backend.get_stats()
        assert stats["count"] == 2
        assert stats["total_size_kb"] > 0
        assert stats["cache_size"] == 2

    def test_cache_hit(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        backend.set("key1", {"name": "Alice"})
        # First get populates cache
        backend.get("key1")
        # Second get should hit cache
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "Alice"

    def test_key_sanitization(self, tmp_path: Any) -> None:
        backend = FlatFileBackend(data_dir=str(tmp_path / "data"))
        # Keys with special chars should be sanitized
        backend.set("key/with/slashes", {"name": "Alice"})
        # The sanitized key should be "keywithslashes"
        result = backend.get("keywithslashes")
        assert result is not None
        assert result["name"] == "Alice"

    def test_persistence_across_instances(self, tmp_path: Any) -> None:
        data_dir = str(tmp_path / "data")
        backend1 = FlatFileBackend(data_dir=data_dir)
        backend1.set("key1", {"name": "Alice"})

        backend2 = FlatFileBackend(data_dir=data_dir)
        result = backend2.get("key1")
        assert result is not None
        assert result["name"] == "Alice"


# ---------------------------------------------------------------------------
# SQLiteBackend
# ---------------------------------------------------------------------------


class TestSQLiteBackend:
    def test_init_creates_db(self, tmp_path: Any) -> None:
        db_path = tmp_path / "data" / "test.db"
        backend = SQLiteBackend(db_path=str(db_path))
        assert db_path.exists()

    def test_set_and_get(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        assert backend.set("key1", {"name": "Alice", "age": 30}) is True
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "Alice"
        assert result["age"] == 30
        assert "_updated" in result

    def test_get_nonexistent(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        assert backend.get("nonexistent") is None

    def test_set_overwrites(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "Alice"})
        backend.set("key1", {"name": "Bob"})
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "Bob"

    def test_delete(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "Alice"})
        assert backend.delete("key1") is True
        assert backend.get("key1") is None

    def test_delete_nonexistent(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        # SQLite DELETE on nonexistent row still succeeds
        assert backend.delete("nonexistent") is True

    def test_list_keys(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "Alice"})
        backend.set("key2", {"name": "Bob"})
        keys = backend.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_search(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "Alice", "company": "Acme"})
        backend.set("key2", {"name": "Bob", "company": "Globex"})
        results = backend.search("Alice")
        assert len(results) == 1
        assert results[0]["key"] == "key1"
        assert results[0]["data"]["name"] == "Alice"

    def test_search_no_match(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "Alice"})
        results = backend.search("Zebra")
        assert results == []

    def test_persistence_across_instances(self, tmp_path: Any) -> None:
        db_path = str(tmp_path / "test.db")
        backend1 = SQLiteBackend(db_path=db_path)
        backend1.set("key1", {"name": "Alice"})

        backend2 = SQLiteBackend(db_path=db_path)
        result = backend2.get("key1")
        assert result is not None
        assert result["name"] == "Alice"

    def test_unicode_data(self, tmp_path: Any) -> None:
        backend = SQLiteBackend(db_path=str(tmp_path / "test.db"))
        backend.set("key1", {"name": "José", "city": "São Paulo"})
        result = backend.get("key1")
        assert result is not None
        assert result["name"] == "José"
        assert result["city"] == "São Paulo"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def flatfile_backend(tmp_path: Any) -> FlatFileBackend:
    return FlatFileBackend(data_dir=str(tmp_path / "data"))


@pytest.fixture()
def sqlite_backend(tmp_path: Any) -> SQLiteBackend:
    return SQLiteBackend(db_path=str(tmp_path / "test.db"))
