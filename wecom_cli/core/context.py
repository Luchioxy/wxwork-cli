"""Application context singleton.

Holds configuration, keys, cache, and shared state for a CLI invocation.
"""

import atexit
import json
import os

from wecom_cli.core.config import load_config, KEYS_FILE
from wecom_cli.data.db_cache import DBCache
from wecom_cli.data.key_utils import strip_key_metadata


class AppContext:
    """Application context for wecom-cli.

    Initialized once per CLI invocation and passed to all commands via Click's
    context mechanism. Holds configuration, encryption keys, and database cache.
    """

    def __init__(self, config_path: str | None = None):
        """Initialize the application context.

        Args:
            config_path: Optional path to a custom config file.

        Raises:
            FileNotFoundError: If keys file doesn't exist (run 'wecom-cli init' first).
            RuntimeError: If configuration cannot be loaded.
        """
        self.cfg = load_config(config_path)
        self.db_dir = self.cfg["db_dir"]
        self.keys_file = self.cfg.get("keys_file", KEYS_FILE)
        self.corp_id = self.cfg.get("corp_id", "")

        # Load encryption keys
        if not os.path.exists(self.keys_file):
            raise FileNotFoundError(
                f"Keys file not found: {self.keys_file}\n"
                "Please run 'wecom-cli init' first to extract encryption keys."
            )

        with open(self.keys_file, encoding="utf-8") as f:
            raw_keys = json.load(f)

        self.all_keys = [strip_key_metadata(k) for k in raw_keys]

        # Initialize database cache
        self.cache = DBCache(self.all_keys, self.db_dir)
        atexit.register(self.cache.cleanup)

    def get_decrypted_db(self, db_path: str) -> str | None:
        """Get the path to a decrypted copy of a database.

        Args:
            db_path: Path to the encrypted database file.

        Returns:
            Path to the decrypted database, or None if decryption fails.
        """
        return self.cache.get(db_path)

    def find_databases(self, name_pattern: str = "") -> list[str]:
        """Find database files in the WXWork data directory.

        Args:
            name_pattern: Optional pattern to filter by (e.g., "msg", "contact").

        Returns:
            List of database file paths.
        """
        db_files = []
        for root, dirs, files in os.walk(self.db_dir):
            for f in files:
                if f.endswith(".db") or f.endswith(".sqlite"):
                    if not name_pattern or name_pattern.lower() in f.lower():
                        db_files.append(os.path.join(root, f))
        return db_files
