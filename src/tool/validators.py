"""
配置验证器

提供实际 API 调用验证配置的有效性。
"""

from typing import Any

import httpx
from openai import APIError, AsyncOpenAI, AuthenticationError, OpenAIError

from log.manager import get_logger

# 常量定义
MAX_MODEL_DISPLAY = 5
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404


class APIValidator:
    """API 配置验证器"""

    def __init__(self) -> None:
        """初始化验证器"""
        self.logger = get_logger(__name__)

    async def validate_llm_config(  # noqa: PLR0913
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: int = 30,  # noqa: ASYNC109
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        验证 LLM 配置

        Args:
            endpoint: API 端点
            api_key: API 密钥
            model: 模型名称
            timeout: 超时时间（秒）
            max_tokens: 最大令牌数，如果为 None 则使用默认值
            temperature: 温度参数，如果为 None 则使用默认值

        Returns:
            tuple[bool, str, dict]: (是否验证成功, 错误/成功消息, 额外信息)

        """
        self.logger.info("开始验证 LLM 配置 - 端点: %s, 模型: %s", endpoint, model)

        try:
            client = AsyncOpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)

            # 测试基本对话功能
            chat_valid, chat_msg = await self._test_basic_chat(client, model, max_tokens, temperature)
            if not chat_valid:
                await client.close()
                return False, chat_msg, {}

            # 测试 function_call 支持
            func_valid, func_msg, func_info = await self._test_function_call(client, model, max_tokens, temperature)

            await client.close()

        except TimeoutError:
            return False, f"连接超时 - 无法在 {timeout} 秒内连接到 {endpoint}", {}
        except (AuthenticationError, APIError, OpenAIError) as e:
            error_msg = f"LLM 配置验证失败: {e!s}"
            self.logger.exception(error_msg)
            return False, error_msg, {}
        else:
            success_msg = "LLM 配置验证成功"
            if func_valid:
                success_msg += " - 支持 function_call"
            else:
                success_msg += f" - 不支持 function_call: {func_msg}"

            return True, success_msg, {
                "supports_function_call": func_valid,
                "function_call_info": func_info,
            }

    async def validate_embedding_config(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: int = 30,  # noqa: ASYNC109
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

    async def _test_basic_chat(
        self,
        client: AsyncOpenAI,
        model: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[bool, str]:
        """测试基本对话功能"""
        try:
            # 使用传入的参数或默认值
            call_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": "请回复'测试成功'"}],
                "max_tokens": max_tokens if max_tokens is not None else 10,
            }

            # 只有当 temperature 不为 None 时才添加到参数中
            if temperature is not None:
                call_kwargs["temperature"] = temperature

            response = await client.chat.completions.create(**call_kwargs)
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
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """测试 function_call 支持"""
        try:
            # 定义一个简单的测试函数
            test_function = {
                "name": "get_current_time",
                "description": "获取当前时间",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }

            # 构建请求参数
            call_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": "请调用函数获取当前时间"}],
                "functions": [test_function],  # type: ignore[arg-type]
                "function_call": "auto",
                "max_tokens": max_tokens if max_tokens is not None else 50,
            }

            # 只有当 temperature 不为 None 时才添加到参数中
            if temperature is not None:
                call_kwargs["temperature"] = temperature

            response = await client.chat.completions.create(**call_kwargs)
        except (AuthenticationError, APIError, OpenAIError) as e:
            # 如果 functions 参数不支持，尝试 tools 格式
            if "functions" in str(e).lower() or "function_call" in str(e).lower():
                return await self._test_tools_format(client, model, max_tokens, temperature)
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
                return await self._test_tools_format(client, model, max_tokens, temperature)

            return False, "function_call 响应为空", {"supports_functions": False}

    async def _test_tools_format(
        self,
        client: AsyncOpenAI,
        model: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
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

            # 构建请求参数
            call_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": "请调用函数获取当前时间"}],
                "tools": [test_tool],  # type: ignore[arg-type]
                "tool_choice": "auto",
                "max_tokens": max_tokens if max_tokens is not None else 50,
            }

            # 只有当 temperature 不为 None 时才添加到参数中
            if temperature is not None:
                call_kwargs["temperature"] = temperature

            response = await client.chat.completions.create(**call_kwargs)
        except (AuthenticationError, APIError, OpenAIError) as e:
            return False, f"tools 格式测试失败: {e!s}", {"supports_functions": False}
        else:
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                    tool_call = choice.message.tool_calls[0]
                    # 安全地访问 function 属性
                    function_name = ""
                    function_obj = getattr(tool_call, "function", None)
                    if function_obj and hasattr(function_obj, "name"):
                        function_name = function_obj.name
                    return True, "支持 tools 格式的 function_call", {
                        "function_name": function_name,
                        "supports_functions": True,
                        "format": "tools",
                    }

            return False, "不支持 function_call 功能", {"supports_functions": False}


async def validate_oi_connection(base_url: str, access_token: str) -> tuple[bool, str]:  # noqa: PLR0911
    """
    验证 openEuler Intelligence 服务连接

    Args:
        base_url: 服务 URL
        access_token: 访问令牌（可为空）

    Returns:
        tuple[bool, str]: (连接是否成功, 消息)

    """
    logger = get_logger(__name__)

    try:
        # 确保 URL 格式正确
        if not base_url.startswith(("http://", "https://")):
            return False, "服务 URL 必须以 http:// 或 https:// 开头"

        # 移除尾部的斜杠
        base_url = base_url.rstrip("/")

        # 构造用户信息 API URL
        api_url = f"{base_url}/api/user"

        # 准备请求头
        headers = {}
        if access_token and access_token.strip():
            headers["Authorization"] = f"Bearer {access_token}"

        async with httpx.AsyncClient(timeout=10) as client:
            # 发送请求
            response = await client.get(api_url, headers=headers)

            # 检查 HTTP 状态码
            if response.status_code != HTTP_OK:
                return _handle_http_error(response.status_code)

            # 检查响应内容
            try:
                response_data = response.json()
            except (ValueError, TypeError, KeyError):
                return False, "服务返回的数据格式不正确"

            # 检查 code 字段
            code = response_data.get("code")
            if code == HTTP_OK:
                logger.info("openEuler Intelligence 服务连接成功")
                return True, "连接成功"

            return False, f"服务返回错误代码: {code}"

    except httpx.ConnectError:
        return False, "无法连接到服务，请检查 URL 和网络连接"
    except httpx.TimeoutException:
        return False, "连接超时，请检查网络连接或服务状态"
    except Exception as e:
        logger.exception("验证 openEuler Intelligence 连接时发生异常")
        return False, f"连接验证失败: {e}"


def _handle_http_error(status_code: int) -> tuple[bool, str]:
    """处理 HTTP 错误状态码"""
    error_messages = {
        HTTP_UNAUTHORIZED: "访问令牌无效或已过期",
        HTTP_FORBIDDEN: "访问权限不足",
        HTTP_NOT_FOUND: "API 接口不存在，请检查服务版本",
    }

    message = error_messages.get(status_code, f"服务响应异常，状态码: {status_code}")
    return False, message
