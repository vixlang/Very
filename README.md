# VPM说明

这是`vix`编程语言的官方包管理器

vpm依托git仓库进行vix包管理，有很多简写语法

## 官方包下载仓库

> 地址： https://github.com/vixlang

### 规范
官方仓库的标准库项目名以`vlib-`开头


## 包索引格式
```bash
vpm add vnet                        # 下载 github.com/vixlang/vlib-vnet
vpm add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库  
vpm add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支      
vpm add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库  
vpm add gitee:fexcode.vnet@master   # .com 可以省略  
```

> o,我还给自己留了个语法糖（因为我比较喜欢gitee嘛），  
> @fexcode.vpm  # 等价于 gitee:fexcode.vpm

---

## VPM命令介绍

### vpm add - 添加包

`vpm add` 命令用于从git仓库下载并安装vix包。

#### 格式
```bash
vpm add git主仓库地址:用户名.git仓库项目名@分支名
```

#### 示例
```bash
vpm add fexcode.vnet                # 下载 github.com/fexcode/vnet 仓库
vpm add fexcode.vnet@master         # 下载 github.com/fexcode/vnet 仓库 master 分支
vpm add gitee.com:fexcode.vnet      # 下载 gitee.com/fexcode/vnet 仓库
vpm add gitee:fexcode.vnet@master   # .com 可以省略
vpm add @fexcode.vnet               # @符号开头默认为 gitee.com
```

### vpm del - 删除包

`vpm del` 命令用于删除已安装的vix包。

#### 格式
```bash
vpm del git主仓库地址:用户名.git仓库项目名
```

#### 示例
```bash
vpm del fexcode.vnet                # 删除 github.com/fexcode/vnet 仓库
vpm del gitee.com:fexcode.vnet      # 删除 gitee.com/fexcode/vnet 仓库
vpm del gitee:fexcode.vnet          # .com 可以省略
vpm del @fexcode.vnet               # @符号开头默认为 gitee.com
```

### vpm list - 列出已安装的包

`vpm list` 命令用于列出所有已安装的vix包。

#### 格式
```bash
vpm list [-t|--tree]
```

#### 参数
- `-t, --tree`: 以树形结构显示包列表

#### 示例
```bash
vpm list              # 列出所有已安装的包
vpm list -t           # 以树形结构显示包列表
```

### vpm prune - 清理无效包和空目录

`vpm prune` 命令用于删除没有vindex.toml的包和空目录。

#### 格式
```bash
vpm prune [--empty-only | --invalid-only]
```

#### 选项
- `--empty-only`: 只删除空目录
- `--invalid-only`: 只删除没有vindex.toml的包

#### 示例
```bash
vpm prune                      # 删除无效包和空目录
vpm prune --empty-only         # 只删除空目录
vpm prune --invalid-only       # 只删除无效包
```

---

## .vix目录结构示例
```bash
.vix
└── libs
    ├── gitee.com
    |    ├── fexcode
    |    │   ├── vpm
    |    │   └── vpm2
    |    └── fexcode2
    |        └── vpm3
    └── github.com
        ├── fexcode
        │   └── vpm
        ├── fexcode2
        │   └── vpm2
        └── fexcode3
            └── vpm3
```

