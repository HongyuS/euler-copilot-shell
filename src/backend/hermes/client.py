"""Hermes Chat API 客户端"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx
from typing_extensions import Self

from backend.base import LLMClientBase
from log.manager import get_logger, log_exception

from .constants import HTTP_OK
from .exceptions import HermesAPIError
from .services.http import HermesHttpManager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from types import TracebackType

    from .models import HermesAgent, HermesChatRequest
    from .services.agent import HermesAgentManager
    from .services.conversation import HermesConversationManager
    from .services.model import HermesModelManager
    from .stream import HermesStreamProcessor


def validate_url(url: str) -> bool:
    """
    校验 URL 是否合法

    校验 URL 是否以 http:// 或 https:// 开头。
    """
    return re.match(r"^https?://", url) is not None


class HermesChatClient(LLMClientBase):
    """Hermes Chat API 客户端 - 重构版本"""

    def __init__(self, base_url: str, auth_token: str = "") -> None:
        """初始化 Hermes Chat API 客户端"""
        self.logger = get_logger(__name__)

        if not validate_url(base_url):
            msg = "无效的 API URL，请确保 URL 以 http:// 或 https:// 开头。"
            self.logger.error(msg)
            raise ValueError(msg)

        # HTTP 管理器 - 立即初始化
        self.http_manager = HermesHttpManager(base_url, auth_token)

        # 延迟初始化的管理器
        self._model_manager: HermesModelManager | None = None
        self._agent_manager: HermesAgentManager | None = None
        self._conversation_manager: HermesConversationManager | None = None
        self._stream_processor: HermesStreamProcessor | None = None

        # 当前选择的智能体ID
        self._current_agent_id: str = ""

        self.logger.info("Hermes 客户端初始化成功 - URL: %s", base_url)

    @property
    def model_manager(self) -> HermesModelManager:
        """获取模型管理器（延迟初始化）"""
        if self._model_manager is None:
            from .services.model import HermesModelManager
            self._model_manager = HermesModelManager(self.http_manager)
        return self._model_manager

    @property
    def agent_manager(self) -> HermesAgentManager:
        """获取智能体管理器（延迟初始化）"""
        if self._agent_manager is None:
            from .services.agent import HermesAgentManager
            self._agent_manager = HermesAgentManager(self.http_manager)
        return self._agent_manager

    @property
    def conversation_manager(self) -> HermesConversationManager:
        """获取会话管理器（延迟初始化）"""
        if self._conversation_manager is None:
            from .services.conversation import HermesConversationManager
            self._conversation_manager = HermesConversationManager(self.http_manager)
        return self._conversation_manager

    @property
    def stream_processor(self) -> HermesStreamProcessor:
        """获取流处理器（延迟初始化）"""
        if self._stream_processor is None:
            from .stream import HermesStreamProcessor
            self._stream_processor = HermesStreamProcessor()
        return self._stream_processor

    def set_current_agent(self, agent_id: str) -> None:
        """
        设置当前使用的智能体

        Args:
            agent_id: 智能体ID，空字符串表示不使用智能体

        """
        self._current_agent_id = agent_id
        self.logger.info("设置当前智能体ID: %s", agent_id or "无智能体")

    def get_current_agent(self) -> str:
        """
        获取当前使用的智能体ID

        Returns:
            str: 当前智能体ID，空字符串表示不使用智能体

        """
        return self._current_agent_id

    def reset_conversation(self) -> None:
        """重置会话，下次聊天时会创建新的会话"""
        if self._conversation_manager is not None:
            self._conversation_manager.reset_conversation()

    async def get_llm_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        生成命令建议

        为了兼容现有的 OpenAI 客户端接口，提供简化的聊天接口。

        Args:
            prompt: 用户输入的提示语

        Yields:
            str: 流式响应的文本内容

        Raises:
            HermesAPIError: 当 API 调用失败时

        """
        # 如果有未完成的会话，先停止它
        await self._stop()

        self.logger.info("开始 Hermes 流式聊天请求")
        self.logger.debug("提示内容长度: %d", len(prompt))
        start_time = time.time()

        try:
            # 确保有会话 ID
            conversation_id = await self.conversation_manager.ensure_conversation()
            self.logger.info("使用会话ID: %s", conversation_id)

            # 创建聊天请求
            from .models import HermesApp, HermesChatRequest, HermesFeatures
            app = HermesApp(self._current_agent_id)
            request = HermesChatRequest(
                app=app,
                conversation_id=conversation_id,
                question=prompt,
                features=HermesFeatures(),
                language="zh_cn",
            )

            # 直接传递异常，不在这里处理
            async for text in self._chat_stream(request):
                yield text

            duration = time.time() - start_time
            self.logger.info("Hermes 流式聊天请求完成 - 耗时: %.3fs", duration)

        except Exception as e:
            duration = time.time() - start_time
            log_exception(self.logger, "Hermes 流式聊天请求失败", e)
            raise

    async def get_available_models(self) -> list[str]:
        """
        获取当前 LLM 服务中可用的模型，返回名称列表

        通过调用 /api/llm 接口获取可用的大模型列表。
        如果调用失败或没有返回，使用空列表，后端接口会自动使用默认模型。
        """
        return await self.model_manager.get_available_models()

    async def get_available_agents(self) -> list[HermesAgent]:
        """
        获取当前用户可用的智能体列表

        通过调用 /api/app 接口获取当前用户可用的智能体列表。
        支持分页获取所有智能体，每页最多16项，会自动请求所有页面。
        这些智能体可以在聊天中使用，选择的智能体 ID 需要在 chat 接口中填入 appId 字段。
        如果调用失败或没有返回，使用空列表。

        Returns:
            list[HermesAgent]: 可用的智能体列表（仅包含已发布的智能体）

        """
        return await self.agent_manager.get_available_agents()

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        # 如果有未完成的会话，先停止它
        await self._stop()
        try:
            await self.http_manager.close()
            self.logger.info("Hermes 客户端已关闭")
        except Exception as e:
            log_exception(self.logger, "关闭 Hermes 客户端失败", e)
            raise

    async def _chat_stream(
        self,
        request: HermesChatRequest,
    ) -> AsyncGenerator[str, None]:
        """
        发送聊天请求并返回流式响应

        Args:
            request: Hermes 聊天请求对象

        Yields:
            str: 流式响应的文本内容

        Raises:
            HermesAPIError: 当 API 调用失败时

        """
        client = await self.http_manager.get_client()
        chat_url = urljoin(self.http_manager.base_url, "/api/chat")
        headers = self.http_manager.build_headers()

        self.logger.info("准备发送聊天请求 - URL: %s, 会话ID: %s", chat_url, request.conversation_id)
        self.logger.debug("请求头: %s", headers)
        self.logger.debug("请求内容: %s", request.to_dict())

        try:
            async with client.stream(
                "POST",
                chat_url,
                json=request.to_dict(),
                headers=headers,
            ) as response:
                self.logger.info("收到聊天响应 - 状态码: %d", response.status_code)
                await self._validate_chat_response(response)
                async for text in self._process_stream_events(response):
                    yield text

        except httpx.RequestError as e:
            raise HermesAPIError(500, f"Network error: {e!s}") from e
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise HermesAPIError(500, f"Data parsing error: {e!s}") from e

    async def _validate_chat_response(self, response: httpx.Response) -> None:
        """验证聊天响应状态"""
        if response.status_code != HTTP_OK:
            error_text = await response.aread()
            raise HermesAPIError(
                response.status_code,
                error_text.decode("utf-8"),
            )

    async def _process_stream_events(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """处理流式响应事件"""
        from .stream import HermesStreamEvent

        has_content = False
        event_count = 0

        self.logger.info("开始处理流式响应事件")

        try:
            async for line in response.aiter_lines():
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                self.logger.debug("收到 SSE 行: %s", stripped_line)
                event = HermesStreamEvent.from_line(stripped_line)
                if event is None:
                    self.logger.warning("无法解析 SSE 事件")
                    continue

                event_count += 1
                self.logger.info("解析到事件 #%d - 类型: %s", event_count, event.event_type)

                # 处理特殊事件类型
                should_break, break_message = self.stream_processor.handle_special_events(event)
                if should_break:
                    if break_message:
                        yield break_message
                    break

                # 处理文本内容
                text_content = event.get_text_content()
                if text_content:
                    has_content = True
                    self.stream_processor.log_text_content(text_content)
                    yield text_content
                else:
                    self.logger.info("事件无文本内容")

            self.logger.info("流式响应处理完成 - 事件数量: %d, 有内容: %s", event_count, has_content)

        except Exception:
            self.logger.exception("处理流式响应事件时出错")
            raise

        # 处理无内容的情况
        if not has_content:
            yield self.stream_processor.get_no_content_message(event_count)

    async def _stop(self) -> None:
        """停止当前会话"""
        if self._conversation_manager is not None:
            await self._conversation_manager.stop_conversation()

    async def __aenter__(self) -> Self:
        """异步上下文管理器入口"""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """异步上下文管理器出口"""
        await self.close()
