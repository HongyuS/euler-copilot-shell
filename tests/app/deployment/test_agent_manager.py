"""
测试 AgentManager 的 RPM 包安装功能

这个脚本会测试：
1. 检查 systrace 配置目录是否存在
2. 模拟 RPM 包安装过程

使用方法: source .venv/bin/activate && PYTHONPATH=src python tests/app/deployment/test_agent_manager.py
"""

import asyncio
import sys
from pathlib import Path

from app.deployment.agent import AgentManager
from app.deployment.models import DeploymentState

# 添加项目路径到 Python 模块搜索路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def progress_callback(state: DeploymentState) -> None:
    """打印进度信息"""
    if state.output_log:
        _output(f"[进度] {state.output_log[-1]}")


async def test_agent_manager() -> None:
    """测试 AgentManager 的功能"""
    _output("开始测试 AgentManager...")

    # 创建 AgentManager 实例
    manager = AgentManager()

    if not manager.resource_dir:
        _output("❌ 资源目录未找到，测试终止")
        return

    _output(f"✅ 找到资源目录: {manager.resource_dir}")
    _output(f"✅ MCP 配置目录: {manager.mcp_config_dir}")

    # 测试检查 systrace 配置
    state = DeploymentState()
    systrace_exists = manager._check_systrace_config(state, progress_callback)  # noqa: SLF001
    _output(f"sysTrace 配置检查结果: {systrace_exists}")

    # 测试必要包安装功能（模拟）
    _output("\n测试必要包安装功能（模拟）...")
    result = await manager._install_prerequisite_packages(state, progress_callback)  # noqa: SLF001
    _output(f"必要包安装结果: {result}")

    # 测试安装必要的包（仅模拟）
    _output("\n测试 RPM 包安装功能（仅检查文件存在性）...")

    # 检查 sysTrace.rpmlist 文件
    systrace_rpm_file = manager.resource_dir / "sysTrace.rpmlist"
    if systrace_rpm_file.exists():
        _output(f"✅ 找到 sysTrace.rpmlist: {systrace_rpm_file}")
        with systrace_rpm_file.open() as f:
            packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        _output(f"  需要安装的包: {packages}")
    else:
        _output(f"⚠️ sysTrace.rpmlist 文件不存在: {systrace_rpm_file}")

    # 检查 mcp-servers.rpmlist 文件
    mcp_rpm_file = manager.resource_dir / "mcp-servers.rpmlist"
    if mcp_rpm_file.exists():
        _output(f"✅ 找到 mcp-servers.rpmlist: {mcp_rpm_file}")
        with mcp_rpm_file.open() as f:
            packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        _output(f"  需要安装的包: {packages}")
    else:
        _output(f"⚠️ mcp-servers.rpmlist 文件不存在: {mcp_rpm_file}")

    _output("\n✅ 测试完成")


def _output(message: str = "") -> None:
    """输出消息到标准输出"""
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(test_agent_manager())
