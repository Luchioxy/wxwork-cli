"""Group members / department members."""

import click

from wecom_cli.core.groups import get_group_members
from wecom_cli.core.contacts import resolve_username, get_department_members
from wecom_cli.output.formatter import output, format_contact_text


@click.command("members")
@click.argument("group_name", required=False)
@click.option("--department", default=None, help="Department ID to list members of")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def members(ctx, group_name, department, fmt):
    """List members of a group chat or department.

    GROUP_NAME is the name of the group chat.
    Use --department to list members of a specific department instead.
    """
    app = ctx.obj["app"]

    if department:
        results = get_department_members(department, app.cache, app.db_dir)
    elif group_name:
        username = resolve_username(group_name, app.cache, app.db_dir)
        if not username:
            username = group_name
        results = get_group_members(username, app.cache, app.db_dir)
    else:
        click.echo("Please specify a group name or --department", err=True)
        return

    if fmt == "text":
        if not results:
            click.echo("No members found.")
        else:
            source = f"department {department}" if department else f"group '{group_name}'"
            lines = [f"Members of {source} ({len(results)}):\n"]
            for member in results:
                lines.append(format_contact_text(member))
            output("\n".join(lines), "text")
    else:
        output(results, fmt)
