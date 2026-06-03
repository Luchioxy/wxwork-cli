"""Department hierarchy operations.

Handles department tree listing, department info queries,
and department member lookups.
"""

import os
import sqlite3
from typing import Any


def _find_dept_db(db_dir: str) -> str | None:
    """Find the department database file.

    Args:
        db_dir: WXWork data directory.

    Returns:
        Path to the department database, or None if not found.
    """
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                if "dept" in f.lower() or "department" in f.lower() or "org" in f.lower():
                    return os.path.join(root, f)
    return None


def get_department_tree(cache, db_dir: str) -> list[dict]:
    """Get the full department hierarchy.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of department dicts with hierarchical structure.
    """
    dept_db_path = _find_dept_db(db_dir)
    if not dept_db_path:
        return []

    decrypted_path = cache.get(dept_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Try common table names
        for table_name in ["department", "Department", "dept", "departments"]:
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


def get_department_info(dept_id: str, cache, db_dir: str) -> dict | None:
    """Get information for a specific department.

    Args:
        dept_id: Department ID.
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Department dict, or None if not found.
    """
    departments = get_department_tree(cache, db_dir)
    for dept in departments:
        if str(dept.get("id", dept.get("dept_id", ""))) == str(dept_id):
            return dept
    return None


def list_departments(parent_id: str, cache, db_dir: str) -> list[dict]:
    """List child departments of a parent department.

    Args:
        parent_id: Parent department ID (0 for root).
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of child department dicts.
    """
    departments = get_department_tree(cache, db_dir)
    return [
        d for d in departments
        if str(d.get("parent_id", d.get("parentid", ""))) == str(parent_id)
    ]


def build_department_tree(departments: list[dict]) -> list[dict]:
    """Build a hierarchical tree from flat department list.

    Args:
        departments: Flat list of department dicts.

    Returns:
        Nested tree structure with 'children' key.
    """
    dept_map = {}
    for dept in departments:
        dept_id = str(dept.get("id", dept.get("dept_id", "")))
        dept_map[dept_id] = {**dept, "children": []}

    tree = []
    for dept in departments:
        dept_id = str(dept.get("id", dept.get("dept_id", "")))
        parent_id = str(dept.get("parent_id", dept.get("parentid", "")))

        if parent_id and parent_id in dept_map:
            dept_map[parent_id]["children"].append(dept_map[dept_id])
        else:
            tree.append(dept_map[dept_id])

    return tree
