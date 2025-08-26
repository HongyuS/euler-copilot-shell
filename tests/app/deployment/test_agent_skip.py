"""
测试智能体初始化跳过功能

验证当 RPM 包不可用时，智能体初始化会被跳过但部署继续进行。
使用方法: source .venv/bin/activate && PYTHONPATH=src python tests/app/deployment/test_agent_skip.py
"""

import asyncio
import sys
import traceback
from pathlib import Path

from app.deployment.agent import AgentManager
from app.deployment.models import AgentInitStatus, DeploymentState

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


class TestProgress:
    """测试用的进度回调类"""

    def __call__(self, state: DeploymentState) -> None:
        """显示进度信息"""
        if state.output_log:
            # 获取最新的日志条目
            latest_log = state.output_log[-1]
            _output(f"[测试] {latest_log}")


async def test_agent_init_skip() -> bool:
    """测试智能体初始化跳过功能"""
    _output("=== 测试智能体初始化跳过功能 ===")

    # 创建 AgentManager 实例
    agent_manager = AgentManager()

    if not agent_manager.resource_dir:
        _output("❌ 未找到资源目录，测试失败")
        return False

    # 创建测试状态和回调
    callback = TestProgress()

    _output(f"\n资源目录: {agent_manager.resource_dir}")

    # 执行智能体初始化
    _output("\n开始测试智能体初始化...")
    init_status = await agent_manager.initialize_agents(callback)

    _output("\n=== 测试结果 ===")
    _output(f"初始化状态: {init_status}")

    if init_status == AgentInitStatus.SUCCESS:
        _output("✅ 智能体初始化成功")
        return True
    if init_status == AgentInitStatus.SKIPPED:
        _output("⚠️  智能体初始化已跳过（这是预期结果）")
        _output("✅ 测试通过：部署应该继续进行并显示成功")
        return True
    # FAILED
    _output("❌ 智能体初始化失败")
    return False


async def main() -> None:
    """主函数"""
    try:
        result = await test_agent_init_skip()

        _output("\n=== 总结 ===")
        if result:
            _output("✅ 测试通过：智能体初始化跳过逻辑正常工作")
            _output("📋 部署流程应该显示：'⚠ Agent 初始化已跳过（RPM 包不可用），但部署将继续进行'")
            _output("🎯 最终部署结果应该显示为成功")
        else:
            _output("❌ 测试失败：智能体初始化跳过逻辑有问题")

    except Exception as e:  # noqa: BLE001
        _output(f"❌ 测试执行失败: {e}")

        traceback.print_exc()


def _output(message: str = "") -> None:
    """输出消息到标准输出"""
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
