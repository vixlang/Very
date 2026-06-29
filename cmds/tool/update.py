"""very tool update — update a Vix tool."""

import typer
from git import Repo

from ..utils import Config, console, parse_tool_name
from .install import install_tool

update_app = typer.Typer()


@update_app.callback(invoke_without_command=True)
def update(package: str = typer.Argument(..., help="工具包名")):
    """更新 Vix 工具"""
    parent = Config.VIX_TOOLS_PATH
    info = parse_tool_name(package, parent=parent)
    pack_path = info.pack_path

    if not pack_path.exists():
        typer.secho(f"工具 {info.full_name} 未安装，正在安装...", fg="cyan")
        install_tool(package)
        return

    console.print(f"[bold cyan]更新工具: {info.full_name}[/bold cyan]")
    try:
        repo = Repo(pack_path)
        origin = repo.remotes.origin
        origin.pull()
        typer.secho(f"已拉取最新代码: {pack_path}", fg="green")
    except Exception as e:
        console.print(f"[red]拉取失败: {e}[/red]")
        raise typer.Exit(code=1)

    typer.secho("正在重新编译...", fg="cyan")
    binary_path = install_tool(package)
    if binary_path is not None:
        typer.secho(f"工具 {info.full_name} 已更新", fg="green")
