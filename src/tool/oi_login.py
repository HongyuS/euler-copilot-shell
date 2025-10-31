"""
浏览器登录功能

实现通过浏览器跳转进行 openEuler Intelligence 登录
"""

import sys
import webbrowser

from config.manager import ConfigManager
from i18n.manager import _
from log.manager import get_logger

from .callback_server import CallbackServer

logger = get_logger(__name__)


def build_auth_url(base_url: str, callback_url: str) -> str:
    """
    构建授权 URL

    根据 openEuler Intelligence 的 base_url 和回调地址构建登录 URL

    Args:
        base_url: openEuler Intelligence 的基础 URL
        callback_url: 本地回调 URL

    Returns:
        完整的授权 URL

    """
    # 移除末尾的斜杠
    base_url = base_url.rstrip("/")

    # 构建授权 URL
    # 根据 API 规范: GET /api/auth/redirect?action=login
    return f"{base_url}/api/auth/redirect?action=login&callback_url={callback_url}"


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

        # 构建授权 URL
        auth_url = build_auth_url(base_url, callback_url)
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
