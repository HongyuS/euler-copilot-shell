"""TUI 应用的 MCP 事件处理器实现"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.mcp_handler import MCPEventHandler
from log.manager import get_logger

if TYPE_CHECKING:
    from app.tui import IntelligentTerminal
    from backend.hermes import HermesChatClient, HermesStreamEvent


class TUIMCPEventHandler(MCPEventHandler):
    """TUI 应用的 MCP 事件处理器实现"""

    def __init__(self, tui_app: IntelligentTerminal, hermes_client: HermesChatClient) -> None:
        """
        初始化 TUI MCP 事件处理器

        Args:
            tui_app: TUI 应用实例
            hermes_client: Hermes 客户端实例

        """
        self.tui_app = tui_app
        self.hermes_client = hermes_client
        self.logger = get_logger(__name__)

    async def handle_waiting_for_start(self, event: HermesStreamEvent) -> None:
        """
        处理等待用户确认执行的事件

        Args:
            event: MCP 事件对象

        """
        try:
            # 通知 TUI 切换到确认界面
            self.tui_app.post_message(self.tui_app.SwitchToMCPConfirm(event))
        except Exception:
            self.logger.exception("处理用户确认请求时发生错误")

    async def handle_waiting_for_param(self, event: HermesStreamEvent) -> None:
        """
        处理等待用户输入参数的事件

        Args:
            event: MCP 事件对象

        """
        try:
            # 通知 TUI 切换到参数输入界面
            self.tui_app.post_message(self.tui_app.SwitchToMCPParameter(event))
        except Exception:
            self.logger.exception("处理用户参数输入请求时发生错误")
