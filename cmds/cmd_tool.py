"""very tool — manage Vix tools."""

import typer
import json
import time
from pathlib import Path
import urllib.request
import ssl
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from .utils import (
    VTOOL_PREFIX, VIndexTool, Config, console, parse_tool_name,
    create_git_progress, DEFAULT_ORG,
)
from .installer import GitProgress
from git import Repo
import shutil
import os
import stat

_SSL_CTX = ssl.create_default_context()
CACHE_DIR = Config.VIX_TOOLS_PATH / "cache"
CACHE_FILE = CACHE_DIR / "tool_search_cache.json"
CACHE_EXPIRY = 3600
MAX_RETRIES = 3
RETRY_DELAY = 2

app = typer.Typer()
add_app = typer.Typer()
del_app = typer.Typer()
update_app = typer.Typer()
search_app = typer.Typer()

app.add_typer(add_app, name="add")
app.add_typer(del_app, name="del")
app.add_typer(update_app, name="update")
app.add_typer(search_app, name="search")


def _remove_readonly_tree(path: Path):
    def _remove_readonly(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onexc=_remove_readonly)


def install_tool(packname: str, parent: Path | None = None) -> Path | None:
    import sys
    if parent is None:
        parent = Config.VIX_TOOLS_PATH

    info = parse_tool_name(packname, parent=parent)
    PACK_PATH = info.pack_path

    if not PACK_PATH.exists():
        console.print(f"[bold cyan]安装工具: {info.full_name}[/bold cyan]")
        typer.secho(f"源: {info.git_url}", fg="cyan")
        if info.branch_name:
            typer.secho(f"分支: {info.branch_name}", fg="cyan")

        with create_git_progress(info.full_name) as progress:
            git_progress = GitProgress(progress, info.full_name)
            try:
                Repo.clone_from(
                    info.git_url,
                    PACK_PATH,
                    branch=info.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                if PACK_PATH.exists():
                    shutil.rmtree(PACK_PATH, ignore_errors=True)
                console.print(f"[red]克隆失败: {e}[/red]")
                return None
    else:
        typer.secho(f"工具 {info.full_name} 已存在，重新编译", fg="cyan")

    content = VIndexTool(PACK_PATH).content()
    if content is None:
        console.print(f"[red]{info.full_name} 缺少 vindex.toml[/red]")
        return None

    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (parent / binary_name).resolve()

    console.print(f"[cyan]正在编译 {project_name} ...[/cyan]")
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    from . import cmd_build
    old_cwd = Path.cwd()
    os.chdir(str(PACK_PATH))
    try:
        input_file, _ = cmd_build._extract_input_file([])
        if input_file is None:
            try:
                import tomllib
                with open("vindex.toml", "rb") as f:
                    vdata = tomllib.load(f)
                entry = vdata.get("project", {}).get("entrypoint", "main.vix")
            except Exception:
                entry = "main.vix"
            cand = Path(entry).resolve()
            if cand.exists():
                input_file = cand
        if input_file:
            root_dir = Path(".").resolve()
            temp_dir = Path(".vix/temp").resolve()
            temp_dir.mkdir(parents=True, exist_ok=True)
            if cmd_build._has_gcc():
                code, obj_path = cmd_build._compile_to_obj(input_file, [], root_dir, temp_dir, silent=True)
                if code == 0:
                    code = cmd_build._link_with_gcc(obj_path, str(binary_path), silent=True)
            else:
                code = cmd_build._compile_direct(input_file, ["-o", str(binary_path)], root_dir, silent=True)
        else:
            code = 1
    finally:
        os.chdir(str(old_cwd))

    if not binary_path.exists():
        console.print(f"[red]编译产物 {binary_name} 未生成[/red]")
        return None

    typer.secho(f"工具 {project_name} 已安装: {binary_path}", fg="green")
    return binary_path


@add_app.callback(invoke_without_command=True)
def add(package: str = typer.Argument(..., help="工具包名")):
    """安装 Vix 工具"""
    install_tool(package)


@del_app.callback(invoke_without_command=True)
def delete(package: str = typer.Argument(..., help="工具包名")):
    """删除 Vix 工具"""
    parent = Config.VIX_TOOLS_PATH
    info = parse_tool_name(package, parent=parent)
    PACK_PATH = info.pack_path

    if not PACK_PATH.exists():
        console.print(f"[red]工具 {info.full_name} 未安装[/red]")
        raise typer.Exit(code=1)

    project_name = info.repo_name
    content = VIndexTool(PACK_PATH).content()
    if content is not None:
        project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if os.name == "nt" else ""
    binary_path = parent / f"{project_name}{suffix}"

    console.print(f"[bold cyan]删除工具: {info.full_name}[/bold cyan]")

    if binary_path.exists():
        binary_path.unlink()
        typer.secho(f"已删除: {binary_path}", fg="green")

    _remove_readonly_tree(PACK_PATH)
    typer.secho(f"已删除: {PACK_PATH}", fg="green")

    for d in [PACK_PATH.parent, PACK_PATH.parent.parent]:
        if d.exists() and not any(d.iterdir()):
            d.rmdir()

    typer.secho(f"工具 {project_name} 已删除", fg="green")


@update_app.callback(invoke_without_command=True)
def update(package: str = typer.Argument(..., help="工具包名")):
    """更新 Vix 工具"""
    parent = Config.VIX_TOOLS_PATH
    info = parse_tool_name(package, parent=parent)
    PACK_PATH = info.pack_path

    if not PACK_PATH.exists():
        typer.secho(f"工具 {info.full_name} 未安装，正在安装...", fg="cyan")
        install_tool(package)
        return

    console.print(f"[bold cyan]更新工具: {info.full_name}[/bold cyan]")
    try:
        repo = Repo(PACK_PATH)
        origin = repo.remotes.origin
        origin.pull()
        typer.secho(f"已拉取最新代码: {PACK_PATH}", fg="green")
    except Exception as e:
        console.print(f"[red]拉取失败: {e}[/red]")
        raise typer.Exit(code=1)

    typer.secho("正在重新编译...", fg="cyan")
    binary_path = install_tool(package)
    if binary_path is not None:
        typer.secho(f"工具 {info.full_name} 已更新", fg="green")


# ---- Search ----


def _read_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["timestamp"] > CACHE_EXPIRY:
            return None
        return data["packages"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(packages):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {"timestamp": time.time(), "packages": packages}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fetch_github_packages():
    packages = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/orgs/{DEFAULT_ORG}/repos?per_page={per_page}&page={page}&type=sources"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Very-Project-Manager"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data:
                break
            for repo in data:
                if repo["name"].startswith(VTOOL_PREFIX):
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
                raise Exception("GitHub API 速率限制已用完，请稍后再试")
            elif e.code == 404:
                raise Exception("GitHub API 端点不存在")
            elif e.code >= 500:
                if attempt < MAX_RETRIES:
                    typer.secho(f"服务器错误 ({e.code})，将重试...", fg="yellow")
                    continue
                raise Exception(f"GitHub API 服务器错误 ({e.code})")
            else:
                raise Exception(f"HTTP 错误: {e.code}")
        except urllib.error.URLError as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                typer.secho("网络错误，将重试...", fg="yellow")
                continue
            raise Exception("网络错误，请检查网络连接")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")
    if last_exception:
        raise Exception(f"经过 {MAX_RETRIES} 次重试后仍然失败")


def _sort_packages(packages, sort_by):
    if sort_by == "stars":
        return sorted(packages, key=lambda x: x["stars"], reverse=True)
    elif sort_by == "updated":
        return sorted(packages, key=lambda x: x["updated"], reverse=True)
    elif sort_by == "name":
        return sorted(packages, key=lambda x: x["name"].lower())
    return sorted(packages, key=lambda x: x["stars"], reverse=True)


@search_app.callback(invoke_without_command=True)
def search(
    keyword: str = typer.Argument(None, help="搜索关键词（可选）"),
    no_cache: bool = typer.Option(False, "--no-cache", help="不使用缓存"),
    clear_cache: bool = typer.Option(False, "--clear-cache", help="清理缓存"),
    cache_status: bool = typer.Option(False, "--cache-status", help="查看缓存状态"),
    sort: str = typer.Option("stars", "--sort", help="排序方式：stars(星标数), updated(更新时间), name(名称)"),
    limit: int = typer.Option(None, "--limit", help="限制显示的工具数量"),
):
    """搜索可用的 Vix 工具"""
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
            typer.secho("缓存文件不存在\n运行 very tool search 将自动创建缓存", fg="cyan")
            return
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        timestamp = cache_data["timestamp"]
        packages_count = len(cache_data["packages"])
        cache_age = time.time() - timestamp
        cache_size = CACHE_FILE.stat().st_size
        remaining_time = CACHE_EXPIRY - cache_age
        status = f"[green]有效[/green]（剩余 {int(remaining_time / 60)} 分钟）" if remaining_time > 0 else "[red]已过期[/red]"
        cache_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        console.print()
        console.print(f"缓存文件: [cyan]{CACHE_FILE}[/cyan]")
        console.print(f"创建时间: [white]{cache_time}[/white]")
        console.print(f"缓存大小: [yellow]{cache_size/1024:.2f} KB[/yellow]")
        console.print(f"工具数量: [magenta]{packages_count}[/magenta]")
        console.print(f"状态: {status}")
        console.print()
        return

    console.print(f"[bold cyan]搜索工具: {kw if kw else '全部'}[/bold cyan]")

    try:
        if no_cache:
            typer.secho("正在从 GitHub 获取工具列表...（不使用缓存）", fg="cyan")
            packages = _fetch_with_retry()
            _save_cache(packages)
        else:
            cached = _read_cache()
            if cached is not None:
                typer.secho(f"使用缓存数据（{len(cached)} 个工具）", fg="cyan")
                packages = cached
            else:
                typer.secho("正在从 GitHub 获取工具列表...", fg="cyan")
                packages = _fetch_with_retry()
                _save_cache(packages)

        if not packages:
            typer.secho("未找到任何工具", fg="yellow")
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
            typer.secho(f"未找到包含 '{kw}' 的工具", fg="yellow")
            return

        filtered = _sort_packages(filtered, sort_by)
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
                pkg["name"].replace(VTOOL_PREFIX, "", 1)
                if pkg["name"].startswith(VTOOL_PREFIX)
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
        typer.secho(f"共找到 {len(filtered)} 个工具（按{sort_label}排序）", fg="green")
        console.print()

    except Exception as e:
        console.print(f"[red]搜索失败: {e}[/red]")
