"""设置页面"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from backend.hermes import HermesChatClient
from backend.openai import OpenAIClient
from config import Backend, ConfigManager
from tool.validators import APIValidator, validate_oi_connection

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Key

    from backend.base import LLMClientBase


class SettingsScreen(Screen):
    """设置页面"""

    CSS_PATH = "css/styles.tcss"

    def __init__(self, config_manager: ConfigManager, llm_client: LLMClientBase) -> None:
        """初始化设置页面"""
        super().__init__()
        self.config_manager = config_manager
        self.llm_client = llm_client
        self.backend = self.config_manager.get_backend()
        self.models: list[str] = []
        self.selected_model = self.config_manager.get_model()
        # 添加保存任务的集合
        self.background_tasks: set[asyncio.Task] = set()

        # 验证相关状态
        self.is_validated = False
        self.validation_message = ""
        self.validator = APIValidator()

    def compose(self) -> ComposeResult:
        """构建设置页面"""
        yield Container(
            Container(
                Label("设置", id="settings-title"),
                # 后端选择
                Horizontal(
                    Label("后端:", classes="settings-label"),
                    Button(
                        f"{self.backend.get_display_name()}",
                        id="backend-btn",
                        classes="settings-value settings-button",
                    ),
                    classes="settings-option",
                ),
                # Base URL 输入
                Horizontal(
                    Label("Base URL:", classes="settings-label"),
                    Input(
                        value=self.config_manager.get_base_url()
                        if self.backend == Backend.OPENAI
                        else self.config_manager.get_eulerintelli_url(),
                        id="base-url",
                    ),
                    classes="settings-option",
                ),
                # API Key 输入
                Horizontal(
                    Label("API Key:", classes="settings-label"),
                    Input(
                        value=self.config_manager.get_api_key()
                        if self.backend == Backend.OPENAI
                        else self.config_manager.get_eulerintelli_key(),
                        id="api-key",
                    ),
                    classes="settings-option",
                ),
                # 模型选择（仅 OpenAI 后端显示）
                *(
                    [
                        Horizontal(
                            Label("模型:", classes="settings-label"),
                            Button(f"{self.selected_model}", id="model-btn", classes="settings-value settings-button"),
                            id="model-section",
                            classes="settings-option",
                        ),
                    ]
                    if self.backend == Backend.OPENAI
                    else []
                ),
                # 添加一个空白区域，确保操作按钮始终可见
                Static("", id="spacer"),
                # 操作按钮
                Horizontal(
                    Button("保存", id="save-btn", variant="primary"),
                    Button("取消", id="cancel-btn", variant="default"),
                    id="action-buttons",
                    classes="settings-option",
                ),
                id="settings-container",
            ),
            id="settings-screen",
        )

    def on_mount(self) -> None:
        """组件挂载时加载可用模型"""
        if self.backend == Backend.OPENAI:
            task = asyncio.create_task(self.load_models())
            # 保存任务引用
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

        # 启动配置验证
        validation_task = asyncio.create_task(self._validate_configuration())
        self.background_tasks.add(validation_task)
        validation_task.add_done_callback(self.background_tasks.discard)

        # 确保操作按钮始终可见
        self._ensure_buttons_visible()

    async def load_models(self) -> None:
        """异步加载当前选中后端的可用模型列表"""
        try:
            # 如果是 EULERINTELLI 后端，直接返回（不需要模型选择）
            if self.backend == Backend.EULERINTELLI:
                return

            # 使用当前选中的客户端获取模型列表
            self.models = await self.llm_client.get_available_models()

            if self.models and self.selected_model not in self.models:
                self.selected_model = self.models[0]

            # 更新模型按钮文本
            model_btn = self.query_one("#model-btn", Button)
            model_btn.label = self.selected_model
        except (OSError, ValueError, RuntimeError):
            model_btn = self.query_one("#model-btn", Button)
            model_btn.label = "暂无可用模型"

    @on(Input.Changed, "#base-url, #api-key")
    def on_config_changed(self) -> None:
        """当 Base URL 或 API Key 改变时更新客户端并验证配置"""
        if self.backend == Backend.OPENAI:
            self._update_llm_client()

        # 重新验证配置
        validation_task = asyncio.create_task(self._validate_configuration())
        self.background_tasks.add(validation_task)
        validation_task.add_done_callback(self.background_tasks.discard)

    @on(Button.Pressed, "#backend-btn")
    def toggle_backend(self) -> None:
        """切换后端"""
        current = self.backend
        new = Backend.EULERINTELLI if current == Backend.OPENAI else Backend.OPENAI
        self.backend = new

        # 更新按钮文本
        backend_btn = self.query_one("#backend-btn", Button)
        backend_btn.label = new.get_display_name()

        # 更新 URL 和 API Key
        base_url = self.query_one("#base-url", Input)
        api_key = self.query_one("#api-key", Input)

        if new == Backend.OPENAI:
            base_url.value = self.config_manager.get_base_url()
            api_key.value = self.config_manager.get_api_key()

            # 创建新的 OpenAI 客户端
            self._update_llm_client()

            # 添加模型选择部分
            if not self.query("#model-section"):
                container = self.query_one("#settings-container")
                spacer = self.query_one("#spacer")
                model_section = Horizontal(
                    Label("模型:", classes="settings-label"),
                    Button(self.selected_model, id="model-btn", classes="settings-value settings-button"),
                    id="model-section",
                    classes="settings-option",
                )

                # 在spacer前面添加model_section
                if spacer:
                    container.mount(model_section, before=spacer)
                else:
                    container.mount(model_section)

                # 重新加载模型
                task = asyncio.create_task(self.load_models())
                # 保存任务引用
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
        else:
            base_url.value = self.config_manager.get_eulerintelli_url()
            api_key.value = self.config_manager.get_eulerintelli_key()

            # 创建新的 Hermes 客户端
            self._update_llm_client()

            # 移除模型选择部分
            model_section = self.query("#model-section")
            if model_section:
                model_section[0].remove()

        # 确保按钮可见
        self._ensure_buttons_visible()

        # 切换后端后重新验证配置
        validation_task = asyncio.create_task(self._validate_configuration())
        self.background_tasks.add(validation_task)
        validation_task.add_done_callback(self.background_tasks.discard)

    @on(Button.Pressed, "#model-btn")
    def toggle_model(self) -> None:
        """循环切换模型"""
        if not self.models:
            return

        try:
            # 如果当前选择的模型在列表中，则找到它的索引
            if self.selected_model in self.models:
                idx = self.models.index(self.selected_model)
                idx = (idx + 1) % len(self.models)
            else:
                # 如果不在列表中，则从第一个模型开始
                idx = 0
            self.selected_model = self.models[idx]

            # 更新按钮文本
            model_btn = self.query_one("#model-btn", Button)
            model_btn.label = self.selected_model

            # 模型改变时重新验证配置
            validation_task = asyncio.create_task(self._validate_configuration())
            self.background_tasks.add(validation_task)
            validation_task.add_done_callback(self.background_tasks.discard)
        except (IndexError, ValueError):
            # 处理任何可能的异常
            self.selected_model = self.models[0] if self.models else "默认模型"
            model_btn = self.query_one("#model-btn", Button)
            model_btn.label = self.selected_model

    @on(Button.Pressed, "#save-btn")
    def save_settings(self) -> None:
        """保存设置"""
        # 检查验证状态
        if not self.is_validated:
            return

        self.config_manager.set_backend(self.backend)

        base_url = self.query_one("#base-url", Input).value
        api_key = self.query_one("#api-key", Input).value

        if self.backend == Backend.OPENAI:
            self.config_manager.set_base_url(base_url)
            self.config_manager.set_api_key(api_key)
            self.config_manager.set_model(self.selected_model)
        else:  # eulerintelli
            self.config_manager.set_eulerintelli_url(base_url)
            self.config_manager.set_eulerintelli_key(api_key)

        # 通知主应用刷新客户端
        refresh_method = getattr(self.app, "refresh_llm_client", None)
        if refresh_method:
            refresh_method()

        self.app.pop_screen()

    @on(Button.Pressed, "#cancel-btn")
    def cancel_settings(self) -> None:
        """取消设置"""
        self.app.pop_screen()

    def on_key(self, event: Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC 键退出设置页面，等效于取消
            self.app.pop_screen()

    def _ensure_buttons_visible(self) -> None:
        """确保操作按钮始终可见"""

        # 延迟一点执行，确保布局已完成
        async def scroll_to_buttons() -> None:
            await asyncio.sleep(0.1)
            container = self.query_one("#settings-container")
            action_buttons = self.query_one("#action-buttons")
            if action_buttons:
                container.scroll_to_widget(action_buttons)

        task = asyncio.create_task(scroll_to_buttons())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _validate_configuration(self) -> None:
        """验证当前配置"""
        base_url = self.query_one("#base-url", Input).value.strip()
        api_key = self.query_one("#api-key", Input).value.strip()

        if not base_url:
            self.is_validated = False
            self.validation_message = "Base URL 不能为空"
            self._update_save_button_state()
            return

        try:
            if self.backend == Backend.OPENAI:
                # 验证 OpenAI 配置
                model = self.selected_model if self.selected_model else "gpt-3.5-turbo"
                valid, message, _ = await self.validator.validate_llm_config(
                    endpoint=base_url,
                    api_key=api_key,
                    model=model,
                    timeout=10,
                )
                self.is_validated = valid
                self.validation_message = message
            else:
                # 验证 openEuler Intelligence 配置
                valid, message = await validate_oi_connection(base_url, api_key)
                self.is_validated = valid
                self.validation_message = message

        except (TimeoutError, ValueError, RuntimeError) as e:
            self.is_validated = False
            self.validation_message = f"验证过程中发生错误: {e!s}"

        self._update_save_button_state()

    def _update_save_button_state(self) -> None:
        """根据验证状态更新保存按钮"""
        save_btn = self.query_one("#save-btn", Button)
        if self.is_validated:
            save_btn.disabled = False
        else:
            save_btn.disabled = True

    def _update_llm_client(self) -> None:
        """根据当前UI中的配置更新LLM客户端"""
        base_url_input = self.query_one("#base-url", Input)
        api_key_input = self.query_one("#api-key", Input)

        if self.backend == Backend.OPENAI:
            self.llm_client = OpenAIClient(
                base_url=base_url_input.value,
                model=self.selected_model,
                api_key=api_key_input.value,
            )
        else:  # EULERINTELLI
            self.llm_client = HermesChatClient(
                base_url=base_url_input.value,
                auth_token=api_key_input.value,
            )
