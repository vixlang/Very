# VPM (Vix Package Manager)

一个简洁高效的 Git 包管理工具，用于从 Git 仓库下载和管理项目依赖。

## 特性

- 🚀 从 Git 仓库快速克隆依赖包
- 📦 支持 GitHub、Gitee 等多种 Git 托管平台
- 🌿 支持指定分支下载
- ⚡ 简洁的命令行接口
- 🎨 彩色日志输出

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd vpm

# 使用 uv 安装依赖
uv sync
```

## 使用方法

### 添加包

```bash
# 从 GitHub 添加包（默认）
python main.py add fexcode.vnet

# 指定分支
python main.py add fexcode.vnet@master

# 从其他 Git 平台添加
python main.py add gitee.com:fexcode.vnet
```

### 包名格式

```
[平台:]<用户名>.<仓库名>[@分支名]
```

- **平台**: 可选，默认为 `github.com`
- **用户名**: 仓库所有者用户名
- **仓库名**: 仓库名称（使用 `.` 代替 `/`）
- **分支名**: 可选，默认为仓库的默认分支

### 示例

```bash
# GitHub 默认分支
python main.py add fexcode.vnet

# GitHub 指定分支
python main.py add fexcode.vnet@develop

# Gitee 平台
python main.py add gitee.com:fexcode.vnet
```

## 项目结构

```
vpm/
├── main.py          # 程序入口
├── pyproject.toml   # 项目配置
├── vindex.toml      # 包索引配置
├── cmds/            # 命令模块
│   ├── __init__.py
│   ├── base.py      # 命令基类
│   ├── add.py       # add 命令实现
│   └── _utils.py    # 工具类
└── .vix/            # 下载的包存储目录
```

## 开发

### 添加新命令

1. 在 `cmds/` 目录下创建新的命令文件（如 `install.py`）
2. 继承 `Command` 基类并实现必要的方法
3. 在 `cmds/__init__.py` 中注册命令

```python
from .base import Command
import argparse

class InstallCmd(Command):
    NAME = "install"

    def execute(self):
        # 命令逻辑
        pass

    def set_parser(self, p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        subparsers = p.add_subparsers(dest="subcommand")
        install_parser = subparsers.add_parser("install", help="Install packages")
        install_parser.add_argument("package", help="Package name")
        return p
```

## 依赖

- Python >= 3.13
- colorama >= 0.4.6
- GitPython >= 3.1.46


