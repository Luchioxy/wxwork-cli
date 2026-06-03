"""Database schema discovery utility.

Used to explore and document WXWork's database structure,
which is not publicly documented.
"""

import sqlite3
from typing import Any


def list_tables(db_path: str) -> list[dict[str, str]]:
    """List all tables in a SQLite database.

    Args:
        db_path: Path to a decrypted SQLite database.

    Returns:
        List of dicts with 'name' and 'type' fields.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
        )
        return [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]
    finally:
        conn.close()


def describe_table(db_path: str, table_name: str) -> list[dict[str, Any]]:
    """Get column information for a table.

    Args:
        db_path: Path to a decrypted SQLite database.
        table_name: Name of the table to describe.

    Returns:
        List of dicts with 'cid', 'name', 'type', 'notnull', 'dflt_value', 'pk' fields.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "dflt_value": row[4],
                "pk": bool(row[5]),
            })
        return columns
    finally:
        conn.close()


def sample_rows(db_path: str, table_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Get sample rows from a table.

    Args:
        db_path: Path to a decrypted SQLite database.
        table_name: Name of the table to sample.
        limit: Maximum number of rows to return.

    Returns:
        List of dicts, each representing a row with column names as keys.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def count_rows(db_path: str, table_name: str) -> int:
    """Count rows in a table.

    Args:
        db_path: Path to a decrypted SQLite database.
        table_name: Name of the table to count.

    Returns:
        Number of rows in the table.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_create_sql(db_path: str, table_name: str) -> str | None:
    """Get the CREATE TABLE SQL for a table.

    Args:
        db_path: Path to a decrypted SQLite database.
        table_name: Name of the table.

    Returns:
        The CREATE TABLE SQL statement, or None if not found.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def guess_purpose(table_name: str, columns: list[dict], sample_data: list[dict]) -> str:
    """Heuristically guess the purpose of a table based on its name and content.

    Args:
        table_name: Name of the table.
        columns: Column information from describe_table().
        sample_data: Sample rows from sample_rows().

    Returns:
        Human-readable description of the table's likely purpose.
    """
    col_names = {c["name"].lower() for c in columns}
    name_lower = table_name.lower()

    # Session tables
    if "session" in name_lower:
        return "Chat session list with unread counts and last message"

    # Contact tables
    if "contact" in name_lower and "room" not in name_lower:
        return "Contact/user information"

    # Chat room / group tables
    if "chatroom" in name_lower or "chat_room" in name_lower:
        return "Group chat information"

    # Group member tables
    if "member" in name_lower and ("chatroom" in name_lower or "room" in name_lower):
        return "Group chat membership"

    # Message tables
    if name_lower.startswith("msg_"):
        return "Chat messages (per-conversation)"

    if "message" in name_lower:
        return "Message data"

    # Department tables
    if "dept" in name_lower or "department" in name_lower:
        return "Department/organization structure"

    # Tag tables
    if "tag" in name_lower:
        return "Contact tags/labels"

    # Favorite tables
    if "fav" in name_lower:
        return "Bookmarked/favorited items"

    # Approval tables
    if "approval" in name_lower or "oa" in name_lower:
        return "Approval workflow data"

    # Schedule tables
    if "schedule" in name_lower or "calendar" in name_lower:
        return "Calendar/schedule data"

    # Check-in tables
    if "checkin" in name_lower or "check_in" in name_lower or "attendance" in name_lower:
        return "Check-in/attendance records"

    # Report tables
    if "report" in name_lower:
        return "Daily/weekly reports"

    # Media tables
    if "media" in name_lower or "file" in name_lower:
        return "Media/file metadata"

    # FTS (full-text search) tables
    if name_lower.startswith("fts"):
        return "Full-text search index"

    # Name-to-ID mapping
    if "name2id" in name_lower or "name_to_id" in name_lower:
        return "Name-to-ID mapping table"

    # Analyze column names for additional hints
    if {"username", "nickname", "remark"} & col_names:
        return "Contact/user related data"

    if {"create_time", "message_content", "sender"} & col_names:
        return "Message related data"

    if {"dept_id", "dept_name"} & col_names:
        return "Department related data"

    return "Unknown purpose"


def probe_database(db_path: str) -> dict[str, Any]:
    """Fully probe a database, returning comprehensive schema information.

    Args:
        db_path: Path to a decrypted SQLite database.

    Returns:
        Dict with 'tables' list, each containing name, columns, row_count,
        sample data, and guessed purpose.
    """
    tables = list_tables(db_path)
    result = {"path": db_path, "tables": []}

    for table_info in tables:
        table_name = table_info["name"]
        try:
            columns = describe_table(db_path, table_name)
            row_count = count_rows(db_path, table_name)
            sample = sample_rows(db_path, table_name, limit=3)
            purpose = guess_purpose(table_name, columns, sample)

            result["tables"].append({
                "name": table_name,
                "type": table_info["type"],
                "columns": columns,
                "row_count": row_count,
                "sample": sample,
                "purpose": purpose,
            })
        except Exception as e:
            result["tables"].append({
                "name": table_name,
                "type": table_info["type"],
                "error": str(e),
            })

    return result
