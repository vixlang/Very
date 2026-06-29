import shutil
from pathlib import Path

import typer
from rich.panel import Panel

from .installer import PackageInstaller
from .utils import (
    Config,
    _remove_readonly,
    add_dep_to_vindex,
    ask_confirm,
    console,
    err_console,
    parse_pack_name,
)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def add(
    package: str = typer.Argument(..., help="需要添加的包名"),
    global_: bool = typer.Option(
        False, "-g", "--global", help="全局安装到 VIX_HOME 目录"
    ),
    local: bool = typer.Option(
        False, "-l", "--local", help="强制在项目 .vix 目录下载（即使全局已存在）"
    ),
):
    """添加包(需要git)"""
    packname = package
    global_install = global_
    local_force = local

    if not global_install:
        vindex_path = Path.cwd() / "vindex.toml"
        if not vindex_path.exists():
            err_console.print()
            err_console.print(
                Panel(
                    "[bold red]未找到 vindex.toml[/bold red]\n\n"
                    "[yellow]请在项目根目录下运行此命令[/yellow]\n\n"
                    "[dim]提示: 使用 [white]very init <name>[/white] 初始化项目，\n"
                    "或使用 [white]very add -g <package>[/white] 进行全局安装[/dim]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            err_console.print()
            raise typer.Exit(code=1)

    if global_install:
        parent = Config.VIX_LIBS_PATH
    else:
        parent = Config.local_libs_path()

    packinfo = parse_pack_name(packname, parent=parent)

    if not global_install and not local_force:
        global_packinfo = parse_pack_name(packname, parent=Config.VIX_LIBS_PATH)
        if global_packinfo.pack_path.exists():
            added = add_dep_to_vindex(packname)
            if added:
                typer.secho(
                    f"已添加 {packinfo.full_name} 到 deps (使用全局副本)", fg="green"
                )
            else:
                typer.secho(f"deps 中已存在: {packname}", fg="cyan")
            return

    pack_path = packinfo.pack_path

    if pack_path.exists():
        console.print()
        console.print(
            Panel(
                f"[bold yellow]包已存在: [white]{packinfo.full_name}[/white][/bold yellow]\n\n"
                f"[dim]该包已经安装在以下位置:[/dim]\n"
                f"  [cyan]{pack_path}[/cyan]\n\n"
                f"[yellow]操作选项:[/yellow]",
                title="[bold]⚠ 提示[/bold]",
                border_style="yellow",
                padding=(1, 2),
            )
        )

        if not ask_confirm("是否覆盖现有包?", default=False):
            typer.secho("已取消操作", fg="yellow")
            console.print()
            return

        shutil.rmtree(pack_path, onexc=_remove_readonly)
        typer.secho(f"已删除旧版本的包 {packinfo.full_name}", fg="green")
        console.print()

    console.print(f"[bold cyan]添加包: {packinfo.full_name}[/bold cyan]")
    typer.secho(f"源: {packinfo.git_url}", fg="cyan")
    if packinfo.branch_name:
        typer.secho(f"分支: {packinfo.branch_name}", fg="cyan")

    result = PackageInstaller.install_one(packname, parent=parent)

    if not result.success:
        if result.no_vindex:
            console.print()
            console.print(
                Panel(
                    f"[bold yellow]包缺少 vindex.toml: [white]{packinfo.full_name}[/white][/bold yellow]\n\n"
                    f"[dim]该目录已被下载但缺少必要的 vindex.toml 文件。[/dim]\n\n"
                    f"[yellow]操作选项:[/yellow]",
                    title="[bold]⚠ 警告[/bold]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
            if ask_confirm("是否删除此不完整的包?", default=True):
                shutil.rmtree(pack_path, onexc=_remove_readonly)
                typer.secho(f"已删除不完整的包 {packinfo.full_name}", fg="yellow")
            else:
                typer.secho(
                    f"已保留包 {packinfo.full_name}，但它可能无法使用", fg="yellow"
                )
            console.print()
        else:
            console.print(
                Panel(
                    f"[bold red]下载失败[/bold red]\n\n[white]{result.reason}[/white]\n\n"
                    "[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • 仓库地址是否正确\n  • 是否有访问权限",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
        return

    if not global_install:
        added = add_dep_to_vindex(packname)
        if added:
            typer.secho(f"已添加 {packname} 到 deps", fg="green")

        vindex_path = pack_path / "vindex.toml"
        if vindex_path.exists():
            import tomllib

            with open(vindex_path, "rb") as f:
                vindex_data = tomllib.load(f)
            pkg_deps = vindex_data.get("project", {}).get("deps", [])
            pkg_legacy = list(vindex_data.get("dependencies", {}).keys())
            transitive = list(dict.fromkeys(pkg_deps + pkg_legacy))
            if transitive:
                typer.secho(
                    f"检测到 {len(transitive)} 个传递依赖: {', '.join(transitive)}",
                    fg="cyan",
                )
                PackageInstaller.install_transitive_deps(parent, transitive)

    typer.secho(f"包 {packinfo.full_name} 添加成功", fg="green")
