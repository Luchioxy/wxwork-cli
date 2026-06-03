"""Chat message history retrieval."""

import click

from wxwork_cli.core.messages import collect_chat_history, get_user_names
from wxwork_cli.core.contacts import resolve_username
from wxwork_cli.output.formatter import output, format_message_text


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
    """
    app = ctx.obj["app"]

    # Try to resolve chat name to user ID(s)
    user_names = get_user_names(app.cache, app.db_dir)
    user_ids = []

    # Search by name - collect all matching IDs
    for uid, name in user_names.items():
        if name == chat_name or chat_name in name:
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
