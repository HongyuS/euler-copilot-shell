"""
测试浏览器可用性检测功能

验证在不同环境下浏览器可用性检测是否正常工作。

运行方法：
    pytest tests/tool/test_browser_availability.py -v
"""

import webbrowser
from unittest.mock import MagicMock, patch

import pytest

from tool.validators import is_browser_available


@pytest.mark.unit
class TestBrowserAvailability:
    """测试浏览器可用性检测"""

    @patch("tool.validators.webbrowser.get")
    def test_browser_available(self, mock_get: MagicMock) -> None:
        """测试浏览器可用的情况"""
        # 模拟浏览器可用
        mock_browser = MagicMock()
        mock_get.return_value = mock_browser

        result = is_browser_available()
        assert result is True
        mock_get.assert_called_once()

    @patch("tool.validators.webbrowser.get")
    def test_browser_not_available_error(self, mock_get: MagicMock) -> None:
        """测试浏览器不可用的情况（抛出 Error）"""
        # 模拟浏览器不可用
        mock_get.side_effect = webbrowser.Error("No web browser found")

        result = is_browser_available()
        assert result is False
        mock_get.assert_called_once()

    @patch("tool.validators.webbrowser.get")
    def test_browser_not_available_exception(self, mock_get: MagicMock) -> None:
        """测试浏览器检测时出现异常的情况"""
        # 模拟检测时出现异常
        mock_get.side_effect = OSError("Failed to detect browser")

        result = is_browser_available()
        assert result is False
        mock_get.assert_called_once()

    @patch("tool.validators.webbrowser.get")
    def test_browser_returns_none(self, mock_get: MagicMock) -> None:
        """测试浏览器返回 None 的情况"""
        # 模拟浏览器返回 None
        mock_get.return_value = None

        result = is_browser_available()
        assert result is False
        mock_get.assert_called_once()

    @patch("tool.validators.webbrowser.get")
    def test_browser_runtime_error(self, mock_get: MagicMock) -> None:
        """测试浏览器检测时出现 RuntimeError"""
        # 模拟运行时错误
        mock_get.side_effect = RuntimeError("Browser detection failed")

        result = is_browser_available()
        assert result is False
        mock_get.assert_called_once()
