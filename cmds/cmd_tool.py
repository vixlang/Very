"""very tool — manage Vix tools (add, search)."""

from .base import Command
from .cmd_build import BuildCmd
from .utils import (
    VTOOL_PREFIX,
    VIndexTool,
    Config,
    log,
    console,
    err_console,
    parse_tool_name,
    create_git_progress,
)
from .installer import GitProgress
from git import Repo
from pathlib import Path
import argparse
import sys
import os
import shutil
import stat
import json
import time
import urllib.request
import ssl
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

_SSL_CTX = ssl.create_default_context()


def _remove_readonly_tree(path: Path):
    """shutil.rmtree with Windows .git read-only file handling."""
    def _remove_readonly(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onexc=_remove_readonly)


def install_tool(packname: str, parent: Path | None = None) -> Path | None:
    """Install and build a Vix tool. Returns the compiled binary path or None."""
    import shutil

    if parent is None:
        parent = Config.VIX_TOOLS_PATH

    info = parse_tool_name(packname, parent=parent)
    PACK_PATH = info.pack_path

    if not PACK_PATH.exists():
        log.section(f"安装工具: {info.full_name}")
        log.info(f"源: [link={info.git_url}]{info.git_url}[/link]")
        if info.branch_name:
            log.info(f"分支: {info.branch_name}")

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
                log.error(f"克隆失败: {e}")
                return None
    else:
        log.info(f"工具 {info.full_name} 已存在，重新编译")

    content = VIndexTool(PACK_PATH).content()
    if content is None:
        log.error(f"{info.full_name} 缺少 vindex.toml")
        return None

    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (parent / binary_name).resolve()

    log.info(f"正在编译 [cyan]{project_name}[/cyan] ...")
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    old_cwd = Path.cwd()
    os.chdir(str(PACK_PATH))
    try:
        ns = argparse.Namespace()
        build_cmd = BuildCmd.create_for_subcommand(ns, ["-o", str(binary_path)])
        code = build_cmd.execute()
        if code is not None and code != 0:
            log.error(f"编译 {info.full_name} 失败")
            return None
    finally:
        os.chdir(str(old_cwd))

    if not binary_path.exists():
        log.error(f"编译产物 {binary_name} 未生成")
        return None

    log.success(f"工具 {project_name} 已安装: {binary_path}")
    return binary_path


class ToolCmd(Command):
    NAME = "tool"

    CACHE_DIR = Config.VIX_TOOLS_PATH / "cache"
    CACHE_FILE = CACHE_DIR / "tool_search_cache.json"
    CACHE_EXPIRY = 3600
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            "tool",
            help="管理 Vix 工具",
            description="安装、搜索和管理 Vix 工具。",
        )
        sub = parser.add_subparsers(dest="tool_subcommand")

        add_parser = sub.add_parser("add", help="安装 Vix 工具")
        add_parser.add_argument("package", help="工具包名")

        del_parser = sub.add_parser("del", help="删除 Vix 工具")
        del_parser.add_argument("package", help="工具包名")

        update_parser = sub.add_parser("update", help="更新 Vix 工具")
        update_parser.add_argument("package", help="工具包名")

        search_parser = sub.add_parser(
            "search",
            help="搜索可用的 Vix 工具",
            description="从 GitHub vixlang 组织中搜索可用的 vix 工具。",
        )
        search_parser.add_argument(
            "keyword", nargs="?", default="", help="搜索关键词（可选）"
        )
        search_parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
        search_parser.add_argument(
            "--clear-cache", action="store_true", help="清理缓存"
        )
        search_parser.add_argument(
            "--cache-status", action="store_true", help="查看缓存状态"
        )
        search_parser.add_argument(
            "--sort",
            choices=["stars", "updated", "name"],
            default="stars",
            help="排序方式：stars(星标数), updated(更新时间), name(名称)",
        )
        search_parser.add_argument(
            "--limit", type=int, default=None, help="限制显示的工具数量"
        )
        return parser

    def execute(self):
        sub = getattr(self.namespace, "tool_subcommand", None)
        if sub == "add":
            self._cmd_add()
        elif sub == "del":
            self._cmd_del()
        elif sub == "update":
            self._cmd_update()
        elif sub == "search":
            self._cmd_search()
        else:
            err_console.print(
                "[red]未知 tool 子命令，使用 'very tool --help' 查看帮助[/red]"
            )

    def _cmd_add(self):
        packname = getattr(self.namespace, "package", "")
        if not packname:
            log.error("请指定工具包名")
            return
        install_tool(packname)

    def _cmd_del(self):
        packname = getattr(self.namespace, "package", "")
        if not packname:
            log.error("请指定工具包名")
            return

        parent = Config.VIX_TOOLS_PATH
        info = parse_tool_name(packname, parent=parent)
        PACK_PATH = info.pack_path

        if not PACK_PATH.exists():
            log.error(f"工具 {info.full_name} 未安装")
            return

        # 获取 project.name 以找到编译产物
        project_name = info.repo_name
        content = VIndexTool(PACK_PATH).content()
        if content is not None:
            project_name = content.get("project", {}).get("name", info.repo_name)
        suffix = ".exe" if sys.platform == "win32" else ""
        binary_path = parent / f"{project_name}{suffix}"

        log.section(f"删除工具: {info.full_name}")

        # 删除编译产物
        if binary_path.exists():
            binary_path.unlink()
            log.success(f"已删除: {binary_path}")

        # 删除源码目录
        _remove_readonly_tree(PACK_PATH)
        log.success(f"已删除: {PACK_PATH}")

        # 清理空父目录
        for d in [PACK_PATH.parent, PACK_PATH.parent.parent]:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()

        log.success(f"工具 {project_name} 已删除")

    def _cmd_update(self):
        packname = getattr(self.namespace, "package", "")
        if not packname:
            log.error("请指定工具包名")
            return

        parent = Config.VIX_TOOLS_PATH
        info = parse_tool_name(packname, parent=parent)
        PACK_PATH = info.pack_path

        if not PACK_PATH.exists():
            log.info(f"工具 {info.full_name} 未安装，正在安装...")
            install_tool(packname)
            return

        log.section(f"更新工具: {info.full_name}")
        try:
            repo = Repo(PACK_PATH)
            origin = repo.remotes.origin
            origin.pull()
            log.success(f"已拉取最新代码: {PACK_PATH}")
        except Exception as e:
            log.error(f"拉取失败: {e}")
            return

        # 重新编译
        log.info("正在重新编译...")
        binary_path = install_tool(packname)
        if binary_path is not None:
            log.success(f"工具 {info.full_name} 已更新")

    # ---- Search ----

    def _cmd_search(self):
        keyword = getattr(self.namespace, "keyword", "")
        no_cache = getattr(self.namespace, "no_cache", False)
        clear_cache = getattr(self.namespace, "clear_cache", False)
        cache_status = getattr(self.namespace, "cache_status", False)
        sort_by = getattr(self.namespace, "sort", "stars")
        limit = getattr(self.namespace, "limit", None)

        if clear_cache:
            self._clear_cache()
            return
        if cache_status:
            self._show_cache_status()
            return

        log.section(f"搜索工具: {keyword if keyword else '全部'}")

        try:
            if no_cache:
                log.info("正在从 GitHub 获取工具列表...（不使用缓存）")
                packages = self._fetch_with_retry()
                self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                self._save_cache(packages)
            else:
                packages = self._fetch_packages_with_cache()

            if not packages:
                log.warning("未找到任何工具")
                return

            if keyword:
                filtered = [
                    p
                    for p in packages
                    if keyword.lower() in p["name"].lower()
                    or keyword.lower() in (p.get("description") or "").lower()
                ]
            else:
                filtered = packages

            if not filtered:
                log.warning(f"未找到包含 '{keyword}' 的工具")
                return

            filtered = self._sort_packages(filtered, sort_by)
            if limit and limit > 0:
                filtered = filtered[:limit]

            self._display_results(filtered, sort_by)

        except Exception as e:
            log.error(
                f"搜索失败\n\n[white]{str(e)}[/white]\n\n"
                "[yellow]请检查网络连接是否正常[/yellow]"
            )

    def _sort_packages(self, packages, sort_by):
        if sort_by == "stars":
            return sorted(packages, key=lambda x: x["stars"], reverse=True)
        elif sort_by == "updated":
            return sorted(packages, key=lambda x: x["updated"], reverse=True)
        elif sort_by == "name":
            return sorted(packages, key=lambda x: x["name"].lower())
        return sorted(packages, key=lambda x: x["stars"], reverse=True)

    def _fetch_with_retry(self):
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    log.info(f"重试第 {attempt - 1} 次...")
                    time.sleep(self.RETRY_DELAY)
                with Live(
                    Spinner("dots", text="正在从 GitHub 获取数据..."),
                    refresh_per_second=10,
                    transient=True,
                ):
                    result = self._fetch_github_packages()
                return result
            except urllib.error.HTTPError as e:
                last_exception = e
                if e.code == 403:
                    if attempt < self.MAX_RETRIES:
                        wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                        log.warning(f"GitHub API 速率限制，{wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    raise Exception("GitHub API 速率限制已用完，请稍后再试")
                elif e.code == 404:
                    raise Exception("GitHub API 端点不存在")
                elif e.code >= 500:
                    if attempt < self.MAX_RETRIES:
                        log.warning(f"服务器错误 ({e.code})，将重试...")
                        continue
                    raise Exception(f"GitHub API 服务器错误 ({e.code})")
                else:
                    raise Exception(f"HTTP 错误: {e.code}")
            except urllib.error.URLError as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    log.warning("网络错误，将重试...")
                    continue
                raise Exception("网络错误，请检查网络连接")
            except Exception as e:
                raise Exception(f"请求失败: {str(e)}")
        if last_exception:
            raise Exception(f"经过 {self.MAX_RETRIES} 次重试后仍然失败")

    def _fetch_packages_with_cache(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached_data = self._read_cache()
        if cached_data is not None:
            log.info(f"使用缓存数据（{len(cached_data)} 个工具）")
            return cached_data
        log.info("正在从 GitHub 获取工具列表...")
        packages = self._fetch_with_retry()
        self._save_cache(packages)
        return packages

    def _read_cache(self):
        if not self.CACHE_FILE.exists():
            return None
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data["timestamp"] > self.CACHE_EXPIRY:
                return None
            return data["packages"]
        except (json.JSONDecodeError, KeyError):
            return None
        except Exception:
            return None

    def _save_cache(self, packages):
        try:
            data = {"timestamp": time.time(), "packages": packages}
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.debug(f"保存缓存失败: {e}")

    def _fetch_github_packages(self):
        from .utils import DEFAULT_ORG

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
                    if repo["name"].startswith(VTOOL_PREFIX):
                        packages.append(
                            {
                                "name": repo["name"],
                                "description": repo["description"] or "无描述",
                                "stars": repo["stargazers_count"],
                                "language": repo["language"] or "Unknown",
                                "updated": repo["updated_at"][:10],
                                "url": repo["html_url"],
                            }
                        )
                if len(data) < per_page:
                    break
                page += 1

        packages.sort(key=lambda x: x["stars"], reverse=True)
        return packages

    def _display_results(self, packages, sort_by="stars"):
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("工具名", style="green", width=25)
        table.add_column("描述", style="white", width=50)
        table.add_column("星标", justify="right", style="yellow", width=6)
        table.add_column("语言", style="magenta", width=12)
        table.add_column("更新时间", style="dim", width=12)

        for pkg in packages:
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
        log.success(f"共找到 {len(packages)} 个工具（按{sort_label}排序）")
        console.print()

    def _clear_cache(self):
        log.section("清理缓存")
        if not self.CACHE_FILE.exists():
            log.info("缓存文件不存在，无需清理")
            return
        try:
            cache_size = self.CACHE_FILE.stat().st_size
            self.CACHE_FILE.unlink()
            log.success(f"缓存已清理（释放 {cache_size/1024:.2f} KB）")
        except Exception as e:
            log.error(f"清理缓存失败: {e}")

    def _show_cache_status(self):
        log.section("缓存状态")
        if not self.CACHE_FILE.exists():
            log.info(
                "缓存文件不存在\n运行 [green]very tool search[/green] 将自动创建缓存"
            )
            return
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            timestamp = cache_data["timestamp"]
            packages_count = len(cache_data["packages"])
            cache_age = time.time() - timestamp
            cache_size = self.CACHE_FILE.stat().st_size
            remaining_time = self.CACHE_EXPIRY - cache_age
            if remaining_time > 0:
                status = f"[green]有效[/green]（剩余 {int(remaining_time / 60)} 分钟）"
            else:
                status = "[red]已过期[/red]"
            cache_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            console.print()
            console.print(f"缓存文件: [cyan]{self.CACHE_FILE}[/cyan]")
            console.print(f"创建时间: [white]{cache_time}[/white]")
            console.print(f"缓存大小: [yellow]{cache_size/1024:.2f} KB[/yellow]")
            console.print(f"工具数量: [magenta]{packages_count}[/magenta]")
            console.print(f"状态: {status}")
            console.print()
        except Exception as e:
            log.error(f"读取缓存状态失败: {e}")
