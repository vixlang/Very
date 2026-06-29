import json
import os
import re
import ssl
import stat
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from rich.console import Console
from rich.prompt import Confirm

console = Console()
err_console = Console(file=sys.stderr)


def ask_confirm(prompt: str, default: bool = False) -> bool:
    return Confirm.ask(prompt, default=default)


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


def iter_package_dirs(libs_path: Path) -> Iterator[tuple[Path, Path, Path, str]]:
    for md in libs_path.iterdir():
        if not md.is_dir():
            continue
        for ud in md.iterdir():
            if not ud.is_dir():
                continue
            for rd in ud.iterdir():
                if not rd.is_dir():
                    continue
                yield md, ud, rd, f"{md.name}:{ud.name}.{rd.name}"


def iter_empty_dirs(libs_path: Path) -> Iterator[Path]:
    for md in sorted(libs_path.iterdir(), reverse=True):
        if not md.is_dir():
            continue
        for ud in sorted(md.iterdir(), reverse=True):
            if not ud.is_dir():
                continue
            for rd in sorted(ud.iterdir(), reverse=True):
                if not rd.is_dir():
                    continue
                if not any(rd.iterdir()):
                    yield rd
            if not any(ud.iterdir()):
                yield ud
        if not any(md.iterdir()):
            yield md


class VIndexTool:
    def __init__(self, dir_path: Path):
        self.path = dir_path / "vindex.toml"

    def content(self) -> dict[str, object] | None:
        import tomllib

        if not self.path.exists():
            return None
        with open(self.path, "rb") as f:
            return tomllib.load(f)


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


def build_dep_tree(libs_path: Path, root_deps: list[str]) -> set[str]:
    import tomllib

    referenced: set[str] = set()
    queue = list(root_deps)
    while queue:
        spec = queue.pop(0)
        if spec in referenced:
            continue
        info = parse_pack_name(spec, parent=libs_path)
        referenced.add(info.full_name)
        vindex_path = info.pack_path / "vindex.toml"
        if vindex_path.exists():
            with open(vindex_path, "rb") as f:
                data = tomllib.load(f)
            sub_deps = data.get("project", {}).get("deps", [])
            sub_legacy = list(data.get("dependencies", {}).keys())
            for d in dict.fromkeys(sub_deps + sub_legacy):
                if d not in referenced:
                    queue.append(d)
    return referenced


def add_dep_to_vindex(pack_spec: str) -> bool:
    vindex_path = Path.cwd() / "vindex.toml"
    if not vindex_path.exists():
        return False

    import tomllib

    import tomli_w

    with open(vindex_path, "rb") as f:
        data = tomllib.load(f)

    deps: list = data.get("project", {}).get("deps", [])
    if not isinstance(deps, list):
        deps = []
    legacy = list(data.get("dependencies", {}).keys())
    existing = list(dict.fromkeys(deps + legacy))

    if pack_spec in existing:
        return False

    data.setdefault("project", {})["deps"] = existing + [pack_spec]
    data.pop("dependencies", None)

    with open(vindex_path, "wb") as f:
        tomli_w.dump(data, f)

    return True


def create_git_progress(package_name: str):
    from rich.progress import (
        BarColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )

    return Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _get_entrypoint(vindex_path: str = "vindex.toml") -> str:
    import tomllib

    try:
        with open(vindex_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("entrypoint", "main.vix")
    except Exception:
        return "main.vix"


def _read_cache(cache_file: Path, expiry: int = 3600):
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["timestamp"] > expiry:
            return None
        return data["packages"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(cache_dir: Path, cache_file: Path, packages):
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        data = {"timestamp": time.time(), "packages": packages}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _clear_cache(cache_file: Path):
    if cache_file.exists():
        cache_file.unlink()


def _fetch_github_packages(prefix: str, include_extra: str | None = None):
    packages = []
    page = 1
    per_page = 100
    ctx = ssl.create_default_context()

    while True:
        url = f"https://api.github.com/orgs/{DEFAULT_ORG}/repos?per_page={per_page}&page={page}&type=sources"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Very-Project-Manager",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data:
                break
            for repo in data:
                if repo["name"].startswith(prefix) or (
                    include_extra and repo["name"] == include_extra
                ):
                    packages.append(
                        {
                            "name": repo["name"],
                            "description": repo["description"] or "无描述",
                            "stars": repo["stargazers_count"],
                            "language": repo["language"] or "Unknown",
                            "updated": repo["updated_at"][:10],
                            "url": repo["html_url"],
                        }
                    )
            if len(data) < per_page:
                break
            page += 1

    packages.sort(key=lambda x: x["stars"], reverse=True)
    return packages


def _fetch_with_retry(fetch_fn, max_retries=3, retry_delay=2):
    from rich.live import Live
    from rich.spinner import Spinner

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                time.sleep(retry_delay)
            with Live(
                Spinner("dots", text="正在从 GitHub 获取数据..."),
                refresh_per_second=10,
                transient=True,
            ):
                result = fetch_fn()
            return result
        except urllib.error.HTTPError as e:
            last_exception = e
            if e.code == 403:
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    time.sleep(wait_time)
                    continue
                raise Exception("GitHub API 速率限制已用完，请稍后再试")
            elif e.code == 404:
                raise Exception("GitHub API 端点不存在")
            elif e.code >= 500:
                if attempt < max_retries:
                    continue
                raise Exception(f"GitHub API 服务器错误 ({e.code})")
            else:
                raise Exception(f"HTTP 错误: {e.code}")
        except urllib.error.URLError as e:
            last_exception = e
            if attempt < max_retries:
                continue
            raise Exception("网络错误，请检查网络连接")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    if last_exception:
        raise Exception(f"经过 {max_retries} 次重试后仍然失败")


def _sort_packages(packages, sort_by):
    if sort_by == "stars":
        return sorted(packages, key=lambda x: x["stars"], reverse=True)
    elif sort_by == "updated":
        return sorted(packages, key=lambda x: x["updated"], reverse=True)
    elif sort_by == "name":
        return sorted(packages, key=lambda x: x["name"].lower())
    return sorted(packages, key=lambda x: x["stars"], reverse=True)
