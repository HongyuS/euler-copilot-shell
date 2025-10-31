"""测试登录功能模块"""

import unittest
from unittest.mock import MagicMock, patch

from tool.callback_server import CallbackServer
from tool.oi_login import build_auth_url


class TestLoginFunctions(unittest.TestCase):
    """测试登录相关函数"""

    def test_build_auth_url(self) -> None:
        """测试构建授权 URL"""
        base_url = "http://127.0.0.1:8002"
        callback_url = "http://127.0.0.1:8081/callback"

        result = build_auth_url(base_url, callback_url)

        expected = "http://127.0.0.1:8002/api/auth/redirect?action=login&callback_url=http://127.0.0.1:8081/callback"
        self.assertEqual(result, expected)

    def test_build_auth_url_with_trailing_slash(self) -> None:
        """测试构建授权 URL（URL 带末尾斜杠）"""
        base_url = "http://127.0.0.1:8002/"
        callback_url = "http://127.0.0.1:8081/callback"

        result = build_auth_url(base_url, callback_url)

        expected = "http://127.0.0.1:8002/api/auth/redirect?action=login&callback_url=http://127.0.0.1:8081/callback"
        self.assertEqual(result, expected)


class TestCallbackServer(unittest.TestCase):
    """测试回调服务器"""

    @patch("socket.socket")
    def test_find_available_port_success(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口成功"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟第一次尝试成功
        mock_socket.bind.return_value = None

        server = CallbackServer(start_port=8081)
        port = server._find_available_port()

        self.assertEqual(port, 8081)

    @patch("socket.socket")
    def test_find_available_port_retry(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口需要重试"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟前两次失败，第三次成功
        mock_socket.bind.side_effect = [OSError, OSError, None]

        server = CallbackServer(start_port=8081)
        port = server._find_available_port()

        self.assertEqual(port, 8083)

    @patch("socket.socket")
    def test_find_available_port_failure(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口全部失败"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟所有尝试都失败
        mock_socket.bind.side_effect = OSError

        server = CallbackServer(start_port=8081, max_attempts=3)

        with self.assertRaises(RuntimeError) as context:
            server._find_available_port()

        self.assertIn("无法找到可用端口", str(context.exception))


if __name__ == "__main__":
    unittest.main()
