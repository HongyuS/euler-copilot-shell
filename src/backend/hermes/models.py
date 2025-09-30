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


class HermesFeatures:
    """Hermes 功能特性配置"""

    def __init__(self, max_tokens: int = 8192, context_num: int = 10) -> None:
        """初始化功能特性配置"""
        self.max_tokens = max_tokens
        self.context_num = context_num

    def to_dict(self) -> dict[str, int]:
        """转换为字典格式"""
        return {
            "max_tokens": self.max_tokens,
            "context_num": self.context_num,
        }


class HermesApp:
    """Hermes 应用配置"""

    def __init__(self, app_id: str, flow_id: str = "") -> None:
        """初始化应用配置"""
        self.app_id = app_id
        self.flow_id = flow_id

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "appId": self.app_id,
            "auth": {},
            "flowId": self.flow_id,
            "params": {},
        }


class HermesChatRequest:
    """Hermes Chat 请求类"""

    def __init__(
        self,
        app: HermesApp,
        conversation_id: str,
        question: str,
        features: HermesFeatures | None = None,
        language: str = "zh_cn",
    ) -> None:
        """初始化 Hermes Chat 请求"""
        self.app = app
        self.conversation_id = conversation_id
        self.question = question
        self.features = features or HermesFeatures()
        self.language = language

    def to_dict(self) -> dict[str, Any]:
        """转换为请求字典格式"""
        return {
            "app": self.app.to_dict(),
            "conversationId": self.conversation_id,
            "features": self.features.to_dict(),
            "language": self.language,
            "question": self.question,
        }
