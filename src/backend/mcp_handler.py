"""MCP 事件处理器接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.hermes.stream import HermesStreamEvent


class MCPEventHandler(ABC):
    """MCP 事件处理器接口"""

    @abstractmethod
    async def handle_waiting_for_start(self, event: HermesStreamEvent) -> None:
        """
        处理等待用户确认执行的事件

        Args:
            event: MCP 事件对象

        """

    @abstractmethod
    async def handle_waiting_for_param(self, event: HermesStreamEvent) -> None:
        """
        处理等待用户输入参数的事件

        Args:
            event: MCP 事件对象

        """
