"""Built-in app listing."""

import click

from wxwork_cli.core.apps import list_apps
from wxwork_cli.output.formatter import output


@click.command("apps")
@click.option("--list", "list_all", is_flag=True, default=True, help="List all apps")
@click.option("--detail", default=None, help="Show detail for specific app")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def apps(ctx, list_all, detail, fmt):
    """List installed WeCom applications.

    Use --detail to view a specific app.
    """
    app = ctx.obj["app"]

    results = list_apps(app.cache, app.db_dir)

    if detail:
        filtered = [a for a in results if str(a.get("id", a.get("app_id", ""))) == str(detail)]
        if filtered:
            output(filtered[0], fmt)
        else:
            click.echo(f"App not found: {detail}", err=True)
        return

    if fmt == "text":
        if not results:
            click.echo("No apps found.")
        else:
            click.echo(f"Installed apps ({len(results)}):\n")
            for app_info in results:
                app_id = app_info.get("id", app_info.get("app_id", "?"))
                name = app_info.get("name", app_info.get("app_name", "unknown"))
                click.echo(f"  [{app_id}] {name}")
    else:
        output(results, fmt)
