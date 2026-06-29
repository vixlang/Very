"""very tool — manage Vix tools."""

import typer

from .delete import del_app
from .install import add_app, install_tool
from .search import search_app
from .update import update_app

app = typer.Typer()
app.add_typer(add_app, name="add")
app.add_typer(del_app, name="del")
app.add_typer(update_app, name="update")
app.add_typer(search_app, name="search")

__all__ = ["app", "install_tool"]
