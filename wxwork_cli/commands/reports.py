"""Daily/weekly report queries."""

import click

from wxwork_cli.core.apps import get_reports
from wxwork_cli.output.formatter import output


@click.command("reports")
@click.option("--type", "report_type", default="daily",
              type=click.Choice(["daily", "weekly"]),
              help="Report type")
@click.option("--date", default=None, help="Date filter (YYYY-MM-DD)")
@click.option("--user", default=None, help="Filter by user")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def reports(ctx, report_type, date, user, fmt):
    """Query daily/weekly reports.

    Use --type to select daily or weekly reports.
    """
    app = ctx.obj["app"]

    results = get_reports(
        app.cache, app.db_dir, report_type=report_type, date=date, username=user
    )

    if fmt == "text":
        if not results:
            click.echo("No reports found.")
        else:
            click.echo(f"{report_type.capitalize()} reports ({len(results)}):\n")
            for report in results:
                report_id = report.get("id", report.get("report_id", "?"))
                title = report.get("title", report.get("summary", "unknown"))
                user_name = report.get("user", report.get("username", "unknown"))
                date_val = report.get("date", report.get("report_date", "?"))
                click.echo(f"  [{report_id}] {title} by {user_name} ({date_val})")
    else:
        output(results, fmt)
