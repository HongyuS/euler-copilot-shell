"""测试令牌验证与 OI 连接集成"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tool.validators import validate_oi_connection

# 添加 src 目录到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


async def test_invalid_token_no_request() -> None:
    """测试无效令牌不会发送 HTTP 请求"""
    base_url = "http://localhost:8080"
    invalid_tokens = [
        "invalid_token",  # 无效格式
        "12345",  # 太短
        "a1b2c3d4e5f6789012345678abcdef9",  # 31个字符
        "sk-invalid",  # sk- 前缀但长度不对
        "Bearer a1b2c3d4e5f6789012345678abcdef90",  # 带 Bearer 前缀
    ]

    # Mock httpx.AsyncClient 来验证是否发送了请求
    with patch("tool.validators.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        for token in invalid_tokens:
            print(f"测试无效令牌: {token}")
            valid, message = await validate_oi_connection(base_url, token)

            # 验证结果
            assert valid is False, f"应该拒绝无效令牌: {token}"
            assert "格式无效" in message, f"错误消息应该提示格式无效: {message}"

            # 验证没有发送 HTTP 请求
            mock_client_instance.get.assert_not_called()

            print(f"  ✓ 正确拒绝，未发送请求")

    print("\n✓ 无效令牌测试通过 - 未发送任何 HTTP 请求")


async def test_valid_token_sends_request() -> None:
    """测试有效令牌会发送 HTTP 请求"""
    base_url = "http://localhost:8080"
    valid_tokens = [
        "",  # 空令牌（兼容旧版本）
        "a1b2c3d4e5f6789012345678abcdef90",  # 短期令牌
        "sk-a1b2c3d4e5f6789012345678abcdef90",  # 长期令牌
    ]

    for token in valid_tokens:
        token_display = token if token else "(空令牌)"
        print(f"测试有效令牌: {token_display}")

        # Mock httpx.AsyncClient
        with patch("tool.validators.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 200, "data": {}}

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # 执行验证
            _valid, _message = await validate_oi_connection(base_url, token)

            # 验证发送了 HTTP 请求
            mock_client_instance.get.assert_called_once()
            print(f"  ✓ 已发送 HTTP 请求")

    print("\n✓ 有效令牌测试通过 - 正确发送 HTTP 请求")


async def test_url_validation() -> None:
    """测试 URL 格式验证优先于令牌验证"""
    invalid_urls = [
        "localhost:8080",  # 缺少协议
        "ftp://localhost:8080",  # 错误的协议
        "localhost",  # 无端口无协议
    ]

    # 使用有效令牌
    valid_token = "a1b2c3d4e5f6789012345678abcdef90"  # noqa: S105

    with patch("tool.validators.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        for url in invalid_urls:
            print(f"测试无效 URL: {url}")
            valid, message = await validate_oi_connection(url, valid_token)

            # 验证结果
            assert valid is False, f"应该拒绝无效 URL: {url}"
            assert "http://" in message or "https://" in message, f"错误消息应该提示协议错误: {message}"

            # 验证没有发送 HTTP 请求
            mock_client_instance.get.assert_not_called()

            print(f"  ✓ 正确拒绝")

    print("\n✓ URL 验证测试通过")


if __name__ == "__main__":
    print("运行令牌验证与 OI 连接集成测试...\n")

    asyncio.run(test_invalid_token_no_request())
    asyncio.run(test_valid_token_sends_request())
    asyncio.run(test_url_validation())

    print("\n所有集成测试通过！✓")
