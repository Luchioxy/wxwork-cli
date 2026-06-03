"""Cross-platform key extraction utilities.

Shared HMAC verification, database collection, and hex pattern scanning.
"""

import hashlib
import os
import re
from pathlib import Path

from wecom_cli.data.crypto import KEY_SZ, SALT_SZ, PAGE_SZ, verify_key

# Hex pattern for SQLCipher keys in process memory
# Format: 96 hex chars = 32-byte key + 16-byte salt (SQLCipher 4)
KEY_HEX_PATTERN = re.compile(rb"x'([0-9a-fA-F]{64,192})")

# Alternative patterns
KEY_ONLY_PATTERN = re.compile(rb"x'([0-9a-fA-F]{64})")  # 32-byte key only
SALT_ONLY_PATTERN = re.compile(rb"x'([0-9a-fA-F]{32})")  # 16-byte salt only


def collect_db_files(db_dir: str) -> list[str]:
    """Collect all .db files in the WXWork data directory.

    Args:
        db_dir: Root directory to scan.

    Returns:
        List of absolute paths to .db files.
    """
    db_files = []
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                db_files.append(os.path.join(root, f))
    return db_files


def collect_db_pages(db_files: list[str], max_pages: int = 3) -> list[tuple[str, bytes]]:
    """Read the first page(s) from each database file for key verification.

    Args:
        db_files: List of database file paths.
        max_pages: Number of pages to read from each file.

    Returns:
        List of (db_path, page_data) tuples.
    """
    pages = []
    for db_path in db_files:
        try:
            with open(db_path, "rb") as f:
                data = f.read(PAGE_SZ * max_pages)
            if len(data) >= PAGE_SZ:
                pages.append((db_path, data[:PAGE_SZ]))
        except OSError:
            continue
    return pages


def extract_hex_candidates(memory_data: bytes) -> list[bytes]:
    """Extract potential key candidates from process memory data.

    Searches for hex-encoded key patterns in various formats.

    Args:
        memory_data: Raw bytes from process memory.

    Returns:
        List of candidate key bytes (32 bytes each).
    """
    candidates = []

    # Pattern 1: Full key+salt (96 hex chars = 48 bytes)
    for match in KEY_HEX_PATTERN.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            # Could be key(32) + salt(16) = 48 bytes
            if len(raw) >= 48:
                candidates.append(raw[:32])  # Just the key part
            # Could be key(32) only
            elif len(raw) == 32:
                candidates.append(raw)
        except (ValueError, UnicodeDecodeError):
            continue

    # Pattern 2: 64 hex chars (key only)
    for match in KEY_ONLY_PATTERN.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            if len(raw) == 32:
                candidates.append(raw)
        except (ValueError, UnicodeDecodeError):
            continue

    return candidates


def verify_and_match_keys(
    candidates: list[bytes],
    db_pages: list[tuple[str, bytes]],
) -> dict[str, bytes]:
    """Verify key candidates against database pages.

    Args:
        candidates: List of 32-byte key candidates.
        db_pages: List of (db_path, first_page_data) tuples.

    Returns:
        Dict mapping database paths to their matching encryption keys.
    """
    matched = {}
    seen_keys = set()

    for key_bytes in candidates:
        key_hex = key_bytes.hex()
        if key_hex in seen_keys:
            continue
        seen_keys.add(key_hex)

        for db_path, page_data in db_pages:
            if db_path in matched:
                continue

            if verify_key(key_bytes, db_path):
                matched[db_path] = key_bytes

    return matched


def cross_verify_keys(
    matched: dict[str, bytes],
    all_db_files: list[str],
) -> dict[str, bytes]:
    """Try matched keys against unmatched databases.

    Some databases may use the same key but weren't matched in the initial scan.

    Args:
        matched: Already matched {db_path: key} dict.
        all_db_files: All database file paths.

    Returns:
        Updated dict with additional matches.
    """
    unmatched = [f for f in all_db_files if f not in matched]
    if not unmatched or not matched:
        return matched

    # Collect unique keys
    unique_keys = list({v.hex(): v for v in matched.values()}.values())

    for db_path in unmatched:
        for key_bytes in unique_keys:
            if verify_key(key_bytes, db_path):
                matched[db_path] = key_bytes
                break

    return matched


def build_keys_json(matched: dict[str, bytes]) -> list[dict]:
    """Build the all_keys.json structure from matched keys.

    Args:
        matched: Dict mapping db paths to their encryption keys.

    Returns:
        List of key entry dicts.
    """
    entries = []
    for db_path, key_bytes in matched.items():
        entries.append({
            "db_path": db_path,
            "db_name": os.path.basename(db_path),
            "key": key_bytes.hex(),
        })
    return entries
