import shutil
import subprocess
import sys
import tomllib
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from pyrsult import Result, Success, Failure

from ._error import Error, Compile, IOError, NotFound
from ._event import Event, Progress, Log


@dataclass
class CheckReport:
    passed: bool
    errors: list[str]
    file_count: int


def _has_gcc() -> bool:
    return shutil.which("gcc") is not None


def _find_entrypoint(root: Path = Path.cwd()) -> Result[Path, NotFound]:
    vindex = root / "vindex.toml"
    entrypoint = "main.vix"
    try:
        with open(vindex, "rb") as f:
            data = tomllib.load(f)
        entrypoint = data.get("project", {}).get("entrypoint", "main.vix")
    except Exception:
        pass
    path = root / entrypoint
    if path.exists():
        return Success(path.resolve())
    return Failure(NotFound(kind="file", name=str(path)))


def _extract_output_name(args: list[str]) -> tuple[str | None, list[str]]:
    output = None
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
            continue
        rest.append(args[i])
        i += 1
    return output, rest


def _extract_input_file(args: list[str]) -> tuple[Path | None, list[str]]:
    rest: list[str] = []
    input_file = None
    for a in args:
        if a.endswith(".vix") and input_file is None:
            input_file = Path(a).resolve()
        else:
            rest.append(a)
    return input_file, rest


def _default_output_name(root: Path = Path.cwd()) -> str:
    vindex = root / "vindex.toml"
    try:
        with open(vindex, "rb") as f:
            data = tomllib.load(f)
        name = data.get("project", {}).get("name", "main")
    except Exception:
        name = "main"
    return f"{name}.exe" if sys.platform == "win32" else name


def build_project(
    root: Path, extra_args: list[str]
) -> Generator[Event, None, Result[Path, Compile | IOError]]:
    yield Log(level="info", msg="开始编译")

    output_name, args_rest = _extract_output_name(extra_args)
    if output_name is None:
        output_name = _default_output_name(root)

    input_file, vixc_flags = _extract_input_file(args_rest)
    if input_file is None:
        r = _find_entrypoint(root)
        if isinstance(r, Failure):
            return Failure(
                IOError(path=str(root / "main.vix"), detail="入口文件不存在")
            )
        input_file = r.unwrap()

    temp_dir = root / ".vix" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = (root / output_name).resolve()
    has_gcc = _has_gcc()

    yield Progress(msg=f"编译: {input_file.name}", pct=0.3)

    if has_gcc:
        obj_path = temp_dir / f"{input_file.stem}.o"
        cmd = ["vixc", str(input_file), "-obj", str(obj_path)] + vixc_flags
        yield Log(level="info", msg=f"vixc: {' '.join(cmd)}")
        r1 = subprocess.run(cmd, cwd=root)
        if r1.returncode != 0:
            return Failure(
                Compile(
                    exit_code=r1.returncode, output=f"编译失败: 返回码 {r1.returncode}"
                )
            )

        yield Progress(msg="链接", pct=0.7)
        link_cmd = ["gcc", str(obj_path), "-o", str(output_path)]
        yield Log(level="info", msg=f"gcc: {' '.join(link_cmd)}")
        r2 = subprocess.run(link_cmd, cwd=root)
        if r2.returncode != 0:
            return Failure(
                Compile(
                    exit_code=r2.returncode, output=f"链接失败: 返回码 {r2.returncode}"
                )
            )
    else:
        cmd = ["vixc", str(input_file)] + vixc_flags
        yield Log(level="info", msg=f"vixc: {' '.join(cmd)}")
        r = subprocess.run(cmd, cwd=root)
        if r.returncode != 0:
            return Failure(
                Compile(
                    exit_code=r.returncode, output=f"编译失败: 返回码 {r.returncode}"
                )
            )

    yield Progress(msg="完成", pct=1.0)
    return Success(output_path)


def build_and_run(
    root: Path, extra_args: list[str], keep: bool = False
) -> Generator[Event, None, Result[int, Error]]:
    result = None
    gen = build_project(root, extra_args)
    try:
        while True:
            event = gen.send(None)
            yield event
    except StopIteration as e:
        result = e.value

    if isinstance(result, Failure):
        return result

    output_path = result.unwrap()
    yield Log(level="info", msg=f"运行: {output_path}")

    if not output_path.exists():
        return Failure(IOError(path=str(output_path), detail="编译产物不存在"))

    r = subprocess.run([str(output_path)], cwd=root)

    if not keep:
        output_path.unlink(missing_ok=True)

    return Success(r.returncode)


def _resolve_files(patterns: list[str], root: Path) -> list[Path]:
    if not patterns:
        r = _find_entrypoint(root)
        if isinstance(r, Success):
            return [r.unwrap()]
        return []

    files: list[Path] = []
    seen: set[Path] = set()
    for p in patterns:
        path = root / p
        if path.is_dir():
            for f in sorted(path.rglob("*.vix")):
                if f not in seen:
                    files.append(f)
                    seen.add(f)
        else:
            expanded = list(root.glob(p)) if ("*" in p or "?" in p) else [path]
            for f in expanded:
                resolved = f.resolve()
                if f.exists() and resolved not in seen:
                    files.append(f)
                    seen.add(resolved)
    return files


def check_files(
    patterns: list[str], root: Path = Path.cwd()
) -> Result[CheckReport, Error]:
    files = _resolve_files(patterns, root)
    if not files:
        return Failure(
            NotFound(kind="file", name=", ".join(patterns) if patterns else "main.vix")
        )

    errors: list[str] = []
    for f in files:
        r = subprocess.run(
            ["vixc", str(f), "--check"], cwd=root, capture_output=True, text=True
        )
        if r.returncode != 0:
            stderr = r.stderr.strip() or f"退出码 {r.returncode}"
            errors.append(f"{f}: {stderr}")

    return Success(
        CheckReport(passed=len(errors) == 0, errors=errors, file_count=len(files))
    )
