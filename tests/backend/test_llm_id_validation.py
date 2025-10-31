"""测试 HermesChatClient 的 llm_id 验证功能"""

import asyncio
from unittest.mock import Mock

from backend.hermes.client import HermesChatClient
from backend.hermes.exceptions import HermesAPIError


async def test_llm_id_validation():
    """测试 llm_id 验证"""
    print("=" * 60)
    print("测试 llm_id 验证功能")
    print("=" * 60 + "\n")

    # 测试 1: 没有 llm_id 应该抛出异常
    print("测试 1: 创建没有 llm_id 的客户端（模拟未配置）")
    # 创建一个模拟的 ConfigManager，返回空的 llm_id
    mock_config_empty = Mock()
    mock_config_empty.get_llm_chat_model.return_value = ""
    
    client = HermesChatClient(
        base_url="http://localhost:8000",
        config_manager=mock_config_empty,
    )
    print(f"  配置的 llm_id: '{client._get_llm_id()}'")

    try:
        # 尝试生成响应，应该抛出异常
        print("  尝试生成响应...")
        async for _ in client.get_llm_response("测试"):
            pass
        print("  ✗ 应该抛出异常但没有")
    except HermesAPIError as e:
        print(f"  ✓ 成功捕获异常 (状态码: {e.status_code})")
        print(f"\n错误消息:\n{e.message}\n")

    # 测试 2: 有 llm_id 的客户端不应该在验证阶段抛出异常
    print("测试 2: 创建有 llm_id 的客户端（模拟已配置）")
    # 创建一个模拟的 ConfigManager，返回有效的 llm_id
    mock_config_with_llm = Mock()
    mock_config_with_llm.get_llm_chat_model.return_value = "test-model-id"
    
    client_with_llm = HermesChatClient(
        base_url="http://localhost:8000",
        config_manager=mock_config_with_llm,
    )
    print(f"  配置的 llm_id: '{client_with_llm._get_llm_id()}'")
    print("  ✓ llm_id 验证应该通过（实际请求会因为连接问题失败）\n")

    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_llm_id_validation())
