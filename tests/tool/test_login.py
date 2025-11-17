"""
测试登录功能模块

运行方法：
    pytest tests/tool/test_login.py -v
"""

from __future__ import annotations

import json
import threading
import urllib.error
from email.message import Message
from typing import Any, ClassVar, Final, Never
from unittest.mock import MagicMock, Mock, patch

import pytest

from tool.callback_server import CallbackHandler, CallbackServer
from tool.oi_login import browser_login, get_auth_url, poll_login_status

TEST_AUTH_URL: Final = "https://auth.example.com/login"
TEST_LOGIN_TOKEN: Final = "test-token"  # noqa: S105 - 测试常量
CALLBACK_START_PORT: Final = 8081
CALLBACK_RETRY_PORT: Final = 8083
CALLBACK_MAX_ATTEMPTS: Final = 3
CALLBACK_DEFAULT_TIMEOUT: Final = 300
SERVER_DEFAULT_PORT: Final = 9000
SERVER_DEFAULT_MAX_ATTEMPTS: Final = 10
LAUNCHER_URL: Final = "http://127.0.0.1:8081/launcher"


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
                    "url": TEST_AUTH_URL,
                    "token": TEST_LOGIN_TOKEN,
                },
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        auth_url, login_token = get_auth_url("https://api.example.com")

        # 验证返回值
        assert auth_url is not None
        assert auth_url == TEST_AUTH_URL
        assert login_token == TEST_LOGIN_TOKEN

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
                "result": {"token": TEST_LOGIN_TOKEN},  # 缺少 url 字段
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        auth_url, login_token = get_auth_url("https://api.example.com")

        assert auth_url is None
        assert login_token is None

    @patch("urllib.request.urlopen")
    def test_poll_login_status_success(self, mock_urlopen: MagicMock) -> None:
        """轮询成功时应返回 sessionId"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "code": 200,
                "result": {"sessionId": "abc123"},
            },
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        session = poll_login_status("https://api.example.com", max_attempts=1, interval=0)

        assert session == "abc123"

    @patch("urllib.request.urlopen")
    def test_poll_login_status_timeout(self, mock_urlopen: MagicMock) -> None:
        """持续失败会返回 None"""

        def _raise_error(*_args: Any, **_kwargs: Any) -> Never:
            headers = Message()
            headers["Content-Type"] = "application/json"
            error = urllib.error.HTTPError("https://api.example.com/api/user/session", 401, "auth", headers, None)
            raise error

        mock_urlopen.side_effect = _raise_error

        session = poll_login_status("https://api.example.com", max_attempts=2, interval=0)

        assert session is None


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

        server = CallbackServer(start_port=CALLBACK_START_PORT)
        port = server._find_available_port()  # noqa: SLF001

        assert port == CALLBACK_START_PORT
        mock_socket.bind.assert_called_once_with(("127.0.0.1", CALLBACK_START_PORT))

    @patch("socket.socket")
    def test_find_available_port_retry(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口需要重试"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟前两次失败，第三次成功
        mock_socket.bind.side_effect = [OSError, OSError, None]

        server = CallbackServer(start_port=CALLBACK_START_PORT)
        port = server._find_available_port()  # noqa: SLF001

        assert port == CALLBACK_RETRY_PORT
        assert mock_socket.bind.call_count == CALLBACK_MAX_ATTEMPTS

    @patch("socket.socket")
    def test_find_available_port_failure(self, mock_socket_class: MagicMock) -> None:
        """测试查找可用端口全部失败"""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # 模拟所有尝试都失败
        mock_socket.bind.side_effect = OSError

        server = CallbackServer(start_port=CALLBACK_START_PORT, max_attempts=CALLBACK_MAX_ATTEMPTS)

        with pytest.raises(RuntimeError) as context:
            server._find_available_port()  # noqa: SLF001

        assert "无法找到可用端口" in str(context.value)

    def test_callback_server_initialization(self) -> None:
        """测试回调服务器初始化"""
        server = CallbackServer(start_port=SERVER_DEFAULT_PORT, max_attempts=SERVER_DEFAULT_MAX_ATTEMPTS)
        assert server.start_port == SERVER_DEFAULT_PORT
        assert server.max_attempts == SERVER_DEFAULT_MAX_ATTEMPTS
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

        server = CallbackServer(start_port=CALLBACK_START_PORT)
        launcher_url = server.start("https://auth.example.com")

        assert launcher_url == LAUNCHER_URL
        assert server.port == CALLBACK_START_PORT
        mock_tcp_server.assert_called_once()

    def test_wait_for_auth_returns_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """事件被设置时返回 auth_result"""
        server = CallbackServer()
        event = threading.Event()
        event.set()

        monkeypatch.setattr(CallbackHandler, "auth_event", event)
        monkeypatch.setattr(CallbackHandler, "auth_result", {"type": "session", "sessionId": "abc"})

        result = server.wait_for_auth(timeout=1)

        assert result == {"type": "session", "sessionId": "abc"}

    def test_wait_for_auth_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """超时时返回错误描述"""
        server = CallbackServer()
        event = threading.Event()

        monkeypatch.setattr(CallbackHandler, "auth_event", event)
        monkeypatch.setattr(CallbackHandler, "auth_result", {})

        result = server.wait_for_auth(timeout=0)

        assert result["error"] == "timeout"


@pytest.mark.unit
class TestBrowserLoginFlow:
    """验证 browser_login 中的关键分支"""

    def test_browser_login_exits_when_browser_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无图形环境时应立刻退出"""
        monkeypatch.setattr("tool.oi_login.is_browser_available", lambda: False)

        with pytest.raises(SystemExit) as exc:
            browser_login()

        assert exc.value.code == 1

    def test_browser_login_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """成功路径下应调用初始化/等待/处理逻辑并关闭服务器"""
        fake_config = object()
        monkeypatch.setattr("tool.oi_login.is_browser_available", lambda: True)
        monkeypatch.setattr("tool.oi_login._load_config_and_check_url", lambda: fake_config)

        recorded: dict[str, Any] = {}

        def fake_initiate(config: object, server: CallbackServer) -> None:
            recorded["init"] = (config, server)

        monkeypatch.setattr("tool.oi_login._initiate_login_flow", fake_initiate)

        class _StubCallback:
            instances: ClassVar[list[_StubCallback]] = []

            def __init__(self) -> None:
                self.stopped = False
                _StubCallback.instances.append(self)

            def wait_for_auth(self, timeout: int = CALLBACK_DEFAULT_TIMEOUT) -> dict[str, str]:
                recorded["wait"] = timeout
                return {"type": "session"}

            def stop(self) -> None:
                self.stopped = True

        monkeypatch.setattr("tool.oi_login.CallbackServer", _StubCallback)

        def fake_handle(auth_result: dict[str, str], config: object) -> None:
            recorded["handle"] = (auth_result, config)

        monkeypatch.setattr("tool.oi_login._handle_auth_result", fake_handle)

        browser_login()

        stub = _StubCallback.instances[0]
        assert stub.stopped is True
        assert recorded["init"][0] is fake_config
        assert recorded["handle"] == ({"type": "session"}, fake_config)
