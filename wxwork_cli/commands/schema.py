"""Database schema inspection tool (developer tool)."""

import click

from wxwork_cli.data.schema_probe import probe_database, list_tables, describe_table, sample_rows
from wxwork_cli.output.formatter import output


@click.command("schema")
@click.option("--db", "db_name", default=None, help="Database name filter")
@click.option("--table", default=None, help="Specific table to inspect")
@click.option("--sample", is_flag=True, help="Include sample rows")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def schema(ctx, db_name, table, sample, fmt):
    """Inspect database schema (developer tool).

    Use to discover WXWork's database structure.
    """
    app = ctx.obj["app"]

    if table and db_name:
        # Show specific table details
        db_files = app.find_databases(db_name)
        if not db_files:
            click.echo(f"No database found matching '{db_name}'", err=True)
            return

        for db_path in db_files:
            decrypted = app.get_decrypted_db(db_path)
            if not decrypted:
                continue

            columns = describe_table(decrypted, table)
            if not columns:
                continue

            result = {
                "database": db_path,
                "table": table,
                "columns": columns,
            }

            if sample:
                result["sample"] = sample_rows(decrypted, table, limit=5)

            output(result, fmt)
            return

        click.echo(f"Table '{table}' not found in any '{db_name}' database", err=True)

    elif db_name:
        # Show tables in specific database
        db_files = app.find_databases(db_name)
        if not db_files:
            click.echo(f"No database found matching '{db_name}'", err=True)
            return

        results = []
        for db_path in db_files:
            decrypted = app.get_decrypted_db(db_path)
            if not decrypted:
                continue

            tables = list_tables(decrypted)
            for t in tables:
                t["database"] = db_path
            results.extend(tables)

        output(results, fmt)

    else:
        # Show all databases with full probe
        db_files = app.find_databases()
        if not db_files:
            click.echo("No databases found.", err=True)
            return

        results = []
        for db_path in db_files:
            decrypted = app.get_decrypted_db(db_path)
            if not decrypted:
                continue

            probe = probe_database(decrypted)
            results.append(probe)

        output(results, fmt)
