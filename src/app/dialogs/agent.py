"""智能体相关对话框组件"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import ComposeResult
    from textual.events import Key as KeyEvent

from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class BackendRequiredDialog(ModalScreen):
    """后端要求提示对话框"""

    def compose(self) -> ComposeResult:
        """构建后端要求提示对话框"""
        yield Container(
            Container(
                Label("智能体功能提示", id="backend-dialog-title"),
                Label("请选择 openEuler Intelligence 后端来使用智能体功能", id="backend-dialog-text"),
                Label("按任意键关闭", id="backend-dialog-help"),
                id="backend-dialog",
            ),
            id="backend-dialog-screen",
        )

    def on_key(self, event: KeyEvent) -> None:
        """处理键盘事件 - 任意键关闭对话框"""
        self.app.pop_screen()


class AgentSelectionDialog(ModalScreen):
    """智能体选择对话框"""

    def __init__(
        self,
        agents: list[tuple[str, str]],
        callback: Callable[[tuple[str, str]], None],
        current_agent: tuple[str, str] | None = None,
    ) -> None:
        """
        初始化智能体选择对话框

        Args:
            agents: 智能体列表，格式为 [(app_id, name), ...]
                    第一项为("", "智能问答")表示无智能体
            callback: 选择完成后的回调函数
            current_agent: 当前已选中的智能体

        """
        super().__init__()
        self.agents = agents
        self.current_agent = current_agent or ("", "智能问答")
        self.callback = callback

        # 设置初始光标位置为当前已选中的智能体
        self.selected_index = 0
        for i, agent in enumerate(self.agents):
            if agent[0] == self.current_agent[0]:  # 按 app_id 匹配
                self.selected_index = i
                break

    def compose(self) -> ComposeResult:
        """构建智能体选择对话框"""
        # 创建富文本内容，包含所有智能体选项
        agent_text_lines = []
        for i, (app_id, name) in enumerate(self.agents):
            is_cursor = i == self.selected_index
            is_current = app_id == self.current_agent[0]

            if is_cursor and is_current:
                # 光标在当前已选中的智能体上：绿底白字 + 勾选符号
                agent_text_lines.append(f"[white on green]► ✓ {name}[/white on green]")
            elif is_cursor:
                # 光标在其他智能体上：蓝底白字
                agent_text_lines.append(f"[white on blue]►   {name}[/white on blue]")
            elif is_current:
                # 当前已选中但光标不在这里：显示勾选符号
                agent_text_lines.append(f"[bright_green]  ✓ {name}[/bright_green]")
            else:
                # 普通状态：亮白字
                agent_text_lines.append(f"[bright_white]    {name}[/bright_white]")

        # 如果没有智能体，添加默认选项
        if not agent_text_lines:
            agent_text_lines.append("[white on green]► ✓ 智能问答[/white on green]")

        # 使用Static组件显示文本，启用Rich markup
        agent_content = Static("\n".join(agent_text_lines), markup=True, id="agent-content")

        yield Container(
            Container(
                Label("OS 智能助手", id="agent-dialog-title"),
                agent_content,
                Label("使用上下键选择，回车确认，ESC取消 | ✓ 表示当前选中", id="agent-dialog-help"),
                id="agent-dialog",
            ),
            id="agent-dialog-screen",
        )

    def on_key(self, event: KeyEvent) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            # 确保有智能体可选择
            if self.agents and 0 <= self.selected_index < len(self.agents):
                selected_agent = self.agents[self.selected_index]
            else:
                selected_agent = ("", "智能问答")
            self.callback(selected_agent)
            self.app.pop_screen()
        elif event.key == "up" and self.selected_index > 0:
            self.selected_index -= 1
            self._update_display()
        elif event.key == "down" and self.selected_index < len(self.agents) - 1:
            self.selected_index += 1
            self._update_display()

    def on_mount(self) -> None:
        """挂载时设置初始显示"""
        self._update_display()

    def _update_display(self) -> None:
        """更新显示内容"""
        # 重新生成文本内容
        agent_text_lines = []
        for i, (app_id, name) in enumerate(self.agents):
            is_cursor = i == self.selected_index
            is_current = app_id == self.current_agent[0]

            if is_cursor and is_current:
                # 光标在当前已选中的智能体上：绿底白字 + 勾选符号
                agent_text_lines.append(f"[white on green]► ✓ {name}[/white on green]")
            elif is_cursor:
                # 光标在其他智能体上：蓝底白字
                agent_text_lines.append(f"[white on blue]►   {name}[/white on blue]")
            elif is_current:
                # 当前已选中但光标不在这里：显示勾选符号
                agent_text_lines.append(f"[bright_green]  ✓ {name}[/bright_green]")
            else:
                # 普通状态：亮白字
                agent_text_lines.append(f"[bright_white]    {name}[/bright_white]")

        # 如果没有智能体，添加默认选项
        if not agent_text_lines:
            agent_text_lines.append("[white on green]► ✓ 智能问答[/white on green]")

        # 更新Static组件的内容
        try:
            agent_content = self.query_one("#agent-content", Static)
            agent_content.update("\n".join(agent_text_lines))
        except (AttributeError, ValueError, RuntimeError):
            # 如果查找失败，忽略错误
            pass
