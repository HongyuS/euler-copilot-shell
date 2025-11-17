"""
测试 HermesChatClient 的 llm_id 验证功能

运行方法：
    pytest tests/backend/test_llm_id_validation.py -v
"""

import pytest

from backend.hermes.client import HermesChatClient
from backend.hermes.exceptions import HermesAPIError


@pytest.mark.asyncio
@pytest.mark.integration
class TestLLMIDValidation:
    """测试 HermesChatClient 的 llm_id 验证"""

    async def test_empty_llm_id_raises_exception(self, mock_config_manager) -> None:
        """测试没有 llm_id 应该抛出异常"""
        # 创建没有 llm_id 的客户端（模拟未配置）
        client = HermesChatClient(
            base_url="http://localhost:8000",
            config_manager=mock_config_manager,
        )

        assert client._get_llm_id() == ""

        # 尝试生成响应，应该抛出 HermesAPIError
        with pytest.raises(HermesAPIError) as exc_info:
            async for _ in client.get_llm_response("测试"):
                pass

        # 验证异常信息
        assert exc_info.value.status_code == 400
        assert "未配置" in exc_info.value.message or "Chat 模型" in exc_info.value.message

    async def test_valid_llm_id_passes_validation(self, mock_config_manager_with_llm) -> None:
        """测试有 llm_id 的客户端通过验证"""
        # 创建有 llm_id 的客户端（模拟已配置）
        client = HermesChatClient(
            base_url="http://localhost:8000",
            config_manager=mock_config_manager_with_llm,
        )

        assert client._get_llm_id() == "test-model-id"

        # llm_id 验证应该通过（实际请求会因为连接问题失败）
        # 这里我们只验证不会在 _validate_llm_id 阶段抛出异常
        try:
            client._validate_llm_id()
        except HermesAPIError:
            pytest.fail("不应该在 llm_id 验证阶段抛出异常")

    def test_get_llm_id_from_config_manager(self, mock_config_manager_with_llm) -> None:
        """测试从配置管理器获取 llm_id"""
        client = HermesChatClient(
            base_url="http://localhost:8000",
            config_manager=mock_config_manager_with_llm,
        )

        llm_id = client._get_llm_id()
        assert llm_id == "test-model-id"

    def test_get_llm_id_without_config_manager(self) -> None:
        """测试没有配置管理器时返回空字符串"""
        client = HermesChatClient(
            base_url="http://localhost:8000",
            config_manager=None,
        )

        llm_id = client._get_llm_id()
        assert llm_id == ""
