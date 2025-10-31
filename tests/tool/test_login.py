"""测试登录功能模块"""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

from tool.callback_server import CallbackServer
from tool.oi_login import get_auth_url


class TestLoginFunctions(unittest.TestCase):
    """测试登录相关函数"""

    @patch("urllib.request.urlopen")
    def test_get_auth_url_success(self, mock_urlopen: MagicMock) -> None:
        """测试成功获取授权 URL"""
        # 模拟后端响应（包含 Web 端的 redirect_uri）
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "code": 200,
                "message": "success",
                "result": {
                    "url": "https://auth.example.com/login?client_id=123&redirect_uri=https://web.example.com/callback",
                },
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        callback_url = "http://localhost:8081/callback"
        result = get_auth_url("https://api.example.com", callback_url)

        # 验证返回的 URL 包含本地回调地址
        self.assertIsNotNone(result)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8081%2Fcallback", result) # type: ignore[ignore]
        self.assertIn("client_id=123", result) # type: ignore[ignore]

    @patch("urllib.request.urlopen")
    def test_get_auth_url_error_response(self, mock_urlopen: MagicMock) -> None:
        """测试后端返回错误"""
        # 模拟后端错误响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"code": 400, "message": "Bad request", "result": None}).encode(
            "utf-8",
        )
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_auth_url("https://api.example.com", "http://localhost:8081/callback")

        self.assertIsNone(result)


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
        port = server._find_available_port()  # noqa: SLF001

        self.assertEqual(port, 8081)

    @patch("socket.socket")
    def test_find_available_port_retry(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口需要重试"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟前两次失败，第三次成功
        mock_socket.bind.side_effect = [OSError, OSError, None]

        server = CallbackServer(start_port=8081)
        port = server._find_available_port()  # noqa: SLF001

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
            server._find_available_port()  # noqa: SLF001

        self.assertIn("无法找到可用端口", str(context.exception))


if __name__ == "__main__":
    unittest.main()
