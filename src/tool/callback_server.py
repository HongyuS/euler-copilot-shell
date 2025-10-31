"""
本地 HTTP 回调服务器

用于接收 openEuler Intelligence 认证服务器的重定向回调
"""

import http.server
import socket
import socketserver
import urllib.parse
from threading import Event, Thread
from typing import ClassVar

from log.manager import get_logger

logger = get_logger(__name__)


class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """处理认证回调的 HTTP 请求处理器"""

    # 类变量，用于存储接收到的认证信息
    auth_result: ClassVar[dict] = {}
    auth_received: ClassVar[Event] = Event()

    def do_GET(self) -> None:
        """处理 GET 请求"""
        # 解析 URL 和查询参数
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        logger.info("接收到回调请求: %s", self.path)

        # 检查是否包含 sessionId
        if "sessionId" in query_params:
            session_id = query_params["sessionId"][0]
            CallbackHandler.auth_result = {"type": "session", "sessionId": session_id}
            self._send_success_response("登录成功！")
            CallbackHandler.auth_received.set()

        elif "error" in query_params:
            # 处理错误情况
            error = query_params["error"][0]
            error_description = query_params.get("error_description", [""])[0]
            CallbackHandler.auth_result = {
                "type": "error",
                "error": error,
                "error_description": error_description,
            }
            self._send_error_response(f"登录失败: {error_description}")
            CallbackHandler.auth_received.set()

        else:
            # 未知请求
            self._send_error_response("无效的回调请求")

    def _send_success_response(self, message: str) -> None:
        """发送成功响应页面"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>登录成功</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 4rem;
                    color: #4caf50;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 0.5rem;
                    font-size: 1.8rem;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>{message}</h1>
                <p>您可以关闭此窗口，返回终端继续操作</p>
            </div>
            <script>
                // 3秒后自动关闭窗口
                setTimeout(function() {{
                    window.close();
                }}, 3000);
            </script>
        </body>
        </html>
        """  # noqa: E501
        self._send_html_response(200, html_content)

    def _send_error_response(self, message: str) -> None:
        """发送错误响应页面"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>登录失败</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #f44336;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 0.5rem;
                    font-size: 1.8rem;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✗</div>
                <h1>{message}</h1>
                <p>请关闭窗口并重试</p>
            </div>
        </body>
        </html>
        """  # noqa: E501
        self._send_html_response(400, html_content)

    def _send_html_response(self, status_code: int, html_content: str) -> None:
        """发送 HTML 响应"""
        self.send_response(status_code)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-length", str(len(html_content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """重写日志方法，避免过多输出"""


class CallbackServer:
    """回调服务器管理类"""

    def __init__(self, start_port: int = 8081, max_attempts: int = 20) -> None:
        """
        初始化回调服务器

        Args:
            start_port: 起始端口号，默认 8081
            max_attempts: 最大尝试次数，默认 20

        """
        self.start_port = start_port
        self.max_attempts = max_attempts
        self.port = None
        self.server = None
        self.thread = None

    def _find_available_port(self) -> int:
        """
        查找可用端口

        Returns:
            可用的端口号

        Raises:
            RuntimeError: 如果找不到可用端口

        """
        for port in range(self.start_port, self.start_port + self.max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError:
                    logger.debug("端口 %d 被占用，尝试下一个", port)
                    continue
                else:
                    logger.info("找到可用端口: %d", port)
                    return port

        msg = f"无法找到可用端口 ({self.start_port}-{self.start_port + self.max_attempts})"
        raise RuntimeError(msg)

    def start(self) -> str:
        """启动服务器，返回回调 URL"""
        # 重置状态
        CallbackHandler.auth_result = {}
        CallbackHandler.auth_received.clear()

        # 查找可用端口
        self.port = self._find_available_port()

        # 创建服务器
        self.server = socketserver.TCPServer(("127.0.0.1", self.port), CallbackHandler)

        # 在新线程中启动服务器
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        callback_url = f"http://127.0.0.1:{self.port}/callback"
        logger.info("回调服务器已启动: %s", callback_url)
        return callback_url

    def wait_for_auth(self, timeout: int = 300) -> dict:
        """
        等待接收认证结果

        Args:
            timeout: 超时时间(秒)，默认 5 分钟

        Returns:
            认证结果字典

        """
        logger.info("等待用户完成登录...")
        success = CallbackHandler.auth_received.wait(timeout=timeout)

        if not success:
            logger.error("等待登录超时")
            return {"type": "error", "error": "timeout", "error_description": "登录超时"}

        return CallbackHandler.auth_result

    def stop(self) -> None:
        """停止服务器"""
        if self.server:
            logger.info("正在关闭回调服务器...")
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=2)
            logger.info("回调服务器已关闭")
