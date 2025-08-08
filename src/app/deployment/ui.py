"""
部署配置 TUI 界面

提供用户友好的部署配置界面。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

from .models import DeploymentConfig, DeploymentState, EmbeddingConfig, LLMConfig
from .service import DeploymentService


class DeploymentConfigScreen(ModalScreen[bool]):
    """
    部署配置屏幕

    允许用户配置部署参数的模态对话框。
    """

    CSS = """
    DeploymentConfigScreen {
        align: center middle;
    }

    .config-container {
        width: 80%;
        max-width: 100;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-radius: 3;
        padding: 1;
    }

    .form-section {
        margin: 1 0;
        padding: 1;
        border: solid $secondary;
        border-radius: 2;
    }

    .form-row {
        height: 3;
        margin: 1 0;
    }

    .form-label {
        width: 1fr;
        content-align: center left;
        text-style: bold;
    }

    .form-input {
        width: 2fr;
    }

    .button-row {
        height: 3;
        margin: 1 0;
        align: center middle;
    }

    .deploy-button {
        margin: 0 1;
        background: $success;
    }

    .cancel-button {
        margin: 0 1;
        background: $error;
    }
    """

    def __init__(self) -> None:
        """初始化部署配置屏幕"""
        super().__init__()
        self.config = DeploymentConfig()

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="config-container"):
            yield Header()
            yield Static(
                "openEuler Intelligence 后端部署配置",
                classes="form-section",
            )

            with TabbedContent():
                with TabPane("基础配置", id="basic"):
                    yield from self._compose_basic_config()

                with TabPane("LLM 配置", id="llm"):
                    yield from self._compose_llm_config()

                with TabPane("Embedding 配置", id="embedding"):
                    yield from self._compose_embedding_config()

                with TabPane("部署选项", id="deployment"):
                    yield from self._compose_deployment_options()

            with Horizontal(classes="button-row"):
                yield Button("开始部署", id="deploy", classes="deploy-button")
                yield Button("取消", id="cancel", classes="cancel-button")

    def _compose_basic_config(self) -> ComposeResult:
        """组合基础配置组件"""
        with Vertical(classes="form-section"):
            yield Static("基础配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("服务器 IP 地址:", classes="form-label")
                yield Input(
                    placeholder="例如：192.168.1.100",
                    id="server_ip",
                    classes="form-input",
                )

    def _compose_llm_config(self) -> ComposeResult:
        """组合 LLM 配置组件"""
        with Vertical(classes="form-section"):
            yield Static("大语言模型配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("API 端点:", classes="form-label")
                yield Input(
                    placeholder="例如：http://localhost:11434/v1",
                    id="llm_endpoint",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("API 密钥:", classes="form-label")
                yield Input(
                    placeholder="sk-123456",
                    password=True,
                    id="llm_api_key",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("模型名称:", classes="form-label")
                yield Input(
                    placeholder="例如：deepseek-llm-7b-chat",
                    id="llm_model",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("最大 Token 数:", classes="form-label")
                yield Input(
                    value="8192",
                    id="llm_max_tokens",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("Temperature:", classes="form-label")
                yield Input(
                    value="0.7",
                    id="llm_temperature",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("请求超时 (秒):", classes="form-label")
                yield Input(
                    value="300",
                    id="llm_timeout",
                    classes="form-input",
                )

    def _compose_embedding_config(self) -> ComposeResult:
        """组合 Embedding 配置组件"""
        with Vertical(classes="form-section"):
            yield Static("嵌入模型配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("类型:", classes="form-label")
                yield Select(
                    [("OpenAI", "openai")],
                    value="openai",
                    id="embedding_type",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("API 端点:", classes="form-label")
                yield Input(
                    placeholder="例如：http://localhost:11434/v1",
                    id="embedding_endpoint",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("API 密钥:", classes="form-label")
                yield Input(
                    placeholder="sk-123456",
                    password=True,
                    id="embedding_api_key",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("模型名称:", classes="form-label")
                yield Input(
                    placeholder="例如：bge-m3",
                    id="embedding_model",
                    classes="form-input",
                )

    def _compose_deployment_options(self) -> ComposeResult:
        """组合部署选项组件"""
        with Vertical(classes="form-section"):
            yield Static("部署选项", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("部署模式:", classes="form-label")
                yield Select(
                    [
                        ("轻量部署（仅框架服务）", "light"),
                        ("全量部署（包含 Web 和 RAG）", "full"),
                    ],
                    value="light",
                    id="deployment_mode",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("启用 Web 界面:", classes="form-label")
                yield Switch(id="enable_web", classes="form-input")

            with Horizontal(classes="form-row"):
                yield Label("启用 RAG 组件:", classes="form-label")
                yield Switch(id="enable_rag", classes="form-input")

    @on(Button.Pressed, "#deploy")
    async def on_deploy_button_pressed(self) -> None:
        """处理部署按钮点击"""
        if self._collect_config():
            # 验证配置
            is_valid, errors = self.config.validate()
            if not is_valid:
                await self.app.push_screen(
                    ErrorMessageScreen("配置验证失败", errors),
                )
                return

            # 关闭配置界面，返回 True 表示开始部署
            self.dismiss(result=True)

    @on(Button.Pressed, "#cancel")
    def on_cancel_button_pressed(self) -> None:
        """处理取消按钮点击"""
        self.dismiss(result=False)

    @on(Select.Changed, "#deployment_mode")
    def on_deployment_mode_changed(self, event: Select.Changed) -> None:
        """处理部署模式改变"""
        if event.value == "full":
            # 全量部署时自动启用 Web 和 RAG
            self.query_one("#enable_web", Switch).value = True
            self.query_one("#enable_rag", Switch).value = True
        else:
            # 轻量部署时禁用 Web 和 RAG
            self.query_one("#enable_web", Switch).value = False
            self.query_one("#enable_rag", Switch).value = False

    def _collect_config(self) -> bool:
        """收集用户配置"""
        try:
            # 基础配置
            self.config.server_ip = self.query_one("#server_ip", Input).value.strip()

            # LLM 配置
            self.config.llm = LLMConfig(
                endpoint=self.query_one("#llm_endpoint", Input).value.strip(),
                api_key=self.query_one("#llm_api_key", Input).value.strip(),
                model=self.query_one("#llm_model", Input).value.strip(),
                max_tokens=int(self.query_one("#llm_max_tokens", Input).value or "8192"),
                temperature=float(self.query_one("#llm_temperature", Input).value or "0.7"),
                request_timeout=int(self.query_one("#llm_timeout", Input).value or "300"),
            )

            # Embedding 配置
            embedding_type_value = self.query_one("#embedding_type", Select).value
            embedding_type = str(embedding_type_value) if embedding_type_value else "openai"

            self.config.embedding = EmbeddingConfig(
                type=embedding_type,
                endpoint=self.query_one("#embedding_endpoint", Input).value.strip(),
                api_key=self.query_one("#embedding_api_key", Input).value.strip(),
                model=self.query_one("#embedding_model", Input).value.strip(),
            )

            # 部署选项
            deployment_mode_value = self.query_one("#deployment_mode", Select).value
            self.config.deployment_mode = str(deployment_mode_value) if deployment_mode_value else "light"
            self.config.enable_web = self.query_one("#enable_web", Switch).value
            self.config.enable_rag = self.query_one("#enable_rag", Switch).value

        except (ValueError, AttributeError) as e:
            # 处理输入转换错误
            self.notify(f"配置输入错误: {e}", severity="error")
            return False
        else:
            return True


class DeploymentProgressScreen(ModalScreen[bool]):
    """
    部署进度屏幕

    显示部署进度和日志的模态对话框。
    """

    CSS = """
    DeploymentProgressScreen {
        align: center middle;
    }

    .progress-container {
        width: 90%;
        max-width: 120;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-radius: 3;
        padding: 1;
    }

    .progress-section {
        margin: 1 0;
        height: 6;
    }

    .log-section {
        margin: 1 0;
        height: 1fr;
        border: solid $secondary;
        border-radius: 2;
    }

    .button-section {
        height: 3;
        margin: 1 0;
        align: center middle;
    }

    .close-button {
        background: $success;
    }

    .cancel-button {
        background: $error;
    }
    """

    def __init__(self, config: DeploymentConfig) -> None:
        """
        初始化部署进度屏幕

        Args:
            config: 部署配置

        """
        super().__init__()
        self.config = config
        self.service = DeploymentService()
        self.deployment_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="progress-container"):
            yield Header()
            yield Static(
                "openEuler Intelligence 后端部署进度",
                classes="progress-section",
            )

            with Vertical(classes="progress-section"):
                yield Static("部署进度:", id="progress_label")
                yield ProgressBar(total=100, show_eta=False, id="progress_bar")
                yield Static("", id="step_label")

            with Container(classes="log-section"):
                yield RichLog(id="deployment_log", highlight=True, markup=True)

            with Horizontal(classes="button-section"):
                yield Button("完成", id="close", classes="close-button", disabled=True)
                yield Button("取消部署", id="cancel", classes="cancel-button")

    async def on_mount(self) -> None:
        """界面挂载时开始部署"""
        self.deployment_task = asyncio.create_task(self._start_deployment())

    @on(Button.Pressed, "#close")
    def on_close_button_pressed(self) -> None:
        """处理完成按钮点击"""
        self.dismiss(result=True)

    @on(Button.Pressed, "#cancel")
    async def on_cancel_button_pressed(self) -> None:
        """处理取消按钮点击"""
        if self.deployment_task and not self.deployment_task.done():
            # 取消部署任务
            self.service.cancel_deployment()
            self.deployment_task.cancel()

            # 更新界面
            self.query_one("#step_label", Static).update("部署已取消")
            self.query_one("#deployment_log", RichLog).write("部署已被用户取消")

            # 启用完成按钮
            self.query_one("#close", Button).disabled = False
            self.query_one("#cancel", Button).disabled = True

    async def _start_deployment(self) -> None:
        """开始部署流程"""
        try:
            success = await self.service.deploy(self.config, self._on_progress_update)

            # 更新界面状态
            if success:
                self.query_one("#step_label", Static).update("部署完成！")
                self.query_one("#deployment_log", RichLog).write(
                    "[bold green]部署成功完成！[/bold green]",
                )
            else:
                self.query_one("#step_label", Static).update("部署失败")
                self.query_one("#deployment_log", RichLog).write(
                    "[bold red]部署失败，请查看上面的错误信息[/bold red]",
                )

        except asyncio.CancelledError:
            self.query_one("#step_label", Static).update("部署已取消")
            self.query_one("#deployment_log", RichLog).write("部署被取消")
        except OSError as e:
            self.query_one("#step_label", Static).update("部署异常")
            self.query_one("#deployment_log", RichLog).write(
                f"[bold red]部署过程中发生异常: {e}[/bold red]",
            )
        finally:
            # 启用完成按钮，禁用取消按钮
            self.query_one("#close", Button).disabled = False
            self.query_one("#cancel", Button).disabled = True

    def _on_progress_update(self, state: DeploymentState) -> None:
        """处理进度更新"""
        # 更新进度条
        progress = (state.current_step / state.total_steps * 100) if state.total_steps > 0 else 0
        self.query_one("#progress_bar", ProgressBar).update(progress=progress)

        # 更新步骤标签
        step_text = f"步骤 {state.current_step}/{state.total_steps}: {state.current_step_name}"
        self.query_one("#step_label", Static).update(step_text)

        # 添加最新的日志条目
        log_widget = self.query_one("#deployment_log", RichLog)
        if state.output_log:
            # 只显示最新的日志条目
            latest_log = state.output_log[-1]
            if latest_log.startswith("✓"):
                log_widget.write(f"[green]{latest_log}[/green]")
            elif latest_log.startswith("✗"):
                log_widget.write(f"[red]{latest_log}[/red]")
            else:
                log_widget.write(latest_log)


class ErrorMessageScreen(ModalScreen[None]):
    """
    错误消息屏幕

    显示错误消息的模态对话框。
    """

    CSS = """
    ErrorMessageScreen {
        align: center middle;
    }

    .error-container {
        width: 60%;
        max-width: 80;
        height: auto;
        background: $surface;
        border: solid $error;
        border-radius: 3;
        padding: 1;
    }

    .error-title {
        color: $error;
        text-style: bold;
        margin: 1 0;
    }

    .error-list {
        margin: 1 0;
        max-height: 20;
    }

    .ok-button {
        margin: 1 0;
        align: center middle;
        background: $primary;
    }
    """

    def __init__(self, title: str, messages: list[str]) -> None:
        """
        初始化错误消息屏幕

        Args:
            title: 错误标题
            messages: 错误消息列表

        """
        super().__init__()
        self.title = title
        self.messages = messages

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="error-container"):
            yield Static(self.title or "错误", classes="error-title")

            with Vertical(classes="error-list"):
                for message in self.messages:
                    yield Static(f"• {message}")

            yield Button("确定", id="ok", classes="ok-button")

    @on(Button.Pressed, "#ok")
    def on_ok_button_pressed(self) -> None:
        """处理确定按钮点击"""
        self.dismiss()
