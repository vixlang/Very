from .base import Command
import argparse
from .utils import log, parse_pack_name
import shutil


命令格式说明 = """
|======================== vpm del 命令格式说明 ========================|
[#] 格式为: 
[>]     vpm del git主仓库地址:用户名.git仓库项目名
[/] 
[#] 注意：默认仓库为 github.com
[/] 
[#] 示例：
[-]     vpm del fexcode.vnet                # 删除 github.com/fexcode/vnet 仓库  
[-]     vpm del gitee.com:fexcode.vnet      # 删除 gitee.com/fexcode/vnet 仓库  
[-]     vpm del gitee:fexcode.vnet          # .com 可以省略  
[-]     vpm del @fexcode.vnet               # @符号开头默认为 gitee.com
|==================================================================|
"""


class DelCmd(Command):
    NAME = "del"


    def execute(self):
        package_name = getattr(self.namespace, "package", "unknown")

        pack_info = parse_pack_name(package_name)
        PACK_PATH = pack_info.pack_path

        if not PACK_PATH.exists():
            log.warning(f"包 {pack_info.full_name} 不存在!")
            return

        log.warning(f"即将删除包 {pack_info.full_name}")
        yn = input("确认删除? (y/n): ")
        if yn.lower() != "y":
            log.warning("已取消操作")
            return

        try:
            shutil.rmtree(PACK_PATH)
            log.success(f"删除包 {pack_info.full_name} 成功")
        except Exception as e:
            log.error(f"删除包 {pack_info.full_name} 失败: {e}")
            return


    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        del_parser = p.add_parser(
            "del",
            help="删除包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        del_parser.add_argument("package", help="需要删除的包名")
        return del_parser
