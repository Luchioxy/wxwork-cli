"""Message search (global / per-chat)."""

import click

from wxwork_cli.core.messages import search_messages
from wxwork_cli.core.contacts import resolve_username
from wxwork_cli.output.formatter import output, format_message_text


@click.command("search")
@click.argument("keyword")
@click.option("--chat", multiple=True, help="Limit search to specific chat(s)")
@click.option("--start-time", default=None, help="Start time filter")
@click.option("--end-time", default=None, help="End time filter")
@click.option("--limit", default=50, help="Maximum results")
@click.option("--type", "msg_type", default=None,
              type=click.Choice(["text", "image", "voice", "video", "sticker",
                                 "file", "link", "system", "approval", "oa"]),
              help="Filter by message type")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def search(ctx, keyword, chat, start_time, end_time, limit, msg_type, fmt):
    """Search messages for a keyword.

    Searches across all chats by default. Use --chat to limit to specific chats.
    """
    app = ctx.obj["app"]

    results = []
    chats_to_search = []

    if chat:
        # Resolve chat names
        for chat_name in chat:
            username = resolve_username(chat_name, app.cache, app.db_dir)
            chats_to_search.append(username or chat_name)
    else:
        chats_to_search = [None]  # Search all

    for chat_username in chats_to_search:
        found = search_messages(
            cache=app.cache,
            db_dir=app.db_dir,
            keyword=keyword,
            chat_username=chat_username,
            limit=limit,
            msg_type=msg_type,
        )
        results.extend(found)

    # Sort by time and limit
    results.sort(key=lambda m: m.get("create_time", 0), reverse=True)
    results = results[:limit]

    if fmt == "text":
        if not results:
            click.echo(f"No messages found matching '{keyword}'.")
        else:
            lines = [f"Search results for '{keyword}' ({len(results)} matches):\n"]
            for msg in results:
                lines.append(format_message_text(msg))
            output("\n".join(lines), "text")
    else:
        output(results, fmt)
