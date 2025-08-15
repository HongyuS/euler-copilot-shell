"""
配置验证器

提供实际 API 调用验证配置的有效性。
"""

from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, OpenAIError

from log.manager import get_logger

# 常量定义
MAX_MODEL_DISPLAY = 5


class APIValidator:
    """API 配置验证器"""

    def __init__(self) -> None:
        """初始化验证器"""
        self.logger = get_logger(__name__)

    async def validate_llm_config(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: int = 30,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        验证 LLM 配置

        Args:
            endpoint: API 端点
            api_key: API 密钥
            model: 模型名称
            timeout: 超时时间（秒）

        Returns:
            tuple[bool, str, dict]: (是否验证成功, 错误/成功消息, 额外信息)

        """
        self.logger.info("开始验证 LLM 配置 - 端点: %s, 模型: %s", endpoint, model)

        try:
            client = AsyncOpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)

            # 1. 验证模型是否存在
            models_valid, models_msg, available_models = await self._check_model_availability(
                client,
                model,
            )
            if not models_valid:
                await client.close()
                return False, models_msg, {"available_models": available_models}

            # 2. 验证基本对话功能
            chat_valid, chat_msg = await self._test_basic_chat(client, model)
            if not chat_valid:
                await client.close()
                return False, chat_msg, {"available_models": available_models}

            # 3. 验证 function_call 支持
            func_valid, func_msg, func_info = await self._test_function_call(client, model)

            await client.close()

            if chat_valid:
                success_msg = "LLM 配置验证成功 - 模型"
                if func_valid:
                    success_msg += "支持 function_call"
                else:
                    success_msg += f"不支持 function_call: {func_msg}"

                return True, success_msg, {
                    "available_models": available_models,
                    "supports_function_call": func_valid,
                    "function_call_info": func_info,
                }

        except TimeoutError:
            return False, f"连接超时 - 无法在 {timeout} 秒内连接到 {endpoint}", {}
        except (AuthenticationError, APIError, OpenAIError) as e:
            error_msg = f"LLM 配置验证失败: {e!s}"
            self.logger.exception(error_msg)
            return False, error_msg, {}

        return False, "未知错误", {}

    async def validate_embedding_config(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: int = 30,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        验证 Embedding 配置

        Args:
            endpoint: API 端点
            api_key: API 密钥
            model: 模型名称
            timeout: 超时时间（秒）

        Returns:
            tuple[bool, str, dict]: (是否验证成功, 错误/成功消息, 额外信息)

        """
        self.logger.info("开始验证 Embedding 配置 - 端点: %s, 模型: %s", endpoint, model)

        try:
            client = AsyncOpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)

            # 测试 embedding 功能
            test_text = "这是一个测试文本"
            response = await client.embeddings.create(input=test_text, model=model)

            await client.close()
        except TimeoutError:
            return False, f"连接超时 - 无法在 {timeout} 秒内连接到 {endpoint}", {}
        except (AuthenticationError, APIError, OpenAIError) as e:
            error_msg = f"Embedding 配置验证失败: {e!s}"
            self.logger.exception(error_msg)
            return False, error_msg, {}
        else:
            if response.data and len(response.data) > 0:
                embedding = response.data[0].embedding
                dimension = len(embedding)
                return True, f"Embedding 配置验证成功 - 维度: {dimension}", {
                    "model": model,
                    "dimension": dimension,
                    "sample_embedding_length": len(embedding),
                }

            return False, "Embedding 响应为空", {}

    async def _check_model_availability(
        self,
        client: AsyncOpenAI,
        target_model: str,
    ) -> tuple[bool, str, list[str]]:
        """检查模型是否可用"""
        try:
            models_response = await client.models.list()
            available_models = [model.id for model in models_response.data]

            if target_model in available_models:
                return True, f"模型 {target_model} 可用", available_models

            return (
                False,
                (
                    f"模型 {target_model} 不可用。可用模型: "
                    f"{', '.join(available_models[:MAX_MODEL_DISPLAY])}"
                    f"{'...' if len(available_models) > MAX_MODEL_DISPLAY else ''}"
                ),
                available_models,
            )
        except (AuthenticationError, APIError, OpenAIError) as e:
            return False, f"获取模型列表失败: {e!s}", []

    async def _test_basic_chat(
        self,
        client: AsyncOpenAI,
        model: str,
    ) -> tuple[bool, str]:
        """测试基本对话功能"""
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请回复'测试成功'"}],
                max_tokens=10,
            )
        except (AuthenticationError, APIError, OpenAIError) as e:
            return False, f"基本对话测试失败: {e!s}"
        else:
            if response.choices and len(response.choices) > 0:
                return True, "基本对话功能正常"

            return False, "对话响应为空"

    async def _test_function_call(
        self,
        client: AsyncOpenAI,
        model: str,
    ) -> tuple[bool, str, dict[str, Any]]:
        """测试 function_call 支持"""
        try:
            # 定义一个简单的测试函数
            test_function = {
                "name": "get_current_time",
                "description": "获取当前时间",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请调用函数获取当前时间"}],
                functions=[test_function],  # type: ignore[arg-type]
                function_call="auto",
                max_tokens=50,
            )
        except (AuthenticationError, APIError, OpenAIError) as e:
            # 如果 functions 参数不支持，尝试 tools 格式
            if "functions" in str(e).lower() or "function_call" in str(e).lower():
                return await self._test_tools_format(client, model)
            return False, f"function_call 测试失败: {e!s}", {"supports_functions": False}
        else:
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice.message, "function_call") and choice.message.function_call:
                    return True, "支持 function_call", {
                        "function_name": choice.message.function_call.name,
                        "supports_functions": True,
                    }

                # 尝试 tools 格式（OpenAI API 新版本）
                return await self._test_tools_format(client, model)

            return False, "function_call 响应为空", {"supports_functions": False}

    async def _test_tools_format(
        self,
        client: AsyncOpenAI,
        model: str,
    ) -> tuple[bool, str, dict[str, Any]]:
        """测试新版 tools 格式的 function calling"""
        try:
            test_tool = {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前时间",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请调用函数获取当前时间"}],
                tools=[test_tool],  # type: ignore[arg-type]
                tool_choice="auto",
                max_tokens=50,
            )
        except (AuthenticationError, APIError, OpenAIError) as e:
            return False, f"tools 格式测试失败: {e!s}", {"supports_functions": False}
        else:
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                    tool_call = choice.message.tool_calls[0]
                    return True, "支持 tools 格式的 function_call", {
                        "function_name": tool_call.function.name,
                        "supports_functions": True,
                        "format": "tools",
                    }

            return False, "不支持 function_call 功能", {"supports_functions": False}
