import time
import json

import typer
from rich.table import Table

from apis.search import (
    read_cache,
    save_cache,
    clear_cache,
    fetch_github_packages,
    fetch_with_retry,
    sort_packages,
    filter_packages,
)
from apis.types import VTOOL_PREFIX, Config
from cmds.share import log
from cmds.utils import console

CACHE_DIR = Config.VIX_TOOLS_PATH / "cache"
CACHE_FILE = CACHE_DIR / "tool_search_cache.json"
CACHE_EXPIRY = 3600

search_app = typer.Typer()


@search_app.callback(invoke_without_command=True)
def search(
    keyword: str = typer.Argument(None, help="搜索关键词（可选）"),
    no_cache: bool = typer.Option(False, "--no-cache", help="不使用缓存"),
    clear_cache_flag: bool = typer.Option(False, "--clear-cache", help="清理缓存"),
    cache_status: bool = typer.Option(False, "--cache-status", help="查看缓存状态"),
    sort: str = typer.Option(
        "stars", "--sort", help="排序方式：stars(星标数), updated(更新时间), name(名称)"
    ),
    limit: int = typer.Option(None, "--limit", help="限制显示的工具数量"),
):
    """搜索可用的 Vix 工具"""
    kw = keyword or ""
    sort_by = sort

    if clear_cache_flag:
        if not CACHE_FILE.exists():
            log.info("缓存文件不存在，无需清理")
            return
        cache_size = CACHE_FILE.stat().st_size
        clear_cache(CACHE_FILE)
        log.ok(f"缓存已清理（释放 {cache_size / 1024:.2f} KB）")
        return

    if cache_status:
        if not CACHE_FILE.exists():
            log.info("缓存文件不存在\n运行 very tool search 将自动创建缓存")
            return
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache_data = json.load(f)
        timestamp = cache_data["timestamp"]
        packages_count = len(cache_data["packages"])
        cache_age = time.time() - timestamp
        cache_size = CACHE_FILE.stat().st_size
        remaining = CACHE_EXPIRY - cache_age
        status = (
            f"[green]有效[/green]（剩余 {int(remaining / 60)} 分钟）"
            if remaining > 0
            else "[red]已过期[/red]"
        )
        log.info(f"缓存文件: [cyan]{CACHE_FILE}[/cyan]")
        log.info(f"工具数量: [magenta]{packages_count}[/magenta]")
        log.info(f"大小: [yellow]{cache_size / 1024:.2f} KB[/yellow]")
        log.info(f"状态: {status}")
        return

    log.info(f"搜索工具: {kw if kw else '全部'}")

    try:
        if no_cache:
            log.info("正在从 GitHub 获取工具列表...（不使用缓存）")
            packages = fetch_with_retry(lambda: fetch_github_packages(VTOOL_PREFIX))
            save_cache(CACHE_DIR, CACHE_FILE, packages)
        else:
            cached = read_cache(CACHE_FILE, CACHE_EXPIRY)
            if cached is not None:
                log.info(f"使用缓存数据（{len(cached)} 个工具）")
                packages = cached
            else:
                log.info("正在从 GitHub 获取工具列表...")
                packages = fetch_with_retry(lambda: fetch_github_packages(VTOOL_PREFIX))
                save_cache(CACHE_DIR, CACHE_FILE, packages)

        if not packages:
            log.warn("未找到任何工具")
            return

        if kw:
            filtered = filter_packages(packages, kw)
        else:
            filtered = packages

        if not filtered:
            log.warn(f"未找到包含 '{kw}' 的工具")
            return

        filtered = sort_packages(filtered, sort_by)
        if limit and limit > 0:
            filtered = filtered[:limit]

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("工具名", style="green", width=25)
        table.add_column("描述", style="white", width=50)
        table.add_column("星标", justify="right", style="yellow", width=6)
        table.add_column("语言", style="magenta", width=12)
        table.add_column("更新时间", style="dim", width=12)

        for pkg in filtered:
            short_name = (
                pkg.name.removeprefix(VTOOL_PREFIX)
                if pkg.name.startswith(VTOOL_PREFIX)
                else pkg.name
            )
            desc = pkg.description or ""
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
        log.ok(
            f"共找到 {len(filtered)} 个工具（按{sort_labels.get(sort_by, '星标数')}排序）"
        )

    except Exception as e:
        log.error(f"搜索失败: {e}")
