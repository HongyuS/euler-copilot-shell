"""MCP 交互组件"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from backend.hermes.stream import HermesStreamEvent


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

    def compose(self) -> ComposeResult:
        """构建确认界面"""
        step_name = self.event.get_step_name()
        content = self.event.get_content()
        risk = content.get("risk", "unknown")
        reason = content.get("reason", "需要用户确认是否执行此工具")

        # 风险级别文本
        risk_text = {
            "low": "低风险",
            "medium": "中等风险",
            "high": "高风险",
        }.get(risk, "未知风险")

        with Vertical():
            yield Static("⚠️ 工具执行确认", classes="confirm-title")
            yield Static(f"工具名称: {step_name}")
            yield Static(f"风险级别: {risk_text}", classes=f"risk-{risk}")
            yield Static(f"原因: {reason}")
            yield Static("")
            with Horizontal(classes="confirm-buttons"):
                yield Button("确认执行 (Y)", variant="success", id="mcp-confirm-yes")
                yield Button("取消 (N)", variant="error", id="mcp-confirm-no")
            yield Static("请选择: Y(确认) / N(取消)")

    @on(Button.Pressed, "#mcp-confirm-yes")
    def confirm_execution(self) -> None:
        """确认执行"""
        self.post_message(MCPConfirmResult(confirmed=True, task_id=self.event.get_task_id()))

    @on(Button.Pressed, "#mcp-confirm-no")
    def cancel_execution(self) -> None:
        """取消执行"""
        self.post_message(MCPConfirmResult(confirmed=False, task_id=self.event.get_task_id()))


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

    def compose(self) -> ComposeResult:
        """构建参数输入界面"""
        step_name = self.event.get_step_name()
        content = self.event.get_content()
        message = content.get("message", "需要补充参数")
        params = content.get("params", {})

        with Vertical():
            yield Static("📝 参数补充", classes="param-title")
            yield Static(f"工具名称: {step_name}")
            yield Static(message, classes="param-message")
            yield Static("")

            # 为每个需要填写的参数创建输入框
            for param_name, param_value in params.items():
                if param_value is None or param_value == "":
                    yield Label(f"{param_name}:")
                    param_input = Input(
                        placeholder=f"请输入 {param_name}",
                        id=f"param_{param_name}",
                    )
                    self.param_inputs[param_name] = param_input
                    yield param_input

            # 额外信息输入框
            yield Label("补充说明（可选）:")
            description_input = Input(
                placeholder="请输入补充说明信息",
                id="param_description",
            )
            self.param_inputs["description"] = description_input
            yield description_input

            with Horizontal(classes="param-buttons"):
                yield Button("提交", variant="success", id="mcp-param-submit")
                yield Button("取消", variant="error", id="mcp-param-cancel")

    @on(Button.Pressed, "#mcp-param-submit")
    def submit_parameters(self) -> None:
        """提交参数"""
        # 收集用户输入的参数
        content_params = {}
        description = ""

        for param_name, input_widget in self.param_inputs.items():
            value = input_widget.value.strip()
            if param_name == "description":
                description = value
            elif value:
                content_params[param_name] = value

        # 构建参数结构
        params = {
            "content": content_params,
            "description": description,
        }

        self.post_message(MCPParameterResult(params=params, task_id=self.event.get_task_id()))

    @on(Button.Pressed, "#mcp-param-cancel")
    def cancel_parameters(self) -> None:
        """取消参数输入"""
        self.post_message(MCPParameterResult(params=None, task_id=self.event.get_task_id()))


class MCPConfirmResult(Message):
    """MCP 确认结果消息"""

    def __init__(self, *, confirmed: bool, task_id: str) -> None:
        """初始化确认结果"""
        super().__init__()
        self.confirmed = confirmed
        self.task_id = task_id


class MCPParameterResult(Message):
    """MCP 参数结果消息"""

    def __init__(self, *, params: dict | None, task_id: str) -> None:
        """初始化参数结果"""
        super().__init__()
        self.params = params
        self.task_id = task_id
