from .base import Command
import argparse
from git import Repo
from .utils import log, parse_pack_name, ask_confirm, console, Config
from .installer import PackageInstaller, GitProgress
from pathlib import Path
import shutil
import os
import stat
from rich.panel import Panel


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class AddCmd(Command):
    NAME = "add"

    def execute(self):
        packname = getattr(self.namespace, "package", "unknown")
        global_install = getattr(self.namespace, "global_install", False)
        parent = Config.VIX_LIBS_PATH if global_install else Path.cwd() / ".vix" / "libs"
        packinfo = parse_pack_name(packname, parent=parent)
        PACK_PATH = packinfo.pack_path

        if PACK_PATH.exists():

            console.print()
            console.print(
                Panel(
                    f"[bold yellow]包已存在: [white]{packinfo.full_name}[/white][/bold yellow]\n\n"
                    f"[dim]该包已经安装在以下位置:[/dim]\n"
                    f"  [cyan]{PACK_PATH}[/cyan]\n\n"
                    f"[yellow]操作选项:[/yellow]",
                    title="[bold]⚠ 提示[/bold]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )

            if not ask_confirm("是否覆盖现有包?", default=False):
                log.warning("已取消操作")
                console.print()
                return

            shutil.rmtree(PACK_PATH, onexc=_remove_readonly)
            log.success(f"已删除旧版本的包 {packinfo.full_name}")
            console.print()

        log.section(f"添加包: {packinfo.full_name}")
        log.info(f"源: [link={packinfo.git_url}]{packinfo.git_url}[/link]")
        if packinfo.branch_name:
            log.info(f"分支: {packinfo.branch_name}")

        result = PackageInstaller.install_one(packname, parent=parent)

        if not result.success:
            if result.no_vindex:
                console.print()
                console.print(
                    Panel(
                        f"[bold yellow]包缺少 vindex.toml: [white]{packinfo.full_name}[/white][/bold yellow]\n\n"
                        f"[dim]该目录已被下载但缺少必要的 vindex.toml 文件。[/dim]\n\n"
                        f"[yellow]操作选项:[/yellow]",
                        title="[bold]⚠ 警告[/bold]",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                )
                if ask_confirm("是否删除此不完整的包?", default=True):
                    shutil.rmtree(PACK_PATH, onexc=_remove_readonly)
                    log.warning(f"已删除不完整的包 {packinfo.full_name}")
                else:
                    log.warning(f"已保留包 {packinfo.full_name}，但它可能无法使用")
                console.print()
            else:
                log.error(
                    f"下载失败\n\n[white]{result.reason}[/white]\n\n"
                    "[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • 仓库地址是否正确\n  • 是否有访问权限"
                )
            return

        log.success(f"包 {packinfo.full_name} 添加成功")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        add_parser = p.add_parser(
            "add",
            help="添加包(需要git)",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        add_parser.add_argument("package", help="需要添加的包名")
        add_parser.add_argument(
            "-g", "--global",
            dest="global_install",
            action="store_true",
            help="全局安装到 VIX_HOME 目录",
        )
        return add_parser


命令格式说明 = """
|======================== very add 命令格式说明 ========================|
[#] 格式为: 
[>]     very add git主仓库地址:用户名.git仓库项目名@分支名
[/] 
[#] 注意：默认仓库为 github.com
[/] 
[#] 示例：
[-]     very add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库  
[-]     very add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支      
[-]     very add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库  
[-]     very add gitee:fexcode.vnet@master   # .com 可以省略  
[-]     very add @fexcode.vnet               # @符号开头默认为 gitee.com
|==================================================================|
"""
