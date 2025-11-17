"""
测试 ModelInfo 数据类

运行方法：
    pytest tests/backend/test_model_info.py
"""

import pytest

from backend.models import LLMType, ModelInfo

# 测试常量
GPT4_MAX_TOKENS = 8192


@pytest.mark.unit
class TestModelInfo:
    """测试 ModelInfo 数据类"""

    def test_model_info_creation_openai_style(self) -> None:
        """测试创建 OpenAI 风格的 ModelInfo 对象（只有 model_name）"""
        openai_model = ModelInfo(model_name="gpt-4")
        assert openai_model.model_name == "gpt-4"
        assert openai_model.llm_id is None
        assert openai_model.llm_description is None
        assert openai_model.llm_type == []
        assert openai_model.max_tokens is None

    def test_model_info_creation_hermes_full(self) -> None:
        """测试创建完整的 Hermes ModelInfo 对象"""
        hermes_model = ModelInfo(
            model_name="gpt-4",
            llm_id="gpt-4",
            llm_description="OpenAI GPT-4 model",
            llm_type=[LLMType.CHAT, LLMType.FUNCTION],
            max_tokens=GPT4_MAX_TOKENS,
        )
        assert hermes_model.model_name == "gpt-4"
        assert hermes_model.llm_id == "gpt-4"
        assert hermes_model.llm_description == "OpenAI GPT-4 model"
        assert hermes_model.llm_type == [LLMType.CHAT, LLMType.FUNCTION]
        assert hermes_model.max_tokens == GPT4_MAX_TOKENS

    def test_model_info_string_representation(self) -> None:
        """测试 ModelInfo 的字符串表示"""
        model = ModelInfo(
            model_name="gpt-3.5-turbo",
            llm_id="gpt-3.5-turbo",
        )
        assert str(model) == "gpt-3.5-turbo"
        assert "gpt-3.5-turbo" in repr(model)

    def test_model_info_str_prefers_llm_id(self) -> None:
        """测试 __str__ 优先使用 llm_id"""
        model_with_both = ModelInfo(
            model_name="model-backend-name",
            llm_id="llm-display-id",
        )
        assert str(model_with_both) == "llm-display-id"

        model_without_llm_id = ModelInfo(model_name="model-name")
        assert str(model_without_llm_id) == "model-name"


@pytest.mark.unit
class TestLLMTypeParser:
    """测试 LLM 类型解析功能"""

    def test_parse_all_valid_llm_types(self) -> None:
        """测试解析所有合法的 LLM 类型"""
        valid_types = ["chat", "function", "embedding", "vision", "thinking"]
        parsed = ModelInfo.parse_llm_types(valid_types)
        expected = [
            LLMType.CHAT,
            LLMType.FUNCTION,
            LLMType.EMBEDDING,
            LLMType.VISION,
            LLMType.THINKING,
        ]
        assert len(parsed) == len(expected)
        assert parsed == expected

    def test_parse_llm_types_filters_invalid(self) -> None:
        """测试过滤不合法的 LLM 类型"""
        mixed_types = ["chat", "invalid_type", "function", "unknown", "vision"]
        parsed = ModelInfo.parse_llm_types(mixed_types)
        # 只保留合法的类型
        expected = [LLMType.CHAT, LLMType.FUNCTION, LLMType.VISION]
        assert len(parsed) == len(expected)
        assert parsed == expected

    def test_parse_llm_types_empty_list(self) -> None:
        """测试解析空列表"""
        assert ModelInfo.parse_llm_types([]) == []

    def test_parse_llm_types_none(self) -> None:
        """测试解析 None"""
        assert ModelInfo.parse_llm_types(None) == []

    @pytest.mark.parametrize(
        "llm_type_str,expected_enum",
        [
            ("chat", LLMType.CHAT),
            ("function", LLMType.FUNCTION),
            ("embedding", LLMType.EMBEDDING),
            ("vision", LLMType.VISION),
            ("thinking", LLMType.THINKING),
        ],
    )
    def test_parse_single_llm_type(self, llm_type_str: str, expected_enum: LLMType) -> None:
        """测试解析单个 LLM 类型"""
        parsed = ModelInfo.parse_llm_types([llm_type_str])
        assert len(parsed) == 1
        assert parsed[0] == expected_enum


@pytest.mark.unit
class TestLLMTypeEnum:
    """测试 LLMType 枚举"""

    def test_llm_type_values(self) -> None:
        """测试 LLMType 枚举值"""
        assert LLMType.CHAT.value == "chat"
        assert LLMType.FUNCTION.value == "function"
        assert LLMType.EMBEDDING.value == "embedding"
        assert LLMType.VISION.value == "vision"
        assert LLMType.THINKING.value == "thinking"

    def test_llm_type_is_string_enum(self) -> None:
        """测试 LLMType 是字符串枚举"""
        assert isinstance(LLMType.CHAT, str)
        assert LLMType.CHAT == "chat"
