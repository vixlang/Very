"""very tool update — update a Vix tool."""

import typer
from git import Repo

from ..share import log
from ..utils import Config, parse_tool_name
from .install import install_tool

update_app = typer.Typer()


@update_app.callback(invoke_without_command=True)
def update(package: str = typer.Argument(..., help="工具包名")):
    """更新 Vix 工具"""
    parent = Config.VIX_TOOLS_PATH
    info = parse_tool_name(package, parent=parent)
    pack_path = info.pack_path

    if not pack_path.exists():
        log.info(f"工具 {info.full_name} 未安装，正在安装...")
        install_tool(package)
        return

    log.info(f"更新工具: {info.full_name}")
    try:
        repo = Repo(pack_path)
        origin = repo.remotes.origin
        origin.pull()
        log.ok(f"已拉取最新代码: {pack_path}")
    except Exception as e:
        log.error(f"拉取失败: {e}")
        raise typer.Exit(code=1)

    log.info("正在重新编译...")
    binary_path = install_tool(package)
    if binary_path is not None:
        log.ok(f"工具 {info.full_name} 已更新")
