"""SSL 校验相关工具测试"""

from typing import Any

import pytest

from tool import validators
from tool.validators import APIValidator


@pytest.mark.unit
class TestEnvFlagParser:
    """验证布尔值解析逻辑"""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("TRUE", True),
            ("on", True),
            ("FALSE", False),
            ("Off", False),
            ("maybe", None),
            (None, None),
        ],
    )
    def test_parse_env_flag(self, value: str | None, expected: bool | None) -> None:  # noqa: FBT001
        """每种输入都应映射到预期的三态结果"""
        result = validators._parse_env_flag(value)  # noqa: SLF001
        assert result is expected


@pytest.mark.unit
class TestSSLResolution:
    """验证不同环境变量组合的决策优先级"""

    def test_explicit_argument_overrides_env(self) -> None:
        """用户传参优先级最高"""
        assert validators.should_verify_ssl(verify_ssl=False) is False
        assert validators.should_verify_ssl(verify_ssl=True) is True

    def test_skip_flag_disables_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OI_SKIP_SSL_VERIFY=1 应直接关闭 SSL"""
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "1")
        monkeypatch.delenv(validators.SSL_VERIFY_ENV_VAR, raising=False)
        assert validators.should_verify_ssl() is False

    def test_skip_flag_false_enables_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """当 skip 变量显式为 0 时，仍应继续验证"""
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "0")
        monkeypatch.setenv(validators.SSL_VERIFY_ENV_VAR, "0")  # 仍然被 skip 标志覆盖
        assert validators.should_verify_ssl() is True

    def test_verify_flag_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """仅设置 verify 变量时按其值执行"""
        monkeypatch.delenv(validators.SSL_SKIP_ENV_VAR, raising=False)
        monkeypatch.setenv(validators.SSL_VERIFY_ENV_VAR, "true")
        assert validators.should_verify_ssl() is True

    def test_default_true_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无环境变量时默认开启 SSL 校验"""
        monkeypatch.delenv(validators.SSL_SKIP_ENV_VAR, raising=False)
        monkeypatch.delenv(validators.SSL_VERIFY_ENV_VAR, raising=False)
        assert validators.should_verify_ssl() is True

    def test_invalid_values_fall_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """未知字符串不会改变默认行为"""
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "invalid")
        monkeypatch.setenv(validators.SSL_VERIFY_ENV_VAR, "invalid")
        assert validators.should_verify_ssl() is True

    def test_parse_flag_reads_environment_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """校验逻辑忽略大小写"""
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "YeS")
        assert validators.should_verify_ssl() is False
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "No")
        monkeypatch.setenv(validators.SSL_VERIFY_ENV_VAR, "off")
        assert validators.should_verify_ssl() is True

    def test_environment_cleanup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """清理变量后应恢复默认 True"""
        monkeypatch.setenv(validators.SSL_SKIP_ENV_VAR, "1")
        monkeypatch.setenv(validators.SSL_VERIFY_ENV_VAR, "1")
        assert validators.should_verify_ssl() is False
        # 清理后恢复默认
        monkeypatch.delenv(validators.SSL_SKIP_ENV_VAR, raising=False)
        monkeypatch.delenv(validators.SSL_VERIFY_ENV_VAR, raising=False)
        assert validators.should_verify_ssl() is True


class _StubOpenAIClient:
    """最小化 AsyncOpenAI 替身"""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
class TestAPIValidator:
    """验证 APIValidator 的行为分支"""

    async def test_validate_llm_config_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """成功路径应返回 function_call 信息并关闭客户端"""
        stub_client = _StubOpenAIClient()
        validator = APIValidator()

        def _return_stub(_self: APIValidator, **_kwargs: Any) -> _StubOpenAIClient:
            assert isinstance(_self, APIValidator)
            return stub_client

        monkeypatch.setattr(APIValidator, "_create_openai_client", _return_stub)

        async def fake_basic_chat(
            self: APIValidator,
            client: Any,
            model: str,
            max_tokens: int | None = None,
            temperature: float | None = None,
        ) -> tuple[bool, str]:
            assert self is validator
            assert client is stub_client
            assert isinstance(model, str)
            if max_tokens is not None:
                assert isinstance(max_tokens, int)
            if temperature is not None:
                assert isinstance(temperature, (float, int))
            return True, "chat ok"

        async def fake_detect(
            self: APIValidator,
            client: Any,
            model: str,
            max_tokens: int | None = None,
            temperature: float | None = None,
        ) -> tuple[bool, str, str]:
            assert self is validator
            assert client is stub_client
            assert isinstance(model, str)
            if max_tokens is not None:
                assert isinstance(max_tokens, int)
            if temperature is not None:
                assert isinstance(temperature, (float, int))
            return True, "detected", "structured_output"

        monkeypatch.setattr(APIValidator, "_test_basic_chat", fake_basic_chat)
        monkeypatch.setattr(APIValidator, "_detect_function_call_type", fake_detect)

        valid, message, info = await validator.validate_llm_config("http://endpoint", "key", "model")

        assert valid is True
        assert "LLM" in message
        assert info == {"supports_function_call": True, "detected_function_call_type": "structured_output"}
        assert stub_client.closed is True

    async def test_validate_llm_config_handles_basic_chat_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """基本对话失败时直接返回错误信息"""
        stub_client = _StubOpenAIClient()
        validator = APIValidator()

        def _return_stub(_self: APIValidator, **_kwargs: Any) -> _StubOpenAIClient:
            assert isinstance(_self, APIValidator)
            return stub_client

        monkeypatch.setattr(APIValidator, "_create_openai_client", _return_stub)

        async def fail_basic_chat(
            self: APIValidator,
            client: Any,
            model: str,
            max_tokens: int | None = None,
            temperature: float | None = None,
        ) -> tuple[bool, str]:
            assert self is validator
            assert client is stub_client
            assert isinstance(model, str)
            if max_tokens is not None:
                assert isinstance(max_tokens, int)
            if temperature is not None:
                assert isinstance(temperature, (float, int))
            return False, "basic chat failed"

        monkeypatch.setattr(APIValidator, "_test_basic_chat", fail_basic_chat)

        valid, message, info = await validator.validate_llm_config("http://endpoint", "key", "model")

        assert valid is False
        assert message == "basic chat failed"
        assert info == {}
        assert stub_client.closed is True

    async def test_validate_embedding_config_falls_back_to_mindie(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Embedding 验证会在 OpenAI 失败后尝试 MindIE"""
        validator = APIValidator()

        async def fail_openai(*_args: Any, **_kwargs: Any) -> tuple[bool, str, dict[str, str]]:
            return False, "openai fail", {}

        async def success_mindie(*_args: Any, **_kwargs: Any) -> tuple[bool, str, dict[str, str]]:
            return True, "mindie ok", {"type": "mindie"}

        monkeypatch.setattr(APIValidator, "_validate_openai_embedding", fail_openai)
        monkeypatch.setattr(APIValidator, "_validate_mindie_embedding", success_mindie)

        valid, message, info = await validator.validate_embedding_config("http://embed", "key", "model")

        assert valid is True
        assert message == "mindie ok"
        assert info == {"type": "mindie"}
