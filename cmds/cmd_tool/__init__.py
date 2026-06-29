import typer
from .install import add_app
from .delete import del_app
from .prune import prune_app
from .update import update_app
from .search import search_app

app = typer.Typer()
app.add_typer(add_app, name="add")
app.add_typer(del_app, name="del")
app.add_typer(prune_app, name="prune")
app.add_typer(update_app, name="update")
app.add_typer(search_app, name="search")
