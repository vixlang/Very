from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from pathlib import Path
import os
import shutil
import stat
import subprocess
import tomllib

from pyrsult import Result, Success, Failure

from ._error import Error, IOError, GitClone, GitPull, NotFound
from ._event import Event, Progress, Log
from .types import Config, parse_pack_name
from .vindex import build_dep_tree, get_transitive_deps


@dataclass
class PackageInfo:
    host: str
    user: str
    repo: str
    full_name: str
    path: Path
    has_vindex: bool


@dataclass
class PruneReport:
    removed_invalid: list[str] = field(default_factory=list)
    removed_empty: list[str] = field(default_factory=list)
    removed_unused: list[str] = field(default_factory=list)


@dataclass
class UpdateInfo:
    full_name: str
    updated: bool


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


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


def _git_clone(
    url: str, dest: Path, branch: str | None = None
) -> Result[None, GitClone]:
    cmd = ["git", "clone", url, str(dest)]
    if branch:
        cmd.extend(["-b", branch])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return Failure(GitClone(url=url, detail=result.stderr.strip()))
        return Success(None)
    except FileNotFoundError:
        return Failure(GitClone(url=url, detail="未找到 git 命令"))
    except OSError as e:
        return Failure(GitClone(url=url, detail=str(e)))


def _git_pull(path: Path) -> Result[bool, GitPull]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "pull"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return Failure(GitPull(path=str(path), detail=result.stderr.strip()))
        already_up_to_date = (
            "Already up to date" in result.stdout or "已经是最新的" in result.stdout
        )
        return Success(not already_up_to_date)
    except FileNotFoundError:
        return Failure(GitPull(path=str(path), detail="未找到 git 命令"))
    except OSError as e:
        return Failure(GitPull(path=str(path), detail=str(e)))


def list_packages() -> Result[list[PackageInfo], Error]:
    libs_path = Config.local_libs_path()
    if not libs_path.exists():
        return Failure(NotFound("libs_path", str(libs_path)))

    packages: list[PackageInfo] = []
    for _, user_dir, repo_dir, full_name in iter_package_dirs(libs_path):
        vindex_file = repo_dir / "vindex.toml"
        packages.append(
            PackageInfo(
                host=repo_dir.parent.parent.name,
                user=user_dir.name,
                repo=repo_dir.name,
                full_name=full_name,
                path=repo_dir,
                has_vindex=vindex_file.exists(),
            )
        )
    return Success(packages)


def delete_package(spec: str) -> Result[None, Error]:
    paths_to_check = [Config.local_libs_path(), Config.VIX_LIBS_PATH]
    for libs_path in paths_to_check:
        info = parse_pack_name(spec, parent=libs_path)
        pack_path = info.pack_path
        if pack_path.exists():
            try:
                shutil.rmtree(pack_path, onexc=_remove_readonly)
            except OSError as e:
                return Failure(IOError(path=str(pack_path), detail=str(e)))
            return Success(None)
    return Failure(NotFound("package", spec))


def prune_packages(
    empty_only: bool = False,
    invalid_only: bool = False,
    remove_unused: bool = False,
) -> Result[PruneReport, Error]:
    libs_path = Config.local_libs_path()
    if not libs_path.exists():
        return Failure(NotFound("libs_path", str(libs_path)))

    report = PruneReport()

    if not empty_only:
        for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
            has_vindex = (repo_dir / "vindex.toml").exists()
            if not has_vindex:
                report.removed_invalid.append(full_name)
                shutil.rmtree(repo_dir, onexc=_remove_readonly)

    if not invalid_only:
        for empty_dir in iter_empty_dirs(libs_path):
            rel = str(empty_dir.relative_to(libs_path))
            report.removed_empty.append(rel)
            empty_dir.rmdir()

    should_find_unused = remove_unused or (not empty_only and not invalid_only)
    if should_find_unused:
        unused = _find_unused_packages(libs_path)
        for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
            if full_name in unused:
                report.removed_unused.append(full_name)
                shutil.rmtree(repo_dir, onexc=_remove_readonly)

    return Success(report)


def _find_unused_packages(libs_path: Path) -> list[str]:
    vindex_path = Path.cwd() / "vindex.toml"
    root_deps: list[str] = []
    if vindex_path.exists():
        with open(vindex_path, "rb") as f:
            data = tomllib.load(f)
        root_deps = data.get("project", {}).get("deps", [])
        legacy = list(data.get("dependencies", {}).keys())
        root_deps = list(dict.fromkeys(root_deps + legacy))

    referenced = build_dep_tree(libs_path, root_deps)
    unused: list[str] = []
    for _, _, _, full_name in iter_package_dirs(libs_path):
        if full_name not in referenced:
            unused.append(full_name)
    return unused


def install_package(
    spec: str, force_local: bool = False
) -> Generator[Event, None, Result[PackageInfo, Error]]:
    yield Log("info", f"正在安装 {spec}")

    libs_path = Config.local_libs_path()
    global_path = Config.VIX_LIBS_PATH

    info = parse_pack_name(spec, parent=libs_path)
    dest = info.pack_path

    if dest.exists():
        yield Log("info", f"包已存在: {info.full_name}")
        return Success(
            PackageInfo(
                host=info.git_master,
                user=info.user_name,
                repo=info.repo_name,
                full_name=info.full_name,
                path=dest,
                has_vindex=(dest / "vindex.toml").exists(),
            )
        )

    if not force_local:
        global_info = parse_pack_name(spec, parent=global_path)
        global_dest = global_info.pack_path
        if global_dest.exists():
            yield Log("info", f"包已存在于全局: {global_info.full_name}")
            return Success(
                PackageInfo(
                    host=global_info.git_master,
                    user=global_info.user_name,
                    repo=global_info.repo_name,
                    full_name=global_info.full_name,
                    path=global_dest,
                    has_vindex=(global_dest / "vindex.toml").exists(),
                )
            )

    libs_path.mkdir(parents=True, exist_ok=True)
    (libs_path / info.git_master).mkdir(parents=True, exist_ok=True)
    (libs_path / info.git_master / info.user_name).mkdir(parents=True, exist_ok=True)

    yield Progress(f"克隆 {info.git_url}")

    clone_result = _git_clone(info.git_url, dest, info.branch_name)
    if isinstance(clone_result, Failure):
        yield Log("error", clone_result.error.detail)
        return clone_result

    yield Log("info", "克隆完成")

    vindex_file = dest / "vindex.toml"
    has_vindex = vindex_file.exists()

    if not has_vindex:
        yield Log("warn", "包缺少 vindex.toml")

    pack_info = PackageInfo(
        host=info.git_master,
        user=info.user_name,
        repo=info.repo_name,
        full_name=info.full_name,
        path=dest,
        has_vindex=has_vindex,
    )

    if has_vindex:
        deps = get_transitive_deps(dest)
        if deps:
            yield Log("info", f"安装 {len(deps)} 个依赖...")
            for dep_spec in deps:
                yield Progress(f"安装依赖 {dep_spec}")
                dep_result = yield from install_package(
                    dep_spec, force_local=force_local
                )
                if isinstance(dep_result, Failure):
                    yield Log("error", f"依赖 {dep_spec} 安装失败: {dep_result.error}")

    return Success(pack_info)


def update_package(spec: str) -> Generator[Event, None, Result[UpdateInfo, Error]]:
    yield Log("info", f"正在更新 {spec}")

    paths_to_check = [Config.local_libs_path(), Config.VIX_LIBS_PATH]
    pack_path = None
    full_name = None

    for libs_path in paths_to_check:
        info = parse_pack_name(spec, parent=libs_path)
        if info.pack_path.exists():
            pack_path = info.pack_path
            full_name = info.full_name
            break

    if pack_path is None:
        return Failure(NotFound("package", spec))

    assert full_name is not None
    yield Progress(f"拉取 {full_name}")
    pull_result = _git_pull(pack_path)
    if isinstance(pull_result, Failure):
        return pull_result

    updated = pull_result.unwrap()
    if updated:
        yield Log("info", f"已更新 {full_name}")
    else:
        yield Log("info", f"{full_name} 已是最新")

    vindex_file = pack_path / "vindex.toml"
    if vindex_file.exists():
        deps = get_transitive_deps(pack_path)
        for dep_spec in deps:
            yield from update_package(dep_spec)

    return Success(UpdateInfo(full_name=full_name, updated=updated))


def install_dependencies(
    force_local: bool = False,
) -> Generator[Event, None, Result[list[PackageInfo], Error]]:
    vindex_path = Path.cwd() / "vindex.toml"
    if not vindex_path.exists():
        return Failure(NotFound("vindex.toml", str(vindex_path)))

    with open(vindex_path, "rb") as f:
        data = tomllib.load(f)

    dep_specs = data.get("project", {}).get("deps", [])
    legacy = list(data.get("dependencies", {}).keys())
    dep_specs = list(dict.fromkeys(dep_specs + legacy))

    if not dep_specs:
        yield Log("info", "没有依赖需要安装")
        return Success([])

    installed: list[PackageInfo] = []
    for dep_spec in dep_specs:
        yield Log("info", f"检查依赖: {dep_spec}")
        result = yield from install_package(dep_spec, force_local=force_local)
        if isinstance(result, Success):
            installed.append(result.unwrap())
        else:
            yield Log("error", f"依赖 {dep_spec} 安装失败: {result.error}")

    return Success(installed)
