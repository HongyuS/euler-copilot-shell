"""应用入口点"""

import argparse
import asyncio
import atexit
import sys

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
from tool.oi_backend_init import oi_backend_init
from tool.oi_select_agent import select_agent


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="openEuler Intelligence")
    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化 openEuler Intelligence 后端",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="选择默认智能体",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="显示最新的日志内容（最多1000行）",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="设置日志级别",
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
        oi_backend_init()
        return

    if args.agent:
        asyncio.run(select_agent())
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
