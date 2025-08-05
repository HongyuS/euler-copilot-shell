"""应用入口点"""

import argparse
import atexit
import sys

from app.tui import IntelligentTerminal
from log.manager import (
    cleanup_empty_logs,
    disable_console_output,
    enable_console_output,
    get_latest_logs,
    get_logger,
    setup_logging,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="openEuler 智能 Shell")
    parser.add_argument(
        "--logs",
        action="store_true",
        help="显示最新的日志内容（最多1000行）",
    )
    return parser.parse_args()


def show_logs() -> None:
    """显示最新的日志内容"""
    # 初始化日志系统以确保日志管理器可用
    setup_logging()
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


def main() -> None:
    """主函数"""
    args = parse_args()

    if args.logs:
        show_logs()
        return

    # 初始化日志系统
    setup_logging()
    # 在 TUI 模式下禁用控制台日志输出，避免干扰界面
    disable_console_output()

    logger = get_logger(__name__)

    # 注册退出时清理空日志文件
    atexit.register(cleanup_empty_logs)

    try:
        app = IntelligentTerminal()
        app.run()
    except Exception:
        logger.exception("智能 Shell 应用发生致命错误")
        raise


if __name__ == "__main__":
    sys.exit(main() or 0)
