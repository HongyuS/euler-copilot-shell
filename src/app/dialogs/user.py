"""用户配置对话框"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TabbedContent, TabPane

from backend.models import LLMType, ModelInfo
from i18n.manager import _

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from backend.base import LLMClientBase
    from config.manager import ConfigManager


class UserConfigDialog(ModalScreen):
    """用户配置对话框"""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("up", "previous_model", _("上一个模型")),
        ("down", "next_model", _("下一个模型")),
        ("space", "select_model", _("选择模型")),
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

        # 模型数据（仅 chat 模型）
        self.all_models: list[ModelInfo] = []
        self.chat_models: list[ModelInfo] = []

        # 当前选择的模型（临时状态，未保存）
        self.selected_chat_model = config_manager.get_llm_chat_model()

        # 用户名（临时状态，未保存）
        self.username = ""  # TODO: 从 config_manager 读取用户名

        # MCP 工具授权相关状态（仅 EULERINTELLI 后端）
        self.auto_execute_status = False  # 默认为手动确认
        self.mcp_status_loaded = False  # 是否已成功加载状态

        # 当前标签页
        self.current_tab = "general"

        # 模型列表光标位置
        self.chat_cursor = 0

        # 加载状态
        self.models_loaded = False
        self.loading_error = False

    def compose(self) -> ComposeResult:
        """构建对话框"""
        with Container(id="user-dialog-screen"), Container(id="user-dialog"):
            # 标签页容器
            with TabbedContent(id="user-tabs", initial="general-tab"):
                with TabPane(_("常规设置"), id="general-tab"):
                    pass  # 内容将在 on_mount 中动态添加
                with TabPane(_("大模型设置"), id="llm-tab"):
                    pass  # 内容将在 on_mount 中动态添加
            # 帮助文本
            yield Static(
                _("Tab: 切换焦点  ↑↓: 选择模型  空格: 确认  ESC: 取消"),
                id="user-dialog-help",
            )

    async def on_mount(self) -> None:
        """组件挂载时加载模型列表和渲染内容"""
        await self._load_models()
        await self._load_mcp_status()
        self._render_all_tabs()
        self._update_cursor_positions()

    async def _load_models(self) -> None:
        """异步加载模型列表"""
        try:
            # 获取所有可用模型
            if hasattr(self.llm_client, "get_available_models"):
                self.all_models = await self.llm_client.get_available_models()  # type: ignore[attr-defined]

                # 只需要 chat 模型
                self.chat_models = [model for model in self.all_models if LLMType.CHAT in model.llm_type]

                self.models_loaded = True
                self.loading_error = False
            else:
                self.models_loaded = False
                self.loading_error = True

        except (OSError, ValueError, RuntimeError):
            self.models_loaded = False
            self.loading_error = True

    async def _load_mcp_status(self) -> None:
        """异步加载 MCP 工具授权状态"""
        try:
            # 从客户端获取自动执行状态
            if hasattr(self.llm_client, "get_auto_execute_status"):
                self.auto_execute_status = await self.llm_client.get_auto_execute_status()  # type: ignore[attr-defined]
                self.mcp_status_loaded = True
            else:
                self.auto_execute_status = False
                self.mcp_status_loaded = False

        except (OSError, ValueError, RuntimeError):
            self.auto_execute_status = False
            self.mcp_status_loaded = False

    def _render_all_tabs(self) -> None:
        """渲染所有标签页内容"""
        self._render_general_tab()
        self._render_llm_tab()

    def _render_general_tab(self) -> None:
        """渲染常规设置标签页"""
        tab_pane = self.query_one("#general-tab", TabPane)

        # 清空现有内容
        tab_pane.remove_children()

        # 创建表单容器
        form_container = Container(classes="general-settings-form")

        # 先挂载表单容器到 tab_pane
        tab_pane.mount(form_container)

        # 然后再向表单容器添加子组件
        # 用户名输入
        form_container.mount(Label(_("用户名:"), classes="form-label"))
        username_input = Input(
            placeholder=_("请输入用户名"),
            value=self.username,
            id="username-input",
            classes="form-input",
        )
        form_container.mount(username_input)

        # MCP 工具授权设置（仅当支持时显示）
        if self.mcp_status_loaded:
            form_container.mount(Label(_("MCP 工具授权:"), classes="form-label"))
            mcp_button_container = Horizontal(classes="mcp-toggle-container")
            form_container.mount(mcp_button_container)
            mcp_button_container.mount(
                Button(
                    _("自动执行") if self.auto_execute_status else _("手动确认"),
                    id="mcp-toggle-btn",
                    classes="form-button",
                ),
            )

        # 按钮区域
        button_container = Horizontal(classes="form-buttons")
        form_container.mount(button_container)

        # 向按钮容器添加按钮
        button_container.mount(Button(_("保存"), id="save-username-btn", variant="primary"))
        button_container.mount(Button(_("取消"), id="cancel-general-btn", variant="default"))

    def _render_llm_tab(self) -> None:
        """渲染大模型设置标签页"""
        self._render_tab_content("llm-tab", self.chat_models, self.selected_chat_model, self.chat_cursor)

    def _render_tab_content(
        self,
        tab_id: str,
        models: list[ModelInfo],
        selected_llm_id: str,
        cursor_index: int,
    ) -> None:
        """
        渲染标签页内容

        Args:
            tab_id: 标签页 ID
            models: 模型列表
            selected_llm_id: 当前选中的模型 llmId
            cursor_index: 光标位置

        """
        tab_pane = self.query_one(f"#{tab_id}", TabPane)

        # 清空现有内容
        tab_pane.remove_children()

        if not self.models_loaded:
            if self.loading_error:
                tab_pane.mount(Static(_("加载模型失败"), classes="llm-error"))
            else:
                tab_pane.mount(Static(_("加载中..."), classes="llm-loading"))
            return

        if not models:
            tab_pane.mount(Static(_("暂无可用模型"), classes="llm-empty"))
            return

        # 渲染模型列表
        model_list_container = Container(id=f"{tab_id}-list", classes="llm-model-list")
        for i, model in enumerate(models):
            is_selected = model.llm_id == selected_llm_id
            is_cursor = i == cursor_index

            # 构建样式类
            classes = "llm-model-item"
            if is_selected:
                classes += " llm-model-selected"
            if is_cursor:
                classes += " llm-model-cursor"

            model_item = Static(model.model_name, classes=classes)
            model_list_container.mount(model_item)

        tab_pane.mount(model_list_container)

        # 显示当前光标所指模型的详细信息
        if 0 <= cursor_index < len(models):
            current_model = models[cursor_index]
            detail_container = self._create_model_detail(current_model)
            tab_pane.mount(detail_container)

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
        if self.selected_chat_model:
            for i, model in enumerate(self.chat_models):
                if model.llm_id == self.selected_chat_model:
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

    @on(Button.Pressed, "#save-username-btn")
    async def on_save_username(self) -> None:
        """保存用户名"""
        username_input = self.query_one("#username-input", Input)
        new_username = username_input.value.strip()

        if not new_username:
            # TODO: 显示错误提示
            return

        # TODO: 调用后端 API 保存用户名
        # await self._save_username_to_backend(new_username)

        # 暂时只保存到本地状态
        self.username = new_username

        # TODO: 显示保存成功提示
        # self.notify(_("用户名已保存"))

    @on(Button.Pressed, "#cancel-general-btn")
    def on_cancel_general(self) -> None:
        """取消常规设置的修改"""
        # 重新渲染常规设置标签页，恢复原始值
        self._render_general_tab()

    @on(Button.Pressed, "#mcp-toggle-btn")
    async def on_toggle_mcp(self) -> None:
        """切换 MCP 工具授权模式"""
        if not self.mcp_status_loaded:
            return

        try:
            # 检查客户端是否支持 MCP 操作
            if (
                not hasattr(self.llm_client, "enable_auto_execute")
                or not hasattr(self.llm_client, "disable_auto_execute")
            ):
                return

            # 先禁用按钮防止重复点击
            mcp_btn = self.query_one("#mcp-toggle-btn", Button)
            mcp_btn.disabled = True
            mcp_btn.label = _("切换中...")

            # 根据当前状态调用相应的方法
            if self.auto_execute_status:
                # 当前是自动执行，切换为手动确认
                await self.llm_client.disable_auto_execute()  # type: ignore[attr-defined]
            else:
                # 当前是手动确认，切换为自动执行
                await self.llm_client.enable_auto_execute()  # type: ignore[attr-defined]

            # 重新获取状态以确保同步
            if hasattr(self.llm_client, "get_auto_execute_status"):
                self.auto_execute_status = await self.llm_client.get_auto_execute_status()  # type: ignore[attr-defined]

            # 更新按钮状态
            mcp_btn.label = _("自动执行") if self.auto_execute_status else _("手动确认")
            mcp_btn.disabled = False

        except (OSError, ValueError, RuntimeError):
            # 发生错误时恢复按钮状态
            mcp_btn = self.query_one("#mcp-toggle-btn", Button)
            mcp_btn.label = _("自动执行") if self.auto_execute_status else _("手动确认")
            mcp_btn.disabled = False

    def action_previous_model(self) -> None:
        """选择上一个模型（仅在大模型设置标签页生效）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        self.chat_cursor = max(0, self.chat_cursor - 1)
        self._render_llm_tab()

    def action_next_model(self) -> None:
        """选择下一个模型（仅在大模型设置标签页生效）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        self.chat_cursor = min(len(self.chat_models) - 1, self.chat_cursor + 1)
        self._render_llm_tab()

    def action_select_model(self) -> None:
        """确认选择当前光标所在的模型（临时选择，未保存）"""
        if not self.models_loaded or self.current_tab != "llm":
            return

        if not self.chat_models:
            return

        if 0 <= self.chat_cursor < len(self.chat_models):
            self.selected_chat_model = self.chat_models[self.chat_cursor].llm_id or ""
            self._render_llm_tab()

    def action_cancel(self) -> None:
        """取消并关闭对话框"""
        # 如果在大模型设置标签页，保存已选择的模型
        if self.current_tab == "llm":
            self.config_manager.set_llm_chat_model(self.selected_chat_model)

        self.app.pop_screen()
