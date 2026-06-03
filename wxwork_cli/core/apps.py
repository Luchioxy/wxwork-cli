"""App management, approval workflows, schedules, check-in, and reports.

Handles WXWork-specific enterprise features.
"""

import os
import sqlite3
from datetime import datetime
from typing import Any


def _find_app_db(db_dir: str) -> str | None:
    """Find the app/OA database file.

    Args:
        db_dir: WXWork data directory.

    Returns:
        Path to the app database, or None if not found.
    """
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                f_lower = f.lower()
                if any(kw in f_lower for kw in ["app", "oa", "approval", "schedule", "checkin"]):
                    return os.path.join(root, f)
    return None


def list_apps(cache, db_dir: str) -> list[dict]:
    """List installed WeCom apps.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        List of app dicts.
    """
    app_db_path = _find_app_db(db_dir)
    if not app_db_path:
        return []

    decrypted_path = cache.get(app_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["app", "App", "apps", "application"]:
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


def get_approval_list(
    cache,
    db_dir: str,
    status: str = "all",
    limit: int = 50,
) -> list[dict]:
    """Get approval workflow records.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        status: Filter by status (pending, approved, rejected, all).
        limit: Maximum results.

    Returns:
        List of approval dicts.
    """
    app_db_path = _find_app_db(db_dir)
    if not app_db_path:
        return []

    decrypted_path = cache.get(app_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["approval", "Approval", "oa_approval"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                cursor.fetchone()

                query = f"SELECT * FROM [{table_name}]"
                params = []

                if status != "all":
                    query += " WHERE status = ?"
                    params.append(status)

                query += f" ORDER BY rowid DESC LIMIT {limit}"

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()


def get_schedule_list(
    cache,
    db_dir: str,
    date: str | None = None,
    range_days: int = 7,
) -> list[dict]:
    """Get calendar/schedule events.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        date: Start date (YYYY-MM-DD), defaults to today.
        range_days: Number of days to look ahead.

    Returns:
        List of schedule event dicts.
    """
    app_db_path = _find_app_db(db_dir)
    if not app_db_path:
        return []

    decrypted_path = cache.get(app_db_path)
    if not decrypted_path:
        return []

    # Calculate date range
    if date:
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.now()
    else:
        start_date = datetime.now()

    end_date = start_date + __import__("datetime").timedelta(days=range_days)
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["schedule", "Schedule", "calendar", "Calendar"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                cursor.fetchone()

                # Try to find time column for filtering
                time_col = None
                for col in ["start_time", "dtstart", "start_timestamp", "time"]:
                    if col in columns:
                        time_col = col
                        break

                query = f"SELECT * FROM [{table_name}]"
                params = []

                if time_col:
                    query += f" WHERE [{time_col}] >= ? AND [{time_col}] <= ?"
                    params.extend([start_ts, end_ts])

                query += " ORDER BY rowid DESC LIMIT 100"

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()


def get_checkin_records(
    cache,
    db_dir: str,
    date: str | None = None,
    range_days: int = 1,
    username: str | None = None,
) -> list[dict]:
    """Get check-in/attendance records.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        date: Date (YYYY-MM-DD), defaults to today.
        range_days: Number of days to query.
        username: Optional filter by user.

    Returns:
        List of check-in record dicts.
    """
    app_db_path = _find_app_db(db_dir)
    if not app_db_path:
        return []

    decrypted_path = cache.get(app_db_path)
    if not decrypted_path:
        return []

    # Calculate date range
    if date:
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.now()
    else:
        start_date = datetime.now()

    end_date = start_date + __import__("datetime").timedelta(days=range_days)
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["checkin", "Checkin", "check_in", "attendance"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                cursor.fetchone()

                query = f"SELECT * FROM [{table_name}]"
                conditions = []
                params = []

                # Find time column for filtering
                time_col = None
                for col in ["time", "checkin_time", "timestamp", "create_time"]:
                    if col in columns:
                        time_col = col
                        break

                if time_col:
                    conditions.append(f"[{time_col}] >= ? AND [{time_col}] <= ?")
                    params.extend([start_ts, end_ts])

                # Filter by username if specified
                if username:
                    user_col = None
                    for col in ["user", "username", "user_name", "userid"]:
                        if col in columns:
                            user_col = col
                            break
                    if user_col:
                        conditions.append(f"[{user_col}] = ?")
                        params.append(username)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY rowid DESC LIMIT 100"

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()


def get_reports(
    cache,
    db_dir: str,
    report_type: str = "daily",
    date: str | None = None,
    username: str | None = None,
) -> list[dict]:
    """Get daily/weekly reports.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        report_type: Type of report (daily, weekly).
        date: Date filter (YYYY-MM-DD).
        username: Optional filter by user.

    Returns:
        List of report dicts.
    """
    app_db_path = _find_app_db(db_dir)
    if not app_db_path:
        return []

    decrypted_path = cache.get(app_db_path)
    if not decrypted_path:
        return []

    conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for table_name in ["report", "Report", "oa_report"]:
            try:
                cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                cursor.fetchone()

                query = f"SELECT * FROM [{table_name}]"
                conditions = []
                params = []

                # Filter by report type
                if report_type:
                    type_col = None
                    for col in ["type", "report_type", "category"]:
                        if col in columns:
                            type_col = col
                            break
                    if type_col:
                        conditions.append(f"[{type_col}] = ?")
                        params.append(report_type)

                # Filter by date
                if date:
                    date_col = None
                    for col in ["date", "report_date", "create_time", "timestamp"]:
                        if col in columns:
                            date_col = col
                            break
                    if date_col:
                        try:
                            date_ts = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
                            conditions.append(f"[{date_col}] >= ?")
                            params.append(date_ts)
                        except ValueError:
                            pass

                # Filter by username
                if username:
                    user_col = None
                    for col in ["user", "username", "user_name", "userid"]:
                        if col in columns:
                            user_col = col
                            break
                    if user_col:
                        conditions.append(f"[{user_col}] = ?")
                        params.append(username)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY rowid DESC LIMIT 50"

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue

        return []
    finally:
        conn.close()
