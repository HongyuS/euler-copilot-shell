"""MCP 交互组件"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Static

from i18n.manager import _

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from backend.hermes.stream import HermesStreamEvent

# 常量定义
MAX_DISPLAY_LENGTH = 30  # 文本显示最大长度
TRUNCATE_LENGTH = 27     # 截断时保留的长度


class MCPConfirmWidget(Container):
    """MCP 工具执行确认组件"""

    def __init__(
        self,
        event: HermesStreamEvent,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """初始化确认组件"""
        super().__init__(name=name, id=widget_id, classes=classes)
        self.event = event
        # 设置为可聚焦，以便键盘导航
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """构建确认界面"""
        step_name = self.event.get_step_name()
        content = self.event.get_content()
        risk = content.get("risk", "unknown")
        reason = content.get("reason", _("需要用户确认是否执行此工具"))

        # 风险级别文本和图标
        risk_info = {
            "low": ("🟢", _("低风险")),
            "medium": ("🟡", _("中等风险")),
            "high": ("🔴", _("高风险")),
        }.get(risk, ("⚪", _("未知风险")))

        risk_icon, risk_text = risk_info

        with Vertical(classes="mcp-content"):
            # 紧凑的工具确认信息显示
            yield Static(
                f"🔧 {step_name} {risk_icon} {risk_text}",
                classes=f"confirm-info risk-{risk}",
                markup=False,
            )
            # 显示简化的说明文字，确保按钮可见
            if len(reason) > MAX_DISPLAY_LENGTH:
                # 如果说明太长，显示省略号
                yield Static(
                    f"💭 {reason[:TRUNCATE_LENGTH]}...",
                    classes="confirm-reason",
                    markup=False,
                )
            else:
                yield Static(
                    f"💭 {reason}",
                    classes="confirm-reason",
                    markup=False,
                )
            # 确保按钮始终显示
            with Horizontal(classes="confirm-buttons"):
                yield Button(_("✓ 确认"), variant="success", id="mcp-confirm-yes")
                yield Button(_("✗ 取消"), variant="error", id="mcp-confirm-no")

    @on(Button.Pressed, "#mcp-confirm-yes")
    def confirm_execution(self) -> None:
        """确认执行"""
        self.post_message(MCPConfirmResult(confirmed=True, conversation_id=self.event.get_conversation_id()))

    @on(Button.Pressed, "#mcp-confirm-no")
    def cancel_execution(self) -> None:
        """取消执行"""
        self.post_message(MCPConfirmResult(confirmed=False, conversation_id=self.event.get_conversation_id()))

    def on_key(self, event) -> None:  # noqa: ANN001
        """处理键盘事件"""
        if event.key in {"enter", "y"}:
            # Enter 或 Y 键确认
            self.confirm_execution()
            event.prevent_default()
            event.stop()
        elif event.key in {"escape", "n"}:
            # Escape 或 N 键取消
            self.cancel_execution()
            event.prevent_default()
            event.stop()
        elif event.key == "tab":
            # Tab 键在按钮间切换焦点
            try:
                buttons = self.query("Button")
                current_focus = self.app.focused
                if current_focus is not None and current_focus in buttons:
                    current_index = list(buttons).index(current_focus)
                    next_index = (current_index + 1) % len(buttons)
                    buttons[next_index].focus()
                # 如果没有按钮聚焦，聚焦到第一个按钮
                elif buttons:
                    buttons[0].focus()
                event.prevent_default()
                event.stop()
            except (AttributeError, ValueError, IndexError):
                pass

    def on_mount(self) -> None:
        """组件挂载时自动聚焦"""
        # 延迟聚焦，确保组件完全渲染
        self.set_timer(0.1, self._focus_first_button)

    def _focus_first_button(self) -> None:
        """聚焦到第一个按钮"""
        try:
            buttons = self.query("Button")
            if buttons:
                buttons[0].focus()
                # 确保组件本身也有焦点，以便键盘事件能正确处理
                self.focus()
        except (AttributeError, ValueError, IndexError):
            # 如果聚焦失败，至少确保组件本身有焦点
            with contextlib.suppress(Exception):
                self.focus()


class MCPParameterWidget(Container):
    """MCP 工具参数输入组件"""

    def __init__(
        self,
        event: HermesStreamEvent,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """初始化参数输入组件"""
        super().__init__(name=name, id=widget_id, classes=classes)
        self.event = event
        self.param_inputs: dict[str, Input] = {}
        # 设置为可聚焦，以便键盘导航
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """构建参数输入界面"""
        step_name = self.event.get_step_name()
        content = self.event.get_content()
        message = content.get("message", _("需要补充参数"))
        params = content.get("params", {})

        with Vertical(classes="mcp-content"):
            # 紧凑的参数输入标题
            yield Static(_("📝 参数输入"), classes="param-header", markup=False)
            yield Static(f"🔧 {step_name}", classes="param-tool", markup=False)
            # 显示说明文字，超长时显示省略号
            if len(message) > MAX_DISPLAY_LENGTH:
                yield Static(f"💭 {message[:TRUNCATE_LENGTH]}...", classes="param-message", markup=False)
            else:
                yield Static(f"💭 {message}", classes="param-message", markup=False)

            # 垂直布局的参数输入，更节省空间
            for param_name, param_value in params.items():
                if param_value is None or param_value == "":
                    param_input = Input(
                        placeholder=_("请输入 {param_name}").format(param_name=param_name),
                        id=f"param_{param_name}",
                        classes="param-input-compact",
                    )
                    self.param_inputs[param_name] = param_input
                    yield param_input

            # 紧凑的按钮行
            with Horizontal(classes="param-buttons"):
                yield Button(_("✓ 提交"), variant="success", id="mcp-param-submit")
                yield Button(_("✗ 取消"), variant="error", id="mcp-param-cancel")

    @on(Button.Pressed, "#mcp-param-submit")
    def submit_parameters(self) -> None:
        """提交参数"""
        # 收集用户输入的参数
        params = {}

        for param_name, input_widget in self.param_inputs.items():
            value = input_widget.value.strip()
            if value:
                params[param_name] = value

        self.post_message(MCPParameterResult(params=params, conversation_id=self.event.get_conversation_id()))

    @on(Button.Pressed, "#mcp-param-cancel")
    def cancel_parameters(self) -> None:
        """取消参数输入"""
        self.post_message(MCPParameterResult(params=None, conversation_id=self.event.get_conversation_id()))


class MCPConfirmResult(Message):
    """MCP 确认结果消息"""

    def __init__(self, *, confirmed: bool, conversation_id: str) -> None:
        """初始化确认结果"""
        super().__init__()
        self.confirmed = confirmed
        self.conversation_id = conversation_id


class MCPParameterResult(Message):
    """MCP 参数结果消息"""

    def __init__(self, *, params: dict | None, conversation_id: str) -> None:
        """初始化参数结果"""
        super().__init__()
        self.params = params
        self.conversation_id = conversation_id
