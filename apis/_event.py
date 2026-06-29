from dataclasses import dataclass


@dataclass
class Progress:
    msg: str
    pct: float | None = None


@dataclass
class Log:
    level: str
    msg: str


Event = Progress | Log
