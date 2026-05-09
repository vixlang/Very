from .base import Command
import argparse
from git import Repo, remote
from .utils import log, VIndexTool, parse_pack_name, ask_confirm, console
import shutil
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn


class GitProgress(remote.RemoteProgress):
    def __init__(self, progress):
        super().__init__()
        self.progress = progress
        self.task_id = progress.add_task("[cyan]克隆中", total=None)

    def update(self, op_code, cur_count, max_count=None, message=""):
        if max_count and max_count > 0:
            self.progress.update(self.task_id, total=max_count, completed=cur_count)

    def __call__(self, op_code, cur_count, max_count=None, message=""):
        self.update(op_code, cur_count, max_count, message)


class AddCmd(Command):
    NAME = "add"

    def execute(self):
        packname = getattr(self.namespace, "package", "unknown")
        packinfo = parse_pack_name(packname)
        PACK_PATH = packinfo.pack_path

        if PACK_PATH.exists():
            log.warning(f"包 [bold]{packinfo.full_name}[/bold] 已存在")
            if not ask_confirm("是否覆盖?"):
                log.warning("已取消操作")
                return
            shutil.rmtree(PACK_PATH)
            log.success(f"已删除包 {packinfo.full_name}")

        log.section(f"添加包: {packinfo.full_name}")
        log.info(f"源: [link={packinfo.git_url}]{packinfo.git_url}[/link]")
        if packinfo.branch_name:
            log.info(f"分支: {packinfo.branch_name}")

        with Progress(
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            git_progress = GitProgress(progress)
            try:
                Repo.clone_from(
                    packinfo.git_url,
                    PACK_PATH,
                    branch=packinfo.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                log.error(f"下载失败: {e}")
                return

        log.info("正在检查包信息...")
        VIndexTool(PACK_PATH).content(package_name=packinfo.full_name)
        log.success(f"包 {packinfo.full_name} 添加成功")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        add_parser = p.add_parser(
            "add",
            help="添加包(需要git)",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        add_parser.add_argument("package", help="需要添加的包名")
        return add_parser


命令格式说明 = """
|======================== xpm add 命令格式说明 ========================|
[#] 格式为: 
[>]     xpm add git主仓库地址:用户名.git仓库项目名@分支名
[/] 
[#] 注意：默认仓库为 github.com
[/] 
[#] 示例：
[-]     xpm add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库  
[-]     xpm add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支      
[-]     xpm add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库  
[-]     xpm add gitee:fexcode.vnet@master   # .com 可以省略  
[-]     xpm add @fexcode.vnet               # @符号开头默认为 gitee.com
|==================================================================|
"""
