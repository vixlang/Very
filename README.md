# Very — Vix 项目管理与构建工具

Very 是 [Vix](https://github.com/vixlang) 语言的官方项目管理与构建工具。基于 git 仓库管理依赖，支持丰富的简写语法。

## 目录

- [安装](#安装)
- [快速入门](#快速入门)
- [包名语法](#包名语法)
- [命令参考](#命令参考)
  - [项目管理](#项目管理)
  - [包管理](#包管理)
  - [工具管理](#工具管理)
- [配置](#配置)
- [目录结构](#目录结构)

---

## 安装

```bash
uv tool install .
```

### 基本用法

```bash
very --help           # 查看所有命令
very -v, --version    # 查看版本号
very <命令> --help     # 查看具体命令的详细信息
```

---

## 包名语法

Very 使用 `parse_pack_name` 支持多种简写形式，所有命令统一适用：

| 输入 | 解析结果 |
|---|---|
| `fexcode.vnet` | `github.com/fexcode/vnet` |
| `fexcode.vnet@master` | `github.com/fexcode/vnet`（分支 `master`） |
| `gitee.com:fexcode.vnet` | `gitee.com/fexcode/vnet` |
| `gitee:fexcode.vnet` | `gitee.com/fexcode/vnet`（`.com` 自动补全） |
| `@fexcode.vnet` | `gitee.com/fexcode/vnet`（`@` 前缀 → gitee） |
| `vnet`（bare name） | `github.com/vixlang/vlib-vnet` |

工具名也使用相同规则，但 bare name 前缀为 `vtool-` 而非 `vlib-`：

| 输入 | 解析结果 |
|---|---|
| `format` | `github.com/vixlang/vtool-format` |
| `fexcode.vtool` | `github.com/fexcode/vtool` |

---

## 命令参考

### 项目管理

#### very init — 初始化新项目

创建 Vix 项目骨架。

```bash
very init <项目名>
very init my-project
```

生成结构：

```
my-project/
├── vindex.toml
├── main.vix
├── .gitignore
└── README.md
```

#### very build — 编译项目

编译 Vix 项目。自动检测 gcc：存在时编译为 `.o` 再链接，否则直接调用 `vixc`。

```bash
very build [vixc 选项...]
very build -o output.exe src/main.vix
very build --optimize
```

- 入口文件默认取自 `vindex.toml` 的 `project.entrypoint`（缺省 `main.vix`）
- 输出名默认取自 `project.name`

#### very run — 编译并运行

编译并运行项目，运行后自动清理产物（`-k` 保留）。

```bash
very run [-k|--keep] [-v|--vdebug] [vixc 选项...]
very run               # 编译 → 运行 → 清理
very run -k            # 保留可执行文件
very run --optimize    # 传递参数给 vixc
```

#### very install — 安装依赖

安装 `vindex.toml` 中声明的所有依赖。

```bash
very install [-l|--local]
very install              # 安装 deps（优先使用全局已存在的副本）
very install -l           # 强制下载到项目本地
```

#### very update — 更新包

更新已安装的包（git pull），支持传递依赖的递归更新。

```bash
very update [<包名>]
very update               # 更新所有已安装的包
very update fexcode.vnet  # 更新指定包及其传递依赖
```

#### very good — 检查语法与类型

调用 `vixc --check` 检查 `.vix` 文件的语法和类型。

```bash
very good [文件...]
very good                      # 检查入口文件（默认 main.vix）
very good src/                 # 递归检查目录下所有 .vix
very good main.vix lib/*.vix   # 检查多个文件 / 通配符
```

---

### 包管理

#### very add — 添加包

从 git 仓库下载并安装 Vix 包。

```bash
very add <包名> [-g|--global]
very add fexcode.vnet           # github.com/fexcode/vnet
very add fexcode.vnet@master    # 指定分支
very add gitee.com:fexcode.vnet # gitee
very add gitee:fexcode.vnet     # .com 可省略
very add @fexcode.vnet          # @ → gitee
```

- 默认安装到项目 `.vix/libs/`
- `-g` 安装到 `$VIX_HOME/libs/`

#### very del — 删除包

```bash
very del <包名>
very del fexcode.vnet
very del @fexcode.vnet
```

#### very list — 列出已安装的包

```bash
very list [-t|--tree]
very list       # 表格形式
very list -t    # 树形结构
```

#### very prune — 清理

删除无效包、空目录、孤立包。

```bash
very prune [--empty-only | --invalid-only | --unused]
very prune                   # 删除无效包 + 空目录 + 孤立包
very prune --empty-only      # 只删空目录
very prune --invalid-only    # 只删缺少 vindex.toml 的包
very prune --unused          # 只删不被任何包引用的孤立包
```

#### very search — 搜索包

从 GitHub 上 `github.com/vixlang` 组织搜索可用包（`vlib-*` 仓库）。

```bash
very search [关键词] [选项]
very search                        # 列出所有包
very search vnet                   # 按名称/描述搜索
very search --sort stars|updated|name
very search --limit N
very search --no-cache             # 强制刷新
very search --cache-status         # 查看缓存状态
very search --clear-cache          # 清理缓存
```

---

### 工具管理

工具命令以 `very tool` 为前缀，分为 `add / del / list / prune / search / update`。

#### very tool add — 安装工具

克隆 + 编译 Vix 工具到 `$VIX_HOME/tools/`。

```bash
very tool add <工具包名>
very tool add game          # github.com/vixlang/vtool-game
very tool add fexcode.vtool
```

工作流程：解析包名 → 克隆源码 → 读取 vindex.toml → 编译输出到 `$VIX_HOME/tools/<name>.exe`。

#### very tool del — 删除工具

删除工具源码和编译产物。

```bash
very tool del <工具名>
very tool del game
```

#### very tool list — 列出已安装工具

```bash
very tool list [-t|--tree]
very tool list       # 表格形式
very tool list -t    # 树形结构
```

#### very tool prune — 清理工具

清理无效工具目录、空目录、孤立编译产物。

```bash
very tool prune [--invalid-only | --empty-only | --binary-only]
very tool prune                   # 全部清理
very tool prune --binary-only     # 只删无源码对应的 .exe
```

#### very tool search — 搜索工具

搜索 GitHub 上 `github.com/vixlang` 组织中的 Vix 工具（`vtool-*` 仓库）。

```bash
very tool search [关键词] [选项]
very tool search                   # 列出所有工具
very tool search game              # 搜索
very tool search --sort updated    # 按更新时间排序
very tool search --no-cache
very tool search --cache-status
very tool search --clear-cache
```

#### very tool update — 更新工具

git pull + 重新编译。如工具未安装则自动执行安装。

```bash
very tool update <工具名>
very tool update game
```

#### very exe — 执行工具

查找并执行已编译的工具。如果未安装，自动执行 `very tool add`。

```bash
very exe <工具名> [参数...]
very exe game
very exe game --score=100
```

---

## 配置

项目依赖通过 `vindex.toml` 声明：

```toml
[project]
name = "my-project"
entrypoint = "main.vix"
deps = ["vnet", "fexcode.vlib"]
```

> 详见 [docs/vindex-toml.md](docs/vindex-toml.md) — 包含所有配置项、依赖格式说明和示例。

### 环境变量

- `VIX_HOME` — 覆盖默认的 `.vix/` 目录位置

### 缓存

- 包搜索缓存: `$VIX_HOME/cache/search_cache.json`（1 小时过期）
- 工具搜索缓存: `$VIX_HOME/tools/cache/tool_search_cache.json`（1 小时过期）

---

## 目录结构

```
项目目录/
├── .vix/                        # 本地依赖和临时文件
│   ├── libs/                    # 已安装的包
│   │   ├── github.com/
│   │   │   ├── fexcode/vnet/
│   │   │   └── vixlang/vlib-xxx/
│   │   └── gitee.com/
│   │       └── fexcode/vnet/
│   └── temp/                    # 编译临时文件
├── vindex.toml                  # 项目配置
└── main.vix                     # 入口文件

$VIX_HOME/                       # 全局目录（默认 .vix/）
├── libs/                        # 全局包
├── tools/                       # 已安装的工具
│   ├── cache/                   # 工具搜索缓存
│   ├── github.com/vixlang/vtool-game/
│   └── game.exe                 # 编译产物
└── cache/                       # 搜索结果缓存
```

---

> 官方组织: [github.com/vixlang](https://github.com/vixlang)
> 标准库前缀: `vlib-*`, 工具前缀: `vtool-*`
