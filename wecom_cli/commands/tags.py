"""Contact tag management."""

import sqlite3

import click

from wecom_cli.output.formatter import output


@click.command("tags")
@click.option("--list", "list_tags", is_flag=True, help="List all tags")
@click.option("--members", default=None, help="Show members with specific tag")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def tags(ctx, list_tags, members, fmt):
    """Manage contact tags/labels.

    Use --list to see all tags, --members to see contacts with a specific tag.
    """
    app = ctx.obj["app"]

    # Find tag database
    tag_dbs = app.find_databases("tag")
    if not tag_dbs:
        tag_dbs = app.find_databases("contact")

    results = []
    for db_path in tag_dbs:
        decrypted = app.get_decrypted_db(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            for table_name in ["tag", "Tag", "tags", "contact_tag"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()
                    if members:
                        cursor = conn.execute(
                            f"SELECT * FROM [{table_name}] WHERE name = ? OR tag_name = ?",
                            (members, members)
                        )
                    else:
                        cursor = conn.execute(f"SELECT * FROM [{table_name}]")
                    results = [dict(row) for row in cursor.fetchall()]
                    break
                except sqlite3.OperationalError:
                    continue
        finally:
            conn.close()

    if fmt == "text":
        if not results:
            click.echo("No tags found.")
        else:
            click.echo(f"Tags ({len(results)}):\n")
            for tag in results:
                name = tag.get("name", tag.get("tag_name", "unknown"))
                tag_id = tag.get("id", tag.get("tag_id", "?"))
                click.echo(f"  [{tag_id}] {name}")
    else:
        output(results, fmt)
