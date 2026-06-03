"""Configuration loading and WXWork path auto-detection.

Handles automatic detection of WeCom data directories on Windows.
"""

import json
import os
import sys
from pathlib import Path

# Default paths
STATE_DIR = os.path.join(os.path.expanduser("~"), ".wxwork-cli")
CONFIG_FILE = os.path.join(STATE_DIR, "config.json")
KEYS_FILE = os.path.join(STATE_DIR, "all_keys.json")

# WXWork process names by platform
WXWORK_PROCESS = "WXWork.exe" if sys.platform == "win32" else "WXWork"


def _auto_detect_db_dir_windows() -> list[str]:
    """Auto-detect WXWork data directories on Windows.

    Searches common locations:
    - C:\\Users\\<user>\\Documents\\WXWork\\<corp_id>\\
    - %APPDATA%\\Tencent\\WXWork\\

    Returns:
        List of candidate directory paths containing .db files.
    """
    candidates = []

    # Location 1: Documents\WXWork\<corp_id>\
    docs_wxwork = os.path.join(os.path.expanduser("~"), "Documents", "WXWork")
    if os.path.isdir(docs_wxwork):
        for entry in os.listdir(docs_wxwork):
            full_path = os.path.join(docs_wxwork, entry)
            if os.path.isdir(full_path):
                # Check if this directory (or subdirectories) contain .db files
                if _has_db_files(full_path):
                    candidates.append(full_path)

    # Location 2: %APPDATA%\Tencent\WXWork\
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        wxwork_appdata = os.path.join(appdata, "Tencent", "WXWork")
        if os.path.isdir(wxwork_appdata) and _has_db_files(wxwork_appdata):
            candidates.append(wxwork_appdata)

    return candidates


def _has_db_files(directory: str, max_depth: int = 3) -> bool:
    """Check if a directory contains .db files.

    Args:
        directory: Directory to search.
        max_depth: Maximum recursion depth.

    Returns:
        True if any .db files are found.
    """
    for root, dirs, files in os.walk(directory):
        # Limit depth
        depth = root[len(directory):].count(os.sep)
        if depth >= max_depth:
            dirs.clear()
            continue

        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                return True
    return False


def _choose_candidate(candidates: list[str], auto_select: bool = True) -> str:
    """Let the user choose from multiple candidate directories.

    Args:
        candidates: List of candidate directory paths.
        auto_select: If True, auto-select the first candidate (for non-interactive mode).

    Returns:
        Selected directory path.
    """
    if len(candidates) == 1:
        return candidates[0]

    # In non-interactive mode, auto-select the first candidate
    if auto_select:
        print(f"\nAuto-selecting first directory: {candidates[0]}", file=sys.stderr)
        return candidates[0]

    print(f"\nFound {len(candidates)} WeCom data directories:", file=sys.stderr)
    for i, path in enumerate(candidates, 1):
        # Try to extract corp_id from path
        parts = Path(path).parts
        corp_id = "unknown"
        for part in parts:
            if part.startswith("ww") or part.isdigit():
                corp_id = part
                break
        print(f"  [{i}] {path} (corp_id: {corp_id})", file=sys.stderr)

    while True:
        try:
            choice = input(f"\nSelect directory [1-{len(candidates)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
            print(f"Please enter a number between 1 and {len(candidates)}", file=sys.stderr)
        except (ValueError, EOFError):
            print("Invalid input. Please enter a number.", file=sys.stderr)


def _extract_corp_id(db_dir: str) -> str:
    """Extract corp_id from the database directory path.

    Args:
        db_dir: WXWork data directory path.

    Returns:
        Corp ID string, or empty string if not found.
    """
    parts = Path(db_dir).parts
    for part in parts:
        # WeCom corp IDs typically start with "ww" or are numeric
        if part.startswith("ww") and len(part) > 2:
            return part
        # Also check for numeric IDs
        if part.isdigit() and len(part) >= 6:
            return part
    return ""


def load_config(config_path: str | None = None) -> dict:
    """Load or create the wecom-cli configuration.

    Args:
        config_path: Optional path to a custom config file.

    Returns:
        Configuration dict with keys:
        - db_dir: Path to the WXWork data directory
        - keys_file: Path to the keys file
        - decrypted_dir: Path to the decrypted cache directory
        - corp_id: Corporate ID
        - wxwork_process: Process name
    """
    config_file = config_path or CONFIG_FILE

    # Try to load existing config
    if os.path.exists(config_file):
        try:
            with open(config_file, encoding="utf-8") as f:
                cfg = json.load(f)
            # Validate required fields
            if cfg.get("db_dir") and os.path.isdir(cfg["db_dir"]):
                cfg.setdefault("keys_file", KEYS_FILE)
                cfg.setdefault("decrypted_dir", "")
                cfg.setdefault("corp_id", _extract_corp_id(cfg["db_dir"]))
                cfg.setdefault("wxwork_process", WXWORK_PROCESS)
                return cfg
        except (json.JSONDecodeError, OSError):
            pass

    # Auto-detect
    candidates = []
    if sys.platform == "win32":
        candidates = _auto_detect_db_dir_windows()

    if not candidates:
        raise RuntimeError(
            "Could not auto-detect WeCom data directory. "
            "Please run 'wxwork-cli init --db-dir <path>' to specify it manually."
        )

    db_dir = _choose_candidate(candidates)
    corp_id = _extract_corp_id(db_dir)

    cfg = {
        "db_dir": db_dir,
        "keys_file": KEYS_FILE,
        "decrypted_dir": "",
        "corp_id": corp_id,
        "wxwork_process": WXWORK_PROCESS,
    }

    return cfg


def save_config(cfg: dict, config_path: str | None = None) -> None:
    """Save configuration to disk.

    Args:
        cfg: Configuration dict to save.
        config_path: Optional path to a custom config file.
    """
    config_file = config_path or CONFIG_FILE
    os.makedirs(os.path.dirname(config_file), exist_ok=True)

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
