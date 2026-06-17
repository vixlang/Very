import sys
import re
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Confirm
from pathlib import Path
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

console = Console()
err_console = Console(file=sys.stderr)


class VeryFatalError(Exception):
    """致命错误标记 —— 由主循环统一捕获后以非零退出码终止。"""


class Logger:
    def info(self, msg):
        console.print(f"  [cyan]ℹ[/cyan]  {msg}")

    def success(self, msg):
        console.print(f"  [green]✔[/green]  {msg}")

    def warning(self, msg):
        console.print(f"  [yellow]⚠[/yellow]  {msg}")

    def error(self, msg):
        err_console.print()
        err_console.print(
            Panel(
                f"[bold red]{msg}[/bold red]",
                title="[bold red]✘ 错误[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        err_console.print()

    def debug(self, msg):
        console.print(f"  [magenta]⚙[/magenta]  {msg}")

    def critical(self, msg):
        err_console.print()
        err_console.print(
            Panel(
                f"[bold red]{msg}[/bold red]\n\n"
                f"[dim]这是一个严重错误，程序将退出[/dim]",
                title="[bold red]✘ 致命错误[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        err_console.print()
        raise VeryFatalError(msg)

    def section(self, title: str):
        console.print(Rule(f"[bold]{title}[/bold]", style="dim"))

    def status_panel(self, msg, title="INFO", border_style="blue"):
        console.print(Panel(msg, title=title, border_style=border_style))


def ask_confirm(prompt: str, default: bool = False) -> bool:
    return Confirm.ask(prompt, default=default)


@dataclass(frozen=True)
class Config:
    VIX_HOME: Path = Path(os.getenv("VIX_HOME", "./.vix"))
    VIX_LIBS_PATH: Path = Path(os.getenv("VIX_HOME", "./.vix")) / "libs"


# Package naming constants
DEFAULT_HOST = "github.com"
DEFAULT_ORG = "vixlang"
VLIB_PREFIX = "vlib-"


def iter_package_dirs(libs_path: Path) -> Iterator[tuple[Path, Path, Path, str]]:
    """遍历所有已安装包的目录结构。

    Yields: (master_dir, user_dir, repo_dir, "host:user.repo")
    """
    for md in libs_path.iterdir():
        if not md.is_dir():
            continue
        for ud in md.iterdir():
            if not ud.is_dir():
                continue
            for rd in ud.iterdir():
                if not rd.is_dir():
                    continue
                yield md, ud, rd, f"{md.name}:{ud.name}.{rd.name}"


def iter_empty_dirs(libs_path: Path) -> Iterator[Path]:
    """从底部向上遍历空目录（反向排序确保子目录先被清理）。"""
    for md in sorted(libs_path.iterdir(), reverse=True):
        if not md.is_dir():
            continue
        for ud in sorted(md.iterdir(), reverse=True):
            if not ud.is_dir():
                continue
            for rd in sorted(ud.iterdir(), reverse=True):
                if not rd.is_dir():
                    continue
                if not any(rd.iterdir()):
                    yield rd
            if not any(ud.iterdir()):
                yield ud
        if not any(md.iterdir()):
            yield md


class VIndexTool:
    def __init__(self, dir_path: Path):
        self.path = dir_path / "vindex.toml"

    def content(self) -> dict[str, object] | None:
        """读取 vindex.toml 并返回解析后的字典。

        返回 None 表示文件不存在（而非解析失败——解析失败会抛异常）。
        本方法绝不调用 exit()，调用方自行处理缺失情况。
        """
        import tomllib

        if not self.path.exists():
            return None

        with open(self.path, "rb") as f:
            return tomllib.load(f)


@dataclass
class PackageNameInfo:
    repo_name: str

    git_master: str = "github.com"
    user_name: str = "vixlang"

    branch_name: str | None = None
    parent: Path | None = None

    _default_parent: ClassVar[Path] = Config.VIX_LIBS_PATH

    @property
    def pack_path(self) -> Path:
        parent = self.parent or PackageNameInfo._default_parent
        path = parent / self.git_master / self.user_name / self.repo_name
        try:
            path.resolve().relative_to(parent.resolve())
        except ValueError:
            raise ValueError(f"包路径穿越检测: {path} 不在 {parent} 下")
        return path

    @property
    def git_url(self):
        return f"https://{self.git_master}/{self.user_name}/{self.repo_name}"

    @property
    def full_name(self):
        return f"{self.git_master}:{self.user_name}.{self.repo_name}"


def parse_pack_name(package_name: str, parent: Path | None = None) -> PackageNameInfo:
    original = package_name
    branch = None
    default_host = DEFAULT_HOST

    # ── 1. @ 前缀 → gitee.com ──────────────────────────────
    if package_name.startswith("@") and "://" not in package_name:
        default_host = "gitee.com"
        package_name = package_name[1:]

    # ── 2. URL 协议 → 立即解析（必须先于 @ 分支提取，否则 URL 中的
    #        credential 如 https://token@github.com/user/repo 的
    #       @github.com/user/repo 会被错误提取为分支名）──────
    if "://" in package_name:
        parsed = urlparse(package_name)
        master = parsed.hostname or parsed.netloc
        path = parsed.path.lstrip("/")
        path = re.sub(r"\.git$", "", path)
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"URL 格式无法提取用户/仓库: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    # ── 3. 提取分支（此时已排除 URL，@ 不会被混淆）─────────
    if "@" in package_name:
        rest, _, possible_branch = package_name.rpartition("@")
        if (
            possible_branch
            and "/" not in possible_branch
            and ":" not in possible_branch
        ):
            branch = possible_branch
            package_name = rest

    # ── 4. SCP 风格：user@host:path ─────────────────────────
    if "@" in package_name and ":" in package_name:
        user_host, _, path = package_name.partition(":")
        host = user_host.split("@")[-1]
        master = host if "." in host else host + ".com"
        path = path.strip()
        path = re.sub(r"\.git$", "", path)
        if "/" in path:
            parts = path.split("/")
        else:
            parts = path.replace(".", "/").split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"SCP 格式无法解析路径: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    if ":" in package_name:
        master, path = package_name.split(":", 1)
        if "." not in master:
            master += ".com"
        path = re.sub(r"\.git$", "", path)
        if "/" not in path and "." not in path:
            path = f"{DEFAULT_ORG}.{VLIB_PREFIX}{path}"
        if "/" not in path:
            path = path.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"包名格式错误: {original}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    if "/" in package_name:
        parts = package_name.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            raise ValueError(f"包名格式错误: {original}")
    elif "." in package_name:
        path = package_name.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            raise ValueError(f"包名格式错误: {original}")
    else:
        user_name = DEFAULT_ORG
        repo_name = f"{VLIB_PREFIX}{package_name}"

    return PackageNameInfo(
        git_master=default_host,
        user_name=user_name,
        repo_name=repo_name,
        branch_name=branch,
        parent=parent,
    )


log = Logger()


def create_git_progress(package_name: str):
    """Create a Rich Progress instance for git operations."""
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )

    return Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    )
