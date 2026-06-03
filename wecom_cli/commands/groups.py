"""Group chat management."""

import click

from wecom_cli.core.groups import list_groups
from wecom_cli.output.formatter import output


@click.command("groups")
@click.option("--query", default=None, help="Search groups by name")
@click.option("--limit", default=50, help="Maximum results")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def groups(ctx, query, limit, fmt):
    """List group chats.

    Use --query to search groups by name.
    """
    app = ctx.obj["app"]

    results = list_groups(app.cache, app.db_dir)

    if query:
        query_lower = query.lower()
        results = [
            g for g in results
            if query_lower in str(g.get("name", g.get("chatroom_name", ""))).lower()
        ]

    results = results[:limit]

    if fmt == "text":
        if not results:
            click.echo("No groups found.")
        else:
            click.echo(f"Groups ({len(results)}):\n")
            for group in results:
                name = group.get("name", group.get("chatroom_name", "unknown"))
                members_count = group.get("member_count", "?")
                click.echo(f"  {name} ({members_count} members)")
    else:
        output(results, fmt)
