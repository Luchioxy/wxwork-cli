"""Cross-platform key extraction utilities.

Shared key verification, database collection, and hex pattern scanning.
Supports both SQLCipher (personal WeChat) and wxSQLite3 (WXWork) key formats.
"""

import hashlib
import os
import re
from pathlib import Path

from wxwork_cli.data.crypto import KEY_SZ, SALT_SZ, PAGE_SZ, verify_key

# Hex pattern for wxSQLite3 keys in process memory
# WXWork uses AES-128, so keys are 16 bytes (32 hex chars)
# Format: x'<32_hex_chars_key><32_hex_chars_salt>' (total 64 hex chars)
# Or just x'<32_hex_chars>' (key only)
KEY_HEX_PATTERN = re.compile(rb"x'([0-9a-fA-F]{32,192})")

# Alternative patterns for different key formats
KEY_ONLY_PATTERN = re.compile(rb"x'([0-9a-fA-F]{32})")  # 16-byte key only (WXWork)
KEY_64_PATTERN = re.compile(rb"x'([0-9a-fA-F]{64})")  # 32-byte key (WeChat) or key+salt (WXWork)


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
    For WXWork (wxSQLite3 AES-128), keys are 16 bytes.

    Args:
        memory_data: Raw bytes from process memory.

    Returns:
        List of candidate key bytes (16 bytes each for WXWork).
    """
    candidates = []

    # Pattern 1: 32 hex chars (16-byte key) - WXWork AES-128
    for match in KEY_ONLY_PATTERN.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            if len(raw) == 16:
                candidates.append(raw)
        except (ValueError, UnicodeDecodeError):
            continue

    # Pattern 2: 64 hex chars - could be key+salt or 32-byte key
    for match in KEY_64_PATTERN.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            if len(raw) == 32:
                # Could be 32-byte key (WeChat) or key+salt (WXWork)
                # Try both: first 16 bytes as key, then all 32 bytes
                candidates.append(raw[:16])  # First 16 bytes as WXWork key
                candidates.append(raw)  # All 32 bytes as WeChat key
        except (ValueError, UnicodeDecodeError):
            continue

    # Pattern 3: Longer hex strings - extract first 16 bytes
    for match in KEY_HEX_PATTERN.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            if len(raw) >= 16:
                candidates.append(raw[:16])  # First 16 bytes as key
        except (ValueError, UnicodeDecodeError):
            continue

    return candidates


def verify_and_match_keys(
    candidates: list[bytes],
    db_pages: list[tuple[str, bytes]],
) -> dict[str, bytes]:
    """Verify key candidates against database pages.

    Args:
        candidates: List of key candidates (16 or 32 bytes each).
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
