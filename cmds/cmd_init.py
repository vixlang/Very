from .base import Command
import argparse
import os
from pathlib import Path
from .utils import log, console
from rich.markdown import Markdown


class InitCmd(Command):
    NAME = "init"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            self.NAME, help="初始化一个新的 Vix 项目"
        )
        parser.add_argument("name", nargs="?", default=None, help="项目名称")
        return parser

    def execute(self):
        args = self.namespace
        project_name = args.name
        
        if not project_name:
            log.error("请提供项目名称")
            exit(1)
        
        project_path = Path(project_name)
        
        if project_path.exists():
            log.error(f"目录 '{project_name}' 已存在")
            exit(1)
        
        try:
            project_path.mkdir(parents=True)
            src_dir = project_path / "src"
            src_dir.mkdir()
            
            vix_toml_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = []
edition = "2024"

[dependencies]
'''
            
            (project_path / "vix.toml").write_text(vix_toml_content)
            
            main_vix_content = '''fn main() -> i32 {
    print("Hello, Vix!")
    return 0
}
'''
            
            (src_dir / "main.vix").write_text(main_vix_content)
            
            gitignore_content = '''# Vix
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
'''
            
            (project_path / ".gitignore").write_text(gitignore_content)
            
            console.print(f"[green]成功创建项目 '{project_name}'[/green]")
            console.print("\n[bold]项目结构:[/bold]")
            console.print(Markdown(f"""
```
{project_name}/
├── vix.toml          # 项目配置
├── src/
│   └── main.vix      # 入口文件
└── .gitignore
```
"""))
            
        except Exception as e:
            log.error(f"创建项目失败: {e}")
            exit(1)
