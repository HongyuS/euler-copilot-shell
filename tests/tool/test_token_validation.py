"""测试令牌格式验证"""

import sys
from pathlib import Path

from tool.validators import _is_valid_token_format

# 添加 src 目录到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_empty_token() -> None:
    """测试空令牌（兼容旧版本）"""
    assert _is_valid_token_format("") is True
    assert _is_valid_token_format("   ") is True
    print("✓ 空令牌测试通过")


def test_short_term_token() -> None:
    """测试短期令牌（32字符十六进制）"""
    # 有效的短期令牌
    valid_tokens = [
        "a1b2c3d4e5f6789012345678abcdef90",  # 小写
        "A1B2C3D4E5F6789012345678ABCDEF90",  # 大写
        "00000000000000000000000000000000",  # 全0
        "ffffffffffffffffffffffffffffffff",  # 全f
    ]

    for token in valid_tokens:
        assert _is_valid_token_format(token) is True, f"应该接受有效的短期令牌: {token}"

    # 无效的短期令牌
    invalid_tokens = [
        "a1b2c3d4e5f6789012345678abcdef9",  # 31个字符
        "a1b2c3d4e5f6789012345678abcdef901",  # 33个字符
        "g1b2c3d4e5f6789012345678abcdef90",  # 包含非十六进制字符 g
        "a1b2c3d4-e5f6-7890-1234-5678abcdef90",  # 包含短横线
    ]

    for token in invalid_tokens:
        assert _is_valid_token_format(token) is False, f"应该拒绝无效的短期令牌: {token}"

    print("✓ 短期令牌测试通过")


def test_long_term_token() -> None:
    """测试长期令牌（sk- 前缀 + 32字符十六进制）"""
    # 有效的长期令牌
    valid_tokens = [
        "sk-a1b2c3d4e5f6789012345678abcdef90",
        "sk-A1B2C3D4E5F6789012345678ABCDEF90",
        "sk-00000000000000000000000000000000",
        "sk-ffffffffffffffffffffffffffffffff",
    ]

    for token in valid_tokens:
        assert _is_valid_token_format(token) is True, f"应该接受有效的长期令牌: {token}"

    # 无效的长期令牌
    invalid_tokens = [
        "sk-a1b2c3d4e5f6789012345678abcdef9",  # 少一个字符
        "sk-a1b2c3d4e5f6789012345678abcdef901",  # 多一个字符
        "sk-g1b2c3d4e5f6789012345678abcdef90",  # 包含非十六进制字符
        "sk_a1b2c3d4e5f6789012345678abcdef90",  # 错误的分隔符
        "SK-a1b2c3d4e5f6789012345678abcdef90",  # 大写前缀
        "sk-a1b2c3d4-e5f6-7890-1234-5678abcdef90",  # 包含短横线
        "a1b2c3d4e5f6789012345678abcdef90-sk",  # 后缀而非前缀
    ]

    for token in invalid_tokens:
        assert _is_valid_token_format(token) is False, f"应该拒绝无效的长期令牌: {token}"

    print("✓ 长期令牌测试通过")


def test_other_invalid_formats() -> None:
    """测试其他无效格式"""
    invalid_tokens = [
        "random_string",
        "12345",
        "Bearer a1b2c3d4e5f6789012345678abcdef90",
        "token-a1b2c3d4e5f6789012345678abcdef90",
        "a1b2c3d4e5f6789012345678abcdef90-suffix",
    ]

    for token in invalid_tokens:
        assert _is_valid_token_format(token) is False, f"应该拒绝无效格式: {token}"

    print("✓ 其他无效格式测试通过")


def test_edge_cases() -> None:
    """测试边界情况"""
    # 带空格的令牌（应该被 strip 处理）
    assert _is_valid_token_format("  a1b2c3d4e5f6789012345678abcdef90  ") is True
    assert _is_valid_token_format("  sk-a1b2c3d4e5f6789012345678abcdef90  ") is True

    print("✓ 边界情况测试通过")


if __name__ == "__main__":
    print("运行令牌格式验证测试...\n")

    test_empty_token()
    test_short_term_token()
    test_long_term_token()
    test_other_invalid_formats()
    test_edge_cases()

    print("\n所有测试通过！✓")
