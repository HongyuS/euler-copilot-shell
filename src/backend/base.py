"""后端客户端基类和工厂"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class LLMClientBase(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    def get_llm_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        生成命令建议

        Args:
            prompt: 用户输入的提示

        Yields:
            str: 流式响应的文本内容

        """

    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """
        获取当前 LLM 服务中可用的模型，返回名称列表

        Returns:
            list[str]: 可用的模型名称列表

        """

    @abstractmethod
    async def close(self) -> None:
        """关闭客户端连接"""

    async def __aenter__(self) -> LLMClientBase:
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.close()
