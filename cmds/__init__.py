from .base import Command as Command
from . import add
from ._utils import log as log


cmd_list: list[type[Command]] = [add.AddCmd]
