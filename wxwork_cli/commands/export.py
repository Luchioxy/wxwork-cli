"""Export chat records to markdown/txt/json."""

import os
import sys

import click

from wxwork_cli.core.messages import collect_chat_history, get_user_names
from wxwork_cli.core.contacts import resolve_username
from wxwork_cli.output.formatter import output_json, output_text, format_message_text


@click.command("export")
@click.argument("chat_name")
@click.option("--format", "export_format", type=click.Choice(["markdown", "txt", "json"]),
              default="markdown", help="Export format")
@click.option("--output", "output_path", default=None, help="Output file path")
@click.option("--start-time", default=None, help="Start time filter")
@click.option("--end-time", default=None, help="End time filter")
@click.option("--limit", default=1000, help="Maximum messages to export")
@click.pass_context
def export(ctx, chat_name, export_format, output_path, start_time, end_time, limit):
    """Export chat records to a file.

    CHAT_NAME is the name of the chat to export.
    """
    app = ctx.obj["app"]

    # Load user names for sender resolution
    user_names = get_user_names(app.cache, app.db_dir)

    # Try to find user ID(s) by name
    user_ids = []
    for uid, name in user_names.items():
        if name == chat_name or chat_name in name:
            user_ids.append(uid)

    if not user_ids:
        username = resolve_username(chat_name, app.cache, app.db_dir)
        if username:
            user_ids.append(username)
        else:
            user_ids.append(chat_name)

    # Try each user_id until we find messages
    messages = []
    for user_id in user_ids:
        messages = collect_chat_history(
            cache=app.cache,
            db_dir=app.db_dir,
            chat_username=str(user_id),
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        if messages:
            break

    if not messages:
        click.echo("No messages to export.", err=True)
        return

    # Generate output
    if export_format == "json":
        content = __import__("json").dumps(messages, ensure_ascii=False, indent=2)
    elif export_format == "markdown":
        lines = [f"# Chat Export: {chat_name}\n"]
        lines.append(f"Total messages: {len(messages)}\n\n---\n")
        for msg in messages:
            sender = msg.get("sender_name", msg.get("sender", "unknown"))
            time_str = msg.get("time", "")
            content_text = msg.get("content", "")
            msg_type = msg.get("type", "text")

            lines.append(f"**{sender}** ({time_str})")
            if msg_type != "text":
                lines.append(f"*[{msg_type}]*")
            lines.append(f"{content_text}\n")
        content = "\n".join(lines)
    else:  # txt
        lines = [f"Chat Export: {chat_name}", f"Total messages: {len(messages)}", ""]
        for msg in messages:
            lines.append(format_message_text(msg))
        content = "\n".join(lines)

    # Write to file or stdout
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"Exported {len(messages)} messages to {output_path}")
    else:
        output_text(content)
