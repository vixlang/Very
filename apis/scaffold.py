from pathlib import Path

from pyrsult import Result, Success, Failure

from ._error import Error, IOError, Validation


def scaffold_project(name: str, dir_path: str | None = None) -> Result[Path, Error]:
    project_path = Path(dir_path or name)
    if project_path.exists():
        return Failure(Validation(reason=f"目录 '{project_path}' 已存在"))

    try:
        project_path.mkdir(parents=True)

        (project_path / "vindex.toml").write_text(
            f'[project]\n'
            f'name = "{name}"\n'
            f'version = "0.1.0"\n'
            f'description = ""\n'
            f'authors = []\n'
            f'edition = "2024"\n'
            f'deps = []\n'
        )

        src = project_path / "src"
        src.mkdir()
        (src / "lib.vix").write_text(
            'pub fn greet() {\n'
            '    print("Hello from src/lib.vix!")\n'
            '}\n'
        )

        (project_path / "main.vix").write_text(
            'import "src/lib.vix"\n'
            '\n'
            'fn main(): i32 {\n'
            '    greet()\n'
            '    return 0\n'
            '}\n'
        )

        (project_path / ".gitignore").write_text(
            '# Vix\n'
            '*.o\n'
            '*.out\n'
            '*.exe\n'
            'target/\n'
            '.very/\n'
            '\n'
            '# IDE\n'
            '.vscode/\n'
            '.idea/\n'
            '*.swp\n'
            '*.swo\n'
            '*~\n'
            '\n'
            '# OS\n'
            '.DS_Store\n'
            'Thumbs.db\n'
        )

        (project_path / "README.md").write_text(
            f'# {name}\n'
            f'\n'
            f'Vix 项目\n'
            f'\n'
            f'## 构建\n'
            f'\n'
            f'```bash\n'
            f'very build\n'
            f'```\n'
        )
    except OSError as e:
        return Failure(IOError(path=str(project_path), detail=str(e)))

    return Success(project_path)
