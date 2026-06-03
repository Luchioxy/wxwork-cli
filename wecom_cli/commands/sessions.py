"""Recent conversation sessions list."""

import sqlite3

import click

from wecom_cli.output.formatter import output, format_session_text


@click.command("sessions")
@click.option("--limit", default=20, help="Maximum sessions to show")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def sessions(ctx, limit, fmt):
    """List recent chat sessions with unread counts and last message."""
    app = ctx.obj["app"]

    # Find session database
    session_dbs = app.find_databases("session")
    if not session_dbs:
        # Try to find in msg databases
        session_dbs = app.find_databases("msg")

    results = []
    for db_path in session_dbs:
        decrypted = app.get_decrypted_db(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # Try common session table names
            for table_name in ["SessionTable", "session", "sessions"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()
                    cursor = conn.execute(
                        f"SELECT * FROM [{table_name}] ORDER BY last_timestamp DESC LIMIT ?",
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
            click.echo("No sessions found.")
        else:
            lines = [f"Recent sessions ({len(results)}):\n"]
            for s in results:
                lines.append(format_session_text(s))
            output("\n".join(lines), "text")
    else:
        output(results, fmt)
