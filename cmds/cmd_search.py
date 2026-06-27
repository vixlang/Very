"""very search — 搜索可用的包"""

import typer
import urllib.request
import json
import ssl
import time
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from .utils import Config, console, DEFAULT_ORG, VLIB_PREFIX

_SSL_CTX = ssl.create_default_context()
CACHE_DIR = Config.VIX_HOME / "cache"
CACHE_FILE = CACHE_DIR / "search_cache.json"
CACHE_EXPIRY = 3600
MAX_RETRIES = 3
RETRY_DELAY = 2

app = typer.Typer()


def _read_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        if time.time() - cache_data["timestamp"] > CACHE_EXPIRY:
            return None
        return cache_data["packages"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(packages):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {"timestamp": time.time(), "packages": packages}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fetch_github_packages():
    packages = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/orgs/{DEFAULT_ORG}/repos?per_page={per_page}&page={page}&type=sources"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Very-Project-Manager",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data:
                break
            for repo in data:
                if repo["name"].startswith(VLIB_PREFIX) or repo["name"] == "ver":
                    packages.append({
                        "name": repo["name"],
                        "description": repo["description"] or "无描述",
                        "stars": repo["stargazers_count"],
                        "language": repo["language"] or "Unknown",
                        "updated": repo["updated_at"][:10],
                        "url": repo["html_url"],
                    })
            if len(data) < per_page:
                break
            page += 1

    packages.sort(key=lambda x: x["stars"], reverse=True)
    return packages


def _fetch_with_retry():
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                typer.secho(f"重试第 {attempt - 1} 次...", fg="yellow")
                time.sleep(RETRY_DELAY)
            with Live(
                Spinner("dots", text="正在从 GitHub 获取数据..."),
                refresh_per_second=10,
                transient=True,
            ):
                result = _fetch_github_packages()
            return result
        except urllib.error.HTTPError as e:
            last_exception = e
            if e.code == 403:
                if attempt < MAX_RETRIES:
                    wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                    typer.secho(f"GitHub API 速率限制，{wait_time} 秒后重试...", fg="yellow")
                    time.sleep(wait_time)
                    continue
                raise Exception("GitHub API 速率限制已用完，请稍后再试（建议等待几分钟后重试）")
            elif e.code == 404:
                raise Exception("GitHub API 端点不存在，请检查网络连接")
            elif e.code >= 500:
                if attempt < MAX_RETRIES:
                    typer.secho(f"服务器错误 ({e.code})，将重试...", fg="yellow")
                    continue
                raise Exception(f"GitHub API 服务器错误 ({e.code})，请稍后重试")
            else:
                raise Exception(f"HTTP 错误: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                typer.secho(f"网络错误: {e.reason}，将重试...", fg="yellow")
                continue
            raise Exception(f"网络错误: {e.reason}，请检查网络连接")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    if last_exception:
        raise Exception(f"经过 {MAX_RETRIES} 次重试后仍然失败: {str(last_exception)}")


def _sort_packages(packages, sort_by):
    if sort_by == "stars":
        return sorted(packages, key=lambda x: x["stars"], reverse=True)
    elif sort_by == "updated":
        return sorted(packages, key=lambda x: x["updated"], reverse=True)
    elif sort_by == "name":
        return sorted(packages, key=lambda x: x["name"].lower())
    else:
        return sorted(packages, key=lambda x: x["stars"], reverse=True)


@app.callback(invoke_without_command=True)
def search(
    keyword: str = typer.Argument(None, help="搜索关键词（可选），留空显示所有包"),
    no_cache: bool = typer.Option(False, "--no-cache", help="不使用缓存，强制从 GitHub 获取最新数据"),
    clear_cache: bool = typer.Option(False, "--clear-cache", help="清理本地缓存文件"),
    cache_status: bool = typer.Option(False, "--cache-status", help="查看缓存状态信息"),
    sort: str = typer.Option("stars", "--sort", help="排序方式：stars(星标数), updated(更新时间), name(名称)，默认按星标数"),
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
        status = f"[green]有效[/green]（剩余 {int(remaining_time / 60)} 分钟）" if remaining_time > 0 else "[red]已过期[/red]"
        cache_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        console.print()
        console.print(f"缓存文件: [cyan]{CACHE_FILE}[/cyan]")
        console.print(f"创建时间: [white]{cache_time}[/white]")
        console.print(f"缓存大小: [yellow]{cache_size/1024:.2f} KB[/yellow]")
        console.print(f"包数量: [magenta]{packages_count}[/magenta]")
        console.print(f"状态: {status}")
        console.print()
        return

    typer.secho(f"[bold]搜索包: {kw if kw else '全部'}[/bold]", fg="cyan")

    try:
        if no_cache:
            typer.secho("正在从 GitHub 获取包列表...（不使用缓存）", fg="cyan")
            packages = _fetch_with_retry()
            _save_cache(packages)
        else:
            cached = _read_cache()
            if cached is not None:
                typer.secho(f"使用缓存数据（{len(cached)} 个包）", fg="cyan")
                packages = cached
            else:
                typer.secho("正在从 GitHub 获取包列表...", fg="cyan")
                packages = _fetch_with_retry()
                _save_cache(packages)

        if not packages:
            typer.secho("未找到任何包", fg="yellow")
            return

        if kw:
            filtered = [
                p for p in packages
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
        console.print(Panel(
            "[dim]使用 [white]very add <包名>[/white] 安装包\n"
            "例如: [green]very add vnet[/green] 或 [green]very add vixlang/vlib-vnet[/green][/dim]",
            title="[bold]💡 提示[/bold]",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()

    except Exception as e:
        console.print(Panel(
            f"[bold red]搜索失败[/bold red]\n\n[white]{str(e)}[/white]\n\n"
            "[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • GitHub API 是否可访问",
            title="[bold red]✘ 错误[/bold red]",
            border_style="red",
            padding=(1, 2),
        ))
