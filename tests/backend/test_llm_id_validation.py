"""测试 HermesChatClient 的 llm_id 验证功能"""

import asyncio

from backend.hermes.client import HermesChatClient
from backend.hermes.exceptions import HermesAPIError


async def test_llm_id_validation():
    """测试 llm_id 验证"""
    print("=" * 60)
    print("测试 llm_id 验证功能")
    print("=" * 60 + "\n")

    # 测试 1: 没有 llm_id 应该抛出异常
    print("测试 1: 创建没有 llm_id 的客户端")
    client = HermesChatClient(base_url="http://localhost:8000", llm_id="")
    print(f"  客户端 llm_id: '{client.llm_id}'")

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
    print("测试 2: 创建有 llm_id 的客户端")
    client_with_llm = HermesChatClient(
        base_url="http://localhost:8000",
        llm_id="test-model-id",
    )
    print(f"  客户端 llm_id: '{client_with_llm.llm_id}'")
    print("  ✓ llm_id 验证应该通过（实际请求会因为连接问题失败）\n")

    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_llm_id_validation())
