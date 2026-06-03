"""Chat statistics analysis."""

import click

from wxwork_cli.core.messages import collect_chat_stats, get_user_names
from wxwork_cli.core.contacts import resolve_username
from wxwork_cli.output.formatter import output


@click.command("stats")
@click.argument("chat_name")
@click.option("--start-time", default=None, help="Start time (YYYY-MM-DD)")
@click.option("--end-time", default=None, help="End time (YYYY-MM-DD)")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def stats(ctx, chat_name, start_time, end_time, fmt):
    """Show chat statistics.

    CHAT_NAME is the name of the chat to analyze.
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
    result = None
    for user_id in user_ids:
        result = collect_chat_stats(
            cache=app.cache,
            db_dir=app.db_dir,
            chat_username=str(user_id),
            start_time=start_time,
            end_time=end_time,
            user_names=user_names,
        )
        if result["total_messages"] > 0:
            break

    if fmt == "text":
        click.echo(f"Statistics for '{chat_name}':\n")
        click.echo(f"  Total messages: {result['total_messages']}")

        if result["type_breakdown"]:
            click.echo("\n  Message types:")
            for msg_type, count in sorted(result["type_breakdown"].items(), key=lambda x: -x[1]):
                click.echo(f"    {msg_type}: {count}")

        if result["top_senders"]:
            click.echo("\n  Top senders:")
            for sender, count in sorted(result["top_senders"].items(), key=lambda x: -x[1])[:10]:
                click.echo(f"    {sender}: {count}")

        if result["hourly_activity"]:
            click.echo("\n  Hourly activity:")
            for hour in range(24):
                count = result["hourly_activity"].get(str(hour), 0)
                bar = "█" * min(count, 50)
                click.echo(f"    {hour:02d}:00 {bar} {count}")
    else:
        output(result, fmt)
