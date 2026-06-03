"""Contact resolution, department tree, and member lookup.

Handles loading contacts from the decrypted database, fuzzy name matching,
and querying contact details.
"""

import os
import sqlite3
from typing import Any

# Module-level cache for contacts within a single CLI invocation
_contact_names: dict[str, str] | None = None
_contact_full: list[dict] | None = None


def _find_contact_db(db_dir: str) -> str | None:
    """Find the contact database file.

    Args:
        db_dir: WXWork data directory.

    Returns:
        Path to the contact database, or None if not found.
    """
    # Search for contact-related database files
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if "contact" in f.lower() and (f.endswith(".db") or f.endswith(".sqlite")):
                return os.path.join(root, f)
    return None


def get_contact_names(cache, db_dir: str) -> dict[str, str]:
    """Get a mapping of usernames to display names.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Dict mapping username -> display_name.
    """
    global _contact_names
    if _contact_names is not None:
        return _contact_names

    contact_db_path = _find_contact_db(db_dir)
    if not contact_db_path:
        return {}

    decrypted_path = cache.get(contact_db_path)
    if not decrypted_path:
        return {}

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    try:
        # Try common table names
        for table_name in ["contact", "Contact", "contacts"]:
            try:
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM [{table_name}]"
                )
                cursor.fetchone()
                # Table exists, query it
                cursor = conn.execute(
                    f"SELECT username, nickname, remark FROM [{table_name}]"
                )
                _contact_names = {}
                for row in cursor.fetchall():
                    username = row[0] or ""
                    nickname = row[1] or ""
                    remark = row[2] or ""
                    display_name = remark if remark else nickname
                    if username:
                        _contact_names[username] = display_name
                return _contact_names
            except sqlite3.OperationalError:
                continue

        return {}
    finally:
        conn.close()


def get_contact_full(cache, db_dir: str) -> list[dict]:
    """Get full contact information for all contacts.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of contact dicts with all available fields.
    """
    global _contact_full
    if _contact_full is not None:
        return _contact_full

    contact_db_path = _find_contact_db(db_dir)
    if not contact_db_path:
        return []

    decrypted_path = cache.get(contact_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["contact", "Contact", "contacts"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                cursor.fetchone()
                # Table exists, query all
                cursor = conn.execute(f"SELECT * FROM [{table_name}]")
                _contact_full = [dict(row) for row in cursor.fetchall()]
                return _contact_full
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()


def resolve_username(name: str, cache, db_dir: str) -> str | None:
    """Resolve a display name to a username using fuzzy matching.

    Args:
        name: Display name, remark, or username to resolve.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Matching username, or None if not found.
    """
    contacts = get_contact_names(cache, db_dir)

    # Exact match on username
    if name in contacts:
        return name

    # Exact match on display name
    for username, display_name in contacts.items():
        if display_name == name:
            return username

    # Case-insensitive match
    name_lower = name.lower()
    for username, display_name in contacts.items():
        if display_name.lower() == name_lower:
            return username

    # Partial match (contains)
    for username, display_name in contacts.items():
        if name_lower in display_name.lower() or name_lower in username.lower():
            return username

    return None


def get_contact_detail(username: str, cache, db_dir: str) -> dict | None:
    """Get detailed information for a single contact.

    Args:
        username: Username to look up.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Contact dict with all available fields, or None if not found.
    """
    contacts = get_contact_full(cache, db_dir)

    for contact in contacts:
        if contact.get("username") == username:
            return contact

    return None


def get_department_members(dept_id: str, cache, db_dir: str) -> list[dict]:
    """Get members of a specific department.

    Args:
        dept_id: Department ID.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of contact dicts belonging to the department.
    """
    contacts = get_contact_full(cache, db_dir)
    return [c for c in contacts if str(c.get("department_id", "")) == str(dept_id)]


def search_contacts(query: str, cache, db_dir: str) -> list[dict]:
    """Search contacts by name, nickname, or userid.

    Args:
        query: Search query.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of matching contact dicts.
    """
    contacts = get_contact_full(cache, db_dir)
    query_lower = query.lower()

    results = []
    for contact in contacts:
        searchable = " ".join([
            str(contact.get("username", "")),
            str(contact.get("nickname", "")),
            str(contact.get("remark", "")),
            str(contact.get("alias", "")),
        ]).lower()

        if query_lower in searchable:
            results.append(contact)

    return results
