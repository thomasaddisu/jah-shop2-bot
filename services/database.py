"""
JSON Database Layer
Thread-safe, atomic writes, backup, corruption detection, caching.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("jah_shop.database")


class JSONDatabase:
    """
    Thread-safe JSON file database with:
    - Atomic writes (write to temp → rename)
    - Automatic backups
    - Corruption detection and recovery
    - In-memory LRU-style cache
    - Async-friendly interface
    """

    _instances: dict[str, "JSONDatabase"] = {}
    _lock_map: dict[str, threading.Lock] = {}
    _cache: dict[str, tuple[Any, float]] = {}
    _cache_ttl: float = 5.0  # seconds

    def __init__(self, filepath: Path, default: Any = None) -> None:
        self.filepath = Path(filepath)
        self.default = default if default is not None else {}
        self._lock = threading.Lock()
        self._ensure_file()

    # ─── Internal ────────────────────────────────────────────────

    def _ensure_file(self) -> None:
        """Create the file with default content if it doesn't exist."""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self._write_raw(self.default)
            logger.info(f"Created data file: {self.filepath}")

    def _read_raw(self) -> Any:
        """Read and parse JSON, attempt backup recovery on corruption."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return self.default
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON corruption in {self.filepath}: {e} — attempting recovery")
            return self._recover()
        except FileNotFoundError:
            self._ensure_file()
            return self.default

    def _write_raw(self, data: Any) -> None:
        """Atomic write: write to temp file then rename."""
        tmp = self.filepath.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp, self.filepath)
        except Exception as e:
            logger.error(f"Failed to write {self.filepath}: {e}")
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise

    def _recover(self) -> Any:
        """Try to restore from the most recent backup."""
        from config import BACKUPS_DIR

        backups = sorted(BACKUPS_DIR.glob(f"{self.filepath.stem}_*.json"), reverse=True)
        for backup in backups:
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Recovered {self.filepath} from {backup}")
                self._write_raw(data)
                return data
            except Exception:
                continue
        logger.warning(f"No valid backup found for {self.filepath}, using default.")
        self._write_raw(self.default)
        return self.default

    def _make_backup(self) -> None:
        """Create a timestamped backup of the current file."""
        from config import BACKUPS_DIR

        if not self.filepath.exists():
            return
        ts = int(time.time())
        backup_path = BACKUPS_DIR / f"{self.filepath.stem}_{ts}.json"
        try:
            shutil.copy2(self.filepath, backup_path)
            # Keep only last 5 backups per file
            backups = sorted(BACKUPS_DIR.glob(f"{self.filepath.stem}_*.json"), reverse=True)
            for old in backups[5:]:
                old.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Backup failed for {self.filepath}: {e}")

    # ─── Public Interface ────────────────────────────────────────

    def read(self) -> Any:
        """Read data from file (cached)."""
        cache_key = str(self.filepath)
        cached = JSONDatabase._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        with self._lock:
            data = self._read_raw()
            JSONDatabase._cache[cache_key] = (data, time.monotonic())
            return data

    def write(self, data: Any, backup: bool = False) -> None:
        """Write data to file atomically, invalidate cache."""
        with self._lock:
            if backup:
                self._make_backup()
            self._write_raw(data)
            JSONDatabase._cache.pop(str(self.filepath), None)

    def update(self, updater_fn) -> Any:
        """Read → transform → write atomically. Returns new data."""
        with self._lock:
            data = self._read_raw()
            new_data = updater_fn(data)
            self._write_raw(new_data)
            JSONDatabase._cache.pop(str(self.filepath), None)
            return new_data

    # ─── Async Wrappers ──────────────────────────────────────────

    async def async_read(self) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read)

    async def async_write(self, data: Any, backup: bool = False) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.write(data, backup))

    async def async_update(self, updater_fn) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.update(updater_fn))

    def invalidate_cache(self) -> None:
        JSONDatabase._cache.pop(str(self.filepath), None)


# ─── Singleton Registry ──────────────────────────────────────

_db_registry: dict[str, JSONDatabase] = {}
_registry_lock = threading.Lock()


def get_db(filepath: Path, default: Any = None) -> JSONDatabase:
    """Return a singleton JSONDatabase for the given path."""
    key = str(filepath)
    with _registry_lock:
        if key not in _db_registry:
            _db_registry[key] = JSONDatabase(filepath, default)
        return _db_registry[key]
