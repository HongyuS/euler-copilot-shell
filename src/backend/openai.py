"""OpenAI 大模型客户端"""

import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from backend.base import LLMClientBase
from log.manager import get_logger, log_api_request, log_exception

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


class OpenAIClient(LLMClientBase):
    """OpenAI 大模型客户端"""

    def __init__(self, base_url: str, model: str, api_key: str = "") -> None:
        """初始化 OpenAI 大模型客户端"""
        self.logger = get_logger(__name__)

        self.model = model
        self.base_url = base_url
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # 添加历史记录管理
        self._conversation_history: list[ChatCompletionMessageParam] = []

        self.logger.info("OpenAI 客户端初始化成功 - URL: %s, Model: %s", base_url, model)

    async def get_llm_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        生成命令建议

        异步调用 OpenAI 或兼容接口的大模型生成命令建议，支持流式输出。
        保持对话历史记录，支持多轮对话上下文。
        """
        start_time = time.time()
        self.logger.info("开始请求 OpenAI 流式聊天 API - Model: %s", self.model)

        # 添加用户消息到历史记录
        user_message: ChatCompletionMessageParam = {"role": "user", "content": prompt}
        self._conversation_history.append(user_message)

        try:
            # 使用完整的对话历史记录
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._conversation_history,
                stream=True,
            )

            # 记录成功的API请求
            duration = time.time() - start_time
            log_api_request(
                self.logger,
                "POST",
                f"{self.base_url}/chat/completions",
                200,
                duration,
                model=self.model,
                stream=True,
                history_length=len(self._conversation_history),
            )

            # 收集助手的完整回复
            assistant_response = ""
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_response += content
                    yield content

            # 将助手回复添加到历史记录
            if assistant_response:
                assistant_message: ChatCompletionMessageParam = {
                    "role": "assistant",
                    "content": assistant_response,
                }
                self._conversation_history.append(assistant_message)
                self.logger.info("对话历史记录已更新，当前消息数: %d", len(self._conversation_history))

        except Exception as e:
            # 如果请求失败，移除刚添加的用户消息
            if (
                self._conversation_history
                and len(self._conversation_history) > 0
                and self._conversation_history[-1].get("content") == prompt
            ):
                self._conversation_history.pop()

            duration = time.time() - start_time
            log_exception(self.logger, "OpenAI 流式聊天 API 请求失败", e)
            # 记录失败的API请求
            log_api_request(
                self.logger,
                "POST",
                f"{self.base_url}/chat/completions",
                500,
                duration,
                model=self.model,
                stream=True,
                error=str(e),
            )
            raise

    def reset_conversation(self) -> None:
        """
        重置对话上下文

        清空历史记录，开始新的对话会话。
        """
        self._conversation_history.clear()
        self.logger.info("OpenAI 客户端对话历史记录已重置")

    async def get_available_models(self) -> list[str]:
        """
        获取当前 LLM 服务中可用的模型，返回名称列表

        调用 LLM 服务的模型列表接口，并解析返回结果提取模型名称。
        """
        start_time = time.time()
        self.logger.info("开始请求 OpenAI 模型列表 API")

        try:
            models_response = await self.client.models.list()
            models = [model.id async for model in models_response]
            # 记录成功的API请求
            duration = time.time() - start_time
            log_api_request(
                self.logger,
                "GET",
                f"{self.base_url}/models",
                200,
                duration,
                model_count=len(models),
            )
        except Exception as e:
            duration = time.time() - start_time
            log_exception(self.logger, "OpenAI 模型列表 API 请求失败", e)
            # 记录失败的API请求
            log_api_request(
                self.logger,
                "GET",
                f"{self.base_url}/models",
                500,
                duration,
                error=str(e),
            )
            raise
        else:
            self.logger.info("获取到 %d 个可用模型", len(models))
            return models

    async def close(self) -> None:
        """关闭 OpenAI 客户端"""
        try:
            await self.client.close()
            self.logger.info("OpenAI 客户端已关闭")
        except Exception as e:
            log_exception(self.logger, "关闭 OpenAI 客户端失败", e)
            raise
