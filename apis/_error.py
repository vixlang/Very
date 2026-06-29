from dataclasses import dataclass


@dataclass
class NotFound:
    kind: str
    name: str


@dataclass
class Validation:
    reason: str


@dataclass
class IOError:
    path: str
    detail: str


@dataclass
class GitClone:
    url: str
    detail: str


@dataclass
class GitPull:
    path: str
    detail: str


@dataclass
class Compile:
    exit_code: int
    output: str


@dataclass
class Network:
    url: str
    status: int | None
    detail: str


Error = NotFound | Validation | IOError | GitClone | GitPull | Compile | Network
