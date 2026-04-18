from .base import Command as Command
from . import cmd_add, cmd_del, cmd_list
from .utils import log as log


cmds: list[type[Command]] = [
    cmd_add.AddCmd,
    cmd_del.DelCmd,
    cmd_list.ListCmd,
]
