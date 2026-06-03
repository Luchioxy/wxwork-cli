"""Approval workflow queries."""

import click

from wxwork_cli.core.apps import get_approval_list
from wxwork_cli.output.formatter import output


@click.command("approval")
@click.option("--status", default="all",
              type=click.Choice(["pending", "approved", "rejected", "all"]),
              help="Filter by status")
@click.option("--limit", default=50, help="Maximum results")
@click.option("--detail", default=None, help="Show detail for specific approval")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def approval(ctx, status, limit, detail, fmt):
    """Query approval workflows.

    Use --status to filter by approval status.
    Use --detail to view a specific approval.
    """
    app = ctx.obj["app"]

    results = get_approval_list(app.cache, app.db_dir, status=status, limit=limit)

    if detail:
        filtered = [a for a in results if str(a.get("id", a.get("approval_id", ""))) == str(detail)]
        if filtered:
            output(filtered[0], fmt)
        else:
            click.echo(f"Approval not found: {detail}", err=True)
        return

    if fmt == "text":
        if not results:
            click.echo("No approvals found.")
        else:
            click.echo(f"Approvals ({len(results)}):\n")
            for approval_item in results:
                approval_id = approval_item.get("id", approval_item.get("approval_id", "?"))
                title = approval_item.get("title", approval_item.get("name", "unknown"))
                status_val = approval_item.get("status", "?")
                click.echo(f"  [{approval_id}] {title} (status: {status_val})")
    else:
        output(results, fmt)
