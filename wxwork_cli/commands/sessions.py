"""Recent conversation sessions list."""

import sqlite3

import click

from wxwork_cli.output.formatter import output, format_session_text


def _decode_bytes(val):
    """Decode bytes to string, handling binary data gracefully."""
    if isinstance(val, bytes):
        try:
            return val.decode('utf-8')
        except UnicodeDecodeError:
            return val.hex()
    return val


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
        conn.text_factory = bytes  # Handle binary data
        try:
            # Try common session table names
            # WXWork uses "conversation_table" instead of "SessionTable"
            for table_name in ["conversation_table", "SessionTable", "session", "sessions"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()

                    # Get column names to handle different schemas
                    cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
                    columns = {row[1] if isinstance(row[1], str) else row[1].decode() for row in cursor.fetchall()}

                    # Determine order column
                    order_col = None
                    for col in ["last_timestamp", "timestamp", "update_time", "last_message_time"]:
                        if col in columns:
                            order_col = col
                            break

                    if order_col:
                        cursor = conn.execute(
                            f"SELECT * FROM [{table_name}] ORDER BY [{order_col}] DESC LIMIT ?",
                            (limit,)
                        )
                    else:
                        cursor = conn.execute(
                            f"SELECT * FROM [{table_name}] LIMIT ?",
                            (limit,)
                        )

                    # Get column names from cursor description
                    col_names = [desc[0] if isinstance(desc[0], str) else desc[0].decode()
                                 for desc in cursor.description]

                    for row in cursor.fetchall():
                        row_dict = {}
                        for i, val in enumerate(row):
                            col_name = col_names[i] if i < len(col_names) else f"col_{i}"
                            row_dict[col_name] = _decode_bytes(val)
                        results.append(row_dict)
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
