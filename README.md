# Very 说明

这是`vix`编程语言的官方项目管理与构建工具

Very依托git仓库进行vix包管理，有很多简写语法

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

