# openEuler Intelligence Smart Shell

这是一个基于 Python Textual 库开发的 TUI（文本用户界面）应用程序。它允许用户输入命令，验证并执行这些命令。如果命令无法执行，应用程序会与大型语言模型交互，生成建议或纠正方案。

## 功能特点

- 用户友好的命令输入和输出显示界面
- 命令验证和执行支持
- 集成大型语言模型提供智能命令建议
- 提供本地或在线模型服务集成选项
- 完整的日志记录功能，支持问题诊断和性能监控

## 项目结构

```text
euler-copilot-shell/
├── README.md                     # 项目文档
├── requirements.txt              # 项目依赖
└── src
    ├── app
    |   ├── css
    │   │   └── styles.tcss       # TUI 样式配置
    │   ├── __init__.py
    │   ├── settings.py           # 设置界面逻辑
    │   └── tui.py                # 主界面布局和组件定义
    ├── backend
    │   ├── hermes
    │   │   ├── __init__.py
    │   │   └── client.py         # Hermes API 客户端
    │   ├── __init__.py
    │   ├── base.py               # 后端客户端基类
    │   ├── factory.py            # 后端工厂类
    │   └── openai.py             # OpenAI API 客户端
    ├── config
    │   ├── __init__.py
    │   ├── manager.py            # 配置管理
    │   └── model.py              # 配置模型定义
    ├── log
    │   ├── __init__.py
    │   └── manager.py            # 日志管理器
    ├── main.py                   # TUI 应用程序入口点
    └── tool
        ├── __init__.py
        └── command_processor.py  # 命令验证和执行逻辑
```

## 安装说明

1. 克隆仓库:

   ```sh
   git clone https://gitee.com/openeuler/euler-copilot-shell.git -b dev
   cd euler-copilot-shell
   ```

2. 安装依赖:

   ```sh
   pip install -r requirements.txt
   ```

## 使用方法

直接运行应用程序:

```sh
python src/main.py
```

查看最新的日志内容:

```sh
python src/main.py --logs
```

初始化 openEuler Intelligence 后端（仅支持 openEuler 操作系统）:

```sh
python src/main.py --init
```

应用启动后，您可以直接在输入框中输入命令。如果命令无效或无法执行，应用程序将基于您的输入提供智能建议。

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

## 大型语言模型集成

该应用程序利用大型语言模型（LLM）增强用户体验，提供智能命令建议。集成在 `backend/openai.py` 文件中处理，该文件与 OpenAI 兼容的 API 通信以获取基于用户输入的建议。应用支持配置不同的后端和模型。

## 配置设置

您可以通过应用内的设置界面（按 Ctrl+S）配置以下选项:

- 后端类型: OpenAI 或 Hermes
- API 基础 URL
- API 密钥
- 模型选择（OpenAI 后端）

配置会保存在`~/.config/eulerintelli/smart-shell.json`。

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

日志文件同时输出到控制台和文件，便于开发调试和生产环境监控。详细说明请参考 [日志功能文档](docs/development/日志功能说明.md)。

## RPM打包

我们提供了一个 spec 文件，可以使用 PyInstaller 打包并生成 RPM 包:

```sh
# 创建源代码归档
tar czf euler-copilot-shell-0.9.6.tar.gz --transform 's,^smart-shell,euler-copilot-shell-0.9.6,' smart-shell

# 构建RPM包(需要已安装rpm-build工具)
rpmbuild -ba euler-copilot-shell.spec
```

## 贡献

欢迎贡献代码！请随时提交 PR 或开启问题讨论任何功能增强或错误修复建议。

## 许可证

本项目采用木兰宽松许可证第2版（MulanPSL-2.0）。详情请参阅 LICENSE 文件。
