import sys
from rich.console import Console
from pathlib import Path
import os
import shutil
from dataclasses import dataclass

console = Console()
err_console = Console(file=sys.stderr)


class Logger:
    def info(self, msg):
        console.print(f"[cyan][INFO][/cyan]\t\t{msg}")

    def success(self, msg):
        console.print(f"[green][SUCCESS][/green]\t{msg}")

    def warning(self, msg):
        console.print(f"[yellow][WARNING][/yellow]\t{msg}")

    def error(self, msg):
        err_console.print(f"[red][ERROR][/red]\t\t{msg}")

    def debug(self, msg):
        console.print(f"[magenta][DEBUG][/magenta]\t{msg}")

    def critical(self, msg):
        """不可恢复的错误，直接退出"""
        err_console.print(
            f"[bold red]====== [CRITICAL] {msg} ======[/bold red]",
        )
        exit(1)


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
            yn = input("是否删除? (y/n)")
            if yn == "y":
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
    repo_name: str  # 仓库名

    git_master: str = "github.com"  # git主仓库名，如：github.com
    user_name: str = "vixlang"  # 用户名

    branch_name: str | None = None  # 分支名

    @property
    def pack_path(self, parent: Path = Config.VIX_LIBS_PATH) -> Path:
        return parent / self.git_master / self.user_name / self.repo_name

    # 计算属性
    @property
    def git_url(self):
        return f"https://{self.git_master}/{self.user_name}/{self.repo_name}"

    @property
    def full_name(self):
        return f"{self.git_master}:{self.user_name}.{self.repo_name}"


def parse_pack_name(package_name: str) -> PackageNameInfo:

    if "." not in package_name:
        # vnet
        package_name = f"github.com:vixlang.vlib-{package_name}"

    # 给自己留的小语法糖~
    if package_name.startswith("@"):
        package_name = "gitee.com:" + package_name[1:]

    if ":" in package_name:
        # github.com:fexcode.vnet
        master, package_name = package_name.split(":")
        if "." not in master:
            # github:fexcode.vnet
            master = master + ".com"
    else:
        master = "github.com"

    if "@" in package_name:
        # fexcode.vnet@master
        package_name, branch = package_name.split("@")
    else:
        branch = None  # git的默认分支

    package_name = package_name.replace(".", "/")

    name_splited = package_name.split("/")
    if len(name_splited) != 2:
        log.critical(f"包名格式错误: {package_name}")

    return PackageNameInfo(
        git_master=master,
        user_name=name_splited[0],
        repo_name=name_splited[1],
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
