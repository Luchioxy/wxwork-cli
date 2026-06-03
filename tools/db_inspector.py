#!/usr/bin/env python3
"""Standalone database schema explorer.

Usage: python tools/db_inspector.py <decrypted_db_path>
"""

import json
import sqlite3
import sys


def inspect_database(db_path: str) -> dict:
    """Fully inspect a SQLite database."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    result = {"path": db_path, "tables": []}

    try:
        # List tables
        cursor = conn.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
        )
        tables = cursor.fetchall()

        for table_name, table_type, create_sql in tables:
            table_info = {
                "name": table_name,
                "type": table_type,
                "create_sql": create_sql,
                "columns": [],
                "row_count": 0,
                "sample": [],
            }

            # Get columns
            try:
                cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
                table_info["columns"] = [
                    {
                        "cid": row[0],
                        "name": row[1],
                        "type": row[2],
                        "notnull": bool(row[3]),
                        "dflt_value": row[4],
                        "pk": bool(row[5]),
                    }
                    for row in cursor.fetchall()
                ]
            except sqlite3.OperationalError:
                pass

            # Get row count
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                table_info["row_count"] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass

            # Get sample rows
            try:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 3")
                table_info["sample"] = [dict(row) for row in cursor.fetchall()]
                conn.row_factory = None
            except sqlite3.OperationalError:
                pass

            result["tables"].append(table_info)

    finally:
        conn.close()

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python db_inspector.py <decrypted_db_path>", file=sys.stderr)
        sys.exit(1)

    db_path = sys.argv[1]
    result = inspect_database(db_path)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
