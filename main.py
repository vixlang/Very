import typer

from cmds.cmd_add import app as add_app
from cmds.cmd_build import app as build_app
from cmds.cmd_del import app as del_app
from cmds.cmd_exe import exe
from cmds.cmd_good import app as good_app
from cmds.cmd_init import app as init_app
from cmds.cmd_install import app as install_app
from cmds.cmd_list import app as list_app
from cmds.cmd_prune import app as prune_app
from cmds.cmd_run import app as run_app
from cmds.cmd_search import app as search_app
from cmds.cmd_tool import app as tool_app
from cmds.cmd_update import app as update_app
from cmds.utils import console

app = typer.Typer(name="very", help="Vix 项目管理与构建工具")
app.add_typer(add_app, name="add")
app.add_typer(build_app, name="build")
app.add_typer(del_app, name="del")
app.add_typer(good_app, name="good")
app.add_typer(init_app, name="init")
app.add_typer(install_app, name="install")
app.add_typer(list_app, name="list")
app.add_typer(prune_app, name="prune")
app.add_typer(run_app, name="run")
app.add_typer(search_app, name="search")
app.add_typer(tool_app, name="tool")
app.add_typer(update_app, name="update")
app.command(
    "exe",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
)(exe)


def _version_callback(value: bool):
    if value:
        from importlib.metadata import version as get_version

        ver = get_version("very")
        from rich.panel import Panel

        text = f"[bold cyan]Very[/bold cyan] [bold green]v{ver}[/bold green]\nVix [yellow]项目管理与构建工具[/yellow]"
        console.print(Panel(text, border_style="cyan"))
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="显示版本号", callback=_version_callback
    ),
):
    pass


def entry():
    app()


if __name__ == "__main__":
    entry()
