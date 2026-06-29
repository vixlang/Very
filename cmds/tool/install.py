"""very tool add — install Vix tools."""

import os
import sys
from pathlib import Path

import typer
from git import Repo

from ..installer import GitProgress
from ..share import _get_entrypoint, log
from ..utils import (
    Config,
    VIndexTool,
    create_git_progress,
    parse_tool_name,
)

add_app = typer.Typer()


def install_tool(packname: str, parent: Path | None = None) -> Path | None:
    import shutil

    if parent is None:
        parent = Config.VIX_TOOLS_PATH

    info = parse_tool_name(packname, parent=parent)
    pack_path = info.pack_path

    if not pack_path.exists():
        log.info(f"安装工具: {info.full_name}")
        log.info(f"源: {info.git_url}")
        if info.branch_name:
            log.info(f"分支: {info.branch_name}")

        with create_git_progress(info.full_name) as progress:
            git_progress = GitProgress(progress, info.full_name)
            try:
                Repo.clone_from(
                    info.git_url,
                    pack_path,
                    branch=info.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                if pack_path.exists():
                    shutil.rmtree(pack_path, ignore_errors=True)
                log.error(f"克隆失败: {e}")
                return None
    else:
        log.info(f"工具 {info.full_name} 已存在，重新编译")

    content = VIndexTool(pack_path).content()
    if content is None:
        log.error(f"{info.full_name} 缺少 vindex.toml")
        return None

    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (parent / binary_name).resolve()

    log.info(f"正在编译 {project_name} ...")
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    from .. import cmd_build

    old_cwd = Path.cwd()
    os.chdir(str(pack_path))
    try:
        input_file, _ = cmd_build._extract_input_file([])
        if input_file is None:
            entry = _get_entrypoint()
            cand = Path(entry).resolve()
            if cand.exists():
                input_file = cand
        if input_file:
            root_dir = Path(".").resolve()
            temp_dir = Path(".vix/temp").resolve()
            temp_dir.mkdir(parents=True, exist_ok=True)
            if cmd_build._has_gcc():
                code, obj_path = cmd_build._compile_to_obj(
                    input_file, [], root_dir, temp_dir, silent=True
                )
                if code == 0:
                    code = cmd_build._link_with_gcc(
                        obj_path, str(binary_path), silent=True
                    )
            else:
                code = cmd_build._compile_direct(
                    input_file, ["-o", str(binary_path)], root_dir, silent=True
                )
        else:
            code = 1
    finally:
        os.chdir(str(old_cwd))

    if not binary_path.exists():
        log.error(f"编译产物 {binary_name} 未生成")
        return None

    log.ok(f"工具 {project_name} 已安装: {binary_path}")
    return binary_path


@add_app.callback(invoke_without_command=True)
def add(package: str = typer.Argument(..., help="工具包名")):
    """安装 Vix 工具"""
    install_tool(package)
