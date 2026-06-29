"""very tool del — remove a Vix tool."""

import os
import shutil

import typer

from ..utils import Config, VIndexTool, _remove_readonly, console, parse_tool_name

del_app = typer.Typer()


@del_app.callback(invoke_without_command=True)
def delete(package: str = typer.Argument(..., help="工具包名")):
    """删除 Vix 工具"""
    parent = Config.VIX_TOOLS_PATH
    info = parse_tool_name(package, parent=parent)
    pack_path = info.pack_path

    if not pack_path.exists():
        console.print(f"[red]工具 {info.full_name} 未安装[/red]")
        raise typer.Exit(code=1)

    project_name = info.repo_name
    content = VIndexTool(pack_path).content()
    if content is not None:
        project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if os.name == "nt" else ""
    binary_path = parent / f"{project_name}{suffix}"

    console.print(f"[bold cyan]删除工具: {info.full_name}[/bold cyan]")

    if binary_path.exists():
        binary_path.unlink()
        typer.secho(f"已删除: {binary_path}", fg="green")

    shutil.rmtree(pack_path, onexc=_remove_readonly)
    typer.secho(f"已删除: {pack_path}", fg="green")

    for d in [pack_path.parent, pack_path.parent.parent]:
        if d.exists() and not any(d.iterdir()):
            d.rmdir()

    typer.secho(f"工具 {project_name} 已删除", fg="green")
