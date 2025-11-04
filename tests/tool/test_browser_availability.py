"""
测试浏览器可用性检测功能

验证在不同环境下浏览器可用性检测是否正常工作。
"""

import sys
import unittest
import webbrowser
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tool.validators import is_browser_available


class TestBrowserAvailability(unittest.TestCase):
    """测试浏览器可用性检测"""

    @patch("tool.validators.webbrowser.get")
    def test_browser_available(self, mock_get: MagicMock) -> None:
        """测试浏览器可用的情况"""
        # 模拟浏览器可用
        mock_browser = MagicMock()
        mock_get.return_value = mock_browser

        result = is_browser_available()
        assert result is True

    @patch("tool.validators.webbrowser.get")
    def test_browser_not_available_error(self, mock_get: MagicMock) -> None:
        """测试浏览器不可用的情况（抛出 Error）"""
        # 模拟浏览器不可用
        mock_get.side_effect = webbrowser.Error("No web browser found")

        result = is_browser_available()
        assert result is False

    @patch("tool.validators.webbrowser.get")
    def test_browser_not_available_exception(self, mock_get: MagicMock) -> None:
        """测试浏览器检测时出现异常的情况"""
        # 模拟检测时出现异常
        mock_get.side_effect = OSError("Failed to detect browser")

        result = is_browser_available()
        assert result is False

    @patch("tool.validators.webbrowser.get")
    def test_browser_returns_none(self, mock_get: MagicMock) -> None:
        """测试浏览器返回 None 的情况"""
        # 模拟浏览器返回 None
        mock_get.return_value = None

        result = is_browser_available()
        assert result is False


if __name__ == "__main__":
    unittest.main()
