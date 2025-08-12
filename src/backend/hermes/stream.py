"""
Hermes 流处理模块

用于处理 SSE (Server-Sent Events) 流式数据和 MCP 事件
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

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
        # 跟踪状态消息去重
        self._last_status_message: str = ""
        self._should_ignore_flow_stop: bool = False

        # 增强的去重机制：跟踪事件类型和时间
        self._event_history: list[tuple[str, str, float]] = []  # (event_type, step_name, timestamp)
        self._event_dedup_window: float = 5.0  # 5秒去重窗口

        # 进度消息替换机制：跟踪当前工具的进度状态
        self._current_tool_progress: dict[str, dict[str, Any]] = {}  # step_id -> progress_info
        self._progress_message_types = {
            "step.init",
            "step.input",
            "step.output",
            "step.cancel",
            "step.error",
            "step.waiting_for_start",
            "step.waiting_for_param",
        }
        self._final_message_types = {
            "flow.success",
            "flow.failed",
            "flow.cancel",
        }

    def reset_status_tracking(self) -> None:
        """重置状态跟踪，用于新对话开始时"""
        self._last_status_message = ""
        self._should_ignore_flow_stop = False
        self._event_history.clear()
        self._current_tool_progress.clear()
        self.logger.debug("状态跟踪已重置")

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
        step_id = event.get_step_id()
        event_type = event.event_type
        content = event.get_content()

        # 基于步骤ID和事件类型的去重检查
        if not self._should_process_event(event_type, step_id):
            return None

        # 检查是否应该替换之前的进度消息
        should_replace = self._should_replace_progress(event, step_id)

        # 处理特殊的等待状态事件
        if event_type == "step.waiting_for_start":
            return self._format_waiting_for_start(content, step_name, step_id, should_replace=should_replace)

        if event_type == "step.waiting_for_param":
            return self._format_waiting_for_param(content, step_name, step_id, should_replace=should_replace)

        # 特殊处理 flow.stop：如果刚刚收到过等待事件，则忽略
        if event_type == "flow.stop":
            return self._handle_flow_stop()

        # 处理其他事件类型
        return self._format_standard_status(event_type, step_name, step_id, should_replace=should_replace)

    def _should_process_event(self, event_type: str, step_id: str) -> bool:
        """检查是否应该处理此事件（去重逻辑）"""
        current_time = time.time()
        event_key = f"{event_type}:{step_id or 'flow'}"

        # 详细调试日志
        self.logger.debug("处理事件: %s, 时间: %.3f", event_key, current_time)

        # 清理过期的事件历史（保留去重窗口内的事件）
        old_count = len(self._event_history)
        self._event_history = [
            (etype, sname, timestamp)
            for etype, sname, timestamp in self._event_history
            if current_time - timestamp < self._event_dedup_window
        ]
        new_count = len(self._event_history)
        if old_count != new_count:
            self.logger.debug("清理过期事件历史: %d -> %d", old_count, new_count)

        # 检查是否为重复事件（基于步骤ID而不是步骤名称）
        for hist_event_type, hist_step_id, timestamp in self._event_history:
            hist_key = f"{hist_event_type}:{hist_step_id or 'flow'}"
            if hist_key == event_key and current_time - timestamp < self._event_dedup_window:
                self.logger.debug("跳过重复事件: %s, 距离上次 %.2f 秒", event_key, current_time - timestamp)
                return False

        # 记录当前事件（使用步骤ID）
        self._event_history.append((event_type, step_id or "", current_time))
        self.logger.debug("记录新事件: %s, 历史记录数量: %d", event_key, len(self._event_history))
        return True

    def _format_waiting_for_start(
        self,
        content: dict[str, Any],
        step_name: str,
        step_id: str,
        *,
        should_replace: bool,
    ) -> str:
        """格式化等待开始执行的消息"""
        self._should_ignore_flow_stop = True  # 标记下一个 flow.stop 应该被忽略
        risk = content.get("risk", "unknown")
        reason = content.get("reason", "需要用户确认是否执行此工具")

        # 风险级别映射
        risk_info = {
            "low": "🟢 低风险",
            "medium": "🟡 中等风险",
            "high": "🔴 高风险",
        }.get(risk, "⚪ 风险等级未知")

        message = f"\n⏸️ **等待用户确认执行工具**\n\n🔧 工具名称: `{step_name}` {risk_info}\n\n💭 说明: {reason}\n"

        # 记录进度信息
        if step_id:
            self._current_tool_progress[step_id] = {
                "message": message,
                "should_replace": should_replace,
                "is_progress": True,
            }

        return message

    def _format_waiting_for_param(
        self,
        content: dict[str, Any],
        step_name: str,
        step_id: str,
        *,
        should_replace: bool,
    ) -> str:
        """格式化等待参数输入的消息"""
        self._should_ignore_flow_stop = True  # 标记下一个 flow.stop 应该被忽略
        message_content = content.get("message", "需要补充参数")
        message = f"\n📝 **等待用户输入参数**\n\n🔧 工具名称: `{step_name}`\n\n💭 说明: {message_content}\n"

        # 记录进度信息
        if step_id:
            self._current_tool_progress[step_id] = {
                "message": message,
                "should_replace": should_replace,
                "is_progress": True,
            }

        return message

    def _handle_flow_stop(self) -> str | None:
        """处理流停止事件"""
        if self._should_ignore_flow_stop:
            self.logger.debug("忽略 flow.stop 事件，因为刚刚收到等待用户操作事件")
            self._should_ignore_flow_stop = False  # 重置标记
            return None
        # 如果不是因为等待用户操作而暂停，则显示通用暂停消息
        message = "\n⏸️ **工作流已暂停**\n"
        if message == self._last_status_message:
            return None
        self._last_status_message = message
        return message

    def _format_standard_status(
        self,
        event_type: str,
        step_name: str,
        step_id: str,
        *,
        should_replace: bool,
    ) -> str | None:
        """格式化标准状态消息"""
        # 定义事件类型到状态消息的映射
        status_messages = {
            "step.init": f"\n🔧 正在初始化工具: `{step_name}`\n",
            "step.input": f"\n📥 工具 `{step_name}` 正在执行...\n",
            "step.output": f"\n✅ 工具 `{step_name}` 执行完成\n",
            "step.cancel": f"\n❌ 工具 `{step_name}` 已取消\n",
            "step.error": f"\n⚠️ 工具 `{step_name}` 执行失败\n",
            # 隐藏 flow.start 和 flow.success，只保留失败相关的状态
            # "flow.start": "\n🚀 **开始执行工作流**\n",  # 隐藏
            # "flow.success": "\n🎉 **工作流执行成功**\n",  # 隐藏
            "flow.failed": "\n💥 **工作流执行失败**\n",
            "flow.cancel": "\n🛑 **工作流已取消**\n",
        }

        base_message = status_messages.get(event_type)
        if not base_message:
            return None

        # 对于所有步骤相关的消息，都检查是否需要替换之前的进度
        if event_type in self._progress_message_types and step_id:
            base_message = self._handle_progress_message(
                event_type,
                step_name,
                step_id,
                base_message,
                should_replace=should_replace,
            )
        elif event_type in self._final_message_types and step_id:
            # 这是一个流级别的最终状态消息，清理对应的进度信息
            self._current_tool_progress.pop(step_id, None)

        # 检查是否与上一次的状态消息相同，避免重复输出
        if base_message == self._last_status_message:
            self.logger.debug("跳过重复的状态消息: %s", base_message.strip())
            return None

        self._last_status_message = base_message
        return base_message

    def _handle_progress_message(
        self,
        event_type: str,
        step_name: str,
        step_id: str,
        base_message: str,
        *,
        should_replace: bool,
    ) -> str:
        """处理进度消息的替换逻辑"""
        # 检查是否为最终状态消息
        is_final_state = event_type in {"step.output", "step.cancel", "step.error"}

        # 关键修复：使用工具名称而不是step_id来跟踪，确保同一工具的后续状态更新能够替换之前的进度
        # 策略：如果是同一个工具名称的后续消息，就应该替换之前的消息
        has_previous_progress = step_name in self._current_tool_progress

        # 这是一个进度消息，记录到跟踪字典中（使用工具名称作为key）
        if not is_final_state:
            self._current_tool_progress[step_name] = {
                "message": base_message,
                "should_replace": should_replace,
                "is_progress": True,
                "step_id": step_id,  # 保留step_id用于调试
            }

        # 核心修复：所有的MCP进度消息都应该标记为MCP状态，而不仅仅是需要替换的消息
        # 使用工具名称作为标识，确保TUI层面能正确识别为MCP消息
        if has_previous_progress:
            # 如果有之前的进度，说明这是一个状态更新，需要替换
            base_message = f"[REPLACE:{step_name}]{base_message}"
            if is_final_state:
                self.logger.debug("添加替换标记给最终状态消息，工具 %s: %s", step_name, event_type)
                # 清理对应的进度信息
                self._current_tool_progress.pop(step_name, None)
            else:
                self.logger.debug("添加替换标记给工具 %s: %s", step_name, event_type)
        else:
            # 如果是第一个进度消息，添加MCP标记但不替换
            base_message = f"[MCP:{step_name}]{base_message}"
            self.logger.debug("添加MCP标记给首次进度消息，工具 %s: %s", step_name, event_type)

        return base_message

    def _should_replace_progress(self, event: HermesStreamEvent, step_id: str | None) -> bool:
        """判断是否应该替换之前的进度消息"""
        step_name = event.get_step_name()
        if not step_name:
            return False

        event_type = event.event_type

        # 对于进度消息类型，只要存在同一个工具名称的之前记录，就应该替换
        # 这确保了同一个工具的状态更新会依次替换，而不是累积
        if event_type in self._progress_message_types and step_name in self._current_tool_progress:
            prev_info = self._current_tool_progress[step_name]
            if prev_info.get("is_progress", False):
                self.logger.debug(
                    "工具 %s 的进度消息将被替换: %s -> %s",
                    step_name,
                    prev_info.get("message", "").strip()[:50],
                    event_type,
                )
                return True

        return False

    def get_replacement_info(self, step_id: str) -> dict[str, Any] | None:
        """获取指定步骤的替换信息"""
        return self._current_tool_progress.get(step_id)
