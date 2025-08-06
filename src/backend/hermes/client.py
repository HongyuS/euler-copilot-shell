"""Hermes Chat API 客户端"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

import httpx
from typing_extensions import Self

from backend.base import LLMClientBase
from log.manager import get_logger, log_api_request, log_exception

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from types import TracebackType

# HTTP 状态码常量
HTTP_OK = 200


class HermesAPIError(Exception):
    """Hermes API 错误异常"""

    def __init__(self, status_code: int, message: str) -> None:
        """初始化 Hermes API 错误异常"""
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


def validate_url(url: str) -> bool:
    """
    校验 URL 是否合法

    校验 URL 是否以 http:// 或 https:// 开头。
    """
    return re.match(r"^https?://", url) is not None


class HermesMessage:
    """Hermes 消息类"""

    def __init__(self, role: str, content: str) -> None:
        """初始化 Hermes 消息"""
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role, "content": self.content}


class HermesFeatures:
    """Hermes 功能特性配置"""

    def __init__(self, max_tokens: int = 2048, context_num: int = 2) -> None:
        """初始化功能特性配置"""
        self.max_tokens = max_tokens
        self.context_num = context_num

    def to_dict(self) -> dict[str, int]:
        """转换为字典格式"""
        return {
            "max_tokens": self.max_tokens,
            "context_num": self.context_num,
        }


class HermesApp:
    """Hermes 应用配置"""

    def __init__(self, app_id: str, flow_id: str = "") -> None:
        """初始化应用配置"""
        self.app_id = app_id
        self.flow_id = flow_id

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "appId": self.app_id,
            "auth": {},
            "flowId": self.flow_id,
            "params": {},
        }


class HermesChatRequest:
    """Hermes Chat 请求类"""

    def __init__(
        self,
        app: HermesApp,
        conversation_id: str,
        question: str,
        features: HermesFeatures | None = None,
        language: str = "zh_cn",
    ) -> None:
        """初始化 Hermes Chat 请求"""
        self.app = app
        self.conversation_id = conversation_id
        self.question = question
        self.features = features or HermesFeatures()
        self.language = language

    def to_dict(self) -> dict[str, Any]:
        """转换为请求字典格式"""
        return {
            "app": self.app.to_dict(),
            "conversationId": self.conversation_id,
            "features": self.features.to_dict(),
            "language": self.language,
            "question": self.question,
        }


class HermesStreamEvent:
    """Hermes 流事件类"""

    def __init__(self, event_type: str, data: dict[str, Any]) -> None:
        """初始化流事件"""
        self.event_type = event_type
        self.data = data

    @classmethod
    def from_line(cls, line: str) -> HermesStreamEvent | None:
        """从 SSE 行解析事件"""
        line = line.strip()
        if not line.startswith("data: "):
            return None

        data_str = line[6:]  # 去掉 "data: " 前缀

        # 处理特殊字段
        special_events = {
            "[DONE]": ("done", {}),
            "[ERROR]": ("error", {"error": "Backend error occurred"}),
            "[SENSITIVE]": ("sensitive", {"message": "Content contains sensitive information"}),
            '{"event": "heartbeat"}': ("heartbeat", {}),
        }

        if data_str in special_events:
            event_type, data = special_events[data_str]
            return cls(event_type, data)

        try:
            data = json.loads(data_str)
            event_type = data.get("event", "unknown")
            return cls(event_type, data)
        except json.JSONDecodeError:
            return None

    def get_text_content(self) -> str | None:
        """获取文本内容"""
        if self.event_type == "text.add":
            return self.data.get("content", {}).get("text", "")
        if self.event_type == "step.output":
            content = self.data.get("content", {})
            if "text" in content:
                return content["text"]
        return None


class HermesChatClient(LLMClientBase):
    """Hermes Chat API 客户端"""

    def __init__(self, base_url: str, auth_token: str = "") -> None:
        """初始化 Hermes Chat API 客户端"""
        self.logger = get_logger(__name__)

        if not validate_url(base_url):
            msg = "无效的 API URL，请确保 URL 以 http:// 或 https:// 开头。"
            self.logger.error(msg)
            raise ValueError(msg)

        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.client: httpx.AsyncClient | None = None
        self._conversation_id: str | None = None  # 存储会话 ID

        self.logger.info("Hermes 客户端初始化成功 - URL: %s", base_url)

    def reset_conversation(self) -> None:
        """重置会话，下次聊天时会创建新的会话"""
        self._conversation_id = None

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
        start_time = time.time()

        try:
            # 确保有会话 ID
            conversation_id = await self._ensure_conversation()

            # 创建聊天请求
            app = HermesApp("")
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
        start_time = time.time()
        self.logger.info("开始请求 Hermes 模型列表 API")

        try:
            client = await self._get_client()
            llm_url = urljoin(self.base_url, "/api/llm")

            headers = {
                "Host": self._get_host_header(),
            }
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            response = await client.get(llm_url, headers=headers)

            duration = time.time() - start_time

            if response.status_code != HTTP_OK:
                # 如果接口调用失败，返回空列表
                log_api_request(
                    self.logger,
                    "GET",
                    llm_url,
                    response.status_code,
                    duration,
                    error="API 调用失败",
                )
                self.logger.warning("Hermes 模型列表 API 调用失败，返回空列表")
                return []

            data = response.json()

            # 检查响应格式
            if not isinstance(data, dict) or "result" not in data:
                log_api_request(
                    self.logger,
                    "GET",
                    llm_url,
                    response.status_code,
                    duration,
                    error="响应格式无效",
                )
                self.logger.warning("Hermes 模型列表 API 响应格式无效，返回空列表")
                return []

            result = data["result"]
            if not isinstance(result, list):
                log_api_request(
                    self.logger,
                    "GET",
                    llm_url,
                    response.status_code,
                    duration,
                    error="result字段不是数组",
                )
                self.logger.warning("Hermes 模型列表 API result字段不是数组，返回空列表")
                return []

            # 提取模型名称
            models = []
            for llm_info in result:
                if isinstance(llm_info, dict):
                    # 优先使用 modelName，如果没有则使用 llmId
                    model_name = llm_info.get("modelName") or llm_info.get("llmId")
                    if model_name:
                        models.append(model_name)

            # 记录成功的API请求
            log_api_request(
                self.logger,
                "GET",
                llm_url,
                response.status_code,
                duration,
                model_count=len(models),
            )

            self.logger.info("获取到 %d 个可用模型", len(models))

        except (
            httpx.HTTPError,
            httpx.InvalidURL,
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ) as e:
            # 如果发生网络错误、JSON解析错误或其他预期错误，返回空列表
            duration = time.time() - start_time
            log_exception(self.logger, "Hermes 模型列表 API 请求异常", e)
            log_api_request(
                self.logger,
                "GET",
                f"{self.base_url}/api/llm",
                500,
                duration,
                error=str(e),
            )
            self.logger.warning("Hermes 模型列表 API 请求异常，返回空列表")
            return []
        else:
            return models

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        # 如果有未完成的会话，先停止它
        await self._stop()
        try:
            if self.client and not self.client.is_closed:
                await self.client.aclose()
                self.logger.info("Hermes 客户端已关闭")
        except Exception as e:
            log_exception(self.logger, "关闭 Hermes 客户端失败", e)
            raise

    def _get_host_header(self) -> str:
        """
        从base_url中提取主机名用于Host头部

        Returns:
            str: 主机名，如 'www.eulercopilot.io'

        """
        parsed_url = urlparse(self.base_url)
        return parsed_url.netloc

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self.client is None or self.client.is_closed:
            headers = {
                "Accept": "text/event-stream",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Content-Type": "application/json; charset=UTF-8",
            }
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            timeout = httpx.Timeout(
                connect=30.0,  # 连接超时，允许30秒建立连接
                read=1800.0,  # 读取超时，支持长时间SSE流（30分钟）
                write=30.0,  # 写入超时
                pool=30.0,  # 连接池超时
            )
            self.client = httpx.AsyncClient(headers=headers, timeout=timeout)
        return self.client

    async def _create_conversation(self, llm_id: str = "") -> str:
        """
        创建新的会话并返回 conversationId

        Args:
            llm_id: 指定的 LLM ID，留空则使用默认模型

        Returns:
            str: 创建的会话 ID

        Raises:
            HermesAPIError: 当 API 调用失败时

        """
        start_time = time.time()
        self.logger.info("开始创建 Hermes 会话 - LLM ID: %s", llm_id or "默认")

        client = await self._get_client()
        conversation_url = urljoin(self.base_url, "/api/conversation")

        # 构建请求参数
        params = {}
        if llm_id:
            params["llm_id"] = llm_id

        headers = {
            "Host": self._get_host_header(),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = await client.post(
                conversation_url,
                params=params,
                json={},  # 空的 JSON 体
                headers=headers,
            )

            duration = time.time() - start_time

            if response.status_code != HTTP_OK:
                error_text = await response.aread()
                log_api_request(
                    self.logger,
                    "POST",
                    conversation_url,
                    response.status_code,
                    duration,
                    error=error_text.decode("utf-8"),
                )
                raise HermesAPIError(response.status_code, error_text.decode("utf-8"))

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                log_api_request(
                    self.logger,
                    "POST",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Invalid JSON response",
                )
                raise HermesAPIError(500, "Invalid JSON response") from e

            # 检查响应格式
            if not isinstance(data, dict) or "result" not in data:
                log_api_request(
                    self.logger,
                    "POST",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Invalid API response format",
                )
                raise HermesAPIError(500, "Invalid API response format")

            result = data["result"]
            if not isinstance(result, dict) or "conversationId" not in result:
                log_api_request(
                    self.logger,
                    "POST",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Missing conversationId in response",
                )
                raise HermesAPIError(500, "Missing conversationId in response")

            conversation_id = result["conversationId"]
            if not conversation_id:
                log_api_request(
                    self.logger,
                    "POST",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Empty conversationId received",
                )
                raise HermesAPIError(500, "Empty conversationId received")

            # 记录成功的API请求
            log_api_request(
                self.logger,
                "POST",
                conversation_url,
                response.status_code,
                duration,
                conversation_id=conversation_id,
            )

        except httpx.RequestError as e:
            duration = time.time() - start_time
            log_exception(self.logger, "Hermes 创建会话请求失败", e)
            log_api_request(
                self.logger,
                "POST",
                conversation_url,
                500,
                duration,
                error=str(e),
            )
            raise HermesAPIError(500, f"Failed to create conversation: {e!s}") from e

        else:
            self.logger.info("Hermes 会话创建成功 - ID: %s", conversation_id)
            return conversation_id

    async def _ensure_conversation(self, llm_id: str = "") -> str:
        """
        确保有可用的会话 ID，智能重用空对话或创建新会话

        优先使用已存在的空对话，如果没有空对话或获取失败，则创建新对话。
        这样可以避免产生过多的空对话记录。

        Args:
            llm_id: 指定的 LLM ID

        Returns:
            str: 可用的会话 ID

        """
        if self._conversation_id is None:
            try:
                # 先尝试获取现有对话列表
                conversation_list = await self._get_conversation_list()

                # 如果有对话，检查最新的对话是否为空
                if conversation_list:
                    latest_conversation_id = conversation_list[0]  # 已经按时间排序，第一个是最新的
                    try:
                        # 检查最新对话是否为空
                        if await self._is_conversation_empty(latest_conversation_id):
                            self.logger.info("重用空对话 - ID: %s", latest_conversation_id)
                            self._conversation_id = latest_conversation_id
                            return self._conversation_id
                    except HermesAPIError:
                        # 如果检查对话记录失败，继续创建新对话
                        self.logger.warning("检查对话记录失败，将创建新对话")

                # 如果没有对话或最新对话不为空，创建新对话
                self._conversation_id = await self._create_conversation(llm_id)

            except HermesAPIError:
                # 如果获取对话列表失败，直接创建新对话
                self.logger.warning("获取对话列表失败，将创建新对话")
                self._conversation_id = await self._create_conversation(llm_id)

        return self._conversation_id

    def _build_chat_headers(self) -> dict[str, str]:
        """构建聊天请求的HTTP头部"""
        headers = {
            "Host": self._get_host_header(),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

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
                should_break, break_message = self._handle_special_events(event)
                if should_break:
                    if break_message:
                        yield break_message
                    break

                # 处理文本内容
                text_content = event.get_text_content()
                if text_content:
                    has_content = True
                    self._log_text_content(text_content)
                    yield text_content
                else:
                    self.logger.info("事件无文本内容")

            self.logger.info("流式响应处理完成 - 事件数量: %d, 有内容: %s", event_count, has_content)

        except Exception:
            self.logger.exception("处理流式响应事件时出错")
            raise

        # 处理无内容的情况
        if not has_content:
            yield self._get_no_content_message(event_count)

    def _handle_special_events(self, event: HermesStreamEvent) -> tuple[bool, str | None]:
        """处理特殊事件类型，返回(是否中断, 中断消息)"""
        if event.event_type == "done":
            self.logger.debug("收到完成事件，结束流式响应")
            return True, None

        if event.event_type == "error":
            self.logger.error("收到后端错误事件: %s", event.data.get("error", "Unknown error"))
            return True, "抱歉，后端服务出现错误，请稍后重试。"

        if event.event_type == "sensitive":
            self.logger.warning("收到敏感内容事件: %s", event.data.get("message", "Sensitive content detected"))
            return True, "抱歉，响应内容包含敏感信息，已被系统屏蔽。"

        return False, None

    async def _handle_stream_error(self, error: Exception, *, has_content: bool) -> AsyncGenerator[str, None]:
        """处理流式响应网络错误"""
        self.logger.exception("处理流式响应时出现网络错误: %s", error)
        if has_content:
            yield "\n\n[连接中断，但已获得部分响应]"
        else:
            raise HermesAPIError(500, f"Network error during streaming: {error!s}") from error

    async def _handle_unexpected_error(self, error: Exception, *, has_content: bool) -> AsyncGenerator[str, None]:
        """处理流式响应未知错误"""
        self.logger.exception("处理流式响应时出现未知错误: %s", error)
        if has_content:
            yield "\n\n[处理响应时出现错误，但已获得部分内容]"
        else:
            raise HermesAPIError(500, f"Unexpected error during streaming: {error!s}") from error

    def _get_no_content_message(self, event_count: int) -> str:
        """获取无内容时的消息"""
        self.logger.warning(
            "流式响应完成但未产生任何文本内容 - 事件总数: %d",
            event_count,
        )
        return "抱歉，服务暂时无法响应您的请求，请稍后重试。"

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
        client = await self._get_client()
        chat_url = urljoin(self.base_url, "/api/chat")
        headers = self._build_chat_headers()

        try:
            async with client.stream(
                "POST",
                chat_url,
                json=request.to_dict(),
                headers=headers,
            ) as response:
                await self._validate_chat_response(response)
                async for text in self._process_stream_events(response):
                    yield text

        except httpx.RequestError as e:
            raise HermesAPIError(500, f"Network error: {e!s}") from e
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise HermesAPIError(500, f"Data parsing error: {e!s}") from e

    def _log_text_content(self, text_content: str) -> None:
        """记录文本内容到日志"""
        max_log_length = 50
        display_text = (
            text_content[:max_log_length] + "..."
            if len(text_content) > max_log_length
            else text_content
        )
        self.logger.debug("产生文本内容: %s", display_text)

    async def _get_conversation_list(self) -> list[str]:
        """
        获取会话ID列表，按创建时间从新到旧排序

        通过调用 /api/conversation 接口获取用户的所有会话，
        提取 conversationId 并按 createdTime 从新到旧排序。

        Returns:
            list[str]: 会话ID列表，按创建时间排序（新到旧）

        Raises:
            HermesAPIError: 当 API 调用失败时

        """
        start_time = time.time()
        self.logger.info("开始请求 Hermes 会话列表 API")

        client = await self._get_client()
        conversation_url = urljoin(self.base_url, "/api/conversation")

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Host": self._get_host_header(),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = await client.get(conversation_url, headers=headers)
            duration = time.time() - start_time

            if response.status_code != HTTP_OK:
                error_text = await response.aread()
                log_api_request(
                    self.logger,
                    "GET",
                    conversation_url,
                    response.status_code,
                    duration,
                    error=error_text.decode("utf-8"),
                )
                raise HermesAPIError(response.status_code, error_text.decode("utf-8"))

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                log_api_request(
                    self.logger,
                    "GET",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Invalid JSON response",
                )
                raise HermesAPIError(500, "Invalid JSON response") from e

            # 检查响应格式
            if not isinstance(data, dict) or "result" not in data:
                log_api_request(
                    self.logger,
                    "GET",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Invalid API response format",
                )
                raise HermesAPIError(500, "Invalid API response format")

            result = data["result"]
            if not isinstance(result, dict) or "conversations" not in result:
                log_api_request(
                    self.logger,
                    "GET",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="Missing conversations in response",
                )
                raise HermesAPIError(500, "Missing conversations in response")

            conversations = result["conversations"]
            if not isinstance(conversations, list):
                log_api_request(
                    self.logger,
                    "GET",
                    conversation_url,
                    response.status_code,
                    duration,
                    error="conversations is not a list",
                )
                raise HermesAPIError(500, "conversations field is not a list")

            # 提取会话信息并按创建时间排序
            conversation_items = [
                {
                    "id": conv["conversationId"],
                    "created_time": conv["createdTime"],
                }
                for conv in conversations
                if isinstance(conv, dict) and "conversationId" in conv and "createdTime" in conv
            ]

            # 按创建时间排序（从新到旧）
            conversation_items.sort(key=lambda x: x["created_time"], reverse=True)

            # 提取排序后的会话ID列表
            conversation_ids = [item["id"] for item in conversation_items]

            # 记录成功的API请求
            log_api_request(
                self.logger,
                "GET",
                conversation_url,
                response.status_code,
                duration,
                conversation_count=len(conversation_ids),
            )

            self.logger.info("获取到 %d 个会话", len(conversation_ids))

        except httpx.RequestError as e:
            duration = time.time() - start_time
            log_exception(self.logger, "Hermes 会话列表请求失败", e)
            log_api_request(
                self.logger,
                "GET",
                conversation_url,
                500,
                duration,
                error=str(e),
            )
            raise HermesAPIError(500, f"Failed to get conversation list: {e!s}") from e
        else:
            return conversation_ids

    async def _is_conversation_empty(self, conversation_id: str) -> bool:
        """
        检查指定对话是否为空（没有聊天记录）

        通过调用 /api/record/{conversation_id} 接口检查对话的聊天记录。
        如果 result.records 为空列表，说明这是一个新对话，可以直接使用。

        Args:
            conversation_id: 要检查的对话ID

        Returns:
            bool: True 表示对话为空，False 表示对话有内容

        Raises:
            HermesAPIError: 当 API 调用失败时

        """
        start_time = time.time()
        self.logger.info("检查对话是否为空 - ID: %s", conversation_id)

        client = await self._get_client()
        record_url = urljoin(self.base_url, f"/api/record/{conversation_id}")

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Host": self._get_host_header(),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = await client.get(record_url, headers=headers)
            duration = time.time() - start_time

            if response.status_code != HTTP_OK:
                error_text = await response.aread()
                log_api_request(
                    self.logger,
                    "GET",
                    record_url,
                    response.status_code,
                    duration,
                    error=error_text.decode("utf-8"),
                )
                raise HermesAPIError(response.status_code, error_text.decode("utf-8"))

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                log_api_request(
                    self.logger,
                    "GET",
                    record_url,
                    response.status_code,
                    duration,
                    error="Invalid JSON response",
                )
                raise HermesAPIError(500, "Invalid JSON response") from e

            # 检查响应格式
            if not isinstance(data, dict) or "result" not in data:
                log_api_request(
                    self.logger,
                    "GET",
                    record_url,
                    response.status_code,
                    duration,
                    error="Invalid API response format",
                )
                raise HermesAPIError(500, "Invalid API response format")

            result = data["result"]
            if not isinstance(result, dict) or "records" not in result:
                log_api_request(
                    self.logger,
                    "GET",
                    record_url,
                    response.status_code,
                    duration,
                    error="Missing records in response",
                )
                raise HermesAPIError(500, "Missing records in response")

            records = result["records"]
            if not isinstance(records, list):
                log_api_request(
                    self.logger,
                    "GET",
                    record_url,
                    response.status_code,
                    duration,
                    error="records is not a list",
                )
                raise HermesAPIError(500, "records field is not a list")

            # 判断对话是否为空
            is_empty = len(records) == 0

            # 记录成功的API请求
            log_api_request(
                self.logger,
                "GET",
                record_url,
                response.status_code,
                duration,
                records_count=len(records),
                is_empty=is_empty,
            )

            self.logger.info("对话 %s %s", conversation_id, "为空" if is_empty else "有内容")

        except httpx.RequestError as e:
            duration = time.time() - start_time
            log_exception(self.logger, "检查对话记录请求失败", e)
            log_api_request(
                self.logger,
                "GET",
                record_url,
                500,
                duration,
                error=str(e),
            )
            raise HermesAPIError(500, f"Failed to check conversation records: {e!s}") from e
        else:
            return is_empty

    async def _stop(self) -> None:
        """停止当前会话"""
        if self.client is None or self.client.is_closed:
            return

        try:
            stop_url = urljoin(self.base_url, "/api/stop")
            headers = {
                "Host": self._get_host_header(),
            }
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            response = await self.client.post(stop_url, headers=headers)

            if response.status_code != HTTP_OK:
                error_text = await response.aread()
                raise HermesAPIError(response.status_code, error_text.decode("utf-8"))

        except httpx.RequestError as e:
            log_exception(self.logger, "停止会话请求失败", e)
            raise HermesAPIError(500, f"Failed to stop conversation: {e!s}") from e

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
