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
官方仓库的标准库项目名以`vlib-`开头


## 包索引格式
```bash
very add vnet                        # 下载 github.com/vixlang/vlib-vnet
very add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库  
very add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支      
very add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库  
very add gitee:fexcode.vnet@master   # .com 可以省略  
```

> o,我还给自己留了个语法糖（因为我比较喜欢gitee嘛），  
> @fexcode.very  # 等价于 gitee:fexcode.very

---

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
├── vindex.toml       # 项目配置
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

