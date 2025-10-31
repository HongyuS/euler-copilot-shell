"""
浏览器登录功能

实现通过浏览器跳转进行 openEuler Intelligence 登录
"""

import json
import sys
import urllib.request
import webbrowser

from config.manager import ConfigManager
from i18n.manager import _
from log.manager import get_logger

from .callback_server import CallbackServer

logger = get_logger(__name__)

# HTTP 状态码常量
HTTP_OK = 200


def get_auth_url(base_url: str, callback_url: str) -> str | None:
    """
    从后端获取授权 URL

    Args:
        base_url: openEuler Intelligence 的基础 URL
        callback_url: 本地回调 URL

    Returns:
        授权 URL，如果获取失败则返回 None

    """
    # 移除末尾的斜杠
    base_url = base_url.rstrip("/")

    # 构建请求 URL
    request_url = f"{base_url}/api/auth/redirect?action=login&callback_url={callback_url}"
    logger.info("请求授权 URL: %s", request_url)

    # 验证 URL 协议
    if not request_url.startswith(("http://", "https://")):
        logger.error("无效的 URL 协议: %s", request_url)
        return None

    try:
        # 发送 HTTP GET 请求
        with urllib.request.urlopen(request_url, timeout=10) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
            logger.debug("后端响应: %s", data)

            # 检查响应格式
            if data.get("code") == HTTP_OK and "result" in data:
                auth_url = data["result"].get("url")
                if auth_url:
                    logger.info("获取到授权 URL: %s", auth_url)
                    return auth_url
                logger.error("响应中缺少 result.url 字段")
                return None

            logger.error("后端返回错误: %s", data.get("message", "未知错误"))
            return None

    except Exception as e:
        logger.exception("获取授权 URL 失败")
        sys.stderr.write(_("✗ Failed to get authorization URL: {error}\n").format(error=e))
        return None


def browser_login() -> None:
    """
    执行浏览器登录流程

    1. 从配置读取 openEuler Intelligence 的地址
    2. 启动本地回调服务器
    3. 构建授权 URL 并打开浏览器
    4. 等待用户完成登录并接收 ECSESSION
    5. 保存 ECSESSION 到配置文件

    """
    logger.info("开始浏览器登录流程")

    # 加载配置
    config_manager = ConfigManager()
    base_url = config_manager.get_eulerintelli_url()

    if not base_url:
        sys.stdout.write(
            _("✗ Error: openEuler Intelligence URL not configured\n")
            + _("Please run deployment initialization first: oi --init\n"),
        )
        sys.exit(1)

    logger.info("使用 openEuler Intelligence URL: %s", base_url)

    # 启动回调服务器（自动查找可用端口）
    callback_server = CallbackServer()

    try:
        # 启动回调服务器
        callback_url = callback_server.start()

        # 从后端获取授权 URL
        sys.stdout.write(_("Getting authorization URL from server...\n"))
        auth_url = get_auth_url(base_url, callback_url)

        if not auth_url:
            sys.stdout.write(_("✗ Failed to get authorization URL\n"))
            sys.exit(1)

        logger.info("授权 URL: %s", auth_url)

        # 打开浏览器
        sys.stdout.write(_("Opening browser for login...\n"))
        sys.stdout.write(_("If the browser doesn't open automatically, please visit:\n"))
        sys.stdout.write(f"  {auth_url}\n\n")
        sys.stdout.flush()

        webbrowser.open(auth_url)

        # 等待回调
        sys.stdout.write(_("Waiting for login to complete...\n"))
        auth_result = callback_server.wait_for_auth(timeout=300)

        # 处理认证结果
        success, error_msg = _process_auth_result(auth_result, config_manager)

        if success:
            sys.stdout.write(_("✓ Login successful!\n"))
            sys.stdout.write(_("✓ API Key has been saved to configuration\n"))
            sys.exit(0)
        else:
            sys.stdout.write(_("✗ Login failed: {error}\n").format(error=error_msg))
            sys.exit(1)

    except Exception as e:
        logger.exception("登录过程中发生错误")
        sys.stdout.write(_("✗ An error occurred during login: {error}\n").format(error=e))
        sys.exit(1)
    finally:
        # 确保关闭服务器
        callback_server.stop()


def _process_auth_result(auth_result: dict, config_manager: ConfigManager) -> tuple[bool, str | None]:
    """
    处理认证结果

    Args:
        auth_result: 从回调服务器接收到的认证结果
        config_manager: 配置管理器实例

    Returns:
        (是否成功, 错误消息)

    """
    result_type = auth_result.get("type")

    if result_type == "error":
        error = auth_result.get("error", "unknown")
        error_desc = auth_result.get("error_description", "未知错误")
        logger.error("认证失败: %s - %s", error, error_desc)
        return False, error_desc

    if result_type == "session":
        # 直接获得 sessionId（即 ECSESSION）
        session_id = auth_result.get("sessionId")
        if session_id:
            # 保存 ECSESSION 作为 API Key
            config_manager.set_eulerintelli_key(session_id)
            logger.info("已保存 API Key 到配置")
            return True, None

        return False, "未收到有效的 session ID"

    return False, f"未知的认证结果类型: {result_type}"
