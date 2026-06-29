import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

_VIX_HOME = Path(os.getenv("VIX_HOME", "./.vix"))


@dataclass(frozen=True)
class Config:
    VIX_HOME: Path = _VIX_HOME
    VIX_LIBS_PATH: Path = _VIX_HOME / "libs"
    VIX_TOOLS_PATH: Path = _VIX_HOME / "tools"

    @staticmethod
    def local_libs_path() -> Path:
        return Path.cwd() / ".vix" / "libs"


DEFAULT_HOST = "github.com"
DEFAULT_ORG = "vixlang"
VLIB_PREFIX = "vlib-"
VTOOL_PREFIX = "vtool-"


@dataclass
class PackageNameInfo:
    repo_name: str
    git_master: str = "github.com"
    user_name: str = "vixlang"
    branch_name: str | None = None
    parent: Path | None = None
    _default_parent: ClassVar[Path] = Config.VIX_LIBS_PATH

    @property
    def pack_path(self) -> Path:
        parent = self.parent or PackageNameInfo._default_parent
        path = parent / self.git_master / self.user_name / self.repo_name
        try:
            path.resolve().relative_to(parent.resolve())
        except ValueError:
            raise ValueError(f"包路径穿越检测: {path} 不在 {parent} 下")
        return path

    @property
    def git_url(self):
        return f"https://{self.git_master}/{self.user_name}/{self.repo_name}"

    @property
    def full_name(self):
        return f"{self.git_master}:{self.user_name}.{self.repo_name}"


def parse_pack_name(
    package_name: str, parent: Path | None = None, bare_prefix: str = VLIB_PREFIX
) -> PackageNameInfo:
    original = package_name
    branch = None
    default_host = DEFAULT_HOST

    if package_name.startswith("@") and "://" not in package_name:
        default_host = "gitee.com"
        package_name = package_name[1:]

    if "://" in package_name:
        parsed = urlparse(package_name)
        master = parsed.hostname or parsed.netloc
        path = parsed.path.lstrip("/")
        path = re.sub(r"\.git$", "", path)
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"URL 格式无法提取用户/仓库: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    if "@" in package_name:
        rest, _, possible_branch = package_name.rpartition("@")
        if (
            possible_branch
            and "/" not in possible_branch
            and ":" not in possible_branch
        ):
            branch = possible_branch
            package_name = rest

    if "@" in package_name and ":" in package_name:
        user_host, _, path = package_name.partition(":")
        host = user_host.split("@")[-1]
        master = host if "." in host else host + ".com"
        path = path.strip()
        path = re.sub(r"\.git$", "", path)
        if "/" in path:
            parts = path.split("/")
        else:
            parts = path.replace(".", "/").split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"SCP 格式无法解析路径: {package_name}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    if ":" in package_name:
        master, path = package_name.split(":", 1)
        if "." not in master:
            master += ".com"
        path = re.sub(r"\.git$", "", path)
        if "/" not in path and "." not in path:
            path = f"{DEFAULT_ORG}.{VLIB_PREFIX}{path}"
        if "/" not in path:
            path = path.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
        else:
            raise ValueError(f"包名格式错误: {original}")
        return PackageNameInfo(
            git_master=master,
            user_name=user_name,
            repo_name=repo_name,
            branch_name=branch,
            parent=parent,
        )

    if "/" in package_name:
        parts = package_name.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            raise ValueError(f"包名格式错误: {original}")
    elif "." in package_name:
        path = package_name.replace(".", "/")
        parts = path.split("/")
        if len(parts) >= 2:
            user_name, repo_name = parts[0], parts[1]
            repo_name = re.sub(r"\.git$", "", repo_name)
        else:
            raise ValueError(f"包名格式错误: {original}")
    else:
        user_name = DEFAULT_ORG
        repo_name = f"{bare_prefix}{package_name}"

    return PackageNameInfo(
        git_master=default_host,
        user_name=user_name,
        repo_name=repo_name,
        branch_name=branch,
        parent=parent,
    )


def parse_tool_name(package_name: str, parent: Path | None = None) -> PackageNameInfo:
    return parse_pack_name(package_name, parent=parent, bare_prefix=VTOOL_PREFIX)
