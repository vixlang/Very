from .base import Command
import argparse
from git import Repo, remote
from .utils import log, VIndexTool, parse_pack_name, ask_confirm, console
import shutil
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, TransferSpeedColumn


class GitProgress(remote.RemoteProgress):
    def __init__(self, progress, package_name):
        super().__init__()
        self.progress = progress
        self.package_name = package_name
        self.task_id = None
        self.current_op = ""
        
    def _get_operation_name(self, op_code):
        """获取操作名称"""
        op_map = {
            remote.RemoteProgress.COUNTING: "统计对象",
            remote.RemoteProgress.COMPRESSING: "压缩对象",
            remote.RemoteProgress.WRITING: "写入对象",
            remote.RemoteProgress.RECEIVING: "接收对象",
            remote.RemoteProgress.RESOLVING: "解析差异",
        }
        return op_map.get(op_code, "处理中")

    def update(self, op_code, cur_count, max_count=None, message=""):
        if self.task_id is None:
            # 第一次调用时创建任务
            op_name = self._get_operation_name(op_code)
            self.task_id = self.progress.add_task(
                f"[cyan]克隆 {self.package_name}[/cyan] - {op_name}",
                total=max_count if max_count and max_count > 0 else None
            )
            self.current_op = op_name
        
        # 检查操作是否变化
        new_op = self._get_operation_name(op_code)
        if new_op != self.current_op:
            self.current_op = new_op
            self.progress.update(
                self.task_id,
                description=f"[cyan]克隆 {self.package_name}[/cyan] - {new_op}"
            )
        
        # 更新进度
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
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            git_progress = GitProgress(progress, packinfo.full_name)
            try:
                Repo.clone_from(
                    packinfo.git_url,
                    PACK_PATH,
                    branch=packinfo.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                log.error(f"下载失败\n\n[white]{str(e)}[/white]\n\n[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • 仓库地址是否正确\n  • 是否有访问权限")
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
|======================== vpm add 命令格式说明 ========================|
[#] 格式为: 
[>]     vpm add git主仓库地址:用户名.git仓库项目名@分支名
[/] 
[#] 注意：默认仓库为 github.com
[/] 
[#] 示例：
[-]     vpm add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库  
[-]     vpm add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支      
[-]     vpm add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库  
[-]     vpm add gitee:fexcode.vnet@master   # .com 可以省略  
[-]     vpm add @fexcode.vnet               # @符号开头默认为 gitee.com
|==================================================================|
"""
