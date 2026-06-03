"""Department hierarchy operations.

Handles department tree listing, department info queries,
and department member lookups.
"""

import os
import sqlite3
from typing import Any


def get_department_tree(cache, db_dir: str) -> list[dict]:
    """Get the full department hierarchy.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of department dicts with hierarchical structure.
    """
    results = []

    # Find user database (departments are stored in user.db)
    user_dbs = []
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f == "user.db":
                user_dbs.append(os.path.join(root, f))

    for db_path in user_dbs:
        decrypted = cache.get(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.text_factory = bytes
        try:
            # Try department_tableV2 first
            for table_name in ["department_tableV2", "department", "Department", "dept"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()

                    cursor = conn.execute(f"SELECT * FROM [{table_name}]")
                    columns = [desc[0] if isinstance(desc[0], str) else desc[0].decode() for desc in cursor.description]

                    for row in cursor.fetchall():
                        dept = {}
                        for i, col in enumerate(columns):
                            val = row[i]
                            if isinstance(val, bytes):
                                try:
                                    val = val.decode('utf-8')
                                except:
                                    val = val.hex()
                            dept[col] = val
                        results.append(dept)
                    return results
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
