"""Hermes 流事件处理器"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from log.manager import get_logger

if TYPE_CHECKING:
    from typing import Any


class HermesStreamEvent:
    """Hermes 流事件类"""

    def __init__(self, event_type: str, data: dict[str, Any]) -> None:
        """初始化流事件"""
        self.event_type = event_type
        self.data = data

    @classmethod
    def from_line(cls, line: str) -> HermesStreamEvent | None:
        """从 SSE 行解析事件"""
        line = line.strip()
        if not line.startswith("data: "):
            return None

        data_str = line[6:]  # 去掉 "data: " 前缀

        # 处理特殊字段
        special_events = {
            "[DONE]": ("done", {}),
            "[ERROR]": ("error", {"error": "Backend error occurred"}),
            "[SENSITIVE]": ("sensitive", {"message": "Content contains sensitive information"}),
            '{"event": "heartbeat"}': ("heartbeat", {}),
        }

        if data_str in special_events:
            event_type, data = special_events[data_str]
            return cls(event_type, data)

        try:
            data = json.loads(data_str)
            event_type = data.get("event", "unknown")
            return cls(event_type, data)
        except json.JSONDecodeError:
            return None

    def get_text_content(self) -> str | None:
        """获取文本内容"""
        if self.event_type == "text.add":
            return self.data.get("content", {}).get("text", "")
        if self.event_type == "step.output":
            content = self.data.get("content", {})
            if "text" in content:
                return content["text"]
        return None

    def get_flow_info(self) -> dict[str, Any]:
        """获取流信息"""
        return self.data.get("flow", {})

    def get_step_name(self) -> str:
        """获取步骤名称"""
        flow = self.get_flow_info()
        return flow.get("stepName", "")

    def get_step_id(self) -> str:
        """获取步骤ID"""
        flow = self.get_flow_info()
        return flow.get("stepId", "")

    def get_conversation_id(self) -> str:
        """获取会话ID"""
        return self.data.get("conversationId", "")

    def get_task_id(self) -> str:
        """获取任务ID"""
        return self.data.get("taskId", "")

    def get_content(self) -> dict[str, Any]:
        """获取内容部分"""
        return self.data.get("content", {})

    def is_mcp_step_event(self) -> bool:
        """判断是否为 MCP 步骤相关事件"""
        step_events = {
            "step.init",
            "step.input",
            "step.output",
            "step.cancel",
            "step.error",
            "step.waiting_for_start",
            "step.waiting_for_param",
        }
        return self.event_type in step_events

    def is_flow_event(self) -> bool:
        """判断是否为流相关事件"""
        flow_events = {
            "flow.start",
            "flow.stop",
            "flow.failed",
            "flow.success",
            "flow.cancel",
        }
        return self.event_type in flow_events


class HermesStreamProcessor:
    """Hermes 流响应处理器"""

    def __init__(self) -> None:
        """初始化流处理器"""
        self.logger = get_logger(__name__)

    def handle_special_events(self, event: HermesStreamEvent) -> tuple[bool, str | None]:
        """处理特殊事件类型，返回(是否中断, 中断消息)"""
        if event.event_type == "done":
            self.logger.debug("收到完成事件，结束流式响应")
            return True, None

        if event.event_type == "error":
            self.logger.error("收到后端错误事件: %s", event.data.get("error", "Unknown error"))
            return True, "后端服务出现错误，请稍后重试。"

        if event.event_type == "sensitive":
            self.logger.warning("收到敏感内容事件: %s", event.data.get("message", "Sensitive content detected"))
            return True, "响应内容包含敏感信息，已被系统屏蔽。"

        return False, None

    def log_text_content(self, text_content: str) -> None:
        """记录文本内容到日志"""
        max_log_length = 100
        display_text = text_content[:max_log_length] + "..." if len(text_content) > max_log_length else text_content
        self.logger.debug("产生文本内容: %s", display_text)

    def get_no_content_message(self, event_count: int) -> str:
        """获取无内容时的消息"""
        self.logger.warning(
            "流式响应完成但未产生任何文本内容 - 事件总数: %d",
            event_count,
        )
        return "服务暂时无法响应，请稍后重试。"

    def format_mcp_status(self, event: HermesStreamEvent) -> str | None:
        """格式化 MCP 状态信息为可读文本"""
        if not event.is_mcp_step_event() and not event.is_flow_event():
            return None

        step_name = event.get_step_name()
        event_type = event.event_type

        # 定义事件类型到状态消息的映射
        status_messages = {
            "step.init": f"🔧 正在初始化工具: {step_name}",
            "step.input": f"📥 工具 {step_name} 正在执行...",
            "step.output": f"✅ 工具 {step_name} 执行完成",
            "step.cancel": f"❌ 工具 {step_name} 已取消",
            "step.error": f"⚠️ 工具 {step_name} 执行失败",
            "flow.start": "🚀 开始执行工作流",
            "flow.stop": "⏸️ 工作流已暂停，等待用户操作",
            "flow.success": "🎉 工作流执行成功",
            "flow.failed": "💥 工作流执行失败",
            "flow.cancel": "🛑 工作流已取消",
        }

        return status_messages.get(event_type)
