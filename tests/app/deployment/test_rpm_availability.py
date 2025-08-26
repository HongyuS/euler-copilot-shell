"""
测试 RPM 包可用性检查功能

这个脚本用于测试 agent.py 中添加的 _check_rpm_packages_availability 方法。
使用方法: source .venv/bin/activate && PYTHONPATH=src python tests/app/deployment/test_rpm_availability.py
"""

import asyncio
import sys
import traceback
from pathlib import Path

from app.deployment.agent import AgentManager
from app.deployment.models import DeploymentState

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


async def test_rpm_availability() -> bool:
    """测试 RPM 包可用性检查"""
    _output("=== 测试 RPM 包可用性检查 ===")

    # 创建 AgentManager 实例
    agent_manager = AgentManager()

    if not agent_manager.resource_dir:
        _output("❌ 未找到资源目录，测试失败")
        return False

    # 创建测试状态和回调
    state = DeploymentState()
    callback = TestProgress()

    # 准备测试的 RPM 列表文件
    rpm_files = ["mcp-servers.rpmlist", "sysTrace.rpmlist"]

    # 检查文件是否存在
    _output(f"\n资源目录: {agent_manager.resource_dir}")
    for rpm_file in rpm_files:
        file_path = agent_manager.resource_dir / rpm_file
        if file_path.exists():
            _output(f"✅ 找到文件: {rpm_file}")
            # 显示文件内容
            with file_path.open(encoding="utf-8") as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                _output(f"   包含的包: {packages}")
        else:
            _output(f"⚠️  文件不存在: {rpm_file}")

    # 执行可用性检查
    _output("\n开始检查 RPM 包可用性...")
    result = await agent_manager._check_rpm_packages_availability(rpm_files, state, callback)  # noqa: SLF001

    _output("\n=== 测试结果 ===")
    if result:
        _output("✅ 所有 RPM 包均可用")
    else:
        _output("❌ 存在不可用的 RPM 包")

    return result


async def main() -> None:
    """主函数"""
    try:
        result = await test_rpm_availability()

        _output("\n=== 总结 ===")
        if result:
            _output("✅ 测试通过：可以继续智能体初始化")
        else:
            _output("❌ 测试失败：应该跳过智能体初始化")

    except Exception as e:  # noqa: BLE001
        _output(f"❌ 测试执行失败: {e}")

        traceback.print_exc()


def _output(message: str = "") -> None:
    """输出消息到标准输出"""
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
