"""OpenAIClient 单元测试"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from openai import OpenAIError

from backend.openai import OpenAIClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _DummyAsyncOpenAI:
    """替身 AsyncOpenAI，用于注入测试资源"""

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        self.http_client = kwargs.get("http_client")
        self.models = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


class _FakeModel:
    """封装模型 ID"""

    def __init__(self, model_id: str) -> None:
        self.id = model_id


class _FakeModelList:
    """异步可迭代的模型集合"""

    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def __aiter__(self) -> AsyncIterator[_FakeModel]:
        async def _iterator() -> AsyncIterator[_FakeModel]:
            for model_id in self._ids:
                yield _FakeModel(model_id)

        return _iterator()


class _FakeModelsResource:
    """仿造 openai.models 资源"""

    def __init__(self, ids: list[str], *, raises: Exception | None = None) -> None:
        self._ids = ids
        self._error = raises

    async def list(self) -> _FakeModelList:
        if self._error is not None:
            raise self._error
        return _FakeModelList(self._ids)


def _make_client(monkeypatch: pytest.MonkeyPatch) -> OpenAIClient:
    """帮助创建注入了假 AsyncOpenAI 的客户端"""
    monkeypatch.setattr("backend.openai.AsyncOpenAI", _DummyAsyncOpenAI)
    return OpenAIClient("https://api.example", "gpt-test", api_key="token")


@pytest.mark.asyncio
async def test_get_available_models_returns_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """成功路径会返回 ModelInfo 列表"""
    client = _make_client(monkeypatch)
    client.client.models = _FakeModelsResource(["gpt-4o", "gpt-4o-mini"])  # type: ignore[assignment]

    models = await client.get_available_models()

    assert [model.model_name for model in models] == ["gpt-4o", "gpt-4o-mini"]

    await client.close()


@pytest.mark.asyncio
async def test_get_available_models_handles_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAIError 会被吞掉并返回空列表"""
    client = _make_client(monkeypatch)
    client.client.models = _FakeModelsResource([], raises=OpenAIError("boom"))  # type: ignore[assignment]

    models = await client.get_available_models()

    assert models == []

    await client.close()
