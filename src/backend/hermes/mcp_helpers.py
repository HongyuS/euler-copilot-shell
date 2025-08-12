"""
MCP (Model Context Protocol) 相关常量定义

统一管理所有 MCP 状态消息、指示符和标记，确保代码的一致性和可维护性。
"""

from __future__ import annotations

import re
from typing import ClassVar


# MCP 状态标记
class MCPTags:
    """MCP 消息标记常量"""

    MCP_PREFIX = "[MCP:"
    REPLACE_PREFIX = "[REPLACE:"
    TAG_SUFFIX = "]"


# MCP 状态表情符号
class MCPEmojis:
    """MCP 状态表情符号常量"""

    INIT = "🔧"
    INPUT = "📥"
    OUTPUT = "✅"
    CANCEL = "❌"
    ERROR = "⚠️"
    WAITING_START = "⏸️"
    WAITING_PARAM = "📝"


# MCP 状态文本片段
class MCPTextFragments:
    """MCP 状态文本片段常量"""

    INIT_TOOL = "正在初始化工具"
    TOOL_WORD = "工具"
    EXECUTING = "正在执行..."
    COMPLETED = "执行完成"
    CANCELLED = "已取消"
    FAILED = "执行失败"
    WAITING_CONFIRM = "**等待用户确认执行工具**"
    WAITING_PARAM = "**等待用户输入参数**"


# MCP 完整状态消息模板
class MCPMessageTemplates:
    """MCP 状态消息模板常量"""

    # 基础状态指示符（用于识别）
    INIT_INDICATOR = f"{MCPEmojis.INIT} {MCPTextFragments.INIT_TOOL}"
    INPUT_INDICATOR = f"{MCPEmojis.INPUT} {MCPTextFragments.TOOL_WORD}"
    EXECUTING_INDICATOR = MCPTextFragments.EXECUTING
    OUTPUT_INDICATOR = f"{MCPEmojis.OUTPUT} {MCPTextFragments.TOOL_WORD}"
    COMPLETED_INDICATOR = MCPTextFragments.COMPLETED
    CANCEL_INDICATOR = f"{MCPEmojis.CANCEL} {MCPTextFragments.TOOL_WORD}"
    CANCELLED_INDICATOR = MCPTextFragments.CANCELLED
    ERROR_INDICATOR = f"{MCPEmojis.ERROR} {MCPTextFragments.TOOL_WORD}"
    FAILED_INDICATOR = MCPTextFragments.FAILED
    WAITING_START_INDICATOR = f"{MCPEmojis.WAITING_START} {MCPTextFragments.WAITING_CONFIRM}"
    WAITING_PARAM_INDICATOR = f"{MCPEmojis.WAITING_PARAM} {MCPTextFragments.WAITING_PARAM}"

    # 完整状态消息模板（用于生成）
    @staticmethod
    def init_message(tool_name: str) -> str:
        """生成工具初始化消息"""
        return f"\n{MCPEmojis.INIT} {MCPTextFragments.INIT_TOOL}: `{tool_name}`\n"

    @staticmethod
    def input_message(tool_name: str) -> str:
        """生成工具执行中消息"""
        return f"\n{MCPEmojis.INPUT} {MCPTextFragments.TOOL_WORD} `{tool_name}` {MCPTextFragments.EXECUTING}\n"

    @staticmethod
    def output_message(tool_name: str) -> str:
        """生成工具执行完成消息"""
        return f"\n{MCPEmojis.OUTPUT} {MCPTextFragments.TOOL_WORD} `{tool_name}` {MCPTextFragments.COMPLETED}\n"

    @staticmethod
    def cancel_message(tool_name: str) -> str:
        """生成工具取消消息"""
        return f"\n{MCPEmojis.CANCEL} {MCPTextFragments.TOOL_WORD} `{tool_name}` {MCPTextFragments.CANCELLED}\n"

    @staticmethod
    def error_message(tool_name: str) -> str:
        """生成工具执行失败消息"""
        return f"\n{MCPEmojis.ERROR} {MCPTextFragments.TOOL_WORD} `{tool_name}` {MCPTextFragments.FAILED}\n"

    @staticmethod
    def waiting_start_message(tool_name: str, risk_info: str, reason: str) -> str:
        """生成等待用户确认消息"""
        return (
            f"\n{MCPEmojis.WAITING_START} {MCPTextFragments.WAITING_CONFIRM}\n\n"
            f"{MCPEmojis.INIT} {MCPTextFragments.TOOL_WORD}名称: `{tool_name}` {risk_info}\n\n💭 说明: {reason}\n"
        )

    @staticmethod
    def waiting_param_message(tool_name: str, message_content: str) -> str:
        """生成等待参数输入消息"""
        return (
            f"\n{MCPEmojis.WAITING_PARAM} {MCPTextFragments.WAITING_PARAM}\n\n"
            f"{MCPEmojis.INIT} {MCPTextFragments.TOOL_WORD}名称: `{tool_name}`\n\n💭 说明: {message_content}\n"
        )


# MCP 状态指示符列表（用于识别和检测）
class MCPIndicators:
    """MCP 状态指示符列表常量"""

    # 所有状态指示符（用于通用检测）
    ALL_INDICATORS: ClassVar[list[str]] = [
        MCPMessageTemplates.INIT_INDICATOR,
        MCPMessageTemplates.INPUT_INDICATOR,
        MCPMessageTemplates.EXECUTING_INDICATOR,
        MCPMessageTemplates.WAITING_START_INDICATOR,
        MCPMessageTemplates.WAITING_PARAM_INDICATOR,
        MCPMessageTemplates.OUTPUT_INDICATOR,
        MCPMessageTemplates.COMPLETED_INDICATOR,
        MCPMessageTemplates.CANCEL_INDICATOR,
        MCPMessageTemplates.CANCELLED_INDICATOR,
        MCPMessageTemplates.ERROR_INDICATOR,
        MCPMessageTemplates.FAILED_INDICATOR,
    ]

    # 最终状态指示符（用于检测工具执行结束）
    FINAL_INDICATORS: ClassVar[list[str]] = [
        MCPMessageTemplates.OUTPUT_INDICATOR,
        MCPMessageTemplates.COMPLETED_INDICATOR,
        MCPMessageTemplates.CANCEL_INDICATOR,
        MCPMessageTemplates.CANCELLED_INDICATOR,
        MCPMessageTemplates.ERROR_INDICATOR,
        MCPMessageTemplates.FAILED_INDICATOR,
    ]

    # 进度状态指示符（用于UI快速检测）
    PROGRESS_INDICATORS: ClassVar[list[str]] = [
        MCPEmojis.INIT,
        MCPEmojis.INPUT,
        MCPEmojis.OUTPUT,
        MCPEmojis.CANCEL,
        MCPEmojis.ERROR,
    ]


# MCP 事件类型映射
class MCPEventTypes:
    """MCP 事件类型常量"""

    STEP_INIT = "step.init"
    STEP_INPUT = "step.input"
    STEP_OUTPUT = "step.output"
    STEP_CANCEL = "step.cancel"
    STEP_ERROR = "step.error"
    STEP_WAITING_FOR_START = "step.waiting_for_start"
    STEP_WAITING_FOR_PARAM = "step.waiting_for_param"

    # 所有步骤事件类型
    ALL_STEP_EVENTS: ClassVar[set[str]] = {
        STEP_INIT,
        STEP_INPUT,
        STEP_OUTPUT,
        STEP_CANCEL,
        STEP_ERROR,
        STEP_WAITING_FOR_START,
        STEP_WAITING_FOR_PARAM,
    }

    # 最终状态事件类型
    FINAL_STATE_EVENTS: ClassVar[set[str]] = {
        STEP_OUTPUT,
        STEP_CANCEL,
        STEP_ERROR,
    }

    # 进度消息事件类型
    PROGRESS_MESSAGE_EVENTS: ClassVar[set[str]] = ALL_STEP_EVENTS


# 风险级别相关常量
class MCPRiskLevels:
    """MCP 工具风险级别常量"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"

    # 风险级别显示映射
    RISK_DISPLAY_MAP: ClassVar[dict[str, str]] = {
        LOW: "🟢 低风险",
        MEDIUM: "🟡 中等风险",
        HIGH: "🔴 高风险",
        UNKNOWN: "⚪ 风险等级未知",
    }

    @classmethod
    def get_risk_display(cls, risk_level: str) -> str:
        """获取风险级别的显示文本"""
        return cls.RISK_DISPLAY_MAP.get(risk_level, cls.RISK_DISPLAY_MAP[cls.UNKNOWN])


# MCP 消息类型枚举
class MCPMessageType:
    """MCP 消息类型常量"""

    NORMAL = "normal"  # 普通消息
    MCP_TAGGED = "mcp_tagged"  # 带有 [MCP:] 标记的消息
    REPLACE_TAGGED = "replace_tagged"  # 带有 [REPLACE:] 标记的消息
    PROGRESS = "progress"  # 进度状态消息
    FINAL = "final"  # 最终状态消息


# 工具函数
def is_mcp_message(content: str) -> bool:
    """检查内容是否为 MCP 状态消息"""
    # 检查是否包含 MCP 标记
    if MCPTags.MCP_PREFIX in content or MCPTags.REPLACE_PREFIX in content:
        return True

    # 检查是否包含任何 MCP 状态指示符
    return any(indicator in content for indicator in MCPIndicators.ALL_INDICATORS)


def is_final_mcp_message(content: str) -> bool:
    """检查内容是否为最终状态的 MCP 消息"""
    return any(indicator in content for indicator in MCPIndicators.FINAL_INDICATORS)


def is_progress_message(content: str) -> bool:
    """检查内容是否为进度状态消息"""
    # 检查是否包含进度表情符号
    if any(emoji in content for emoji in MCPIndicators.PROGRESS_INDICATORS):
        return True

    # 检查是否包含 MCP 或 REPLACE 标记
    return MCPTags.MCP_PREFIX in content or MCPTags.REPLACE_PREFIX in content


def classify_mcp_message(content: str) -> str:
    """分类 MCP 消息类型"""
    if MCPTags.REPLACE_PREFIX in content:
        return MCPMessageType.REPLACE_TAGGED

    if MCPTags.MCP_PREFIX in content:
        return MCPMessageType.MCP_TAGGED

    if is_final_mcp_message(content):
        return MCPMessageType.FINAL

    if is_progress_message(content):
        return MCPMessageType.PROGRESS

    return MCPMessageType.NORMAL


def extract_mcp_tag(content: str) -> tuple[str | None, str]:
    """从内容中提取 MCP 标记并返回清理后的内容"""
    # 构建 REPLACE 标记的正则表达式
    replace_prefix = re.escape(MCPTags.REPLACE_PREFIX)
    tag_suffix = re.escape(MCPTags.TAG_SUFFIX)
    replace_pattern = f"{replace_prefix}([^{tag_suffix}]+){tag_suffix}"

    replace_match = re.search(replace_pattern, content)
    if replace_match:
        tool_name = replace_match.group(1)
        cleaned_content = re.sub(replace_pattern, "", content).strip()
        return tool_name, cleaned_content

    # 构建 MCP 标记的正则表达式
    mcp_prefix = re.escape(MCPTags.MCP_PREFIX)
    mcp_pattern = f"{mcp_prefix}([^{tag_suffix}]+){tag_suffix}"

    mcp_match = re.search(mcp_pattern, content)
    if mcp_match:
        tool_name = mcp_match.group(1)
        cleaned_content = re.sub(mcp_pattern, "", content).strip()
        return tool_name, cleaned_content

    return None, content


def create_mcp_tag(tool_name: str, *, is_replace: bool = False) -> str:
    """创建 MCP 标记字符串"""
    prefix = MCPTags.REPLACE_PREFIX if is_replace else MCPTags.MCP_PREFIX
    return f"{prefix}{tool_name}{MCPTags.TAG_SUFFIX}"


def format_error_message(error_text: str) -> str:
    """格式化错误消息"""
    return f"{MCPEmojis.ERROR} {error_text}"


def format_tool_message(tool_name: str, status: str, *, use_emoji: bool = True) -> str:
    """格式化工具状态消息"""
    emoji_map = {
        "init": MCPEmojis.INIT,
        "executing": MCPEmojis.INPUT,
        "completed": MCPEmojis.OUTPUT,
        "cancelled": MCPEmojis.CANCEL,
        "failed": MCPEmojis.ERROR,
    }

    if use_emoji and status in emoji_map:
        return f"{emoji_map[status]} {MCPTextFragments.TOOL_WORD} `{tool_name}` {status}"

    return f"{MCPTextFragments.TOOL_WORD} `{tool_name}` {status}"


def clean_content_for_display(content: str) -> str:
    """清理内容以用于显示，移除所有 MCP 标记"""
    # 构建正则表达式组件
    replace_prefix = re.escape(MCPTags.REPLACE_PREFIX)
    mcp_prefix = re.escape(MCPTags.MCP_PREFIX)
    tag_suffix = re.escape(MCPTags.TAG_SUFFIX)

    # 移除 REPLACE 标记
    replace_pattern = f"{replace_prefix}[^{tag_suffix}]+{tag_suffix}"
    content = re.sub(replace_pattern, "", content)

    # 移除 MCP 标记
    mcp_pattern = f"{mcp_prefix}[^{tag_suffix}]+{tag_suffix}"
    content = re.sub(mcp_pattern, "", content)

    return content.strip()
