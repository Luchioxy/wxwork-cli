"""Group chat operations.

Handles group chat listing, member queries, and group information.
"""

import os
import sqlite3
from typing import Any


def _find_group_db(db_dir: str) -> str | None:
    """Find the group/chatroom database file.

    Args:
        db_dir: WXWork data directory.

    Returns:
        Path to the group database, or None if not found.
    """
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                if "chatroom" in f.lower() or "group" in f.lower():
                    return os.path.join(root, f)
    return None


def list_groups(cache, db_dir: str) -> list[dict]:
    """List all group chats.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of group dicts with basic info.
    """
    group_db_path = _find_group_db(db_dir)
    if not group_db_path:
        return []

    decrypted_path = cache.get(group_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Try common table names
        for table_name in ["chat_room", "chatroom", "groups"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                cursor.fetchone()
                cursor = conn.execute(f"SELECT * FROM [{table_name}]")
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()


def get_group_info(group_username: str, cache, db_dir: str) -> dict | None:
    """Get information for a specific group.

    Args:
        group_username: Group username/ID.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Group dict, or None if not found.
    """
    groups = list_groups(cache, db_dir)
    for group in groups:
        if group.get("username") == group_username or group.get("chatroom_name") == group_username:
            return group
    return None


def get_group_members(group_username: str, cache, db_dir: str) -> list[dict]:
    """Get members of a specific group.

    Args:
        group_username: Group username/ID.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of member dicts.
    """
    # Members might be stored in the chatroom_member table or as a blob in the chat_room table
    group_db_path = _find_group_db(db_dir)
    if not group_db_path:
        return []

    decrypted_path = cache.get(group_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Try chatroom_member table
        for table_name in ["chatroom_member", "ChatRoomMember"]:
            try:
                cursor = conn.execute(
                    f"SELECT * FROM [{table_name}] WHERE chatroom_name = ? OR username = ?",
                    (group_username, group_username)
                )
                rows = cursor.fetchall()
                if rows:
                    return [dict(row) for row in rows]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()
