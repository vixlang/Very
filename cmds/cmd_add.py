from .base import Command
import argparse
from git import Repo, remote
from .utils import log, VIndexTool, parse_pack_name
import shutil

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

from tqdm import tqdm


class TqdmProgress(remote.RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = tqdm(unit="objects", desc="Cloning")

    def update(self, op_code, cur_count, max_count=None, message=""):
        if max_count and not self.pbar.total:
            self.pbar.total = max_count
        new_count = cur_count - self.pbar.n
        self.pbar.update(new_count)

    def __call__(self, op_code, cur_count, max_count=None, message=""):
        self.update(op_code, cur_count, max_count, message)

    def __del__(self):
        if hasattr(self, "pbar"):
            self.pbar.close()


class AddCmd(Command):
    NAME = "add"

    def execute(self):
        packname = getattr(self.namespace, "package", "unknown")
        packinfo = parse_pack_name(packname)

        PACK_PATH = packinfo.pack_path

        if PACK_PATH.exists():
            log.warning(f"包 {packinfo.full_name} 已经存在!")
            yn = input("是否覆盖? (y/n): ")
            if yn.lower() != "y":
                log.warning("已取消操作")
                return
            else:
                shutil.rmtree(PACK_PATH)
                log.success(f"删除包 {packinfo.full_name} 成功")

        log.info(f"开始下载包 {packinfo.git_url} ...")

        try:
            Repo.clone_from(
                f"{packinfo.git_url}",
                PACK_PATH,
                branch=packinfo.branch_name,
                progress=TqdmProgress(),
            )
        except Exception as e:
            log.error(f"下载包 {packinfo.full_name} 失败: {e}")
            return

        log.info(f"下载包 {packinfo.full_name} 成功，正在检查包信息 ...")

        content = VIndexTool(PACK_PATH).content(
            package_name=packinfo.full_name,
        )

        log.success(f"增加包 {packinfo.full_name} 成功")
        log.debug(content)

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        add_parser = p.add_parser(
            "add",
            help="添加包(需要git)",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        add_parser.add_argument("package", help="需要添加的包名")
        return add_parser
