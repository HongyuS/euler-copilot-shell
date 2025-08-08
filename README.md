# openEuler Intelligence Smart Shell

一个基于 Python Textual 构建的智能终端应用程序，提供 AI 驱动的命令行交互体验。支持多种 LLM 后端，集成 MCP 协议，提供现代化的 TUI 界面。

## 核心特性

- **多后端支持**: 支持 OpenAI API 和 openEuler Intelligence（Hermes）后端
- **智能终端界面**: 基于 Textual 的现代化 TUI 界面
- **流式响应**: 实时显示 AI 回复内容
- **会话管理**: 完整的对话历史管理功能
- **部署助手**: 内置 openEuler Intelligence 自动部署功能
- **配置管理**: 灵活的配置文件管理系统
- **日志系统**: 完善的日志记录和管理功能

## 项目结构

```text
smart-shell/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python 依赖包列表
├── setup.py                      # 包安装配置文件
├── MANIFEST.in                   # 包文件清单
├── LICENSE                       # 开源许可证
├── distribution/                 # 发布相关文件
├── docs/                         # 项目文档目录
│   └── development/              # 开发设计文档
│       └── server-side/          # 服务端相关文档
├── scripts/                      # 部署脚本目录
│   └── deploy/                   # 自动化部署脚本
├── tests/                        # 测试文件目录
└── src/                          # 源代码目录
    ├── main.py                   # 应用程序入口点
    ├── app/                      # TUI 应用模块
    │   ├── __init__.py
    │   ├── tui.py                # 主界面应用类
    │   ├── mcp_widgets.py        # MCP 交互组件
    │   ├── tui_mcp_handler.py    # MCP 事件处理器
    │   ├── settings.py           # 设置界面
    │   ├── css/
    │   │   └── styles.tcss       # TUI 样式文件
    │   ├── deployment/           # 部署助手模块
    │   │   ├── __init__.py
    │   │   ├── models.py         # 部署配置模型
    │   │   ├── service.py        # 部署服务逻辑
    │   │   ├── ui.py             # 部署界面组件
    │   │   └── validators.py     # 配置验证器
    │   └── dialogs/              # 对话框组件
    │       ├── __init__.py
    │       ├── agent.py          # 智能体选择对话框
    │       └── common.py         # 通用对话框组件
    ├── backend/                  # 后端适配模块
    │   ├── __init__.py
    │   ├── base.py               # 后端客户端基类
    │   ├── factory.py            # 后端工厂类
    │   ├── mcp_handler.py        # MCP 事件处理接口
    │   ├── openai.py             # OpenAI 兼容客户端
    │   └── hermes/               # openEuler Intelligence 客户端
    │       ├── __init__.py
    │       ├── client.py         # Hermes API 客户端
    │       ├── constants.py      # 常量定义
    │       ├── exceptions.py     # 异常类定义
    │       ├── models.py         # 数据模型
    │       ├── stream.py         # 流式响应处理
    │       └── services/         # 服务层组件
    │           ├── agent.py      # 智能体服务
    │           ├── conversation.py # 对话管理服务
    │           ├── http.py       # HTTP 请求服务
    │           └── model.py      # 模型管理服务
    ├── config/                   # 配置管理模块
    │   ├── __init__.py
    │   ├── manager.py            # 配置管理器
    │   └── model.py              # 配置数据模型
    ├── log/                      # 日志管理模块
    │   ├── __init__.py
    │   └── manager.py            # 日志管理器
    └── tool/                     # 工具模块
        ├── __init__.py
        ├── command_processor.py  # 命令处理器
        └── oi_backend_init.py    # 后端初始化工具
```

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

### 方式二：使用 pip 安装

```sh
pip install -e .
```

安装完成后，可以使用 `oi` 命令启动应用程序。

## 使用方法

直接运行应用程序:

```sh
python src/main.py
```

或者使用 pip 安装后:

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

### 自动部署助手

应用程序内置了 TUI 部署助手，支持在 openEuler 系统上一键部署 openEuler Intelligence 后端：

1. **系统环境检查**: 自动验证 openEuler 系统和权限
2. **配置文件生成**: 根据用户输入自动生成配置文件
3. **服务部署**: 支持 Web 界面和 RAG 功能的可选部署
4. **实时进度显示**: 提供详细的部署日志和进度反馈

该功能通过 `app.deployment` 模块实现，包含完整的配置验证和部署流程管理。

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
- API Key: 如 `lm-studio`

**openEuler Intelligence 配置:**

- Base URL: 如 `http://your-server:8000`
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

- **Python**: 3.9 或更高版本
- **操作系统**: openEuler 24.03 LTS 或更高版本
- **网络**: 访问配置的 LLM API 服务

### 依赖包

核心依赖（会自动安装）：

- **textual**: >=3.0.0 - TUI 界面框架
- **rich**: >=14.1.0 - 富文本渲染
- **httpx**: >=0.28.0 - HTTP 客户端
- **openai**: >=1.97.0 - OpenAI API 客户端

### 特殊功能要求

**自动部署功能（`--init` 命令）**:

- 仅支持 openEuler 操作系统
- 需要管理员权限（sudo）
- 需要 dnf 包管理器
- 需要网络连接

## 详细日志功能

应用程序提供详细的日志记录功能，包括:

- **操作日志**: 用户交互和系统状态
- **性能监控**: 请求响应时间和系统资源使用
- **错误追踪**: 异常和错误的详细堆栈信息  
- **API请求详情**: URL、状态码、耗时等
- **异常和错误信息**: 完整的错误上下文
- **模块级别的操作日志**: 各组件的运行状态

日志文件同时输出到控制台和文件，便于开发调试和生产环境监控。详细说明请参考 [日志功能文档](docs/development/日志功能说明.md)。

## RPM 打包

我们提供了一个 spec 文件，可以使用 PyInstaller 打包并生成 RPM 包:

```sh
# 创建源代码归档
tar czf euler-copilot-shell-0.10.0.tar.gz --transform 's,^smart-shell,euler-copilot-shell-0.10.0,' smart-shell

# 构建RPM包(需要已安装rpm-build工具)
rpmbuild -ba distribution/linux/euler-copilot-shell.spec
```

## 高级功能

### MCP (Model Context Protocol) 支持

应用程序完整支持 Model Context Protocol，提供工具集成和交互功能：

**特性**:

- **内联工具确认**: 工具执行前的风险评估和确认界面
- **动态参数收集**: 根据工具需求自动生成参数输入表单
- **流式工具响应**: 实时显示工具执行结果
- **事件驱动架构**: 完整的 MCP 事件处理流程

**技术实现**:

- `app.mcp_widgets`: MCP 交互组件
- `app.tui_mcp_handler`: TUI MCP 事件处理器
- `backend.mcp_handler`: MCP 事件处理器接口
- 完整的 SSE (Server-Sent Events) 支持

### 部署助手

内置的可视化部署助手支持：

**功能**:

- **环境检测**: 自动检测 openEuler 系统和依赖
- **配置验证**: LLM 和 Embedding API 连接性验证
- **组件选择**: Web 界面和 RAG 功能的可选部署
- **实时监控**: 部署过程的实时日志和进度显示

**模块结构**:

- `app.deployment.models`: 部署配置数据模型
- `app.deployment.service`: 部署服务逻辑
- `app.deployment.ui`: 部署界面组件
- `app.deployment.validators`: 配置验证器

### 多后端架构

应用程序采用插件化的后端架构：

**后端支持**:

- **OpenAI 兼容**: 支持所有 OpenAI API 兼容的服务
- **Hermes**: 专为 openEuler Intelligence 优化的后端
- **可扩展**: 基于 `backend.base.LLMClientBase` 可轻松添加新后端

**核心组件**:

- `backend.factory`: 后端工厂类
- `backend.openai`: OpenAI 兼容客户端
- `backend.hermes`: Hermes 客户端实现

## 贡献

欢迎贡献代码！请随时提交 PR 或开启问题讨论任何功能增强或错误修复建议。

## 版本信息

- **当前版本**: 0.10.0
- **Python 要求**: >=3.9
- **许可证**: MulanPSL-2.0

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
