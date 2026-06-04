"""Chat message history retrieval."""

import sqlite3

import click

from wxwork_cli.core.messages import collect_chat_history, get_user_names
from wxwork_cli.core.contacts import resolve_username
from wxwork_cli.output.formatter import output, format_message_text


def _find_conversation_by_name(cache, db_dir, chat_name):
    """Find conversation_id by searching session/conversation table.

    Prioritizes conversations with the most recent messages.

    Args:
        cache: DBCache instance.
        db_dir: WXWork data directory.
        chat_name: Name to search for.

    Returns:
        List of conversation_ids sorted by last_message_time (newest first).
    """
    import os

    # Find session database
    session_db = os.path.join(db_dir, "Data", "session.db")
    if not os.path.exists(session_db):
        return []

    decrypted = cache.get(session_db)
    if not decrypted:
        return []

    conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
    conn.text_factory = bytes

    try:
        # Search in conversation_table
        cursor = conn.execute(
            "SELECT id, name, last_message_time FROM conversation_table "
            "WHERE name LIKE ? ORDER BY last_message_time DESC",
            (f"%{chat_name}%",)
        )
        results = []
        for row in cursor.fetchall():
            conv_id = row[0].decode('utf-8') if isinstance(row[0], bytes) else str(row[0])
            name = row[1].decode('utf-8') if isinstance(row[1], bytes) and row[1] else ''
            last_time = row[2] if row[2] else 0
            results.append({
                "id": conv_id,
                "name": name,
                "last_message_time": last_time
            })
        return results
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


@click.command("history")
@click.argument("chat_name")
@click.option("--limit", default=50, help="Maximum messages to return")
@click.option("--offset", default=0, help="Number of messages to skip")
@click.option("--start-time", default=None, help="Start time (YYYY-MM-DD [HH:MM:SS])")
@click.option("--end-time", default=None, help="End time (YYYY-MM-DD [HH:MM:SS])")
@click.option("--type", "msg_type", default=None,
              type=click.Choice(["text", "image", "voice", "video", "sticker",
                                 "file", "link", "system", "approval", "oa"]),
              help="Filter by message type")
@click.option("--media", is_flag=True, help="Include media file paths")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def history(ctx, chat_name, limit, offset, start_time, end_time, msg_type, media, fmt):
    """Fetch chat message history for a conversation.

    CHAT_NAME is the name, remark, or username of the chat.
    Searches conversation list first for accurate name matching.
    """
    app = ctx.obj["app"]

    # First, try to find conversation by name in session table
    # This ensures we match the correct conversation_id (especially for group chats)
    conversations = _find_conversation_by_name(app.cache, app.db_dir, chat_name)

    user_ids = []

    # Add conversation IDs from session table (sorted by newest first)
    for conv in conversations:
        user_ids.append(conv["id"])

    # Also try to resolve chat name to user ID(s) from contacts
    user_names = get_user_names(app.cache, app.db_dir)
    for uid, name in user_names.items():
        if name == chat_name or chat_name in name:
            if uid not in user_ids:
                user_ids.append(uid)

    # If not found by name, try to resolve as username
    if not user_ids:
        username = resolve_username(chat_name, app.cache, app.db_dir)
        if username:
            user_ids.append(username)

    # Use chat_name as-is if not resolved
    if not user_ids:
        user_ids.append(chat_name)

    # Try each user_id until we find messages
    messages = []
    for user_id in user_ids:
        messages = collect_chat_history(
            cache=app.cache,
            db_dir=app.db_dir,
            chat_username=str(user_id),
            limit=limit,
            offset=offset,
            start_time=start_time,
            end_time=end_time,
            msg_type=msg_type,
        )
        if messages:
            break

    if fmt == "text":
        if not messages:
            click.echo("No messages found.")
        else:
            lines = [f"Chat history with {chat_name} ({len(messages)} messages):\n"]
            for msg in messages:
                lines.append(format_message_text(msg))
            output("\n".join(lines), "text")
    else:
        output(messages, fmt)
