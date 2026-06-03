"""Contact list, search, and detail view."""

import sqlite3

import click

from wxwork_cli.output.formatter import output, format_contact_text


def _get_contacts_from_db(cache, db_dir, query=None, department=None, tag=None, limit=50):
    """Get contacts from user.db database."""
    results = []

    # Find user database
    user_dbs = []
    import os
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f == "user.db":
                user_dbs.append(os.path.join(root, f))

    for db_path in user_dbs:
        decrypted = cache.get(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.text_factory = bytes
        try:
            # Build query
            sql = "SELECT id, name, english_name, position, avator_url FROM user_table"
            conditions = []
            params = []

            if query:
                conditions.append("(name LIKE ? OR english_name LIKE ? OR CAST(id AS TEXT) LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += f" LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                user_id, name, english_name, position, avator_url = row

                def decode(val):
                    if isinstance(val, bytes):
                        try:
                            return val.decode('utf-8')
                        except:
                            return val.hex()
                    return val

                results.append({
                    'id': user_id,
                    'name': decode(name),
                    'english_name': decode(english_name),
                    'position': decode(position),
                    'avator_url': decode(avator_url),
                })
        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    return results


def _get_contact_detail(user_id, cache, db_dir):
    """Get contact detail from user.db database."""
    import os

    # Find user database
    user_dbs = []
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f == "user.db":
                user_dbs.append(os.path.join(root, f))

    for db_path in user_dbs:
        decrypted = cache.get(db_path)
        if not decrypted:
            continue

        conn = sqlite3.connect(f"file:{decrypted}?mode=ro", uri=True)
        conn.text_factory = bytes
        try:
            cursor = conn.execute(
                "SELECT id, name, english_name, position, avator_url, department_id FROM user_table WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                user_id, name, english_name, position, avator_url, dept_id = row

                def decode(val):
                    if isinstance(val, bytes):
                        try:
                            return val.decode('utf-8')
                        except:
                            return val.hex()
                    return val

                return {
                    'id': user_id,
                    'name': decode(name),
                    'english_name': decode(english_name),
                    'position': decode(position),
                    'avator_url': decode(avator_url),
                    'department_id': dept_id,
                }
        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    return None


@click.command("contacts")
@click.option("--query", default=None, help="Search contacts by name/userid")
@click.option("--detail", default=None, help="Show detail for specific contact (user ID)")
@click.option("--department", default=None, help="Filter by department ID")
@click.option("--tag", default=None, help="Filter by tag name")
@click.option("--limit", default=50, help="Maximum results")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def contacts(ctx, query, detail, department, tag, limit, fmt):
    """Search and view contacts.

    Without arguments, lists all contacts. Use --query to search,
    --detail to view a specific contact.
    """
    app = ctx.obj["app"]

    if detail:
        # Try to parse as user ID
        try:
            user_id = int(detail)
        except ValueError:
            # Search by name
            results = _get_contacts_from_db(app.cache, app.db_dir, query=detail, limit=1)
            if results:
                output(results[0], fmt)
            else:
                click.echo(f"Contact not found: {detail}", err=True)
            return

        contact = _get_contact_detail(user_id, app.cache, app.db_dir)
        if not contact:
            click.echo(f"Contact not found: {detail}", err=True)
            return
        output(contact, fmt)
        return

    results = _get_contacts_from_db(
        app.cache, app.db_dir,
        query=query,
        department=department,
        tag=tag,
        limit=limit
    )

    if fmt == "text":
        if not results:
            click.echo("No contacts found.")
        else:
            lines = [f"Contacts ({len(results)}):\n"]
            for contact in results:
                lines.append(format_contact_text(contact))
            output("\n".join(lines), "text")
    else:
        output(results, fmt)
