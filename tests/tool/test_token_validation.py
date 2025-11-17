"""
测试令牌格式验证

运行方法：
    pytest tests/tool/test_token_validation.py -v
"""

import pytest

from tool.validators import _is_valid_token_format


@pytest.mark.unit
class TestTokenFormatValidation:
    """测试令牌格式验证功能"""

    def test_empty_token_is_valid(self) -> None:
        """测试空令牌（兼容旧版本）"""
        assert _is_valid_token_format("") is True
        assert _is_valid_token_format("   ") is True

    @pytest.mark.parametrize(
        "token",
        [
            "a1b2c3d4e5f6789012345678abcdef90",  # 小写
            "A1B2C3D4E5F6789012345678ABCDEF90",  # 大写
            "00000000000000000000000000000000",  # 全0
            "ffffffffffffffffffffffffffffffff",  # 全f
        ],
    )
    def test_valid_short_term_tokens(self, token: str) -> None:
        """测试有效的短期令牌（32字符十六进制）"""
        assert _is_valid_token_format(token) is True

    @pytest.mark.parametrize(
        "token",
        [
            "a1b2c3d4e5f6789012345678abcdef9",  # 31个字符
            "a1b2c3d4e5f6789012345678abcdef901",  # 33个字符
            "g1b2c3d4e5f6789012345678abcdef90",  # 包含非十六进制字符 g
            "a1b2c3d4-e5f6-7890-1234-5678abcdef90",  # 包含短横线
        ],
    )
    def test_invalid_short_term_tokens(self, token: str) -> None:
        """测试无效的短期令牌"""
        assert _is_valid_token_format(token) is False

    @pytest.mark.parametrize(
        "token",
        [
            "sk-a1b2c3d4e5f6789012345678abcdef90",
            "sk-A1B2C3D4E5F6789012345678ABCDEF90",
            "sk-00000000000000000000000000000000",
            "sk-ffffffffffffffffffffffffffffffff",
        ],
    )
    def test_valid_long_term_tokens(self, token: str) -> None:
        """测试有效的长期令牌（sk- 前缀 + 32字符十六进制）"""
        assert _is_valid_token_format(token) is True

    @pytest.mark.parametrize(
        "token",
        [
            "sk-a1b2c3d4e5f6789012345678abcdef9",  # 少一个字符
            "sk-a1b2c3d4e5f6789012345678abcdef901",  # 多一个字符
            "sk-g1b2c3d4e5f6789012345678abcdef90",  # 包含非十六进制字符
            "sk_a1b2c3d4e5f6789012345678abcdef90",  # 错误的分隔符
            "SK-a1b2c3d4e5f6789012345678abcdef90",  # 大写前缀
            "sk-a1b2c3d4-e5f6-7890-1234-5678abcdef90",  # 包含短横线
            "a1b2c3d4e5f6789012345678abcdef90-sk",  # 后缀而非前缀
        ],
    )
    def test_invalid_long_term_tokens(self, token: str) -> None:
        """测试无效的长期令牌"""
        assert _is_valid_token_format(token) is False

    @pytest.mark.parametrize(
        "token",
        [
            "random_string",
            "12345",
            "Bearer a1b2c3d4e5f6789012345678abcdef90",
            "token-a1b2c3d4e5f6789012345678abcdef90",
            "a1b2c3d4e5f6789012345678abcdef90-suffix",
        ],
    )
    def test_other_invalid_formats(self, token: str) -> None:
        """测试其他无效格式"""
        assert _is_valid_token_format(token) is False

    def test_tokens_with_whitespace(self) -> None:
        """测试带空格的令牌（应该被 strip 处理）"""
        assert _is_valid_token_format("  a1b2c3d4e5f6789012345678abcdef90  ") is True
        assert _is_valid_token_format("  sk-a1b2c3d4e5f6789012345678abcdef90  ") is True

    def test_mixed_case_hex_tokens(self) -> None:
        """测试混合大小写的十六进制令牌"""
        mixed_case_short = "A1b2C3d4E5f6789012345678AbCdEf90"
        mixed_case_long = "sk-A1b2C3d4E5f6789012345678AbCdEf90"
        assert _is_valid_token_format(mixed_case_short) is True
        assert _is_valid_token_format(mixed_case_long) is True
