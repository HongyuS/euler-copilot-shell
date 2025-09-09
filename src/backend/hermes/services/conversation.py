"""Hermes 会话管理器"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx

from backend.hermes.constants import HTTP_OK
from backend.hermes.exceptions import HermesAPIError
from log.manager import get_logger, log_api_request, log_exception

if TYPE_CHECKING:
    from .http import HermesHttpManager


class HermesConversationManager:
    """Hermes 会话管理器"""

    def __init__(self, http_manager: HermesHttpManager) -> None:
        """初始化会话管理器"""
        self.logger = get_logger(__name__)
        self.http_manager = http_manager
        self._conversation_id: str | None = None

    def reset_conversation(self) -> None:
        """重置会话，下次聊天时会创建新的会话"""
        self._conversation_id = None

    async def ensure_conversation(self, llm_id: str = "") -> str:
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

    async def stop_conversation(self, task_id: str = "") -> None:
        """
        停止当前会话

        Args:
            task_id: 可选的任务ID，如果提供且非空，则作为查询参数发送

        """
        if self.http_manager.client is None or self.http_manager.client.is_closed:
            return

        try:
            stop_url = urljoin(self.http_manager.base_url, "/api/stop")
            headers = self.http_manager.build_headers()

            # 构建请求参数
            params = {}
            if task_id:
                params["taskId"] = task_id

            response = await self.http_manager.client.post(stop_url, headers=headers, params=params)

            if response.status_code != HTTP_OK:
                error_text = await response.aread()
                raise HermesAPIError(response.status_code, error_text.decode("utf-8"))

        except httpx.RequestError as e:
            log_exception(self.logger, "停止会话请求失败", e)
            raise HermesAPIError(500, f"Failed to stop conversation: {e!s}") from e

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

        client = await self.http_manager.get_client()
        conversation_url = urljoin(self.http_manager.base_url, "/api/conversation")

        # 构建请求参数
        params = {}
        if llm_id:
            params["llm_id"] = llm_id

        headers = self.http_manager.build_headers()

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

        client = await self.http_manager.get_client()
        conversation_url = urljoin(self.http_manager.base_url, "/api/conversation")

        headers = self.http_manager.build_headers({
            "Accept": "application/json, text/plain, */*",
        })

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

        client = await self.http_manager.get_client()
        record_url = urljoin(self.http_manager.base_url, f"/api/record/{conversation_id}")

        headers = self.http_manager.build_headers({
            "Accept": "application/json, text/plain, */*",
        })

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
