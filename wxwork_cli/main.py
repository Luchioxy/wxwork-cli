"""WXWork CLI - Enterprise WeChat local data query tool for LLMs and developers.

Main entry point with Click group and command registration.
"""

import sys

import click

from wxwork_cli import __version__


@click.group()
@click.version_option(version=__version__, prog_name="wxwork-cli")
@click.option(
    "--config", "config_path",
    default=None,
    envvar="WXWORK_CLI_CONFIG",
    help="Path to config file (default: ~/.wxwork-cli/config.json)"
)
@click.pass_context
def cli(ctx, config_path):
    """WXWork CLI - Query enterprise WeChat data from the terminal.

    AI-first design: all commands output JSON by default.
    Use --format text for human-readable output.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path

    # Skip context initialization for init and version commands
    if ctx.invoked_subcommand in ("init", "version", None):
        return

    # Initialize app context
    try:
        from wxwork_cli.core.context import AppContext
        ctx.obj["app"] = AppContext(config_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error initializing: {e}", err=True)
        sys.exit(1)


# Import and register commands
from wxwork_cli.commands.init import init
from wxwork_cli.commands.sessions import sessions
from wxwork_cli.commands.history import history
from wxwork_cli.commands.search import search
from wxwork_cli.commands.contacts import contacts
from wxwork_cli.commands.departments import departments
from wxwork_cli.commands.members import members
from wxwork_cli.commands.groups import groups
from wxwork_cli.commands.tags import tags
from wxwork_cli.commands.schema import schema
from wxwork_cli.commands.stats import stats
from wxwork_cli.commands.export import export
from wxwork_cli.commands.favorites import favorites
from wxwork_cli.commands.unread import unread
from wxwork_cli.commands.new_messages import new_messages
from wxwork_cli.commands.apps import apps
from wxwork_cli.commands.approval import approval
from wxwork_cli.commands.schedule import schedule
from wxwork_cli.commands.checkin import checkin
from wxwork_cli.commands.reports import reports

cli.add_command(init)
cli.add_command(sessions)
cli.add_command(history)
cli.add_command(search)
cli.add_command(contacts)
cli.add_command(departments)
cli.add_command(members)
cli.add_command(groups)
cli.add_command(tags)
cli.add_command(schema)
cli.add_command(stats)
cli.add_command(export)
cli.add_command(favorites)
cli.add_command(unread)
cli.add_command(new_messages)
cli.add_command(apps)
cli.add_command(approval)
cli.add_command(schedule)
cli.add_command(checkin)
cli.add_command(reports)


@cli.command()
def version():
    """Show version information."""
    click.echo(f"wxwork-cli {__version__}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
