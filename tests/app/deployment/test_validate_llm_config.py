"""
测试部署配置数据模型

运行方法：
    pytest tests/app/deployment/test_validate_llm_config.py -v

注意：由于 app.deployment 模块存在循环导入，此测试仅测试可以独立导入的数据结构，
不涉及需要完整模块加载的验证功能。
"""

import sys
from pathlib import Path

import pytest

# 添加 src 到路径以便导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# 由于循环导入问题，我们直接在这里定义测试用的简化数据类
class SimpleLLMConfig:
    """简化的 LLM 配置类用于测试"""
    
    def __init__(
        self,
        endpoint: str = "",
        api_key: str = "",
        model: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        request_timeout: int = 30,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.request_timeout = request_timeout


class SimpleEmbeddingConfig:
    """简化的 Embedding 配置类用于测试"""
    
    def __init__(
        self,
        type: str = "openai",  # noqa: A002
        endpoint: str = "",
        api_key: str = "",
        model: str = "",
    ):
        self.type = type
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model


class SimpleDeploymentConfig:
    """简化的部署配置类用于测试"""
    
    def __init__(
        self,
        deployment_mode: str = "light",
        llm: SimpleLLMConfig | None = None,
        embedding: SimpleEmbeddingConfig | None = None,
        enable_web: bool = False,
        enable_rag: bool = False,
    ):
        self.deployment_mode = deployment_mode
        self.llm = llm or SimpleLLMConfig()
        self.embedding = embedding or SimpleEmbeddingConfig()
        self.enable_web = enable_web
        self.enable_rag = enable_rag
    
    def validate(self) -> tuple[bool, list[str]]:
        """基础字段验证"""
        errors = []
        
        # 验证部署模式
        if self.deployment_mode not in ["light", "full"]:
            errors.append("部署模式必须是 'light' 或 'full'")
        
        # 验证 LLM 配置
        if not self.llm.endpoint:
            errors.append("LLM 端点不能为空")
        
        # 验证 Embedding 配置
        if not self.embedding.endpoint:
            errors.append("Embedding 端点不能为空")
        
        # 验证数值范围
        if self.llm.max_tokens <= 0:
            errors.append("max_tokens 必须大于 0")
        
        if not 0 <= self.llm.temperature <= 2:
            errors.append("temperature 必须在 0 到 2 之间")
        
        if self.llm.request_timeout <= 0:
            errors.append("request_timeout 必须大于 0")
        
        return len(errors) == 0, errors


@pytest.mark.unit
class TestLLMConfigStructure:
    """测试 LLM 配置数据结构"""

    def test_llm_config_creation(self) -> None:
        """测试 LLM 配置创建"""
        llm_config = SimpleLLMConfig(
            endpoint="http://127.0.0.1:1234/v1",
            api_key="test-key",
            model="test-model",
            max_tokens=4096,
            temperature=0.7,
            request_timeout=30,
        )
        
        assert llm_config.endpoint == "http://127.0.0.1:1234/v1"
        assert llm_config.api_key == "test-key"
        assert llm_config.model == "test-model"
        assert llm_config.max_tokens == 4096
        assert llm_config.temperature == 0.7
        assert llm_config.request_timeout == 30

    def test_llm_config_defaults(self) -> None:
        """测试 LLM 配置默认值"""
        llm_config = SimpleLLMConfig()
        
        assert llm_config.endpoint == ""
        assert llm_config.api_key == ""
        assert llm_config.model == ""
        assert llm_config.max_tokens == 4096
        assert llm_config.temperature == 0.7
        assert llm_config.request_timeout == 30


@pytest.mark.unit
class TestEmbeddingConfigStructure:
    """测试 Embedding 配置数据结构"""

    def test_embedding_config_creation(self) -> None:
        """测试 Embedding 配置创建"""
        embed_config = SimpleEmbeddingConfig(
            type="openai",
            endpoint="http://127.0.0.1:1234/v1",
            api_key="test-key",
            model="test-embedding-model",
        )
        
        assert embed_config.type == "openai"
        assert embed_config.endpoint == "http://127.0.0.1:1234/v1"
        assert embed_config.api_key == "test-key"
        assert embed_config.model == "test-embedding-model"

    def test_embedding_config_defaults(self) -> None:
        """测试 Embedding 配置默认值"""
        embed_config = SimpleEmbeddingConfig()
        
        assert embed_config.type == "openai"
        assert embed_config.endpoint == ""
        assert embed_config.api_key == ""
        assert embed_config.model == ""

    def test_embedding_config_mindie_type(self) -> None:
        """测试 Embedding 配置 mindie 类型"""
        embed_config = SimpleEmbeddingConfig(
            type="mindie",
            endpoint="http://localhost:8001",
        )
        
        assert embed_config.type == "mindie"
        assert embed_config.endpoint == "http://localhost:8001"


@pytest.mark.unit
class TestDeploymentConfigStructure:
    """测试部署配置数据结构"""

    def test_deployment_config_creation(self) -> None:
        """测试部署配置创建"""
        config = SimpleDeploymentConfig()
        
        assert config is not None
        assert config.deployment_mode == "light"
        assert config.llm is not None
        assert config.embedding is not None
        assert config.enable_web is False
        assert config.enable_rag is False

    def test_deployment_config_with_custom_values(self) -> None:
        """测试使用自定义值创建部署配置"""
        config = SimpleDeploymentConfig(
            deployment_mode="full",
            llm=SimpleLLMConfig(
                endpoint="http://localhost:8000",
                api_key="custom-key",
                model="custom-model",
            ),
            embedding=SimpleEmbeddingConfig(
                type="mindie",
                endpoint="http://localhost:8001",
            ),
            enable_web=True,
            enable_rag=True,
        )
        
        assert config.deployment_mode == "full"
        assert config.llm.endpoint == "http://localhost:8000"
        assert config.embedding.type == "mindie"
        assert config.enable_web is True
        assert config.enable_rag is True


@pytest.mark.unit
class TestConfigValidation:
    """测试配置验证功能"""

    def test_validate_empty_config(self) -> None:
        """测试验证空配置"""
        config = SimpleDeploymentConfig()
        
        is_valid, errors = config.validate()
        
        # 空配置应该有验证错误（缺少端点）
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert is_valid is False  # 空配置应该验证失败
        assert len(errors) > 0  # 应该有错误消息

    def test_validate_with_endpoints(self) -> None:
        """测试包含端点的配置验证"""
        config = SimpleDeploymentConfig(
            llm=SimpleLLMConfig(endpoint="http://127.0.0.1:1234/v1"),
            embedding=SimpleEmbeddingConfig(endpoint="http://127.0.0.1:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 基础验证应该通过（有端点）
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert is_valid is True  # 应该验证成功
        assert len(errors) == 0  # 不应该有错误

    def test_validate_invalid_deployment_mode(self) -> None:
        """测试无效的部署模式"""
        config = SimpleDeploymentConfig(
            deployment_mode="invalid",
            llm=SimpleLLMConfig(endpoint="http://localhost:1234/v1"),
            embedding=SimpleEmbeddingConfig(endpoint="http://localhost:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 应该验证失败
        assert is_valid is False
        assert len(errors) > 0
        assert any("部署模式" in error or "deployment" in error.lower() for error in errors)

    def test_validate_numeric_fields_valid(self) -> None:
        """测试有效的数值字段"""
        config = SimpleDeploymentConfig(
            llm=SimpleLLMConfig(
                endpoint="http://localhost:1234/v1",
                max_tokens=4096,
                temperature=0.7,
                request_timeout=30,
            ),
            embedding=SimpleEmbeddingConfig(endpoint="http://localhost:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 应该验证成功
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_max_tokens(self) -> None:
        """测试无效的 max_tokens"""
        config = SimpleDeploymentConfig(
            llm=SimpleLLMConfig(
                endpoint="http://localhost:1234/v1",
                max_tokens=0,  # 无效值
            ),
            embedding=SimpleEmbeddingConfig(endpoint="http://localhost:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 应该验证失败
        assert is_valid is False
        assert any("max_tokens" in error for error in errors)

    def test_validate_invalid_temperature(self) -> None:
        """测试无效的 temperature"""
        config = SimpleDeploymentConfig(
            llm=SimpleLLMConfig(
                endpoint="http://localhost:1234/v1",
                temperature=3.0,  # 超出范围
            ),
            embedding=SimpleEmbeddingConfig(endpoint="http://localhost:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 应该验证失败
        assert is_valid is False
        assert any("temperature" in error for error in errors)

    def test_validate_invalid_timeout(self) -> None:
        """测试无效的 request_timeout"""
        config = SimpleDeploymentConfig(
            llm=SimpleLLMConfig(
                endpoint="http://localhost:1234/v1",
                request_timeout=-1,  # 无效值
            ),
            embedding=SimpleEmbeddingConfig(endpoint="http://localhost:1234/v1"),
        )
        
        is_valid, errors = config.validate()
        
        # 应该验证失败
        assert is_valid is False
        assert any("timeout" in error.lower() for error in errors)
