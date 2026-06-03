"""Key path matching and metadata stripping utilities.

Handles Windows/Unix path separator normalization for cross-platform key matching.
"""

import os
import re
from pathlib import PurePosixPath, PureWindowsPath


def strip_key_metadata(key_entry: dict) -> dict:
    """Strip metadata from a key entry, returning only essential fields.

    Args:
        key_entry: Raw key entry from all_keys.json.

    Returns:
        Cleaned key entry with only path and key fields.
    """
    if isinstance(key_entry, str):
        # Legacy format: just a hex string
        return {"key": key_entry}

    cleaned = {}
    for k, v in key_entry.items():
        if k in ("key", "salt", "db_path", "db_name"):
            cleaned[k] = v
    return cleaned


def normalize_path(path: str) -> str:
    """Normalize a file path for consistent comparison.

    Converts backslashes to forward slashes and lowercases on Windows.

    Args:
        path: File path to normalize.

    Returns:
        Normalized path string.
    """
    # Replace backslashes with forward slashes
    normalized = path.replace("\\", "/")
    # Lowercase on Windows for case-insensitive comparison
    if os.name == "nt":
        normalized = normalized.lower()
    return normalized


def key_path_variants(db_path: str) -> list[str]:
    """Generate all possible path variants for key matching.

    Handles Windows backslash vs Unix forward slash differences,
    and strips leading drive letters and metadata prefixes.

    Args:
        db_path: Original database path.

    Returns:
        List of normalized path variants to try for matching.
    """
    variants = set()

    # Original path
    variants.add(db_path)

    # Normalized version
    norm = normalize_path(db_path)
    variants.add(norm)

    # Try to extract just the filename
    try:
        win_path = PureWindowsPath(db_path)
        variants.add(win_path.name.lower() if os.name == "nt" else win_path.name)
        # Also try with parent directory
        variants.add(f"{win_path.parent.name}/{win_path.name}".lower() if os.name == "nt"
                     else f"{win_path.parent.name}/{win_path.name}")
    except Exception:
        pass

    try:
        posix_path = PurePosixPath(db_path.replace("\\", "/"))
        variants.add(posix_path.name.lower() if os.name == "nt" else posix_path.name)
    except Exception:
        pass

    # Strip common prefixes
    for prefix in ["\\\\?\\", "\\??\\"]:
        if db_path.startswith(prefix):
            variants.add(db_path[len(prefix):])
            variants.add(normalize_path(db_path[len(prefix):]))

    return list(variants)


def get_key_info(key_entry: dict) -> dict:
    """Extract human-readable info from a key entry.

    Args:
        key_entry: Key entry dict.

    Returns:
        Dict with 'db_name', 'db_path', 'has_key', 'has_salt' fields.
    """
    info = {
        "db_name": key_entry.get("db_name", "unknown"),
        "db_path": key_entry.get("db_path", ""),
        "has_key": bool(key_entry.get("key")),
        "has_salt": bool(key_entry.get("salt")),
    }
    return info


def find_key_for_db(all_keys: list[dict], db_path: str) -> dict | None:
    """Find the matching key entry for a given database path.

    Tries multiple path variants to handle cross-platform differences.

    Args:
        all_keys: List of key entries from all_keys.json.
        db_path: Database file path to match.

    Returns:
        Matching key entry, or None if not found.
    """
    target_variants = set(key_path_variants(db_path))

    for key_entry in all_keys:
        entry_path = key_entry.get("db_path", "")
        if not entry_path:
            continue

        entry_variants = set(key_path_variants(entry_path))

        # Check if any variant matches
        if target_variants & entry_variants:
            return key_entry

        # Also check if the db_name matches
        entry_name = key_entry.get("db_name", "")
        if entry_name:
            target_name = os.path.basename(db_path)
            if os.name == "nt":
                if entry_name.lower() == target_name.lower():
                    return key_entry
            else:
                if entry_name == target_name:
                    return key_entry

    return None
