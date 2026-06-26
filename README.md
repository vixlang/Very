# Very 说明

这是`vix`编程语言的官方项目管理与构建工具

Very依托git仓库进行vix项目管理，有很多简写语法

## 安装

```bash
uv tool install .
```

## 使用

```bash
very --help           # 查看所有命令
very -v, --version    # 查看版本号
very <命令> --help     # 查看具体命令的详细信息
```

## 官方包下载仓库

> 地址： https://github.com/vixlang

### 规范
官方仓库的标准库项目名以`vlib-`开头，工具项目名以`vtool-`开头


## vindex.toml 项目配置

> 详见 [docs/vindex-toml.md](docs/vindex-toml.md) — 包含所有配置项、依赖格式说明和示例。

## Very 命令介绍

### very add - 添加包

`very add` 命令用于从git仓库下载并安装vix包。

#### 格式
```bash
very add git主仓库地址:用户名.git仓库项目名@分支名
```

#### 示例
```bash
very add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库
very add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支
very add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库
very add gitee:fexcode.vnet@master   # .com 可以省略
very add @fexcode.vnet               # @符号开头默认为 gitee.com
```

### very del - 删除包

`very del` 命令用于删除已安装的vix包。

#### 格式
```bash
very del git主仓库地址:用户名.git仓库项目名
```

#### 示例
```bash
very del fexcode.vnet                # 删除 github.com/fexcode/vnet 仓库
very del gitee.com:fexcode.vnet      # 删除 gitee.com/fexcode/vnet 仓库
very del gitee:fexcode.vnet          # .com 可以省略
very del @fexcode.vnet               # @符号开头默认为 gitee.com
```

### very list - 列出已安装的包

`very list` 命令用于列出所有已安装的vix包。

#### 格式
```bash
very list [-t|--tree]
```

#### 参数
- `-t, --tree`: 以树形结构显示包列表

#### 示例
```bash
very list              # 列出所有已安装的包
very list -t           # 以树形结构显示包列表
```

### very prune - 清理无效包和空目录

`very prune` 命令用于删除没有vindex.toml的包和空目录。

#### 格式
```bash
very prune [--empty-only | --invalid-only]
```

#### 选项
- `--empty-only`: 只删除空目录
- `--invalid-only`: 只删除没有vindex.toml的包

#### 示例
```bash
very prune                      # 删除无效包和空目录
very prune --empty-only         # 只删除空目录
very prune --invalid-only       # 只删除无效包
```

### very init - 初始化新项目

`very init` 命令用于创建一个新的 vix 项目骨架。

#### 格式
```bash
very init <项目名>
```

#### 示例
```bash
very init my-project    # 创建 my-project/ 项目目录
```

#### 生成结构
```
my-project/
├── vindex.toml       # 项目配置（详见 docs/vindex-toml.md）
├── main.vix          # 入口文件
├── .gitignore
└── README.md
```

### very search - 搜索可用的包

`very search` 命令用于从 GitHub vixlang 组织搜索可用的 vix 包。

#### 格式
```bash
very search [关键词] [选项]
```

#### 选项
- `--sort stars|updated|name`: 排序方式（默认按星标数）
- `--limit N`: 限制显示的包数量
- `--no-cache`: 不使用缓存，强制从 GitHub 获取最新数据
- `--clear-cache`: 清理本地缓存文件
- `--cache-status`: 查看缓存状态信息

#### 示例
```bash
very search                    # 列出所有包（按星标数排序）
very search vnet               # 搜索名称或描述中包含 vnet 的包
very search --sort updated     # 按更新时间排序
very search --limit 5          # 只显示前 5 个
very search --no-cache         # 强制刷新缓存
very search --cache-status     # 查看缓存状态
very search --clear-cache      # 清理缓存
```

### very tool add - 安装 Vix 工具

`very tool add` 命令用于安装 Vix 工具。包名展开规则与 `very add` 相同，但 bare name 使用 `vtool-` 前缀而非 `vlib-`。

#### 格式
```bash
very tool add <工具包名>
```

#### 示例
```bash
very tool add game           # 安装 github.com/vixlang/vtool-game
very tool add fexcode.vtool  # 安装 github.com/fexcode/vtool
```

#### 工作流程
1. 解析包名（bare name → `vtool-` 前缀）
2. 克隆到 `$VIX_HOME/tools/{host}/{user}/{repo}/`
3. 读取 `vindex.toml` 获取 `project.name`
4. 编译，输出到 `$VIX_HOME/tools/{name}.exe`

### very tool del - 删除 Vix 工具

`very tool del` 命令用于删除已安装的 Vix 工具，包括编译产物和源码。

#### 格式
```bash
very tool del <工具名>
```

#### 示例
```bash
very tool del game           # 删除 game 工具
```

### very tool update - 更新 Vix 工具

`very tool update` 命令用于更新已安装的 Vix 工具（git pull + 重新编译）。如果工具未安装，会自动执行安装。

#### 格式
```bash
very tool update <工具名>
```

#### 示例
```bash
very tool update game        # 更新 game 工具
```

### very tool search - 搜索 Vix 工具

`very tool search` 命令用于从 GitHub vixlang 组织搜索可用的 Vix 工具（`vtool-*` 仓库）。

#### 格式
```bash
very tool search [关键词] [选项]
```

#### 选项
- `--sort stars|updated|name`: 排序方式（默认按星标数）
- `--limit N`: 限制显示的工具数量
- `--no-cache`: 不使用缓存
- `--clear-cache`: 清理缓存
- `--cache-status`: 查看缓存状态

#### 示例
```bash
very tool search                    # 列出所有工具
very tool search game               # 搜索工具名包含 game 的
very tool search --sort updated     # 按更新时间排序
```

### very exe - 执行 Vix 工具

`very exe` 命令用于查找并执行已编译的 Vix 工具。如果工具未安装，会自动执行 `very tool add`。

#### 格式
```bash
very exe <工具名> [参数...]
```

#### 示例
```bash
very exe game                    # 运行 game 工具
very exe game --score=100        # 带参数运行
```

---

## .vix目录结构示例
```bash
.vix
└── libs
    ├── gitee.com
    |    ├── fexcode
    |    │   ├── very
    |    │   └── very2
    |    └── fexcode2
    |        └── very3
    └── github.com
        ├── fexcode
        │   └── very
        ├── fexcode2
        │   └── very2
        └── fexcode3
            └── very3
```

