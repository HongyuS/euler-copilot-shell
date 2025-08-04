"""配置模型"""

from dataclasses import dataclass, field
from enum import Enum


class Backend(str, Enum):
    """后端类型"""

    OPENAI = "openai"
    EULERINTELLI = "eulerintelli"


@dataclass
class OpenAIConfig:
    """OpenAI 后端配置"""

    base_url: str = field(default="http://127.0.0.1:1234/v1")
    model: str = field(default="qwen/qwen3-30b-a3b-2507")
    api_key: str = field(default="lm-studio")

    @classmethod
    def from_dict(cls, d: dict) -> "OpenAIConfig":
        """从字典初始化配置"""
        return cls(
            base_url=d.get("base_url", cls.base_url),
            model=d.get("model", cls.model),
            api_key=d.get("api_key", cls.api_key),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"base_url": self.base_url, "model": self.model, "api_key": self.api_key}


@dataclass
class HermesConfig:
    """Hermes 后端配置"""

    base_url: str = field(default="https://www.eulerintelli.com")
    api_key: str = field(default="your-eulerintelli-api-key")

    @classmethod
    def from_dict(cls, d: dict) -> "HermesConfig":
        """从字典初始化配置"""
        return cls(
            base_url=d.get("base_url", cls.base_url),
            api_key=d.get("api_key", cls.api_key),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"base_url": self.base_url, "api_key": self.api_key}


@dataclass
class ConfigModel:
    """配置模型"""

    backend: Backend = field(default=Backend.OPENAI)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    eulerintelli: HermesConfig = field(default_factory=HermesConfig)

    @classmethod
    def from_dict(cls, d: dict) -> "ConfigModel":
        """从字典初始化配置模型"""
        backend_value = d.get("backend", Backend.OPENAI)
        # 确保 backend 始终是 Backend 枚举类型
        if isinstance(backend_value, Backend):
            backend = backend_value
        elif isinstance(backend_value, str):
            backend = Backend(backend_value)
        else:
            backend = Backend.OPENAI

        return cls(
            backend=backend,
            openai=OpenAIConfig.from_dict(d.get("openai", {})),
            eulerintelli=HermesConfig.from_dict(d.get("eulerintelli", {})),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backend": self.backend.value,  # 保存枚举的值
            "openai": self.openai.to_dict(),
            "eulerintelli": self.eulerintelli.to_dict(),
        }
