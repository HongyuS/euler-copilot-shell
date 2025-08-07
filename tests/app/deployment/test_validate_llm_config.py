"""
API 配置验证功能演示

简单演示如何使用新的验证功能。
使用方法: source .venv/bin/activate && PYTHONPATH=src python tests/app/deployment/test_validate_llm_config.py
"""

import asyncio
import sys
from typing import Any

from app.deployment.models import DeploymentConfig, EmbeddingConfig, LLMConfig


def _output(message: str = "") -> None:
    """输出消息到标准输出"""
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


def _output_llm_validation_info(llm_info: dict[str, Any]) -> None:
    """输出 LLM 验证信息"""
    _output(f"   📱 LLM: {llm_info['message']}")

    if llm_info.get("supports_function_call"):
        _output("   🔧 Function Call: ✅ 支持")
        if "function_call_info" in llm_info:
            format_type = llm_info["function_call_info"].get("format", "unknown")
            _output(f"   📋 支持格式: {format_type}")
    else:
        _output("   🔧 Function Call: ❌ 不支持")

    if "available_models" in llm_info:
        models = llm_info["available_models"][:3]
        _output(f"   📦 可用模型示例: {', '.join(models)}")


def _output_embedding_validation_info(embed_info: dict[str, Any]) -> None:
    """输出 Embedding 验证信息"""
    _output(f"   🔢 Embedding: {embed_info['message']}")
    if "dimension" in embed_info:
        _output(f"   📐 向量维度: {embed_info['dimension']}")


async def main() -> None:
    """主演示函数"""
    _output("🔧 API 配置验证演示")
    _output("=" * 40)

    config = DeploymentConfig(
        server_ip="127.0.0.1",
        deployment_mode="light",
        llm=LLMConfig(
            endpoint="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            model="qwen/qwen3-30b-a3b-2507",
            max_tokens=4096,
            temperature=0.7,
            request_timeout=30,
        ),
        embedding=EmbeddingConfig(
            type="openai",
            endpoint="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            model="text-embedding-bge-m3",
        ),
    )

    _output("📋 步骤 1: 基础字段验证")
    is_valid, errors = config.validate()
    if not is_valid:
        _output("❌ 基础验证失败:")
        for error in errors:
            _output(f"   • {error}")
        return
    _output("✅ 基础验证通过")

    _output("\n🌐 步骤 2: API 连接性验证")
    _output("⚠️  注意: 需要有效的 API 密钥才能通过此步骤")
    try:
        # 分别验证 LLM 和 Embedding 配置
        llm_valid, llm_msg, llm_info = await config.validate_llm_connectivity()
        embed_valid, embed_msg, embed_info = await config.validate_embedding_connectivity()

        api_valid = llm_valid and embed_valid
        api_errors = []

        if not llm_valid:
            api_errors.append(f"LLM 验证失败: {llm_msg}")
        if not embed_valid:
            api_errors.append(f"Embedding 验证失败: {embed_msg}")

        validation_info = {
            "llm": {
                "valid": llm_valid,
                "message": llm_msg,
                **llm_info,
            },
            "embedding": {
                "valid": embed_valid,
                "message": embed_msg,
                **embed_info,
            },
        }

        if not api_valid:
            _output("❌ API 验证失败:")
            for error in api_errors:
                _output(f"   • {error}")
            return

        _output("✅ API 验证成功!")
        if "llm" in validation_info:
            _output_llm_validation_info(validation_info["llm"])
        if "embedding" in validation_info:
            _output_embedding_validation_info(validation_info["embedding"])

    except (ConnectionError, TimeoutError, ValueError) as e:
        _output(f"⚠️  验证过程异常: {e}")
        _output("💡 通常是网络连接或 API 密钥问题")


if __name__ == "__main__":
    _output("🚀 开始演示...")
    _output("💡 运行方法: ")
    _output("💡 source .venv/bin/activate && PYTHONPATH=src python tests/app/deployment/test_validate_llm_config.py")
    _output()

    asyncio.run(main())

    _output("\n" + "=" * 40)
    _output("📝 验证功能特点:")
    _output("✓ API 连接性测试")
    _output("✓ 模型可用性检查")
    _output("✓ Function Call 支持检测")
    _output("✓ Embedding 向量维度验证")
    _output("✓ 支持 OpenAI 和兼容 API")
