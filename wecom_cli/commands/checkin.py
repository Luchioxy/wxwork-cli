"""Check-in/attendance records."""

import click

from wecom_cli.core.apps import get_checkin_records
from wecom_cli.output.formatter import output


@click.command("checkin")
@click.option("--date", default=None, help="Date (YYYY-MM-DD), defaults to today")
@click.option("--range", "range_days", default=1, help="Number of days to query")
@click.option("--user", default=None, help="Filter by user")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def checkin(ctx, date, range_days, user, fmt):
    """Query check-in/attendance records.

    Use --date to specify a date, --user to filter by user.
    """
    app = ctx.obj["app"]

    results = get_checkin_records(
        app.cache, app.db_dir, date=date, range_days=range_days, username=user
    )

    if fmt == "text":
        if not results:
            click.echo("No check-in records found.")
        else:
            click.echo(f"Check-in records ({len(results)}):\n")
            for record in results:
                user_name = record.get("user", record.get("username", "unknown"))
                check_time = record.get("time", record.get("checkin_time", "?"))
                location = record.get("location", "")
                click.echo(f"  {user_name} - {check_time} {location}")
    else:
        output(results, fmt)
