"""Chat message history retrieval."""

import click

from wecom_cli.core.messages import collect_chat_history
from wecom_cli.core.contacts import resolve_username
from wecom_cli.output.formatter import output, format_message_text


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

    # Resolve chat name to username
    username = resolve_username(chat_name, app.cache, app.db_dir)
    if not username:
        username = chat_name  # Use as-is if not resolved

    messages = collect_chat_history(
        cache=app.cache,
        db_dir=app.db_dir,
        chat_username=username,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
        msg_type=msg_type,
    )

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
