"""
测试登录功能模块

运行方法：
    pytest tests/tool/test_login.py -v
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from tool.callback_server import CallbackServer
from tool.oi_login import get_auth_url


@pytest.mark.unit
class TestLoginFunctions:
    """测试登录相关函数"""

    @patch("urllib.request.urlopen")
    def test_get_auth_url_success(self, mock_urlopen: MagicMock) -> None:
        """测试成功获取授权 URL"""
        # 模拟后端响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "code": 200,
                "message": "success",
                "result": {
                    "url": "https://auth.example.com/login",
                    "token": "test-token",
                },
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        auth_url, login_token = get_auth_url("https://api.example.com")

        # 验证返回值
        assert auth_url is not None
        assert auth_url == "https://auth.example.com/login"
        assert login_token == "test-token"

    @patch("urllib.request.urlopen")
    def test_get_auth_url_error_response(self, mock_urlopen: MagicMock) -> None:
        """测试后端返回错误"""
        # 模拟后端错误响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "code": 400,
                "message": "Bad request",
                "result": None,
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        auth_url, login_token = get_auth_url("https://api.example.com")

        assert auth_url is None
        assert login_token is None

    @patch("urllib.request.urlopen")
    def test_get_auth_url_missing_url(self, mock_urlopen: MagicMock) -> None:
        """测试响应中缺少 URL"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "code": 200,
                "message": "success",
                "result": {"token": "test-token"},  # 缺少 url 字段
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        auth_url, login_token = get_auth_url("https://api.example.com")

        assert auth_url is None
        assert login_token is None


@pytest.mark.unit
class TestCallbackServer:
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

        assert port == 8081
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 8081))

    @patch("socket.socket")
    def test_find_available_port_retry(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口需要重试"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟前两次失败，第三次成功
        mock_socket.bind.side_effect = [OSError, OSError, None]

        server = CallbackServer(start_port=8081)
        port = server._find_available_port()

        assert port == 8083
        assert mock_socket.bind.call_count == 3

    @patch("socket.socket")
    def test_find_available_port_failure(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口全部失败"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟所有尝试都失败
        mock_socket.bind.side_effect = OSError

        server = CallbackServer(start_port=8081, max_attempts=3)

        with pytest.raises(RuntimeError) as context:
            server._find_available_port()

        assert "无法找到可用端口" in str(context.value)

    def test_callback_server_initialization(self) -> None:
        """测试回调服务器初始化"""
        server = CallbackServer(start_port=9000, max_attempts=10)
        assert server.start_port == 9000
        assert server.max_attempts == 10
        assert server.port is None
        assert server.server is None
        assert server.thread is None

    @patch("socketserver.TCPServer")
    @patch("socket.socket")
    def test_callback_server_start(
        self,
        mock_socket_class: MagicMock,
        mock_tcp_server: MagicMock,
    ) -> None:
        """测试启动回调服务器"""
        # 模拟端口可用
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.bind.return_value = None

        # 模拟 TCPServer
        mock_server_instance = MagicMock()
        mock_tcp_server.return_value = mock_server_instance

        server = CallbackServer(start_port=8081)
        launcher_url = server.start("https://auth.example.com")

        assert launcher_url == "http://127.0.0.1:8081/launcher"
        assert server.port == 8081
        mock_tcp_server.assert_called_once()
