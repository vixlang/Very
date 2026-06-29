import shutil
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from .share import log
from .share import _remove_readonly
from .utils import (
    Config,
    build_dep_tree,
    console,
    iter_empty_dirs,
    iter_package_dirs,
)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def prune(
    empty_only: bool = typer.Option(False, "--empty-only", help="只删除空目录"),
    invalid_only: bool = typer.Option(
        False, "--invalid-only", help="只删除没有vindex.toml的包"
    ),
    unused: bool = typer.Option(False, "--unused", help="只删除不被引用的孤立包"),
):
    """删除没有vindex.toml的包"""
    libs_path = Config.local_libs_path()

    if not libs_path.exists():
        log.error("包目录不存在!")
        raise typer.Exit(code=1)
    if not libs_path.is_dir():
        log.error("包路径不是目录!")
        raise typer.Exit(code=1)

    removed_packages = []
    removed_dirs = []
    unused_packages = []

    if not empty_only:
        for _, _, repo_dir, package_name in iter_package_dirs(libs_path):
            vindex_file = repo_dir / "vindex.toml"
            if not vindex_file.exists():
                removed_packages.append(package_name)
                log.warn(f"无效包: {package_name}")
                shutil.rmtree(repo_dir, onexc=_remove_readonly)

    if not invalid_only:
        for empty_dir in iter_empty_dirs(libs_path):
            rel = empty_dir.relative_to(libs_path)
            removed_dirs.append(str(rel))
            empty_dir.rmdir()
            log.info(f"清理空目录: [dim]{rel}[/dim]")

    if not empty_only and not invalid_only or unused:
        unused_packages = _remove_unused(libs_path)

    _print_summary(
        removed_packages,
        removed_dirs,
        unused_packages,
        empty_only,
        invalid_only,
        unused,
    )


def _remove_unused(libs_path: Path) -> list[str]:
    vindex_path = Path.cwd() / "vindex.toml"
    root_deps: list[str] = []
    if vindex_path.exists():
        import tomllib

        with open(vindex_path, "rb") as f:
            data = tomllib.load(f)
        root_deps = data.get("project", {}).get("deps", [])
        legacy = list(data.get("dependencies", {}).keys())
        root_deps = list(dict.fromkeys(root_deps + legacy))

    log.info("构建依赖树...")
    referenced = build_dep_tree(libs_path, root_deps)

    unused: list[str] = []
    for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
        if full_name not in referenced:
            unused.append(full_name)

    if unused:
        log.warn(f"发现 {len(unused)} 个孤立包: [dim]{', '.join(unused)}[/dim]")
        from .utils import ask_confirm

        if ask_confirm("是否删除这些孤立包?", default=False):
            for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
                if full_name in unused:
                    shutil.rmtree(repo_dir, onexc=_remove_readonly)
                    log.ok(f"已删除孤立包: {full_name}")
            return unused
    else:
        log.info("没有孤立包")

    return []


def _print_summary(
    packages, dirs, unused, empty_only: bool, invalid_only: bool, unused_only: bool
):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("label", style="cyan")
    table.add_column("value", style="bold white")

    if empty_only:
        table.add_row("清理的空目录数", str(len(dirs)))
    elif invalid_only:
        table.add_row("删除的无效包数", str(len(packages)))
    elif unused_only:
        table.add_row("删除的孤立包数", str(len(unused)))
    else:
        if packages:
            table.add_row("删除的无效包数", str(len(packages)))
        if dirs:
            table.add_row("清理的空目录数", str(len(dirs)))
        if unused:
            table.add_row("删除的孤立包数", str(len(unused)))

    total = len(packages) + len(dirs) + len(unused)
    table.add_row("合计", f"[green]{total}[/green]")

    console.print(Panel(table, title=" 清理完成 ", border_style="green"))
