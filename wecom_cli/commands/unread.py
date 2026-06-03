"""Unread session listing."""

import sqlite3

import click

from wecom_cli.output.formatter import output, format_session_text


@click.command("unread")
@click.option("--limit", default=20, help="Maximum sessions to show")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def unread(ctx, limit, fmt):
    """Show sessions with unread messages.

    Only displays sessions that have unread message counts > 0.
    """
    app = ctx.obj["app"]

    session_dbs = app.find_databases("session")
    if not session_dbs:
        session_dbs = app.find_databases("msg")

    results = []
    for db_path in session_dbs:
        decrypted = app.get_decrypted_db(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            for table_name in ["SessionTable", "session", "sessions"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()

                    # Query only unread sessions
                    cursor = conn.execute(
                        f"""SELECT * FROM [{table_name}]
                        WHERE unread_count > 0
                        ORDER BY last_timestamp DESC
                        LIMIT ?""",
                        (limit,)
                    )
                    results = [dict(row) for row in cursor.fetchall()]
                    break
                except sqlite3.OperationalError:
                    continue
        finally:
            conn.close()

    if fmt == "text":
        if not results:
            click.echo("No unread messages.")
        else:
            click.echo(f"Unread sessions ({len(results)}):\n")
            for session in results:
                click.echo(format_session_text(session))
    else:
        output(results, fmt)
