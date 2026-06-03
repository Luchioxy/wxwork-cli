"""Incremental new message detection (stateful)."""

import json
import os
import sqlite3

import click

from wxwork_cli.core.config import STATE_DIR
from wxwork_cli.core.messages import _parse_message_row
from wxwork_cli.output.formatter import output, format_message_text


LAST_CHECK_FILE = os.path.join(STATE_DIR, "last_check.json")


def _load_last_check() -> dict:
    """Load the last check state."""
    if os.path.exists(LAST_CHECK_FILE):
        try:
            with open(LAST_CHECK_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_timestamp": 0, "seen_ids": []}


def _save_last_check(state: dict) -> None:
    """Save the last check state."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


@click.command("new-messages")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def new_messages(ctx, fmt):
    """Show new messages since last check (stateful).

    Tracks state in ~/.wecom-cli/last_check.json.
    Each call returns only messages newer than the last check.
    """
    app = ctx.obj["app"]

    state = _load_last_check()
    last_ts = state.get("last_timestamp", 0)
    seen_ids = set(state.get("seen_ids", []))

    # Find message databases
    msg_dbs = app.find_databases("msg")
    if not msg_dbs:
        msg_dbs = app.find_databases("message")

    new_msgs = []
    max_ts = last_ts

    for db_path in msg_dbs:
        decrypted = app.get_decrypted_db(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        try:
            # Find all message tables
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table_name in tables:
                try:
                    # Get column names
                    cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
                    columns = [row[1] for row in cursor.fetchall()]

                    # Query new messages
                    cursor = conn.execute(
                        f"SELECT * FROM [{table_name}] WHERE create_time > ? ORDER BY create_time",
                        (last_ts,)
                    )
                    for row in cursor.fetchall():
                        msg = {}
                        for i, col in enumerate(columns):
                            if i < len(row):
                                msg[col] = row[i]

                        msg_id = f"{table_name}_{msg.get('local_id', msg.get('msg_id', ''))}"
                        if msg_id not in seen_ids:
                            parsed = _parse_message_row(row, columns)
                            parsed["_table"] = table_name
                            new_msgs.append(parsed)
                            seen_ids.add(msg_id)

                            ts = msg.get("create_time", 0)
                            if ts > max_ts:
                                max_ts = ts
                except sqlite3.OperationalError:
                    continue
        finally:
            conn.close()

    # Update state
    if max_ts > last_ts:
        state["last_timestamp"] = max_ts
        state["seen_ids"] = list(seen_ids)[-1000:]  # Keep last 1000 IDs
        _save_last_check(state)

    # Sort by time
    new_msgs.sort(key=lambda m: m.get("create_time", 0))

    if fmt == "text":
        if not new_msgs:
            click.echo("No new messages.")
        else:
            click.echo(f"New messages ({len(new_msgs)}):\n")
            for msg in new_msgs:
                click.echo(format_message_text(msg))
    else:
        output(new_msgs, fmt)
