"""Department hierarchy listing."""

import click

from wecom_cli.core.departments import get_department_tree, list_departments, build_department_tree
from wecom_cli.output.formatter import output


@click.command("departments")
@click.option("--parent", default=None, help="Parent department ID (0 for root)")
@click.option("--tree", is_flag=True, help="Show full tree structure")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def departments(ctx, parent, tree, fmt):
    """List department hierarchy.

    Use --parent to list children of a specific department.
    Use --tree to show the full hierarchical structure.
    """
    app = ctx.obj["app"]

    all_depts = get_department_tree(app.cache, app.db_dir)

    if tree:
        result = build_department_tree(all_depts)
    elif parent is not None:
        result = list_departments(parent, app.cache, app.db_dir)
    else:
        result = all_depts

    if fmt == "text":
        if not result:
            click.echo("No departments found.")
        elif tree:
            _print_dept_tree(result)
        else:
            for dept in result:
                dept_id = dept.get("id", dept.get("dept_id", "?"))
                name = dept.get("name", dept.get("dept_name", "unknown"))
                parent_id = dept.get("parent_id", dept.get("parentid", ""))
                click.echo(f"  [{dept_id}] {name} (parent: {parent_id})")
    else:
        output(result, fmt)


def _print_dept_tree(tree, indent=0):
    """Print department tree in text format."""
    for dept in tree:
        name = dept.get("name", dept.get("dept_name", "unknown"))
        dept_id = dept.get("id", dept.get("dept_id", "?"))
        click.echo(f"{'  ' * indent}[{dept_id}] {name}")
        children = dept.get("children", [])
        if children:
            _print_dept_tree(children, indent + 1)
