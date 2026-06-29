import shutil
import subprocess
import sys
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from pyrsult import Result, Success, Failure

from ._error import Error, GitClone, GitPull, Compile, IOError, NotFound, Validation
from ._event import Event, Progress, Log
from .types import Config, parse_tool_name
from .vindex import VIndexTool


@dataclass
class ToolInfo:
    full_name: str
    binary_path: Path


@dataclass
class UpdateInfo:
    full_name: str
    updated: bool
    binary_path: Path | None = None


def _has_gcc() -> bool:
    return shutil.which("gcc") is not None


def _get_entrypoint(dir_path: Path) -> str:
    import tomllib

    vindex = dir_path / "vindex.toml"
    if vindex.exists():
        try:
            with open(vindex, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("entrypoint", "main.vix")
        except Exception:
            pass
    return "main.vix"


def _clone_repo(url: str, dest: Path, branch: str | None = None) -> Result[None, GitClone]:
    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.extend([url, str(dest)])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return Failure(GitClone(url=url, detail=r.stderr.strip()))
    return Success(None)


def _pull_repo(repo_path: Path) -> Result[None, GitPull]:
    r = subprocess.run(
        ["git", "-C", str(repo_path), "pull"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return Failure(GitPull(path=str(repo_path), detail=r.stderr.strip()))
    return Success(None)


def _compile_tool(source_dir: Path, binary_path: Path) -> Result[Path, Compile | IOError]:
    entry_name = _get_entrypoint(source_dir)
    input_file = (source_dir / entry_name).resolve()

    if not input_file.exists():
        return Failure(IOError(path=str(input_file), detail=f"入口文件不存在: {input_file}"))

    binary_path.parent.mkdir(parents=True, exist_ok=True)

    if _has_gcc():
        temp_dir = (source_dir / ".vix" / "temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        obj_path = temp_dir / f"{input_file.stem}.o"

        r1 = subprocess.run(
            ["vixc", str(input_file), "-obj", str(obj_path)],
            capture_output=True,
            text=True,
            cwd=str(source_dir),
        )
        if r1.returncode != 0:
            return Failure(Compile(exit_code=r1.returncode, output=r1.stderr.strip()))

        r2 = subprocess.run(
            ["gcc", str(obj_path), "-o", str(binary_path)],
            capture_output=True,
            text=True,
        )
        if r2.returncode != 0:
            return Failure(Compile(exit_code=r2.returncode, output=r2.stderr.strip()))
    else:
        r = subprocess.run(
            ["vixc", str(input_file), "-o", str(binary_path)],
            capture_output=True,
            text=True,
            cwd=str(source_dir),
        )
        if r.returncode != 0:
            return Failure(Compile(exit_code=r.returncode, output=r.stderr.strip()))

    if not binary_path.exists():
        return Failure(IOError(path=str(binary_path), detail="编译产物未生成"))

    return Success(binary_path)


def install_tool(packname: str) -> Generator[Event, None, Result[ToolInfo, Error]]:
    yield Log("info", f"安装工具: {packname}")

    info = parse_tool_name(packname, parent=Config.VIX_TOOLS_PATH)
    pack_path = info.pack_path

    if not pack_path.exists():
        yield Log("info", f"源: {info.git_url}")
        if info.branch_name:
            yield Log("info", f"分支: {info.branch_name}")
        yield Progress("克隆仓库...", 0)
        clone_result = _clone_repo(info.git_url, pack_path, info.branch_name)
        if clone_result.is_failure():
            if pack_path.exists():
                shutil.rmtree(pack_path, ignore_errors=True)
            return Failure(clone_result.error())
        yield Progress("仓库克隆完成", 100)
    else:
        yield Log("info", f"工具 {info.full_name} 已存在，重新编译")

    vindex = VIndexTool(pack_path)
    content = vindex.content()
    if content is None:
        return Failure(Validation(reason=f"{info.full_name} 缺少 vindex.toml"))

    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (Config.VIX_TOOLS_PATH / binary_name).resolve()

    yield Log("info", f"正在编译 {project_name} ...")
    yield Progress("编译中...", 50)
    compile_result = _compile_tool(pack_path, binary_path)
    if compile_result.is_failure():
        return Failure(compile_result.error())

    yield Progress("编译完成", 100)
    yield Log("ok", f"工具 {project_name} 已安装: {binary_path}")

    return Success(ToolInfo(full_name=info.full_name, binary_path=binary_path))


def delete_tool(packname: str) -> Result[None, Error]:
    info = parse_tool_name(packname, parent=Config.VIX_TOOLS_PATH)
    pack_path = info.pack_path

    if not pack_path.exists():
        return Failure(NotFound(kind="tool", name=info.full_name))

    content = VIndexTool(pack_path).content()
    project_name = info.repo_name
    if content is not None:
        project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_path = Config.VIX_TOOLS_PATH / f"{project_name}{suffix}"

    if binary_path.exists():
        binary_path.unlink()

    shutil.rmtree(pack_path, ignore_errors=True)

    for d in [pack_path.parent, pack_path.parent.parent]:
        if d.exists() and not any(d.iterdir()):
            d.rmdir()

    return Success(None)


def update_tool(packname: str) -> Generator[Event, None, Result[ToolInfo, Error]]:
    yield Log("info", f"更新工具: {packname}")

    info = parse_tool_name(packname, parent=Config.VIX_TOOLS_PATH)
    pack_path = info.pack_path

    if not pack_path.exists():
        yield Log("info", "工具未安装，正在安装...")
        result = yield from install_tool(packname)
        return result

    yield Log("info", "正在拉取更新...")
    yield Progress("拉取中...", 30)
    pull_result = _pull_repo(pack_path)
    if pull_result.is_failure():
        return Failure(pull_result.error())

    vindex = VIndexTool(pack_path)
    content = vindex.content()
    if content is None:
        return Failure(Validation(reason=f"{info.full_name} 缺少 vindex.toml"))

    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (Config.VIX_TOOLS_PATH / binary_name).resolve()

    yield Log("info", "正在重新编译...")
    yield Progress("编译中...", 60)
    compile_result = _compile_tool(pack_path, binary_path)
    if compile_result.is_failure():
        return Failure(compile_result.error())

    yield Progress("更新完成", 100)
    yield Log("ok", f"工具 {info.full_name} 已更新")

    return Success(ToolInfo(full_name=info.full_name, binary_path=binary_path))
