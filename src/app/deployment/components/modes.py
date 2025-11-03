"""
初始化模式选择 TUI 界面

提供用户选择初始化方式的界面。
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any, ClassVar

from textual import on
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from config.manager import ConfigManager
from config.model import Backend, ConfigModel
from log.manager import get_logger
from tool.validators import validate_oi_connection

from . import EnvironmentCheckScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Focus


class ModeOptionButton(Button):
    """自定义的模式选择按钮，禁用文字高亮"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """初始化自定义按钮"""
        super().__init__(*args, **kwargs)
        # 禁用默认的文字样式
        self.styles.text_style = "none"

    def _on_focus(self, event: Focus) -> None:
        """覆盖焦点事件，禁用文字高亮"""
        super()._on_focus(event)
        self.styles.text_style = "none"


class InitializationModeScreen(ModalScreen[bool]):
    """
    初始化模式选择屏幕

    让用户选择连接现有服务或部署新服务。
    """

    BINDINGS: ClassVar = [
        Binding("escape", "app.quit", "退出"),
    ]

    def __init__(self) -> None:
        """初始化模式选择屏幕"""
        super().__init__()

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="mode-container"):
            yield Static("openEuler Intelligence 初始化", classes="mode-title")
            yield Static(
                "请选择您的初始化方式：",
                classes="mode-description",
            )

            with Horizontal(classes="options-row"):
                # 连接现有服务选项
                yield ModeOptionButton(
                    "连接现有服务\n\n输入现有服务的 URL 和 Token 即可连接使用",
                    id="connect_existing",
                    classes="mode-option",
                    variant="default",
                )

                # 部署新服务选项
                yield ModeOptionButton(
                    "部署新服务\n\n在本机部署全新的服务环境和配置",
                    id="deploy_new",
                    classes="mode-option",
                    variant="default",
                )

            with Horizontal(classes="mode-button-row"):
                yield Button("退出", id="exit", variant="error", classes="exit-button")

    def on_mount(self) -> None:
        """组件挂载时的处理"""
        # 设置默认焦点到第一个按钮
        try:
            connect_btn = self.query_one("#connect_existing", Button)
            connect_btn.focus()
        except (ValueError, AttributeError):
            pass

    @on(Button.Pressed, "#connect_existing")
    async def on_connect_existing_pressed(self) -> None:
        """处理连接现有服务按钮点击"""
        await self.app.push_screen(ConnectExistingServiceScreen())
        self.dismiss(result=True)

    @on(Button.Pressed, "#deploy_new")
    async def on_deploy_new_pressed(self) -> None:
        """处理部署新服务按钮点击"""
        await self.app.push_screen(EnvironmentCheckScreen())
        self.dismiss(result=True)

    @on(Button.Pressed, "#exit")
    def on_exit_button_pressed(self) -> None:
        """处理退出按钮点击"""
        self.app.exit()


class ConnectExistingServiceScreen(ModalScreen[bool]):
    """
    连接现有服务配置屏幕

    允许用户输入现有 openEuler Intelligence 服务的连接信息。
    """

    CSS = """
    .form-row {
        height: 3;
        margin: 1 0;
        align: left middle;
    }

    .form-label {
        color: #4963b1;
        text-style: bold;
        width: 20;
        content-align: left middle;
        padding-right: 1;
        padding-top: 1;
    }

    .form-input {
        width: 1fr;
        margin-left: 1;
    }
    """

    BINDINGS: ClassVar = [
        Binding("escape", "back", "返回"),
        Binding("ctrl+q", "app.quit", "退出"),
    ]

    def __init__(self) -> None:
        """初始化连接现有服务屏幕"""
        super().__init__()
        self.validation_task: asyncio.Task[None] | None = None
        self.is_validated = False

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="connect-container"):
            yield Static("连接现有 openEuler Intelligence 服务", classes="connect-title")
            yield Static(
                "请输入您的 openEuler Intelligence 服务连接信息：",
                classes="connect-description",
            )

            with Horizontal(classes="form-row"):
                yield Label("服务 URL:", classes="form-label")
                yield Input(
                    placeholder="例如：http://your-server:8002",
                    id="service_url",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("Access Token:", classes="form-label")
                yield Input(
                    placeholder="可选，您的访问令牌",
                    password=True,
                    id="access_token",
                    classes="form-input",
                )

            yield Static("未验证", id="validation_status", classes="validation-status")

            yield Static(
                "提示：\n"
                "• 服务 URL 通常以 http:// 或 https:// 开头\n"
                "• Access Token 为可选项，如果服务无需认证可留空\n"
                "• 如有 Token，可以从 openEuler Intelligence 管理界面获取\n"
                "• 系统会自动验证连接并保存配置",
                classes="help-text",
            )

            with Horizontal(classes="mode-button-row"):
                yield Button("连接并保存", id="connect", variant="success", disabled=True)
                yield Button("返回", id="back", variant="primary")
                yield Button("退出", id="exit", variant="error")

    @on(Input.Changed, "#service_url, #access_token")
    async def on_field_changed(self, event: Input.Changed) -> None:
        """处理输入字段变化"""
        # 取消之前的验证任务
        if self.validation_task and not self.validation_task.done():
            self.validation_task.cancel()

        # 检查是否需要验证
        if self._should_validate():
            # 延迟验证，避免频繁触发
            self.validation_task = asyncio.create_task(self._delayed_validation())

    def _should_validate(self) -> bool:
        """检查是否应该进行验证"""
        try:
            url = self.query_one("#service_url", Input).value.strip()
            # 只需要 URL 不为空即可进行验证，Token 是可选的
            return bool(url)
        except (AttributeError, ValueError):
            return False

    async def _delayed_validation(self) -> None:
        """延迟验证"""
        try:
            await asyncio.sleep(1)  # 等待 1 秒
            await self._validate_connection()
        except asyncio.CancelledError:
            pass

    async def _validate_connection(self) -> None:
        """验证连接"""
        status_widget = self.query_one("#validation_status", Static)
        connect_button = self.query_one("#connect", Button)

        # 更新状态为验证中
        status_widget.update("[yellow]验证连接中...[/yellow]")
        connect_button.disabled = True
        self.is_validated = False

        try:
            # 获取输入值
            url = self.query_one("#service_url", Input).value.strip()
            token = self.query_one("#access_token", Input).value.strip()

            # 执行连接验证
            is_valid, message = await validate_oi_connection(url, token)

            if is_valid:
                status_widget.update(f"[green]✓ {message}[/green]")
                connect_button.disabled = False
                self.is_validated = True
                self.notify("连接验证成功", severity="information")
            else:
                status_widget.update(f"[red]✗ {message}[/red]")
                connect_button.disabled = True
                self.is_validated = False
                self.notify(f"连接验证失败: {message}", severity="error")

        except (OSError, RuntimeError, ValueError) as e:
            status_widget.update(f"[red]✗ 验证异常: {e}[/red]")
            connect_button.disabled = True
            self.is_validated = False
            self.notify(f"验证过程中出现异常: {e}", severity="error")

    @on(Button.Pressed, "#connect")
    async def on_connect_pressed(self) -> None:
        """处理连接按钮点击"""
        if not self.is_validated:
            self.notify("请等待连接验证完成", severity="warning")
            return

        try:
            # 获取输入值
            url = self.query_one("#service_url", Input).value.strip()
            token = self.query_one("#access_token", Input).value.strip()

            # 保存配置
            await self._save_configuration(url, token)

            # 显示成功信息
            self.notify("配置已保存，初始化完成！", severity="information")
            self.app.exit()

        except (OSError, RuntimeError, ValueError) as e:
            self.notify(f"保存配置时发生错误: {e}", severity="error")

    async def _save_configuration(self, url: str, token: str) -> None:
        """保存连接配置"""
        logger = get_logger(__name__)

        try:
            # 更新当前用户配置
            config_manager = ConfigManager()
            config_manager.set_eulerintelli_url(url)
            config_manager.set_eulerintelli_key(token)
            config_manager.set_backend(Backend.EULERINTELLI)

            logger.info("用户配置已保存: URL=%s", url)

            # 如果是 root 用户，从用户配置创建全局模板
            is_root = os.geteuid() == 0
            if is_root:
                logger.info("检测到 root 用户，创建全局配置模板")

                deployment_manager = ConfigManager.create_deployment_manager()

                config_dict = config_manager.data.to_dict()
                deployment_manager.data = ConfigModel.from_dict(config_dict)

                if deployment_manager.create_global_template():
                    logger.info("全局配置模板创建成功")
                else:
                    logger.warning("创建全局配置模板失败，但用户配置已保存")

        except (OSError, RuntimeError, ValueError):
            logger.exception("保存配置时发生错误")
            raise

    @on(Button.Pressed, "#back")
    async def on_back_pressed(self) -> None:
        """处理返回按钮点击"""
        self.dismiss(result=False)

    @on(Button.Pressed, "#exit")
    def on_exit_pressed(self) -> None:
        """处理退出按钮点击"""
        self.app.exit()

    async def action_back(self) -> None:
        """键盘返回操作"""
        self.dismiss(result=False)
