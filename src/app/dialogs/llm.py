"""LLM 模型配置对话框"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Static, TabbedContent, TabPane

from backend.models import LLMType, ModelInfo
from i18n.manager import _

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from backend.base import LLMClientBase
    from config.manager import ConfigManager


class LLMConfigDialog(ModalScreen):
    """LLM 模型配置对话框"""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("left", "previous_tab", _("上一个标签")),
        ("right", "next_tab", _("下一个标签")),
        ("up", "previous_model", _("上一个模型")),
        ("down", "next_model", _("下一个模型")),
        ("space", "select_model", _("选择模型")),
        ("enter", "save_and_close", _("保存并关闭")),
        ("escape", "cancel", _("取消")),
    ]

    def __init__(
        self,
        config_manager: ConfigManager,
        llm_client: LLMClientBase,
    ) -> None:
        """
        初始化 LLM 配置对话框

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
        self.function_models: list[ModelInfo] = []

        # 当前选择的模型（临时状态，未保存）
        self.selected_chat_model = config_manager.get_llm_chat_model()
        self.selected_function_model = config_manager.get_llm_function_model()

        # 当前标签页
        self.current_tab = "chat"

        # 当前光标位置（每个标签页独立）
        self.chat_cursor = 0
        self.function_cursor = 0

        # 加载状态
        self.models_loaded = False
        self.loading_error = False

    def compose(self) -> ComposeResult:
        """构建对话框"""
        with Container(id="llm-dialog-screen"), Container(id="llm-dialog"):
            # 标签页容器
            with TabbedContent(id="llm-tabs", initial="chat-tab"):
                with TabPane(_("基础模型"), id="chat-tab"):
                    pass  # 内容将在 on_mount 中动态添加
                with TabPane(_("工具调用"), id="function-tab"):
                    pass  # 内容将在 on_mount 中动态添加
            # 帮助文本
            yield Static(
                _("↑↓: 选择模型  ←→: 切换标签  空格: 确认  回车: 保存  ESC: 取消"),
                id="llm-dialog-help",
            )

    async def on_mount(self) -> None:
        """组件挂载时加载模型列表"""
        await self._load_models()
        self._render_all_tabs()
        self._update_cursor_positions()

    async def _load_models(self) -> None:
        """异步加载模型列表"""
        try:
            # 获取所有可用模型
            if hasattr(self.llm_client, "get_available_models"):
                self.all_models = await self.llm_client.get_available_models()  # type: ignore[attr-defined]

                # 按类型分类模型
                self.chat_models = [model for model in self.all_models if LLMType.CHAT in model.llm_type]
                self.function_models = [model for model in self.all_models if LLMType.FUNCTION in model.llm_type]

                self.models_loaded = True
                self.loading_error = False
            else:
                self.models_loaded = False
                self.loading_error = True

        except (OSError, ValueError, RuntimeError):
            self.models_loaded = False
            self.loading_error = True

    def _render_all_tabs(self) -> None:
        """渲染所有标签页内容"""
        self._render_tab_content("chat-tab", self.chat_models, self.selected_chat_model, self.chat_cursor)
        self._render_tab_content(
            "function-tab",
            self.function_models,
            self.selected_function_model,
            self.function_cursor,
        )

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

        # 工具调用模型光标
        if self.selected_function_model:
            for i, model in enumerate(self.function_models):
                if model.llm_id == self.selected_function_model:
                    self.function_cursor = i
                    break

    @on(TabbedContent.TabActivated)
    def on_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """标签页切换事件"""
        tab_id = event.tab.id
        if tab_id == "chat-tab":
            self.current_tab = "chat"
        elif tab_id == "function-tab":
            self.current_tab = "function"

    def action_previous_tab(self) -> None:
        """切换到上一个标签页"""
        tabs = self.query_one("#llm-tabs", TabbedContent)
        if self.current_tab == "chat":
            tabs.active = "function-tab"
        elif self.current_tab == "function":
            tabs.active = "chat-tab"

    def action_next_tab(self) -> None:
        """切换到下一个标签页"""
        tabs = self.query_one("#llm-tabs", TabbedContent)
        if self.current_tab == "chat":
            tabs.active = "function-tab"
        elif self.current_tab == "function":
            tabs.active = "chat-tab"

    def action_previous_model(self) -> None:
        """选择上一个模型"""
        if not self.models_loaded:
            return

        models = self._get_current_models()
        if not models:
            return

        if self.current_tab == "chat":
            self.chat_cursor = max(0, self.chat_cursor - 1)
            self._render_tab_content("chat-tab", self.chat_models, self.selected_chat_model, self.chat_cursor)
        elif self.current_tab == "function":
            self.function_cursor = max(0, self.function_cursor - 1)
            self._render_tab_content(
                "function-tab",
                self.function_models,
                self.selected_function_model,
                self.function_cursor,
            )

    def action_next_model(self) -> None:
        """选择下一个模型"""
        if not self.models_loaded:
            return

        models = self._get_current_models()
        if not models:
            return

        if self.current_tab == "chat":
            self.chat_cursor = min(len(self.chat_models) - 1, self.chat_cursor + 1)
            self._render_tab_content("chat-tab", self.chat_models, self.selected_chat_model, self.chat_cursor)
        elif self.current_tab == "function":
            self.function_cursor = min(len(self.function_models) - 1, self.function_cursor + 1)
            self._render_tab_content(
                "function-tab",
                self.function_models,
                self.selected_function_model,
                self.function_cursor,
            )

    def action_select_model(self) -> None:
        """确认选择当前光标所在的模型（临时选择，未保存）"""
        if not self.models_loaded:
            return

        models = self._get_current_models()
        if not models:
            return

        if self.current_tab == "chat" and 0 <= self.chat_cursor < len(self.chat_models):
            self.selected_chat_model = self.chat_models[self.chat_cursor].llm_id or ""
            self._render_tab_content("chat-tab", self.chat_models, self.selected_chat_model, self.chat_cursor)
        elif self.current_tab == "function" and 0 <= self.function_cursor < len(self.function_models):
            self.selected_function_model = self.function_models[self.function_cursor].llm_id or ""
            self._render_tab_content(
                "function-tab",
                self.function_models,
                self.selected_function_model,
                self.function_cursor,
            )

    def action_save_and_close(self) -> None:
        """保存配置并关闭对话框"""
        # 保存所有选择
        self.config_manager.set_llm_chat_model(self.selected_chat_model)
        self.config_manager.set_llm_function_model(self.selected_function_model)

        self.app.pop_screen()

    def action_cancel(self) -> None:
        """取消并关闭对话框"""
        self.app.pop_screen()

    def _get_current_models(self) -> list[ModelInfo]:
        """获取当前标签页的模型列表"""
        if self.current_tab == "chat":
            return self.chat_models
        if self.current_tab == "function":
            return self.function_models
        return []
