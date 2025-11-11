"""Hermes 数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HermesAgent:
    """Hermes 智能体数据结构"""

    app_id: str
    """应用ID"""

    name: str
    """智能体名称"""

    author: str
    """作者"""

    description: str
    """描述"""

    icon: str
    """图标"""

    favorited: bool
    """是否已收藏"""

    published: bool = True
    """是否已发布"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HermesAgent:
        """从字典创建智能体对象"""
        return cls(
            app_id=data.get("appId", ""),
            name=data.get("name", ""),
            author=data.get("author", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            favorited=data.get("favorited", False),
            published=data.get("published", True),
        )


class HermesMessage:
    """Hermes 消息类"""

    def __init__(self, role: str, content: str) -> None:
        """初始化 Hermes 消息"""
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role, "content": self.content}


class HermesApp:
    """Hermes 应用配置"""

    def __init__(
        self,
        app_id: str,
        flow_id: str = "",
        *,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        初始化应用配置

        Args:
            app_id: 应用ID
            flow_id: 流ID
            params: MCP 响应参数
                - 对于 MCP 确认消息: {"confirm": true/false}
                - 对于参数补全: 包含补全参数的字典

        """
        self.app_id = app_id
        self.flow_id = flow_id
        self.params = params

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        app_dict: dict[str, Any] = {
            "appId": self.app_id,
            "flowId": self.flow_id,
        }

        # 如果有 MCP 响应参数，直接使用 params 的值
        if self.params is not None:
            app_dict["params"] = self.params
        else:
            # 没有 params 时，添加空的 params 字段（保持向后兼容）
            app_dict["params"] = {}

        return app_dict


class HermesChatRequest:
    """Hermes Chat 请求类"""

    def __init__(  # noqa: PLR0913
        self,
        app: HermesApp,
        question: str,
        conversation_id: str = "",
        language: str = "zh",
        llm_id: str = "",
        kb_ids: list[str] | None = None,
    ) -> None:
        """
        初始化 Hermes Chat 请求

        Args:
            app: 应用配置
            question: 用户问题
            conversation_id: 会话ID
            language: 语言
            llm_id: 大模型ID
            kb_ids: 知识库ID列表

        """
        self.app = app
        self.conversation_id = conversation_id
        self.question = question
        self.language = language
        self.llm_id = llm_id
        self.kb_ids = kb_ids or []

    def to_dict(self) -> dict[str, Any]:
        """转换为请求字典格式"""
        request_dict: dict[str, Any] = {
            "question": self.question,
            "language": self.language,
            "llmId": self.llm_id,
        }

        if self.app and self.app.app_id:
            request_dict["app"] = self.app.to_dict()

        if self.conversation_id:
            request_dict["conversationId"] = self.conversation_id

        if self.kb_ids:
            request_dict["kbIds"] = self.kb_ids

        return request_dict
