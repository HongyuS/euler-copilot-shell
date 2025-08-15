# openEuler Intelligence Smart Shell

一个基于 Python Textual 构建的智能终端应用程序，提供 AI 驱动的命令行交互体验。支持多种 LLM 后端，集成 MCP 协议，提供现代化的 TUI 界面。

## 核心特性

- **多后端支持**: 支持 OpenAI API 大模型和 openEuler Intelligence 后端
- **智能终端界面**: 基于 Textual 的现代化 TUI 界面
- **流式响应**: 实时显示 AI 回复内容
- **部署助手**: 内置 openEuler Intelligence 自动部署功能

## 安装说明

### 方式一：从源码安装（推荐开发者）

1. 克隆仓库:

   ```sh
   git clone https://gitee.com/openeuler/euler-copilot-shell.git -b dev
   cd euler-copilot-shell
   ```

2. 安装依赖:

   ```sh
   pip install -r requirements.txt
   ```

### 方式二：通过 RPM 包安装

注意：*仅适用于 openEuler 24.03 LTS SP2*

```sh
sudo dnf install openeuler-intelligence-cli
```

安装完成后，可以使用 `oi` 命令启动应用程序。

## 使用方法

直接运行应用程序:

```sh
python src/main.py
```

或者安装 RPM 包后:

```sh
oi
```

查看最新的日志内容:

```sh
python src/main.py --logs
# 或安装后使用
oi --logs
```

设置日志级别并验证:

```sh
python src/main.py --log-level DEBUG
# 或安装后使用
oi --log-level INFO
```

初始化 openEuler Intelligence 后端（仅支持 openEuler 操作系统）:

```sh
python src/main.py --init
# 或安装后使用
oi --init
```

应用启动后，您可以直接在输入框中输入命令。如果命令无效或无法执行，应用程序将基于您的输入提供智能建议。

### 界面操作快捷键

- **Ctrl+S**: 打开设置界面
- **Ctrl+R**: 重置对话历史
- **Ctrl+T**: 选择智能体
- **Tab**: 在命令输入框和输出区域之间切换焦点
- **Esc**: 退出应用程序

### MCP 工具交互

当使用支持 MCP (Model Context Protocol) 的后端时，应用程序会在需要工具确认或参数输入时：

1. **工具执行确认**: 显示工具名称、风险级别和执行原因，用户可选择确认或取消
2. **参数补全**: 动态生成参数输入表单，用户填写必要信息后提交

应用程序使用内联交互模式，不会打开模态对话框，确保流畅的用户体验。

### --init 命令详细说明

`--init` 命令用于在 openEuler 操作系统上自动安装和配置 openEuler Intelligence 后端，它将执行以下步骤：

1. **系统检测**: 检测当前操作系统是否为 openEuler
2. **环境检查**: 验证 dnf 包管理器和管理员权限
3. **包安装**: 通过 dnf 安装 `openeuler-intelligence-installer` RPM 包
4. **服务部署**: 运行部署脚本完成系统初始化

**使用要求**:

- 仅支持 openEuler 操作系统
- 需要管理员权限（sudo）
- 需要网络连接以下载 RPM 包

**注意**: 此命令会自动安装系统服务，请在生产环境使用前仔细评估。

## 配置说明

应用程序支持两种后端配置，配置文件会自动保存在 `~/.config/eulerintelli/smart-shell.json`：

### 后端类型

1. **OpenAI 兼容 API** (包括 LM Studio、vLLM、Ollama 等)
2. **openEuler Intelligence (Hermes)**

### 配置示例

首次运行时，可通过设置界面 (Ctrl+S) 配置以下参数：

**OpenAI 兼容 API 配置:**

- Base URL: 如 `http://localhost:1234/v1`
- Model: 如 `qwen/qwen3-30b-a3b`
- API Key: 如 `sk-xxxxxx`

**openEuler Intelligence 配置:**

- Base URL: 如 `http://your-server:8002`
- API Key: 您的认证令牌

### 智能体管理

对于 openEuler Intelligence 后端，应用程序支持多智能体切换：

1. **默认智能问答**: 通用 AI 助手
2. **专业智能体**: 针对特定领域的专门助手

使用 `Ctrl+T` 可以在运行时切换不同的智能体。

### 日志配置

应用程序提供多级日志记录：

- **DEBUG**: 详细调试信息
- **INFO**: 基本信息（默认）
- **WARNING**: 警告信息
- **ERROR**: 仅错误信息

## 日志功能

应用程序提供完整的日志记录功能：

- **日志位置**: `~/.cache/openEuler Intelligence/logs/`
- **日志格式**: `smart-shell-YYYYMMDD-HHMMSS.log`（使用本地时区时间）
- **自动清理**: 每次启动时自动删除7天前的旧日志和空日志文件
- **命令行查看**: 使用 `python src/main.py --logs` 查看最新日志内容
- **记录内容**:
  - 程序启动和退出
  - API请求详情（URL、状态码、耗时等）
  - 异常和错误信息
  - 模块级别的操作日志

## 系统要求

### 基本要求

- **Python**: 3.11 或更高版本
- **操作系统**: openEuler 24.03 LTS 或更高版本
- **网络**: 访问配置的 LLM API 服务

### 依赖包

核心依赖：

- **textual**: 5.3.0 - TUI 界面框架
- **rich**: 14.1.0 - 富文本渲染
- **httpx**: 0.28.1 - HTTP 客户端
- **openai**: 1.99.6 - OpenAI API 客户端

开发依赖：

- **ruff**: *Latest* - 代码检查器

### 特殊功能要求

**自动部署功能（`--init` 命令）**:

- 仅支持 openEuler 操作系统
- 需要管理员权限（sudo）
- 需要 dnf 包管理器
- 需要网络连接

## 在 openEuler 系统下的 RPM 打包

以下步骤演示如何在 openEuler 24.03 LTS 或更高版本上，使用自带脚本打包生成 RPM 包。

前提条件：

- 操作系统：openEuler 24.03 LTS 或更高版本
- 工具依赖：rpmdevtools、git、bash
- 具有管理员权限（sudo）

构建步骤：

1. 克隆仓库并切换到对应分支：

   ```sh
   git clone https://gitee.com/openeuler/euler-copilot-shell.git -b dev
   cd euler-copilot-shell
   ```

2. 为构建脚本添加可执行权限：

   ```sh
   chmod +x scripts/build/create_tarball.sh scripts/build/build_rpm.sh
   ```

3. 运行 RPM 构建脚本：

   ```sh
   ./scripts/build/build_rpm.sh
   ```

   脚本执行完成后，会在临时构建目录下的 `RPMS` 和 `SRPMS` 子目录中生成相应的二进制包和源码包，并在终端输出具体路径。

## 项目结构

```text
smart-shell/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python 依赖包列表
├── setup.py                      # 包安装配置文件
├── LICENSE                       # 开源许可证
├── distribution/                 # 发布相关文件
├── docs/                         # 项目文档目录
│   └── development/              # 开发设计文档
│       └── server-side/          # 服务端相关文档
├── scripts/                      # 部署脚本目录
│   └── build/                    # RPM 包构建脚本
│   └── deploy/                   # 自动化部署脚本
├── tests/                        # 测试文件目录
└── src/                          # 源代码目录
    ├── main.py                   # 应用程序入口点
    ├── app/                      # TUI 应用模块
    │   ├── tui.py                # 主界面应用类
    │   ├── mcp_widgets.py        # MCP 交互组件
    │   ├── tui_mcp_handler.py    # MCP 事件处理器
    │   ├── settings.py           # 设置界面
    │   ├── css/
    │   │   └── styles.tcss       # TUI 样式文件
    │   ├── deployment/           # 部署助手模块
    │   │   ├── models.py         # 部署配置模型
    │   │   ├── service.py        # 部署服务逻辑
    │   │   ├── ui.py             # 部署界面组件
    │   │   └── validators.py     # 配置验证器
    │   └── dialogs/              # 对话框组件
    │       ├── agent.py          # 智能体选择对话框
    │       └── common.py         # 通用对话框组件
    ├── backend/                  # 后端适配模块
    │   ├── base.py               # 后端客户端基类
    │   ├── factory.py            # 后端工厂类
    │   ├── mcp_handler.py        # MCP 事件处理接口
    │   ├── openai.py             # OpenAI 兼容客户端
    │   └── hermes/               # openEuler Intelligence 客户端
    │       ├── client.py         # Hermes API 客户端
    │       ├── constants.py      # 常量定义
    │       ├── exceptions.py     # 异常类定义
    │       ├── models.py         # 数据模型
    │       ├── stream.py         # 流式响应处理
    │       └── services/         # 服务层组件
    ├── config/                   # 配置管理模块
    │   ├── manager.py            # 配置管理器
    │   └── model.py              # 配置数据模型
    ├── log/                      # 日志管理模块
    │   └── manager.py            # 日志管理器
    └── tool/                     # 工具模块
        ├── command_processor.py  # 命令处理器
        └── oi_backend_init.py    # 后端初始化工具
```

## 贡献

欢迎贡献代码！请随时提交 PR 或开启问题讨论任何功能增强或错误修复建议。

## 相关文档

### 开发文档

- [项目整体设计](docs/development/项目整体设计.md) - 系统架构和整体设计方案
- [TUI应用模块设计](docs/development/TUI应用模块设计.md) - 用户界面模块设计
- [后端适配模块设计](docs/development/后端适配模块设计.md) - 多后端支持架构
- [部署助手模块设计](docs/development/部署助手模块设计.md) - 自动部署功能设计
- [配置管理模块设计](docs/development/配置管理模块设计.md) - 配置管理系统设计
- [日志管理模块设计](docs/development/日志管理模块设计.md) - 日志记录系统设计

### 部署文档

- [安装部署手册](scripts/deploy/安装部署手册.md) - 详细的部署指南

## 开源许可

本项目采用 MulanPSL-2.0 许可证。详细信息请参见 [LICENSE](LICENSE) 文件。
