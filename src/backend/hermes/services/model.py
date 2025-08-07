"""Hermes 模型管理器"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx

from backend.hermes.constants import HTTP_OK
from log.manager import get_logger, log_api_request, log_exception

if TYPE_CHECKING:
    from .http import HermesHttpManager


class HermesModelManager:
    """Hermes 模型管理器"""

    def __init__(self, http_manager: HermesHttpManager) -> None:
        """初始化模型管理器"""
        self.logger = get_logger(__name__)
        self.http_manager = http_manager

    async def get_available_models(self) -> list[str]:
        """
        获取当前 LLM 服务中可用的模型，返回名称列表

        通过调用 /api/llm 接口获取可用的大模型列表。
        如果调用失败或没有返回，使用空列表，后端接口会自动使用默认模型。
        """
        start_time = time.time()
        self.logger.info("开始请求 Hermes 模型列表 API")

        try:
            client = await self.http_manager.get_client()
            llm_url = urljoin(self.http_manager.base_url, "/api/llm")

            headers = self.http_manager.build_headers()
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
                f"{self.http_manager.base_url}/api/llm",
                500,
                duration,
                error=str(e),
            )
            self.logger.warning("Hermes 模型列表 API 请求异常，返回空列表")
            return []
        else:
            return models
