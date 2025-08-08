"""
部署配置数据模型

定义部署过程中需要的配置项数据结构。
"""

from dataclasses import dataclass, field

# 常量定义
MAX_TEMPERATURE = 2.0
MIN_TEMPERATURE = 0.0


@dataclass
class LLMConfig:
    """
    LLM 配置

    包含大语言模型的配置信息。
    """

    endpoint: str = ""
    api_key: str = ""
    model: str = ""
    max_tokens: int = 8192
    temperature: float = 0.7
    request_timeout: int = 300


@dataclass
class EmbeddingConfig:
    """
    Embedding 配置

    包含嵌入模型的配置信息。
    """

    type: str = "openai"
    endpoint: str = ""
    api_key: str = ""
    model: str = ""


@dataclass
class DeploymentConfig:
    """
    部署配置

    包含完整的部署配置信息。
    """

    # 基础设置
    server_ip: str = ""
    deployment_mode: str = "light"  # light: 轻量部署, full: 全量部署

    # LLM 配置
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Embedding 配置
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # 高级配置（可选）
    enable_web: bool = False
    enable_rag: bool = False

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置的有效性

        Returns:
            tuple[bool, list[str]]: (是否有效, 错误消息列表)

        """
        errors = []

        # 验证基础字段
        errors.extend(self._validate_basic_fields())

        # 验证 LLM 字段
        errors.extend(self._validate_llm_fields())

        # 验证 Embedding 字段
        errors.extend(self._validate_embedding_fields())

        # 验证数值范围
        errors.extend(self._validate_numeric_fields())

        return len(errors) == 0, errors

    def _validate_basic_fields(self) -> list[str]:
        """验证基础字段"""
        errors = []
        if not self.server_ip.strip():
            errors.append("服务器 IP 地址不能为空")
        return errors

    def _validate_llm_fields(self) -> list[str]:
        """验证 LLM 配置字段"""
        errors = []
        if not self.llm.endpoint.strip():
            errors.append("LLM API 端点不能为空")
        if not self.llm.api_key.strip():
            errors.append("LLM API 密钥不能为空")
        if not self.llm.model.strip():
            errors.append("LLM 模型名称不能为空")
        return errors

    def _validate_embedding_fields(self) -> list[str]:
        """验证 Embedding 配置字段"""
        errors = []
        if not self.embedding.endpoint.strip():
            errors.append("Embedding API 端点不能为空")
        if not self.embedding.api_key.strip():
            errors.append("Embedding API 密钥不能为空")
        if not self.embedding.model.strip():
            errors.append("Embedding 模型名称不能为空")
        return errors

    def _validate_numeric_fields(self) -> list[str]:
        """验证数值字段"""
        errors = []
        if self.llm.max_tokens <= 0:
            errors.append("LLM max_tokens 必须大于 0")
        if not (MIN_TEMPERATURE <= self.llm.temperature <= MAX_TEMPERATURE):
            errors.append(f"LLM temperature 必须在 {MIN_TEMPERATURE} 到 {MAX_TEMPERATURE} 之间")
        if self.llm.request_timeout <= 0:
            errors.append("LLM 请求超时时间必须大于 0")
        return errors


@dataclass
class DeploymentState:
    """
    部署状态

    跟踪部署过程的状态信息。
    """

    current_step: int = 0
    total_steps: int = 0
    current_step_name: str = ""
    is_running: bool = False
    is_completed: bool = False
    is_failed: bool = False
    error_message: str = ""
    output_log: list[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        """
        添加日志消息

        Args:
            message: 日志消息

        """
        self.output_log.append(message)

    def clear_log(self) -> None:
        """清空日志"""
        self.output_log.clear()

    def reset(self) -> None:
        """重置状态"""
        self.current_step = 0
        self.current_step_name = ""
        self.is_running = False
        self.is_completed = False
        self.is_failed = False
        self.error_message = ""
        self.clear_log()
