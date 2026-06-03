"""Bookmarked/favorited items."""

import sqlite3

import click

from wecom_cli.output.formatter import output


@click.command("favorites")
@click.option("--limit", default=50, help="Maximum results")
@click.option("--type", "fav_type", default=None,
              type=click.Choice(["text", "image", "file", "link", "card"]),
              help="Filter by favorite type")
@click.option("--query", default=None, help="Search favorites")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def favorites(ctx, limit, fav_type, query, fmt):
    """View saved favorites/collections.

    Use --type to filter by favorite type, --query to search.
    """
    app = ctx.obj["app"]

    # Find favorites database
    fav_dbs = app.find_databases("fav")
    if not fav_dbs:
        fav_dbs = app.find_databases("favorite")

    results = []
    for db_path in fav_dbs:
        decrypted = app.get_decrypted_db(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            for table_name in ["fav_db_item", "favorite", "favorites"]:
                try:
                    cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    cursor.fetchone()

                    conditions = []
                    params = []

                    if fav_type:
                        conditions.append("type = ?")
                        params.append(fav_type)

                    if query:
                        conditions.append("content LIKE ?")
                        params.append(f"%{query}%")

                    query_sql = f"SELECT * FROM [{table_name}]"
                    if conditions:
                        query_sql += " WHERE " + " AND ".join(conditions)
                    query_sql += f" ORDER BY rowid DESC LIMIT {limit}"

                    cursor = conn.execute(query_sql, params)
                    results = [dict(row) for row in cursor.fetchall()]
                    break
                except sqlite3.OperationalError:
                    continue
        finally:
            conn.close()

    if fmt == "text":
        if not results:
            click.echo("No favorites found.")
        else:
            click.echo(f"Favorites ({len(results)}):\n")
            for fav in results:
                fav_id = fav.get("id", fav.get("fav_id", "?"))
                fav_type = fav.get("type", "unknown")
                content = fav.get("content", "")[:80]
                click.echo(f"  [{fav_id}] ({fav_type}) {content}")
    else:
        output(results, fmt)
