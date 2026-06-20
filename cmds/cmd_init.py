from .base import Command
import argparse
from pathlib import Path
from .utils import log, console
from rich.markdown import Markdown


class InitCmd(Command):
    NAME = "init"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(self.NAME, help="初始化一个新的 Vix 项目")
        parser.add_argument("name", nargs="?", default=None, help="项目名称")
        parser.add_argument("-d", "--dir", default=None, help="初始化目录（默认使用项目名称）")
        return parser

    def execute(self):
        args = self.namespace
        project_name = args.name

        if not project_name:
            log.error("请提供项目名称")
            return

        project_path = Path(getattr(args, "dir", None) or project_name)

        if project_path.exists():
            log.error(f"目录 '{project_path}' 已存在")
            return

        try:
            project_path.mkdir(parents=True)

            vindex_toml_content = f"""[project]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = []
edition = "2024"

deps = []
"""

            (project_path / "vindex.toml").write_text(vindex_toml_content)

            (project_path / "src").mkdir()

            lib_vix_content = """pub fn greet() {
    print("Hello from src/lib.vix!")
}
"""

            (project_path / "src" / "lib.vix").write_text(lib_vix_content)

            main_vix_content = """import "src/lib.vix"

fn main(): i32 {
    greet()
    return 0
}
"""

            (project_path / "main.vix").write_text(main_vix_content)

            gitignore_content = """# Vix
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
"""

            (project_path / ".gitignore").write_text(gitignore_content)

            readme_content = f"""# {project_name}

Vix 项目

## 构建

```bash
very build
```
"""

            (project_path / "README.md").write_text(readme_content)

            console.print(f"[green]成功创建项目 '{project_name}'[/green]")
            console.print("\n[bold]项目结构:[/bold]")
            console.print(Markdown(f"""
```
{project_name}/
├── vindex.toml       # 项目配置
├── main.vix          # 入口文件
├── src/
│   └── lib.vix       # 库模块
├── .gitignore
└── README.md
```
"""))

        except Exception as e:
            log.error(f"创建项目失败: {e}")
            return
