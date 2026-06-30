import os
import shutil
import stat
import subprocess
from pathlib import Path

from pyrsult import Result, Success, Failure

from ._error import Error, GitClone, GitPull
from .types import Config


VSTD_URL = "https://github.com/vixlang/vstd"


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def sync_std() -> Result[Path, Error]:
    std_path = Config.VIX_HOME / "std"
    std_path.mkdir(parents=True, exist_ok=True)

    git_dir = std_path / ".git"
    if git_dir.exists():
        cmd = ["git", "-C", str(std_path), "pull"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return Failure(GitPull(path=str(std_path), detail=result.stderr.strip()))

        is_updated = "Already up to date" not in result.stdout and "已经是最新的" not in result.stdout
        if is_updated:
            return Success(std_path)
        else:
            return Success(std_path)
    else:
        shutil.rmtree(std_path, onexc=_remove_readonly)
        std_path.mkdir(parents=True, exist_ok=True)

        cmd = ["git", "clone", VSTD_URL, str(std_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return Failure(GitClone(url=VSTD_URL, detail=result.stderr.strip()))

        return Success(std_path)
