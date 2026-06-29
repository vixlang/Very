"""very init — 初始化新项目"""

from pathlib import Path

import typer

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def init(
    name: str = typer.Argument(..., help="项目名称"),
    dir: str = typer.Option(None, "-d", "--dir", help="初始化目录（默认使用项目名称）"),
):
    """初始化一个新的 Vix 项目"""
    project_name = name
    project_path = Path(dir or project_name)

    if project_path.exists():
        log.error(f"目录 '{project_path}' 已存在")
        raise typer.Exit(code=1)

    try:
        project_path.mkdir(parents=True)

        (project_path / "vindex.toml").write_text(f"""[project]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = []
edition = "2024"

deps = []
""")

        (project_path / "src").mkdir()

        (project_path / "src" / "lib.vix").write_text("""pub fn greet() {
    print("Hello from src/lib.vix!")
}
""")

        (project_path / "main.vix").write_text("""import "src/lib.vix"

fn main(): i32 {
    greet()
    return 0
}
""")

        (project_path / ".gitignore").write_text("""# Vix
*.o
*.out
*.exe
target/
.very/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
""")

        (project_path / "README.md").write_text(f"""# {project_name}

Vix 项目

## 构建

```bash
very build
```
""")

        log.ok(f"成功创建项目 '{project_name}'")

    except Exception as e:
        log.error(f"创建项目失败: {e}")
        raise typer.Exit(code=1)
