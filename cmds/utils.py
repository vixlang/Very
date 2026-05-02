import sys
import re
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Confirm
from pathlib import Path
import os
import shutil
from dataclasses import dataclass

console = Console()
err_console = Console(file=sys.stderr)


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
        exit(1)

    def section(self, title: str):
        console.print(Rule(f"[bold]{title}[/bold]", style="dim"))

    def status_panel(self, msg, title="INFO", border_style="blue"):
        console.print(Panel(msg, title=title, border_style=border_style))


def ask_confirm(prompt: str, default: bool = False) -> bool:
    return Confirm.ask(prompt, default=default)


class Config:
    VIX_HOME = Path(os.getenv("VIX_HOME", "./.vix"))
    VIX_LIBS_PATH = VIX_HOME / "libs"


class VIndexTool:
    def __init__(self, dir_path: Path):
        self.path = dir_path / "vindex.toml"

    def content(self, package_name=None) -> dict[str, object]:
        import tomllib

        if not (self.path).exists():
            log.error(f"包 {package_name} 不存在 vindex.toml 文件!")
            if ask_confirm("是否删除?"):
                shutil.rmtree(self.path.parent)
                log.warning(f"已删除包 {package_name}")
                exit(0)
            else:
                log.critical(
                    "已保留此包，但它不可用（缺少vindex.toml文件，vpm无法识别它）"
                )

        with open(self.path, "rb") as f:
            return tomllib.load(f)


@dataclass
class PackageNameInfo:
    repo_name: str

    git_master: str = "github.com"
    user_name: str = "vixlang"

    branch_name: str | None = None

    @property
    def pack_path(self, parent: Path = Config.VIX_LIBS_PATH) -> Path:
        return parent / self.git_master / self.user_name / self.repo_name

    @property
    def git_url(self):
        return f"https://{self.git_master}/{self.user_name}/{self.repo_name}"

    @property
    def full_name(self):
        return f"{self.git_master}:{self.user_name}.{self.repo_name}"


def parse_pack_name(package_name: str) -> PackageNameInfo:
    original = package_name
    branch = None
    default_host = "github.com"

    if package_name.startswith("@") and "://" not in package_name:
        default_host = "gitee.com"
        package_name = package_name[1:]

    if "@" in package_name:
        rest, _, possible_branch = package_name.rpartition("@")
        if possible_branch and "/" not in possible_branch and ":" not in possible_branch:
            branch = possible_branch
            package_name = rest

    if "://" in package_name:
        parsed = urlparse(package_name)
        master = parsed.netloc
        path = parsed.path.lstrip("/")
        path = re.sub(r"\.git$", "", path)
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            log.critical(f"URL 格式无法提取用户/仓库: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
        )

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
            log.critical(f"SCP 格式无法解析路径: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
        )

    if ":" in package_name:
        master, path = package_name.split(":", 1)
        if "." not in master:
            master += ".com"
        path = re.sub(r"\.git$", "", path)
        if "/" not in path and "." not in path:
            path = f"vixlang.vlib-{path}"
        if "/" not in path:
            path = path.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            log.critical(f"包名格式错误: {original}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
        )

    if "/" in package_name:
        parts = package_name.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            log.critical(f"包名格式错误: {original}")
    elif "." in package_name:
        path = package_name.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            log.critical(f"包名格式错误: {original}")
    else:
        user_name = "vixlang"
        repo_name = f"vlib-{package_name}"

    return PackageNameInfo(
        git_master=default_host,
        user_name=user_name,
        repo_name=repo_name,
        branch_name=branch,
    )


log = Logger()


if __name__ == "__main__":
    print(parse_pack_name("fexcode.vnet@master"))
    print(parse_pack_name("@fexcode.vnet@master"))
    print(parse_pack_name("gitee.com:fexcode.vnet@master"))
    print(parse_pack_name("gitee:fexcode.vnet@master"))
    print(parse_pack_name("gitee:fexcode.vnet"))
    print(parse_pack_name("fexcode.vnet"))