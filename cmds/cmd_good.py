"""very good — 检查 Vix 语法和类型"""

from pathlib import Path

import typer
from pyrsult import Failure, Success

from apis.build import check_files

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def good(
    files: list[str] = typer.Argument(
        None, help="要检查的 .vix 文件或目录 (支持通配符, 默认: main.vix)"
    ),
):
    match check_files(files or [], Path.cwd()):
        case Success(report):
            if report.passed:
                log.ok("全部通过")
            else:
                for err in report.errors:
                    log.error(err)
            raise typer.Exit(code=0 if report.passed else 1)
        case Failure(err):
            log.error(str(err))
            raise typer.Exit(code=1)
