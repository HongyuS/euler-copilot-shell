"""后端模型数据结构定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LLMType(str, Enum):
    """
    LLM 类型枚举

    定义了 Hermes 后端支持的 LLM 能力类型。
    """

    CHAT = "chat"
    """模型支持 Chat（聊天对话）"""

    FUNCTION = "function"
    """模型支持 Function Call（函数调用）"""

    EMBEDDING = "embedding"
    """模型支持 Embedding（向量嵌入）"""

    VISION = "vision"
    """模型支持图片理解（视觉能力）"""

    THINKING = "thinking"
    """模型支持思考推理（推理能力）"""


@dataclass
class ModelInfo:
    """
    模型信息数据类

    该类用于统一表示不同后端（OpenAI、Hermes）返回的模型信息。

    注意：
    - model_name: 仅用于后端调用大模型 API 时使用，CLI 前端不需要关心
    - llm_id: CLI 前端使用的模型标识符，用于显示和配置保存
    """

    # 通用字段（所有后端都支持）
    model_name: str
    """模型名称，仅用于后端调用大模型 API"""

    # Hermes 特有字段
    llm_id: str | None = None
    """LLM ID，CLI 前端使用的模型唯一标识符（用于显示和配置）"""

    llm_description: str | None = None
    """LLM 描述，Hermes 后端的模型说明"""

    llm_type: list[LLMType] = field(default_factory=list)
    """LLM 类型列表，如 [LLMType.CHAT, LLMType.FUNCTION]，Hermes 后端特有"""

    max_tokens: int | None = None
    """模型支持的最大 token 数，Hermes 后端提供"""

    def __str__(self) -> str:
        """返回模型的字符串表示（优先使用 llm_id）"""
        return self.llm_id or self.model_name

    def __repr__(self) -> str:
        """返回模型的详细表示"""
        return f"ModelInfo(model_name={self.model_name!r}, llm_id={self.llm_id!r})"

    @staticmethod
    def parse_llm_types(llm_types: list[str] | None) -> list[LLMType]:
        """
        解析 LLM 类型字符串列表，过滤掉不合法的值

        Args:
            llm_types: LLM 类型字符串列表

        Returns:
            list[LLMType]: 合法的 LLM 类型枚举列表

        """
        if not llm_types:
            return []

        valid_values = {t.value for t in LLMType}
        return [LLMType(llm_type_str) for llm_type_str in llm_types if llm_type_str in valid_values]
