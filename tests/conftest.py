"""
Pytest 配置文件

定义全局 fixtures 和测试配置
"""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_config_manager() -> Mock:
    """模拟的配置管理器"""
    mock = Mock()
    mock.get_llm_chat_model.return_value = ""
    mock.get_eulerintelli_url.return_value = "http://localhost:8080"
    mock.get_eulerintelli_key.return_value = ""
    return mock


@pytest.fixture
def mock_config_manager_with_llm() -> Mock:
    """模拟的配置管理器（已配置 LLM）"""
    mock = Mock()
    mock.get_llm_chat_model.return_value = "test-model-id"
    mock.get_eulerintelli_url.return_value = "http://localhost:8080"
    mock.get_eulerintelli_key.return_value = "test-token"
    return mock


@pytest.fixture
def valid_token_samples() -> list[str]:
    """有效的令牌样本"""
    return [
        "",  # 空令牌（兼容旧版本）
        "a1b2c3d4e5f6789012345678abcdef90",  # 短期令牌
        "sk-a1b2c3d4e5f6789012345678abcdef90",  # 长期令牌
    ]


@pytest.fixture
def invalid_token_samples() -> list[str]:
    """无效的令牌样本"""
    return [
        "invalid_token",  # 无效格式
        "12345",  # 太短
        "a1b2c3d4e5f6789012345678abcdef9",  # 31个字符
        "sk-invalid",  # sk- 前缀但长度不对
        "Bearer a1b2c3d4e5f6789012345678abcdef90",  # 带 Bearer 前缀
    ]
