import json
import time
from datetime import datetime

import typer
from rich.table import Table

from apis.search import (
    CACHE_EXPIRY,
    clear_cache,
    fetch_github_packages,
    fetch_with_retry,
    filter_packages,
    read_cache,
    save_cache,
    sort_packages,
)
from apis.types import Config, VLIB_PREFIX

from .share import log
from .utils import console

CACHE_DIR = Config.VIX_HOME / "cache"
CACHE_FILE = CACHE_DIR / "search_cache.json"

app = typer.Typer()


@app.callback(invoke_without_command=True)
def search(
    keyword: str = typer.Argument(None, help="搜索关键词（可选），留空显示所有包"),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="不使用缓存，强制从 GitHub 获取最新数据"
    ),
    clear_: bool = typer.Option(False, "--clear-cache", help="清理本地缓存文件"),
    cache_status: bool = typer.Option(False, "--cache-status", help="查看缓存状态信息"),
    sort: str = typer.Option(
        "stars",
        "--sort",
        help="排序方式：stars(星标数), updated(更新时间), name(名称)，默认按星标数",
    ),
    limit: int = typer.Option(None, "--limit", help="限制显示的包数量"),
):
    """搜索可用的包"""
    if clear_:
        if not CACHE_FILE.exists():
            log.info("缓存文件不存在，无需清理")
            return
        size = CACHE_FILE.stat().st_size
        clear_cache(CACHE_FILE)
        log.ok(f"缓存已清理（释放 {size / 1024:.2f} KB）")
        return

    if cache_status:
        if not CACHE_FILE.exists():
            log.info("缓存文件不存在")
            log.info("运行 very search 将自动创建缓存")
            return
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        ts = raw["timestamp"]
        count = len(raw["packages"])
        age = time.time() - ts
        remaining = CACHE_EXPIRY - age
        status = (
            f"[green]有效[/green]（剩余 {int(remaining / 60)} 分钟）"
            if remaining > 0
            else "[red]已过期[/red]"
        )
        cache_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        cache_size = CACHE_FILE.stat().st_size
        log.info(f"缓存文件: [cyan]{CACHE_FILE}[/cyan]")
        log.info(f"创建时间: [white]{cache_time}[/white]")
        log.info(f"缓存大小: [yellow]{cache_size / 1024:.2f} KB[/yellow]")
        log.info(f"包数量: [magenta]{count}[/magenta]")
        log.info(f"状态: {status}")
        return

    try:
        if no_cache:
            log.info("正在从 GitHub 获取包列表...（不使用缓存）")
            packages = fetch_with_retry(
                lambda: fetch_github_packages(VLIB_PREFIX, "ver")
            )
            save_cache(CACHE_DIR, CACHE_FILE, packages)
        else:
            cached = read_cache(CACHE_FILE, CACHE_EXPIRY)
            if cached is not None:
                log.info(f"使用缓存数据（{len(cached)} 个包）")
                packages = cached
            else:
                log.info("正在从 GitHub 获取包列表...")
                packages = fetch_with_retry(
                    lambda: fetch_github_packages(VLIB_PREFIX, "ver")
                )
                save_cache(CACHE_DIR, CACHE_FILE, packages)
    except Exception as e:
        log.error(f"搜索失败: {e}")
        raise typer.Exit(code=1)

    if not packages:
        log.warn("未找到任何包")
        return

    if keyword:
        packages = filter_packages(packages, keyword)

    if not packages:
        log.warn(f"未找到包含 '{keyword}' 的包")
        return

    packages = sort_packages(packages, sort)
    if limit:
        packages = packages[:limit]

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("包名", style="green", width=25)
    table.add_column("描述", style="white", width=50)
    table.add_column("星标", justify="right", style="yellow", width=6)
    table.add_column("语言", style="magenta", width=12)
    table.add_column("更新时间", style="dim", width=12)

    for pkg in packages:
        short_name = (
            pkg.name.replace(VLIB_PREFIX, "", 1)
            if pkg.name.startswith(VLIB_PREFIX)
            else pkg.name
        )
        desc = pkg.description
        table.add_row(
            short_name,
            desc[:47] + "..." if len(desc) > 50 else desc,
            str(pkg.stars),
            pkg.language,
            pkg.updated,
        )

    console.print()
    console.print(table)
    console.print()

    sort_labels = {"stars": "星标数", "updated": "更新时间", "name": "名称"}
    log.ok(f"共找到 {len(packages)} 个包（按{sort_labels.get(sort, '星标数')}排序）")
