"""
测试 ModelInfo 数据类

运行方法：

```shell
source .venv/bin/activate && PYTHONPATH=src python tests/backend/test_model_info.py
```
"""

from backend.models import LLMType, ModelInfo

# 测试常量
GPT4_MAX_TOKENS = 8192


def test_model_info_creation() -> None:
    """测试创建 ModelInfo 对象"""
    # OpenAI 风格（只有 model_name）
    openai_model = ModelInfo(model_name="gpt-4")
    assert openai_model.model_name == "gpt-4"
    assert openai_model.llm_id is None
    assert openai_model.llm_description is None
    assert openai_model.llm_type == []
    assert openai_model.max_tokens is None


def test_model_info_hermes_full() -> None:
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


def test_model_info_string_representation() -> None:
    """测试 ModelInfo 的字符串表示"""
    model = ModelInfo(
        model_name="gpt-3.5-turbo",
        llm_id="gpt-3.5-turbo",
    )
    assert str(model) == "gpt-3.5-turbo"
    assert "gpt-3.5-turbo" in repr(model)


def test_parse_llm_types_valid() -> None:
    """测试解析合法的 LLM 类型"""
    # 测试所有合法类型
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


def test_parse_llm_types_invalid() -> None:
    """测试过滤不合法的 LLM 类型"""
    # 包含合法和不合法的类型
    mixed_types = ["chat", "invalid_type", "function", "unknown", "vision"]
    parsed = ModelInfo.parse_llm_types(mixed_types)
    # 只保留合法的类型
    expected = [LLMType.CHAT, LLMType.FUNCTION, LLMType.VISION]
    assert len(parsed) == len(expected)
    assert parsed == expected


def test_parse_llm_types_empty() -> None:
    """测试空列表和 None"""
    assert ModelInfo.parse_llm_types([]) == []
    assert ModelInfo.parse_llm_types(None) == []


if __name__ == "__main__":
    test_model_info_creation()
    test_model_info_hermes_full()
    test_model_info_string_representation()
    test_parse_llm_types_valid()
    test_parse_llm_types_invalid()
    test_parse_llm_types_empty()
    # 测试完成
    import sys

    sys.stdout.write("所有测试通过！✅\n")
