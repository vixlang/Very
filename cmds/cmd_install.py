import shutil
from pathlib import Path

import typer
from git import Repo
from rich.panel import Panel

from .installer import GitProgress
from .utils import Config, console, create_git_progress, parse_pack_name

app = typer.Typer()


@app.callback(invoke_without_command=True)
def install(
    local: bool = typer.Option(
        False, "-l", "--local", help="强制在项目 .vix 目录下载（即使全局已存在）"
    ),
):
    """安装 vindex.toml 中声明的所有依赖"""
    from .utils import VIndexTool, ask_confirm

    local_force = local

    vindex_toml_path = Path("vindex.toml")
    if not vindex_toml_path.exists():
        console.print("[red]未找到 vindex.toml，请确保在项目根目录运行此命令[/red]")
        raise typer.Exit(code=1)

    import tomllib

    with open(vindex_toml_path, "rb") as f:
        data = tomllib.load(f)

    deps = data.get("project", {}).get("deps", [])
    legacy_deps = list(data.get("dependencies", {}).keys())
    all_deps = list(dict.fromkeys(deps + legacy_deps))
    if not all_deps:
        typer.secho("vindex.toml 中没有声明依赖", fg="cyan")
        return

    local_parent = Config.local_libs_path()

    console.print("[bold cyan]安装依赖[/bold cyan]")
    success = []
    skipped = []
    global_skipped = []
    failed = []

    for spec in all_deps:
        local_packinfo = parse_pack_name(spec, parent=local_parent)
        if local_packinfo.pack_path.exists():
            skipped.append(spec)
            continue

        if not local_force:
            global_packinfo = parse_pack_name(spec, parent=Config.VIX_LIBS_PATH)
            if global_packinfo.pack_path.exists():
                global_skipped.append(spec)
                continue

        PACK_PATH = local_packinfo.pack_path
        console.print(f"[cyan]正在安装 {spec} ...[/cyan]")
        with create_git_progress(local_packinfo.full_name) as progress:
            git_progress = GitProgress(progress, local_packinfo.full_name)
            try:
                Repo.clone_from(
                    local_packinfo.git_url,
                    PACK_PATH,
                    branch=local_packinfo.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                if PACK_PATH.exists():
                    shutil.rmtree(PACK_PATH, ignore_errors=True)
                failed.append((spec, str(e)))
                continue

        content = VIndexTool(PACK_PATH).content()
        if content is None:
            console.print()
            console.print(
                Panel(
                    f"[bold yellow]包缺少 vindex.toml: [white]{local_packinfo.full_name}[/white][/bold yellow]\n\n"
                    "[dim]该包已下载但缺少必要的 vindex.toml 文件[/dim]",
                    title="[bold]⚠ 警告[/bold]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
            if ask_confirm("是否删除此不完整的包?", default=True):
                shutil.rmtree(PACK_PATH)
                failed.append((spec, "缺少 vindex.toml"))
            else:
                success.append(spec)
        else:
            success.append(spec)

    console.print()
    console.print("[bold cyan]安装结果[/bold cyan]")
    if success:
        typer.secho(f"成功: {', '.join(success)}", fg="green")
    if skipped:
        typer.secho(f"跳过(本地已存在): {', '.join(skipped)}", fg="cyan")
    if global_skipped:
        typer.secho(f"跳过(使用全局副本): {', '.join(global_skipped)}", fg="cyan")
    if failed:
        for spec, reason in failed:
            console.print(Panel(f"[red]{spec}: {reason}[/red]", border_style="red"))
