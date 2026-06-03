"""Chat statistics analysis."""

import click

from wecom_cli.core.messages import collect_chat_stats
from wecom_cli.core.contacts import resolve_username
from wecom_cli.output.formatter import output


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

    username = resolve_username(chat_name, app.cache, app.db_dir)
    if not username:
        username = chat_name

    result = collect_chat_stats(
        cache=app.cache,
        db_dir=app.db_dir,
        chat_username=username,
        start_time=start_time,
        end_time=end_time,
    )

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
