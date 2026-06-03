"""Contact list, search, and detail view."""

import click

from wxwork_cli.core.contacts import get_contact_full, search_contacts, get_contact_detail
from wxwork_cli.output.formatter import output, format_contact_text


@click.command("contacts")
@click.option("--query", default=None, help="Search contacts by name/userid")
@click.option("--detail", default=None, help="Show detail for specific contact")
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
        contact = get_contact_detail(detail, app.cache, app.db_dir)
        if not contact:
            click.echo(f"Contact not found: {detail}", err=True)
            return
        output(contact, fmt)
        return

    if query:
        results = search_contacts(query, app.cache, app.db_dir)
    else:
        results = get_contact_full(app.cache, app.db_dir)

    # Apply filters
    if department:
        results = [c for c in results if str(c.get("department_id", "")) == str(department)]

    if tag:
        # Filter by tag - contacts may have tags field or be in a separate tag table
        results = [
            c for c in results
            if tag.lower() in str(c.get("tags", c.get("tag", ""))).lower()
        ]

    results = results[:limit]

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
