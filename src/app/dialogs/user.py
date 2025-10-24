"""用户配置对话框"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TabbedContent, TabPane

from backend import HermesChatClient
from backend.models import LLMType, ModelInfo
from i18n.manager import _

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from backend import LLMClientBase
    from config.manager import ConfigManager


class UserConfigDialog(ModalScreen):
    """用户配置对话框"""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("up", "previous_model", _("上一个模型")),
        ("down", "next_model", _("下一个模型")),
        ("space", "activate_model", _("激活模型")),
        ("enter", "save_llm_settings", _("保存大模型设置")),
        ("escape", "cancel", _("取消")),
    ]

    def __init__(
        self,
        config_manager: ConfigManager,
        llm_client: LLMClientBase,
    ) -> None:
        """
        初始化用户配置对话框

        Args:
            config_manager: 配置管理器
            llm_client: LLM 客户端（用于获取模型列表）

        """
        super().__init__()
        self.config_manager = config_manager
        self.llm_client = llm_client

        # 模型数据
        self.all_models: list[ModelInfo] = []
        self.chat_models: list[ModelInfo] = []

        # 当前已保存的模型（从配置读取）
        self.saved_chat_model = config_manager.get_llm_chat_model()
        # 已激活的模型（用空格键确认，等待保存）
        self.activated_chat_model = self.saved_chat_model

        # 用户名（临时状态，未保存）
        self.username = ""
        if isinstance(self.llm_client, HermesChatClient):
            self.username = self.llm_client.get_user_name()

        # 是否管理员
        self.is_admin = False
        if isinstance(self.llm_client, HermesChatClient):
            self.is_admin = self.llm_client.is_admin()

        # MCP 工具授权相关状态
        self.auto_execute_status = False  # 默认为手动确认
        self.mcp_status_loaded = False  # 是否已成功加载状态
        if isinstance(self.llm_client, HermesChatClient):
            self.auto_execute_status = self.llm_client.get_auto_execute_status()
            self.mcp_status_loaded = True

        # 当前标签页
        self.current_tab = "general"

        # 模型列表光标位置
        self.chat_cursor = 0

        # 加载状态
        self.models_loaded = False
        self.loading_error = False

    def compose(self) -> ComposeResult:
        """构建对话框"""
        with (
            Container(id="user-dialog-screen"),
            Container(id="user-dialog"),
            TabbedContent(
                id="user-tabs",
                initial="general-tab",
            ),
        ):
            yield TabPane(_("常规设置"), id="general-tab")
            yield TabPane(_("大模型设置"), id="llm-tab")

    async def on_mount(self) -> None:
        """组件挂载时加载模型列表和渲染内容"""
        await self._load_models()
        self._render_all_tabs()
        self._update_cursor_positions()

    async def _load_models(self) -> None:
        """异步加载模型列表"""
        try:
            self.all_models = await self.llm_client.get_available_models()
            self.chat_models = [model for model in self.all_models if LLMType.CHAT in model.llm_type]
            self.models_loaded = True
            self.loading_error = False
        except (OSError, ValueError, RuntimeError):
            self.models_loaded = False
            self.loading_error = True

    def _render_all_tabs(self) -> None:
        """渲染所有标签页内容"""
        self._render_general_tab()
        self._render_chat_llm_tab()

    def _render_general_tab(self) -> None:
        """渲染常规设置标签页"""
        tab_pane = self.query_one("#general-tab", TabPane)

        # 清空现有内容
        tab_pane.remove_children()

        # 创建表单容器
        form_container = Container(classes="general-settings-form")

        # 先挂载表单容器到 tab_pane
        tab_pane.mount(form_container)

        # 用户名和用户类型显示（用户类型在右侧）
        user_row = Horizontal(classes="settings-option")
        form_container.mount(user_row)

        # 左侧：标签
        user_row.mount(Label(_("用户名:"), classes="settings-label"))

        # 右侧：值容器（包含用户名和徽章）
        value_container = Horizontal(classes="settings-value-container")
        user_row.mount(value_container)

        # 用户名
        value_container.mount(
            Static(
                self.username if self.username else _("未登录"),
                id="username-display",
                classes="settings-value",
            ),
        )

        # 用户类型徽章
        if self.username:
            user_type_text = _("管理员") if self.is_admin else _("普通用户")
            user_type_class = "user-type-admin" if self.is_admin else "user-type-user"
            value_container.mount(
                Static(
                    user_type_text,
                    id="user-type-display",
                    classes=f"user-type-badge {user_type_class}",
                ),
            )

        # MCP 工具授权设置（仅当支持时显示）
        if self.mcp_status_loaded:
            form_container.mount(
                Horizontal(
                    Label(_("MCP 工具授权:"), classes="settings-label"),
                    Button(
                        _("自动执行") if self.auto_execute_status else _("手动确认"),
                        id="mcp-toggle-btn",
                        classes="settings-button",
                    ),
                    classes="settings-option",
                ),
            )

        # 按钮区域
        button_container = Horizontal(id="general-buttons", classes="form-buttons")
        tab_pane.mount(button_container)

        # 创建按钮并挂载到按钮容器
        button_container.mount(Button(_("保存"), id="save-user-settings-btn", variant="primary"))
        button_container.mount(Button(_("取消"), id="cancel-general-btn", variant="default"))

    def _render_chat_llm_tab(self) -> None:
        """渲染大模型设置标签页"""
        self._render_tab_content("llm-tab", self.chat_models, self.activated_chat_model, self.chat_cursor)

    def _render_tab_content(
        self,
        tab_id: str,
        models: list[ModelInfo],
        activated_llm_id: str,
        cursor_index: int,
    ) -> None:
        """
        渲染标签页内容

        Args:
            tab_id: 标签页 ID
            models: 模型列表
            activated_llm_id: 已激活的模型 llmId（用空格键确认）
            cursor_index: 光标位置

        """
        tab_pane = self.query_one(f"#{tab_id}", TabPane)

        # 清空现有内容
        tab_pane.remove_children()

        # 创建内容容器
        content_container = Container(id=f"{tab_id}-content", classes="llm-tab-content")
        tab_pane.mount(content_container)

        if not self.models_loaded:
            if self.loading_error:
                content_container.mount(Static(_("加载模型失败"), classes="llm-error"))
            else:
                content_container.mount(Static(_("加载中..."), classes="llm-loading"))

        elif not models:
            content_container.mount(Static(_("暂无可用模型"), classes="llm-empty"))

        else:
            # 渲染模型列表
            model_list_container = Container(id=f"{tab_id}-list", classes="llm-model-list")
            for i, model in enumerate(models):
                is_saved = model.llm_id == self.saved_chat_model  # 已保存的
                is_activated = model.llm_id == activated_llm_id  # 已激活的（用空格确认）
                is_cursor = i == cursor_index  # 光标选中的

                # 构建样式类
                classes = "llm-model-item"
                if is_saved:
                    classes += " llm-model-saved"
                if is_activated:
                    classes += " llm-model-activated"
                if is_cursor:
                    classes += " llm-model-cursor"

                model_item = Static(model.model_name, classes=classes)
                model_list_container.mount(model_item)

            content_container.mount(model_list_container)

            # 显示当前光标所指模型的详细信息
            if 0 <= cursor_index < len(models):
                current_model = models[cursor_index]
                detail_container = self._create_model_detail(current_model)
                content_container.mount(detail_container)

        # 添加帮助文本
        tab_pane.mount(
            Static(
                _("↑↓: 选择模型  空格: 激活  回车: 保存  ESC: 取消"),
                id="llm-dialog-help",
            ),
        )

    def _create_model_detail(self, model: ModelInfo) -> Container:
        """
        创建模型详情容器

        Args:
            model: 模型信息

        Returns:
            包含模型详情的容器

        """
        detail_container = Container(classes="llm-model-detail")

        # 模型描述
        if model.llm_description:
            detail_container.mount(
                Horizontal(
                    Label(_("描述: "), classes="llm-detail-label"),
                    Static(model.llm_description, classes="llm-detail-value"),
                    classes="llm-detail-row",
                ),
            )

        # 模型类型标签
        if model.llm_type:
            type_str = ", ".join([t.value for t in model.llm_type])
            detail_container.mount(
                Horizontal(
                    Label(_("类型: "), classes="llm-detail-label"),
                    Static(type_str, classes="llm-detail-value"),
                    classes="llm-detail-row",
                ),
            )

        # 最大 token 数
        if model.max_tokens:
            detail_container.mount(
                Horizontal(
                    Label(_("最大 Token: "), classes="llm-detail-label"),
                    Static(str(model.max_tokens), classes="llm-detail-value"),
                    classes="llm-detail-row",
                ),
            )

        return detail_container

    def _update_cursor_positions(self) -> None:
        """根据已保存的配置更新光标位置"""
        # 基础模型光标
        if self.activated_chat_model:
            for i, model in enumerate(self.chat_models):
                if model.llm_id == self.activated_chat_model:
                    self.chat_cursor = i
                    break

    @on(TabbedContent.TabActivated)
    def on_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """标签页切换事件"""
        tab_id = event.tab.id
        if tab_id == "general-tab":
            self.current_tab = "general"
        elif tab_id == "llm-tab":
            self.current_tab = "llm"

    @on(Button.Pressed, "#save-user-settings-btn")
    async def on_save_user_settings(self) -> None:
        """保存用户设置（MCP 自动执行状态）"""
        # 调用后端 API 保存 MCP 自动执行状态
        if isinstance(self.llm_client, HermesChatClient):
            await self.llm_client.update_user_info(
                user_name=self.username,
                auto_execute=self.auto_execute_status,
            )

        # 保存成功后关闭对话框
        self.app.pop_screen()

    @on(Button.Pressed, "#cancel-general-btn")
    def on_cancel_general(self) -> None:
        """取消常规设置的修改，关闭对话框"""
        self.app.pop_screen()

    @on(Button.Pressed, "#mcp-toggle-btn")
    def on_toggle_mcp(self) -> None:
        """切换 MCP 工具授权模式（仅改变本地临时状态）"""
        if not self.mcp_status_loaded:
            return

        # 切换本地状态
        self.auto_execute_status = not self.auto_execute_status

        # 更新按钮显示
        mcp_btn = self.query_one("#mcp-toggle-btn", Button)
        mcp_btn.label = _("自动执行") if self.auto_execute_status else _("手动确认")

    def action_previous_model(self) -> None:
        """选择上一个模型（仅在大模型设置标签页生效）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        self.chat_cursor = max(0, self.chat_cursor - 1)
        self._render_chat_llm_tab()

    def action_next_model(self) -> None:
        """选择下一个模型（仅在大模型设置标签页生效）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        self.chat_cursor = min(len(self.chat_models) - 1, self.chat_cursor + 1)
        self._render_chat_llm_tab()

    def action_activate_model(self) -> None:
        """激活当前光标所在的模型（用空格键），等待保存"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        if 0 <= self.chat_cursor < len(self.chat_models):
            self.activated_chat_model = self.chat_models[self.chat_cursor].llm_id or ""
            self._render_chat_llm_tab()

    def action_save_llm_settings(self) -> None:
        """保存大模型设置（用回车键）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        # 保存已激活的模型到配置
        self.config_manager.set_llm_chat_model(self.activated_chat_model)
        self.saved_chat_model = self.activated_chat_model
        # 关闭对话框
        self.app.pop_screen()

    def action_cancel(self) -> None:
        """取消并关闭对话框"""
        self.app.pop_screen()
