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
    Static,
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
        width: 95%;
        max-width: 130;
        height: 95%;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }

    .form-row {
        height: 3;
        margin: 0;
    }

    .form-label {
        width: 18;
        text-align: left;
        text-style: bold;
        content-align: left middle;
    }

    .form-input {
        width: 1fr;
        margin-left: 1;
    }

    .button-row {
        height: 3;
        margin: 1 0 0 0;
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

    #llm_validation_status, #embedding_validation_status {
        text-style: italic;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        height: auto;
        scrollbar-size: 1 1;
        overflow: auto;
    }

    .llm-config-container, .embedding-config-container {
        height: 1fr;
        scrollbar-size: 1 1;
        overflow-y: auto;
        overflow-x: hidden;
    }
    """

    def __init__(self) -> None:
        """初始化部署配置屏幕"""
        super().__init__()
        self.config = DeploymentConfig()
        self._llm_validation_task: asyncio.Task[None] | None = None
        self._embedding_validation_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="config-container"):
            yield Header()

            with TabbedContent():
                with TabPane("基础配置", id="basic"):
                    yield from self._compose_basic_config()

                with TabPane("LLM 配置", id="llm"):
                    yield from self._compose_llm_config()

                with TabPane("Embedding 配置", id="embedding"):
                    yield from self._compose_embedding_config()

            with Horizontal(classes="button-row"):
                yield Button("开始部署", id="deploy", classes="deploy-button")
                yield Button("取消", id="cancel", classes="cancel-button")

    def _compose_basic_config(self) -> ComposeResult:
        """组合基础配置组件"""
        with Vertical():
            yield Static("基础配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("服务器 IP 地址:", classes="form-label")
                yield Input(
                    placeholder="例如：127.0.0.1",
                    id="server_ip",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("部署模式:", classes="form-label")
                # 使用按钮在轻量/全量间切换，按钮文本显示当前选择（不包含括号描述）
                yield Button("轻量部署", id="deployment_mode_btn", classes="form-input")

            # 描述区域，显示当前部署模式的详细说明
            with Horizontal(classes="form-row"):
                yield Static(
                    "轻量部署：仅部署框架服务。",
                    id="deployment_mode_desc",
                    classes="form-input",
                )

    def _compose_llm_config(self) -> ComposeResult:
        """组合 LLM 配置组件"""
        with Vertical(classes="llm-config-container"):
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
                yield Label("验证状态:", classes="form-label")
                yield Static("未验证", id="llm_validation_status", classes="form-input")

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
        with Vertical(classes="embedding-config-container"):
            yield Static("嵌入模型配置", classes="form-label")

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

            with Horizontal(classes="form-row"):
                yield Label("验证状态:", classes="form-label")
                yield Static("未验证", id="embedding_validation_status", classes="form-input")

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

            # 直接推送部署进度屏幕，不关闭当前界面
            await self.app.push_screen(DeploymentProgressScreen(self.config))
            # 部署完成后，退出整个应用
            self.app.exit()

    @on(Button.Pressed, "#cancel")
    def on_cancel_button_pressed(self) -> None:
        """处理取消按钮点击"""
        # 退出整个程序
        self.app.exit()

    @on(Button.Pressed, "#deployment_mode_btn")
    def on_deployment_mode_btn_pressed(self) -> None:
        """切换部署模式按钮：在轻量和全量之间切换，更新按钮文本和描述。"""
        try:
            btn = self.query_one("#deployment_mode_btn", Button)
            desc = self.query_one("#deployment_mode_desc", Static)
            # 如果当前为轻量，则切换到全量
            if btn.label and "轻量" in str(btn.label):
                btn.label = "全量部署"
                desc.update("全量部署：部署框架服务、Web 界面和 RAG 组件。")
            else:
                btn.label = "轻量部署"
                desc.update("轻量部署：仅部署框架服务。")
        except (AttributeError, ValueError):
            # 查询失败或属性错误时忽略
            return

    @on(Input.Changed, "#llm_endpoint, #llm_api_key, #llm_model")
    async def on_llm_field_changed(self, event: Input.Changed) -> None:
        """处理 LLM 字段变化，检查是否需要自动验证"""
        # 取消之前的验证任务
        if self._llm_validation_task and not self._llm_validation_task.done():
            self._llm_validation_task.cancel()

        # 检查是否所有核心字段都已填写
        if self._should_validate_llm():
            # 延迟 1 秒后进行验证，避免用户快速输入时频繁触发
            self._llm_validation_task = asyncio.create_task(self._delayed_llm_validation())

    @on(Input.Changed, "#embedding_endpoint, #embedding_api_key, #embedding_model")
    async def on_embedding_field_changed(self, event: Input.Changed) -> None:
        """处理 Embedding 字段变化，检查是否需要自动验证"""
        # 取消之前的验证任务
        if self._embedding_validation_task and not self._embedding_validation_task.done():
            self._embedding_validation_task.cancel()

        # 检查是否所有核心字段都已填写
        if self._should_validate_embedding():
            # 延迟 1 秒后进行验证，避免用户快速输入时频繁触发
            self._embedding_validation_task = asyncio.create_task(self._delayed_embedding_validation())

    def _should_validate_llm(self) -> bool:
        """检查是否应该验证 LLM 配置"""
        try:
            endpoint = self.query_one("#llm_endpoint", Input).value.strip()
            api_key = self.query_one("#llm_api_key", Input).value.strip()
            model = self.query_one("#llm_model", Input).value.strip()
            return bool(endpoint and api_key and model)
        except (AttributeError, ValueError):
            return False

    def _should_validate_embedding(self) -> bool:
        """检查是否应该验证 Embedding 配置"""
        try:
            endpoint = self.query_one("#embedding_endpoint", Input).value.strip()
            api_key = self.query_one("#embedding_api_key", Input).value.strip()
            model = self.query_one("#embedding_model", Input).value.strip()
            return bool(endpoint and api_key and model)
        except (AttributeError, ValueError):
            return False

    async def _delayed_llm_validation(self) -> None:
        """延迟 LLM 验证"""
        try:
            await asyncio.sleep(1)  # 等待 1 秒
            await self._validate_llm_config()
        except asyncio.CancelledError:
            pass

    async def _delayed_embedding_validation(self) -> None:
        """延迟 Embedding 验证"""
        try:
            await asyncio.sleep(1)  # 等待 1 秒
            await self._validate_embedding_config()
        except asyncio.CancelledError:
            pass

    async def _validate_llm_config(self) -> None:
        """验证 LLM 配置"""
        # 更新状态为验证中
        status_widget = self.query_one("#llm_validation_status", Static)
        status_widget.update("[yellow]验证中...[/yellow]")

        # 收集当前 LLM 配置
        self._collect_llm_config()

        try:
            # 执行验证
            is_valid, message, info = await self.config.validate_llm_connectivity()

            # 更新验证状态
            if is_valid:
                status_widget.update(f"[green]✓ {message}[/green]")
                # 检查是否支持 function_call
                if info.get("supports_function_call"):
                    self.notify("LLM 验证成功，支持 function_call 功能", severity="information")
                else:
                    self.notify("LLM 验证成功，但不支持 function_call 功能", severity="warning")
            else:
                status_widget.update(f"[red]✗ {message}[/red]")
                self.notify(f"LLM 验证失败: {message}", severity="error")

        except (OSError, ValueError, TypeError) as e:
            status_widget.update(f"[red]✗ 验证异常: {e}[/red]")
            self.notify(f"LLM 验证过程中出现异常: {e}", severity="error")

    async def _validate_embedding_config(self) -> None:
        """验证 Embedding 配置"""
        # 更新状态为验证中
        status_widget = self.query_one("#embedding_validation_status", Static)
        status_widget.update("[yellow]验证中...[/yellow]")

        # 收集当前 Embedding 配置
        self._collect_embedding_config()

        try:
            # 执行验证
            is_valid, message, info = await self.config.validate_embedding_connectivity()

            # 更新验证状态
            if is_valid:
                status_widget.update(f"[green]✓ {message}[/green]")
                # 显示维度信息
                dimension = info.get("dimension", "未知")
                self.notify(f"Embedding 验证成功，向量维度: {dimension}", severity="information")
            else:
                status_widget.update(f"[red]✗ {message}[/red]")
                self.notify(f"Embedding 验证失败: {message}", severity="error")

        except (OSError, ValueError, TypeError) as e:
            status_widget.update(f"[red]✗ 验证异常: {e}[/red]")
            self.notify(f"Embedding 验证过程中出现异常: {e}", severity="error")

    def _collect_llm_config(self) -> None:
        """收集 LLM 配置"""
        try:
            self.config.llm.endpoint = self.query_one("#llm_endpoint", Input).value.strip()
            self.config.llm.api_key = self.query_one("#llm_api_key", Input).value.strip()
            self.config.llm.model = self.query_one("#llm_model", Input).value.strip()
            self.config.llm.max_tokens = int(self.query_one("#llm_max_tokens", Input).value or "8192")
            self.config.llm.temperature = float(self.query_one("#llm_temperature", Input).value or "0.7")
            self.config.llm.request_timeout = int(self.query_one("#llm_timeout", Input).value or "300")
        except (ValueError, AttributeError):
            # 如果转换失败，使用默认值
            pass

    def _collect_embedding_config(self) -> None:
        """收集 Embedding 配置"""
        try:
            # 固定使用 openai 类型
            self.config.embedding.type = "openai"
            self.config.embedding.endpoint = self.query_one("#embedding_endpoint", Input).value.strip()
            self.config.embedding.api_key = self.query_one("#embedding_api_key", Input).value.strip()
            self.config.embedding.model = self.query_one("#embedding_model", Input).value.strip()
        except AttributeError:
            # 如果获取失败，使用默认值
            pass

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
            self.config.embedding = EmbeddingConfig(
                type="openai",  # 固定使用 openai 类型
                endpoint=self.query_one("#embedding_endpoint", Input).value.strip(),
                api_key=self.query_one("#embedding_api_key", Input).value.strip(),
                model=self.query_one("#embedding_model", Input).value.strip(),
            )

            # 部署选项 - 从切换按钮读取当前模式
            try:
                btn = self.query_one("#deployment_mode_btn", Button)
                label = str(btn.label) if btn.label is not None else ""
                if "全量" in label:
                    self.config.deployment_mode = "full"
                else:
                    self.config.deployment_mode = "light"
            except (AttributeError, ValueError):
                self.config.deployment_mode = "light"

            # 根据部署模式自动设置组件启用状态
            if self.config.deployment_mode == "full":
                self.config.enable_web = True
                self.config.enable_rag = True
            else:
                self.config.enable_web = False
                self.config.enable_rag = False

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
        # 退出整个程序
        self.app.exit()

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
