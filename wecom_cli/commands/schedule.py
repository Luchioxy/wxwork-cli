"""Calendar/schedule queries."""

import click

from wecom_cli.core.apps import get_schedule_list
from wecom_cli.output.formatter import output


@click.command("schedule")
@click.option("--date", default=None, help="Date (YYYY-MM-DD), defaults to today")
@click.option("--range", "range_days", default=7, help="Number of days to look ahead")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def schedule(ctx, date, range_days, fmt):
    """Query calendar/schedule events.

    Use --date to specify a start date, --range for number of days.
    """
    app = ctx.obj["app"]

    results = get_schedule_list(app.cache, app.db_dir, date=date, range_days=range_days)

    if fmt == "text":
        if not results:
            click.echo("No schedule events found.")
        else:
            click.echo(f"Schedule events ({len(results)}):\n")
            for event in results:
                event_id = event.get("id", event.get("event_id", "?"))
                title = event.get("title", event.get("summary", "unknown"))
                start_time = event.get("start_time", event.get("dtstart", "?"))
                click.echo(f"  [{event_id}] {title} ({start_time})")
    else:
        output(results, fmt)
