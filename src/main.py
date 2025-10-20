"""应用入口点"""

import argparse
import asyncio
import atexit
import sys

from __version__ import __version__
from app.tui import IntelligentTerminal
from config.manager import ConfigManager
from config.model import LogLevel
from log.manager import (
    cleanup_empty_logs,
    disable_console_output,
    enable_console_output,
    get_latest_logs,
    get_logger,
    setup_logging,
)
from tool import backend_init, llm_config, select_agent


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="oi",
        description="openEuler Intelligence - 智能命令行工具",
        epilog="""
更多信息和使用文档请访问:
  https://gitee.com/openeuler/euler-copilot-shell/tree/master/docs
        """,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )

    # 通用选项组
    general_group = parser.add_argument_group(
        "通用选项",
        "显示帮助信息和版本信息",
    )
    general_group.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示此帮助信息并退出",
    )
    general_group.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示程序版本号并退出",
    )

    # 后端配置选项组
    backend_group = parser.add_argument_group(
        "后端配置选项",
        "用于初始化和配置 openEuler Intelligence 后端服务",
    )
    backend_group.add_argument(
        "--init",
        action="store_true",
        help="初始化 openEuler Intelligence 后端\n * 初始化操作需要管理员权限和网络连接",
    )
    backend_group.add_argument(
        "--llm-config",
        action="store_true",
        help="更改 openEuler Intelligence 大模型设置（需要有效的本地后端服务）\n * 配置编辑操作需要管理员权限",
    )

    # 应用配置选项组
    app_group = parser.add_argument_group(
        "应用配置选项",
        "用于配置应用前端行为和偏好设置",
    )
    app_group.add_argument(
        "--agent",
        action="store_true",
        help="选择默认智能体",
    )

    # 日志管理选项组
    log_group = parser.add_argument_group(
        "日志管理选项",
        "用于查看和配置日志输出",
    )
    log_group.add_argument(
        "--logs",
        action="store_true",
        help="显示最新的日志内容（最多1000行）",
    )
    log_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="设置日志级别 (可选: DEBUG, INFO, WARNING, ERROR)",
    )

    # 注册清理函数，确保在程序异常退出时也能清理空日志文件
    atexit.register(cleanup_empty_logs)

    return parser.parse_args()


def show_logs() -> None:
    """显示最新的日志内容"""
    # 初始化配置和日志系统
    config_manager = ConfigManager()
    setup_logging(config_manager)
    # 显示日志时启用控制台输出
    enable_console_output()

    try:
        log_lines = get_latest_logs(max_lines=1000)
        for line in log_lines:
            # 直接输出到标准输出，保持原有的日志格式
            sys.stdout.write(line.rstrip() + "\n")
    except (OSError, RuntimeError) as e:
        sys.stderr.write(f"获取日志失败: {e}\n")
        sys.exit(1)


def set_log_level(config_manager: ConfigManager, level: str) -> None:
    """设置日志级别"""
    if level not in LogLevel.__members__:
        sys.stderr.write(f"无效的日志级别: {level}\n")
        sys.exit(1)
    config_manager.set_log_level(LogLevel(level))

    # 初始化日志系统并验证设置
    setup_logging(config_manager)
    enable_console_output()  # 启用控制台输出以显示验证信息

    logger = get_logger(__name__)
    logger.info("日志级别已设置为: %s", level)
    logger.debug("这是一条 DEBUG 级别的测试消息")
    logger.info("这是一条 INFO 级别的测试消息")
    logger.warning("这是一条 WARNING 级别的测试消息")
    logger.error("这是一条 ERROR 级别的测试消息")

    sys.stdout.write(f"✓ 日志级别已成功设置为: {level}\n")
    sys.stdout.write("✓ 日志系统初始化完成\n")


def main() -> None:
    """主函数"""
    args = parse_args()

    if args.logs:
        show_logs()
        return

    if args.init:
        backend_init()
        return

    if args.agent:
        asyncio.run(select_agent())
        return

    if args.llm_config:
        llm_config()
        return

    # 初始化配置和日志系统
    config_manager = ConfigManager()

    # 处理命令行参数设置的日志级别
    if args.log_level:
        set_log_level(config_manager, args.log_level)
        return

    setup_logging(config_manager)
    # 在 TUI 模式下禁用控制台日志输出，避免干扰界面
    disable_console_output()

    logger = get_logger(__name__)

    try:
        app = IntelligentTerminal()
        app.run()
    except Exception:
        logger.exception("智能 Shell 应用发生致命错误")
        raise


if __name__ == "__main__":
    sys.exit(main() or 0)
