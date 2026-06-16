from .base import Command as Command
from . import (
    cmd_add,
    cmd_build,
    cmd_del,
    cmd_list,
    cmd_prune,
    cmd_init,
    cmd_search,
    cmd_install,
    cmd_update,
    cmd_run,
)
from .utils import log as log, console as console

CMD_REGISTRY: dict[str, dict] = {
    "add": {"cls": cmd_add.AddCmd, "color": "green", "desc": "添加包"},
    "build": {"cls": cmd_build.BuildCmd, "color": "cyan", "desc": "编译 Vix 项目"},
    "run": {"cls": cmd_run.RunCmd, "color": "yellow", "desc": "编译并运行 Vix 项目"},
    "del": {"cls": cmd_del.DelCmd, "color": "red", "desc": "删除包"},
    "list": {"cls": cmd_list.ListCmd, "color": "cyan", "desc": "列出已安装的包"},
    "prune": {
        "cls": cmd_prune.PruneCmd,
        "color": "yellow",
        "desc": "清理无效包和空目录",
    },
    "init": {"cls": cmd_init.InitCmd, "color": "magenta", "desc": "初始化新项目"},
    "search": {"cls": cmd_search.SearchCmd, "color": "blue", "desc": "搜索可用的包"},
    "install": {
        "cls": cmd_install.InstallCmd,
        "color": "green",
        "desc": "安装 vindex.toml 中声明的所有依赖",
    },
    "update": {
        "cls": cmd_update.UpdateCmd,
        "color": "cyan",
        "desc": "更新已安装的包",
    },
}

cmds: list[type[Command]] = [entry["cls"] for entry in CMD_REGISTRY.values()]
