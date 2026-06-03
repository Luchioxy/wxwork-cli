"""Decrypted database cache with mtime-based invalidation.

Caches decrypted databases in the system temp directory.
Cache validity is tracked via file modification times.
"""

import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path

from wxwork_cli.data.crypto import full_decrypt, decrypt_wal, verify_key
from wxwork_cli.data.key_utils import find_key_for_db, normalize_path

CACHE_DIR = os.path.join(tempfile.gettempdir(), "wxwork_cli_cache")
MTIMES_FILE = "_mtimes.json"


class DBCache:
    """Manages decrypted database copies with mtime-based cache invalidation.

    Decrypted databases are stored in the system temp directory.
    Cache validity is tracked by comparing source file modification times
    against stored values.
    """

    def __init__(self, all_keys: list[dict], db_dir: str):
        """Initialize the cache.

        Args:
            all_keys: List of key entries (from all_keys.json).
            db_dir: Root directory of the WXWork data files.
        """
        self.all_keys = all_keys
        self.db_dir = db_dir
        self.cache_dir = CACHE_DIR
        self.mtimes_path = os.path.join(self.cache_dir, MTIMES_FILE)
        self._mtimes: dict[str, dict] = {}
        self._ensure_cache_dir()
        self._load_mtimes()

    def _ensure_cache_dir(self) -> None:
        """Create the cache directory if it doesn't exist."""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _load_mtimes(self) -> None:
        """Load cached mtime metadata from disk."""
        if os.path.exists(self.mtimes_path):
            try:
                with open(self.mtimes_path, encoding="utf-8") as f:
                    self._mtimes = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._mtimes = {}

    def _save_mtimes(self) -> None:
        """Persist mtime metadata to disk."""
        try:
            with open(self.mtimes_path, "w", encoding="utf-8") as f:
                json.dump(self._mtimes, f, indent=2)
        except OSError:
            pass  # Best effort

    def _get_cache_key(self, db_path: str) -> str:
        """Generate a unique cache key for a database path.

        Uses normalized path to avoid duplicates on Windows.
        """
        return normalize_path(db_path)

    def _get_cached_path(self, cache_key: str) -> str:
        """Get the file path for a cached decrypted database."""
        # Use SHA-256 hash of the cache key to avoid filesystem issues with long paths
        import hashlib
        key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:32]
        return os.path.join(self.cache_dir, f"{key_hash}.db")

    def _is_cache_valid(self, db_path: str, cache_key: str) -> bool:
        """Check if the cached version is still valid.

        Compares current mtime of source DB and WAL against stored values.

        Args:
            db_path: Path to the source encrypted database.
            cache_key: Cache key for this database.

        Returns:
            True if cache is valid (file hasn't changed).
        """
        if cache_key not in self._mtimes:
            return False

        cached = self._mtimes[cache_key]
        cached_path = self._get_cached_path(cache_key)

        # Check if cached file exists
        if not os.path.exists(cached_path):
            return False

        # Check source DB mtime
        try:
            current_mtime = os.path.getmtime(db_path)
        except OSError:
            return False

        if current_mtime != cached.get("db_mtime"):
            return False

        # Check WAL file mtime if it exists
        wal_path = db_path + "-wal"
        if os.path.exists(wal_path):
            try:
                wal_mtime = os.path.getmtime(wal_path)
            except OSError:
                wal_mtime = 0
            if wal_mtime != cached.get("wal_mtime", 0):
                return False

        return True

    def get(self, db_path: str) -> str | None:
        """Get the path to a decrypted copy of the database.

        Returns cached version if valid, otherwise decrypts and caches.

        Args:
            db_path: Path to the encrypted database file.

        Returns:
            Path to the decrypted database file, or None if decryption fails.
        """
        if not os.path.exists(db_path):
            return None

        cache_key = self._get_cache_key(db_path)
        cached_path = self._get_cached_path(cache_key)

        # Check cache validity
        if self._is_cache_valid(db_path, cache_key):
            return cached_path

        # Cache miss - need to decrypt
        key_entry = find_key_for_db(self.all_keys, db_path)
        if not key_entry or not key_entry.get("key"):
            return None

        enc_key = bytes.fromhex(key_entry["key"])

        # Verify key against the database
        if not verify_key(enc_key, db_path):
            return None

        try:
            # Decrypt the database
            full_decrypt(db_path, cached_path, enc_key)

            # Decrypt WAL file if it exists
            wal_path = db_path + "-wal"
            if os.path.exists(wal_path):
                wal_cached_path = cached_path + "-wal"
                try:
                    decrypt_wal(wal_path, wal_cached_path, enc_key)
                except (ValueError, OSError):
                    # WAL decryption failure is non-fatal
                    pass

            # Update mtime cache
            try:
                db_mtime = os.path.getmtime(db_path)
                wal_mtime = os.path.getmtime(wal_path) if os.path.exists(wal_path) else 0
            except OSError:
                db_mtime = 0
                wal_mtime = 0

            self._mtimes[cache_key] = {
                "db_path": db_path,
                "db_mtime": db_mtime,
                "wal_mtime": wal_mtime,
                "cached_path": cached_path,
            }
            self._save_mtimes()

            return cached_path

        except (ValueError, OSError) as e:
            # Decryption failed - clean up partial output
            if os.path.exists(cached_path):
                try:
                    os.remove(cached_path)
                except OSError:
                    pass
            return None

    def invalidate(self, db_path: str) -> None:
        """Invalidate the cache for a specific database.

        Args:
            db_path: Path to the database to invalidate.
        """
        cache_key = self._get_cache_key(db_path)
        cached_path = self._get_cached_path(cache_key)

        if os.path.exists(cached_path):
            try:
                os.remove(cached_path)
            except OSError:
                pass

        self._mtimes.pop(cache_key, None)
        self._save_mtimes()

    def cleanup(self) -> None:
        """Save metadata and clean up on exit."""
        self._save_mtimes()

    def clear(self) -> None:
        """Clear all cached data."""
        self._mtimes = {}
        self._save_mtimes()

        # Remove cached files
        if os.path.exists(self.cache_dir):
            try:
                shutil.rmtree(self.cache_dir)
            except OSError:
                pass
        self._ensure_cache_dir()
