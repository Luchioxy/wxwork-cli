"""Message querying, search, formatting, and statistics.

Handles message table discovery, content decompression (zstd),
XML parsing for rich messages, and all query/search/statistics logic.
"""

import hashlib
import os
import re
import sqlite3
import struct
from datetime import datetime
from typing import Any

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

# Message type constants (from WXWork)
MSG_TYPE_MAP = {
    0: "text",
    1: "image",
    2: "voice",
    3: "video",
    4: "file",
    5: "link",
    6: "location",
    7: "card",
    8: "sticker",
    9: "call",
    10: "system",
    14: "screenshot",  # 企业微信截图
    10000: "system",
    10002: "system",
    # WXWork-specific types
    2001: "approval",
    2002: "oa",
    2003: "schedule",
    2004: "checkin",
    2005: "report",
}

# Content compression types
CONTENT_COMPRESS_NONE = 0
CONTENT_COMPRESS_ZSTD = 4

# Batch query size for pagination
_HISTORY_QUERY_BATCH_SIZE = 500


def find_msg_db_files(db_dir: str) -> list[str]:
    """Find message database files.

    Args:
        db_dir: WXWork data directory.

    Returns:
        List of paths to message database files.
    """
    msg_files = []
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                if "msg" in f.lower() or "message" in f.lower():
                    msg_files.append(os.path.join(root, f))
    return sorted(msg_files)


def find_msg_tables(decrypted_db_path: str) -> list[str]:
    """Find message tables in a decrypted database.

    Args:
        decrypted_db_path: Path to a decrypted database.

    Returns:
        List of table names that look like message tables.
    """
    conn = sqlite3.connect(f"file:{decrypted_db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        )
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _get_msg_table_hash(username: str) -> str:
    """Get the MD5 hash used for message table naming.

    Args:
        username: The username/chat ID.

    Returns:
        MD5 hex hash string.
    """
    return hashlib.md5(username.encode()).hexdigest()


def _decompress_content(content: bytes, compress_type: int = 0) -> str:
    """Decompress message content.

    Args:
        content: Raw content bytes.
        compress_type: Compression type (0=none, 4=zstd).

    Returns:
        Decompressed content string.
    """
    if not content:
        return ""

    if compress_type == CONTENT_COMPRESS_ZSTD and HAS_ZSTD:
        try:
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress(content)
            return decompressed.decode("utf-8", errors="replace")
        except Exception:
            return content.decode("utf-8", errors="replace")

    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def parse_wxwork_message(content: bytes) -> str:
    """Parse WXWork message content from protobuf format.

    Args:
        content: Raw message content bytes.

    Returns:
        Parsed text content.
    """
    if not content or not isinstance(content, bytes):
        return ''

    try:
        # Look for pattern: \x12<length>\n<length><text>
        idx = content.find(b'\x12')
        if idx > 0:
            remaining = content[idx+1:]
            if len(remaining) > 2:
                length = remaining[0]
                if length < len(remaining):
                    text_bytes = remaining[2:2+length-1]
                    text = text_bytes.decode('utf-8')
                    # Remove control characters
                    text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
                    return text.strip()
    except:
        pass

    # Fallback: try to decode as UTF-8
    try:
        text = content.decode('utf-8', errors='ignore')
        text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
        return text.strip()
    except:
        return content.hex()


def _parse_message_row(row: tuple, columns: list[str]) -> dict:
    """Parse a message row into a structured dict.

    Args:
        row: Raw row tuple from SQLite.
        columns: Column names.

    Returns:
        Structured message dict.
    """
    msg = {}
    for i, col in enumerate(columns):
        if i < len(row):
            msg[col] = row[i]

    # Normalize fields
    msg_type = msg.get("content_type", msg.get("local_type", msg.get("type", 0)))
    msg["type"] = MSG_TYPE_MAP.get(msg_type, f"unknown_{msg_type}")

    # Parse timestamp
    send_time = msg.get("send_time", msg.get("create_time", 0))
    if send_time:
        try:
            msg["time"] = datetime.fromtimestamp(send_time).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            msg["time"] = str(send_time)

    # Parse content
    content = msg.get("content", "")
    if isinstance(content, bytes):
        msg["content"] = parse_wxwork_message(content)
    elif content is None:
        msg["content"] = ""
    else:
        msg["content"] = str(content)

    return msg


def get_user_names(cache, db_dir: str) -> dict[int, str]:
    """Get mapping of user IDs to names.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.

    Returns:
        Dict mapping user_id -> name.
    """
    user_names = {}

    # Find user database
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
            cursor = conn.execute("SELECT id, name FROM user_table")
            for row in cursor.fetchall():
                user_id = row[0]
                name = row[1]
                if isinstance(name, bytes):
                    try:
                        name = name.decode('utf-8')
                    except:
                        name = str(user_id)
                user_names[user_id] = name
        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    return user_names


def get_image_cache_mapping(db_dir: str) -> dict[str, str]:
    """Get mapping of media IDs to local file paths.

    Args:
        db_dir: WXWork data directory.

    Returns:
        Dict mapping media_key -> local_file_path.
    """
    mapping = {}

    # Find CacheMapping database
    cache_mapping_dir = os.path.join(db_dir, "..", "CacheMapping")
    if not os.path.isdir(cache_mapping_dir):
        cache_mapping_dir = os.path.join(os.path.dirname(db_dir), "CacheMapping")

    if not os.path.isdir(cache_mapping_dir):
        return mapping

    for f in os.listdir(cache_mapping_dir):
        if f.endswith(".db"):
            db_path = os.path.join(cache_mapping_dir, f)
            # CacheMapping is not encrypted
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                conn.text_factory = bytes
                cursor = conn.execute(
                    "SELECT key, file_name FROM mapping WHERE type = 2"
                )
                for row in cursor.fetchall():
                    key = row[0]
                    file_name = row[1]
                    if isinstance(key, bytes):
                        try:
                            key = key.decode('utf-8')
                        except:
                            continue
                    if isinstance(file_name, bytes):
                        try:
                            file_name = file_name.decode('utf-8')
                        except:
                            continue
                    mapping[key] = file_name
                conn.close()
            except sqlite3.OperationalError:
                continue

    return mapping


def collect_chat_history(
    cache,
    db_dir: str,
    chat_username: str,
    limit: int = 50,
    offset: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
    msg_type: str | None = None,
) -> list[dict]:
    """Collect chat history for a specific conversation.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        chat_username: Username/ID of the chat.
        limit: Maximum messages to return.
        offset: Number of messages to skip.
        start_time: Optional start time filter (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
        end_time: Optional end time filter.
        msg_type: Optional message type filter.

    Returns:
        List of message dicts.
    """
    table_hash = _get_msg_table_hash(chat_username)
    table_name = f"Msg_{table_hash}"

    # Find message databases
    msg_db_files = find_msg_db_files(db_dir)
    if not msg_db_files:
        return []

    messages = []
    for db_path in msg_db_files:
        decrypted_path = cache.get(db_path)
        if not decrypted_path:
            continue

        conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
        try:
            # Check if the table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if not cursor.fetchone():
                continue

            # Get column names
            cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
            columns = [row[1] for row in cursor.fetchall()]

            # Build query
            query = f"SELECT * FROM [{table_name}]"
            conditions = []
            params = []

            if start_time:
                try:
                    start_ts = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp())
                except ValueError:
                    try:
                        start_ts = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp())
                    except ValueError:
                        start_ts = None
                if start_ts is not None:
                    conditions.append("create_time >= ?")
                    params.append(start_ts)

            if end_time:
                try:
                    end_ts = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp())
                except ValueError:
                    try:
                        end_ts = int(datetime.strptime(end_time, "%Y-%m-%d").timestamp())
                    except ValueError:
                        end_ts = None
                if end_ts is not None:
                    conditions.append("create_time <= ?")
                    params.append(end_ts)

            if msg_type:
                # Find the numeric type for the string type
                type_num = None
                for k, v in MSG_TYPE_MAP.items():
                    if v == msg_type:
                        type_num = k
                        break
                if type_num is not None:
                    conditions.append("local_type = ?")
                    params.append(type_num)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY create_time DESC"

            # Always fetch limit + offset rows to handle offset at application level
            # This is necessary because messages come from multiple databases
            query += f" LIMIT {limit + offset}"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                msg = _parse_message_row(row, columns)
                messages.append(msg)

        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    # Sort by time and apply offset
    messages.sort(key=lambda m: m.get("create_time", 0), reverse=True)
    if offset:
        messages = messages[offset:]
    messages = messages[:limit]

    return messages


def search_messages(
    cache,
    db_dir: str,
    keyword: str,
    chat_username: str | None = None,
    limit: int = 50,
    msg_type: str | None = None,
) -> list[dict]:
    """Search messages for a keyword.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        keyword: Search keyword.
        chat_username: Optional - limit search to specific chat.
        limit: Maximum results to return.
        msg_type: Optional message type filter.

    Returns:
        List of matching message dicts.
    """
    msg_db_files = find_msg_db_files(db_dir)
    if not msg_db_files:
        return []

    results = []
    keyword_lower = keyword.lower()

    for db_path in msg_db_files:
        decrypted_path = cache.get(db_path)
        if not decrypted_path:
            continue

        conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
        try:
            # Find all message tables
            tables = find_msg_tables(decrypted_path)

            for table_name in tables:
                # If chat_username specified, check if this table is for that chat
                if chat_username:
                    expected_hash = _get_msg_table_hash(chat_username)
                    if expected_hash not in table_name:
                        continue

                # Get column names
                try:
                    cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
                    columns = [row[1] for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    continue

                # Search in message_content
                content_col = "message_content"
                if content_col not in columns:
                    for col in columns:
                        if "content" in col.lower():
                            content_col = col
                            break

                try:
                    query = f"SELECT * FROM [{table_name}] WHERE [{content_col}] LIKE ? LIMIT ?"
                    cursor = conn.execute(query, (f"%{keyword}%", limit))
                    rows = cursor.fetchall()

                    for row in rows:
                        msg = _parse_message_row(row, columns)
                        # Double-check case-insensitive match
                        if keyword_lower in str(msg.get("content", "")).lower():
                            results.append(msg)
                except sqlite3.OperationalError:
                    continue

        finally:
            conn.close()

    # Sort by time and limit
    results.sort(key=lambda m: m.get("create_time", 0), reverse=True)
    return results[:limit]


def collect_chat_stats(
    cache,
    db_dir: str,
    chat_username: str,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """Collect statistics for a chat.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        chat_username: Username/ID of the chat.
        start_time: Optional start time filter.
        end_time: Optional end time filter.

    Returns:
        Dict with statistics (total_messages, type_breakdown, top_senders, hourly_activity).
    """
    table_hash = _get_msg_table_hash(chat_username)
    table_name = f"Msg_{table_hash}"

    msg_db_files = find_msg_db_files(db_dir)

    stats = {
        "chat": chat_username,
        "total_messages": 0,
        "type_breakdown": {},
        "top_senders": {},
        "hourly_activity": {str(h): 0 for h in range(24)},
    }

    for db_path in msg_db_files:
        decrypted_path = cache.get(db_path)
        if not decrypted_path:
            continue

        conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if not cursor.fetchone():
                continue

            # Get column names
            cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
            columns = [row[1] for row in cursor.fetchall()]

            # Build time filter
            conditions = []
            params = []
            if start_time:
                try:
                    start_ts = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp())
                    conditions.append("create_time >= ?")
                    params.append(start_ts)
                except ValueError:
                    pass
            if end_time:
                try:
                    end_ts = int(datetime.strptime(end_time, "%Y-%m-%d").timestamp())
                    conditions.append("create_time <= ?")
                    params.append(end_ts)
                except ValueError:
                    pass

            where_clause = ""
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

            # Total count
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM [{table_name}]{where_clause}", params
            )
            stats["total_messages"] += cursor.fetchone()[0]

            # Type breakdown
            type_col = "local_type" if "local_type" in columns else "type"
            if type_col in columns:
                cursor = conn.execute(
                    f"SELECT [{type_col}], COUNT(*) FROM [{table_name}]{where_clause} GROUP BY [{type_col}]",
                    params
                )
                for row in cursor.fetchall():
                    type_name = MSG_TYPE_MAP.get(row[0], f"unknown_{row[0]}")
                    stats["type_breakdown"][type_name] = stats["type_breakdown"].get(type_name, 0) + row[1]

            # Top senders
            sender_col = "real_sender_id" if "real_sender_id" in columns else "sender"
            if sender_col in columns:
                cursor = conn.execute(
                    f"SELECT [{sender_col}], COUNT(*) FROM [{table_name}]{where_clause} GROUP BY [{sender_col}] ORDER BY COUNT(*) DESC LIMIT 10",
                    params
                )
                for row in cursor.fetchall():
                    stats["top_senders"][str(row[0])] = row[1]

            # Hourly activity
            if "create_time" in columns:
                cursor = conn.execute(
                    f"SELECT create_time FROM [{table_name}]{where_clause}", params
                )
                for row in cursor.fetchall():
                    try:
                        hour = datetime.fromtimestamp(row[0]).hour
                        stats["hourly_activity"][str(hour)] += 1
                    except (ValueError, OSError):
                        pass

        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    return stats
