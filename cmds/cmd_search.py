"""very search — 搜索可用的包"""

import json
import time
from datetime import datetime

import typer
from rich.panel import Panel
from rich.table import Table

from .utils import (
    VLIB_PREFIX,
    Config,
    _fetch_github_packages,
    _fetch_with_retry,
    _read_cache,
    _save_cache,
    _sort_packages,
    console,
)

CACHE_DIR = Config.VIX_HOME / "cache"
CACHE_FILE = CACHE_DIR / "search_cache.json"
CACHE_EXPIRY = 3600

app = typer.Typer()


@app.callback(invoke_without_command=True)
def search(
    keyword: str = typer.Argument(None, help="搜索关键词（可选），留空显示所有包"),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="不使用缓存，强制从 GitHub 获取最新数据"
    ),
    clear_cache: bool = typer.Option(False, "--clear-cache", help="清理本地缓存文件"),
    cache_status: bool = typer.Option(False, "--cache-status", help="查看缓存状态信息"),
    sort: str = typer.Option(
        "stars",
        "--sort",
        help="排序方式：stars(星标数), updated(更新时间), name(名称)，默认按星标数",
    ),
    limit: int = typer.Option(None, "--limit", help="限制显示的包数量"),
):
    """搜索可用的包"""
    kw = keyword or ""
    sort_by = sort

    if clear_cache:
        if not CACHE_FILE.exists():
            typer.secho("缓存文件不存在，无需清理", fg="cyan")
            return
        cache_size = CACHE_FILE.stat().st_size
        CACHE_FILE.unlink()
        typer.secho(f"缓存已清理（释放 {cache_size/1024:.2f} KB）", fg="green")
        return

    if cache_status:
        if not CACHE_FILE.exists():
            typer.secho("缓存文件不存在", fg="cyan")
            typer.secho("运行 very search 将自动创建缓存", fg="cyan")
            return
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        timestamp = cache_data["timestamp"]
        packages_count = len(cache_data["packages"])
        cache_age = time.time() - timestamp
        cache_size = CACHE_FILE.stat().st_size
        remaining_time = CACHE_EXPIRY - cache_age
        status = (
            f"[green]有效[/green]（剩余 {int(remaining_time / 60)} 分钟）"
            if remaining_time > 0
            else "[red]已过期[/red]"
        )
        cache_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        console.print()
        console.print(f"缓存文件: [cyan]{CACHE_FILE}[/cyan]")
        console.print(f"创建时间: [white]{cache_time}[/white]")
        console.print(f"缓存大小: [yellow]{cache_size/1024:.2f} KB[/yellow]")
        console.print(f"包数量: [magenta]{packages_count}[/magenta]")
        console.print(f"状态: {status}")
        console.print()
        return

    console.print(f"[bold cyan]搜索包: {kw if kw else '全部'}[/bold cyan]")

    try:
        if no_cache:
            typer.secho("正在从 GitHub 获取包列表...（不使用缓存）", fg="cyan")
            packages = _fetch_with_retry(
                lambda: _fetch_github_packages(VLIB_PREFIX, "ver")
            )
            _save_cache(CACHE_DIR, CACHE_FILE, packages)
        else:
            cached = _read_cache(CACHE_FILE, CACHE_EXPIRY)
            if cached is not None:
                typer.secho(f"使用缓存数据（{len(cached)} 个包）", fg="cyan")
                packages = cached
            else:
                typer.secho("正在从 GitHub 获取包列表...", fg="cyan")
                packages = _fetch_with_retry(
                    lambda: _fetch_github_packages(VLIB_PREFIX, "ver")
                )
                _save_cache(CACHE_DIR, CACHE_FILE, packages)

        if not packages:
            typer.secho("未找到任何包", fg="yellow")
            return

        if kw:
            filtered = [
                p
                for p in packages
                if kw.lower() in p["name"].lower()
                or kw.lower() in (p.get("description") or "").lower()
            ]
        else:
            filtered = packages

        if not filtered:
            typer.secho(f"未找到包含 '{kw}' 的包", fg="yellow")
            return

        filtered = _sort_packages(filtered, sort_by)
        if limit and limit > 0:
            filtered = filtered[:limit]

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("包名", style="green", width=25)
        table.add_column("描述", style="white", width=50)
        table.add_column("星标", justify="right", style="yellow", width=6)
        table.add_column("语言", style="magenta", width=12)
        table.add_column("更新时间", style="dim", width=12)

        for pkg in filtered:
            short_name = (
                pkg["name"].replace(VLIB_PREFIX, "", 1)
                if pkg["name"].startswith(VLIB_PREFIX)
                else pkg["name"]
            )
            desc = pkg.get("description") or ""
            table.add_row(
                short_name,
                desc[:47] + "..." if len(desc) > 50 else desc,
                str(pkg["stars"]),
                pkg["language"],
                pkg["updated"],
            )

        console.print()
        console.print(table)
        console.print()

        sort_labels = {"stars": "星标数", "updated": "更新时间", "name": "名称"}
        sort_label = sort_labels.get(sort_by, "星标数")
        typer.secho(f"共找到 {len(filtered)} 个包（按{sort_label}排序）", fg="green")

        console.print()
        console.print(
            Panel(
                "[dim]使用 [white]very add <包名>[/white] 安装包\n"
                "例如: [green]very add vnet[/green] 或 [green]very add vixlang/vlib-vnet[/green][/dim]",
                title="[bold]💡 提示[/bold]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print()

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]搜索失败[/bold red]\n\n[white]{str(e)}[/white]\n\n"
                "[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • GitHub API 是否可访问",
                title="[bold red]✘ 错误[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
