"""
部署服务模块

处理 openEuler Intelligence 后端部署的核心逻辑。
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
from pathlib import Path
from typing import TYPE_CHECKING

from log.manager import get_logger

from .models import DeploymentConfig, DeploymentState

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

logger = get_logger(__name__)


class DeploymentResourceManager:
    """部署资源管理器，管理 RPM 包安装的资源文件"""

    # RPM 包安装的资源文件路径
    INSTALLER_BASE_PATH = Path("/usr/lib/openeuler-intelligence/scripts")
    RESOURCE_PATH = INSTALLER_BASE_PATH / "5-resource"
    DEPLOY_SCRIPT = INSTALLER_BASE_PATH / "deploy"

    # 配置文件模板路径
    ENV_TEMPLATE = RESOURCE_PATH / "env"
    CONFIG_TEMPLATE = RESOURCE_PATH / "config.toml"

    # 系统配置文件路径
    INSTALL_MODEL_FILE = Path("/etc/euler_Intelligence_install_model")

    @classmethod
    def check_installer_available(cls) -> bool:
        """检查安装器是否可用"""
        return (
            cls.INSTALLER_BASE_PATH.exists()
            and cls.RESOURCE_PATH.exists()
            and cls.DEPLOY_SCRIPT.exists()
            and cls.ENV_TEMPLATE.exists()
            and cls.CONFIG_TEMPLATE.exists()
        )

    @classmethod
    def get_template_content(cls, template_path: Path) -> str:
        """获取模板文件内容"""
        try:
            return template_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.exception("读取模板文件失败 %s", template_path)
            msg = f"无法读取模板文件: {template_path}"
            raise RuntimeError(msg) from e

    @classmethod
    def update_config_values(cls, content: str, config: DeploymentConfig) -> str:
        """根据用户配置更新配置文件内容"""
        # 更新 LLM 配置
        content = re.sub(r"(MODEL_NAME\s*=\s*).*", rf"\1{config.llm.model}", content)
        content = re.sub(r"(OPENAI_API_BASE\s*=\s*).*", rf"\1{config.llm.endpoint}", content)
        content = re.sub(r"(OPENAI_API_KEY\s*=\s*).*", rf"\1{config.llm.api_key}", content)
        content = re.sub(r"(MAX_TOKENS\s*=\s*).*", rf"\1{config.llm.max_tokens}", content)
        content = re.sub(r"(TEMPERATURE\s*=\s*).*", rf"\1{config.llm.temperature}", content)
        content = re.sub(r"(REQUEST_TIMEOUT\s*=\s*).*", rf"\1{config.llm.request_timeout}", content)

        # 更新 Embedding 配置
        content = re.sub(r"(EMBEDDING_TYPE\s*=\s*).*", rf"\1{config.embedding.type}", content)
        content = re.sub(r"(EMBEDDING_API_KEY\s*=\s*).*", rf"\1{config.embedding.api_key}", content)
        content = re.sub(r"(EMBEDDING_ENDPOINT\s*=\s*).*", rf"\1{config.embedding.endpoint}", content)
        return re.sub(r"(EMBEDDING_MODEL_NAME\s*=\s*).*", rf"\1{config.embedding.model}", content)

    @classmethod
    def update_toml_values(cls, content: str, config: DeploymentConfig) -> str:
        """更新 TOML 配置文件的值"""
        import re

        # 更新服务器 IP
        content = re.sub(r"(host\s*=\s*')[^']*(')", rf"\1http://{config.server_ip}:8000\2", content)
        content = re.sub(r"(login_api\s*=\s*')[^']*(')", rf"\1http://{config.server_ip}:8080/api/auth/login\2", content)
        content = re.sub(r"(domain\s*=\s*')[^']*(')", rf"\1{config.server_ip}\2", content)

        # 更新 LLM 配置
        content = re.sub(r'(endpoint\s*=\s*")[^"]*(")', rf"\1{config.llm.endpoint}\2", content)
        content = re.sub(r"(key\s*=\s*')[^']*(')", rf"\1{config.llm.api_key}\2", content)
        content = re.sub(r"(model\s*=\s*')[^']*(')", rf"\1{config.llm.model}\2", content)
        content = re.sub(r"(max_tokens\s*=\s*)\d+", rf"\1{config.llm.max_tokens}", content)
        content = re.sub(r"(temperature\s*=\s*)[\d.]+", rf"\1{config.llm.temperature}", content)

        # 更新 Embedding 配置
        content = re.sub(r"(type\s*=\s*')[^']*(')", rf"\1{config.embedding.type}\2", content)
        return re.sub(r"(api_key\s*=\s*')[^']*(')", rf"\1{config.embedding.api_key}\2", content)

    @classmethod
    def create_deploy_mode_content(cls, config: DeploymentConfig) -> str:
        """创建部署模式配置内容"""
        web_install = "y" if config.enable_web else "n"
        rag_install = "y" if config.enable_rag else "n"

        return f"""web_install={web_install}
rag_install={rag_install}
"""


class DeploymentService:
    """
    部署服务

    负责执行 openEuler Intelligence 后端的部署流程。
    基于已安装的 openeuler-intelligence-installer RPM 包资源。
    """

    def __init__(self) -> None:
        """初始化部署服务"""
        self.state = DeploymentState()
        self._process: asyncio.subprocess.Process | None = None
        self.resource_manager = DeploymentResourceManager()

    async def deploy(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None = None,
    ) -> bool:
        """
        执行部署

        Args:
            config: 部署配置
            progress_callback: 进度回调函数

        Returns:
            bool: 部署是否成功

        """
        try:
            logger.info("开始部署 openEuler Intelligence 后端")

            # 重置状态
            self.state.reset()
            self.state.is_running = True
            self.state.total_steps = 4

            # 步骤1：检查系统环境和资源
            if not await self._check_environment(config, progress_callback):
                return False

            # 步骤2：生成配置文件
            if not await self._generate_config_files(config, progress_callback):
                return False

            # 步骤3：设置部署模式
            if not await self._setup_deploy_mode(config, progress_callback):
                return False

            # 步骤4：执行部署脚本
            if not await self._run_deployment_script(config, progress_callback):
                return False

        except Exception:
            logger.exception("部署过程中发生错误")
            self.state.is_running = False
            self.state.is_failed = True
            self.state.error_message = "部署过程中发生异常"
            self.state.add_log("✗ 部署失败")

            if progress_callback:
                progress_callback(self.state)

            return False
        else:
            # 部署完成
            self.state.is_running = False
            self.state.is_completed = True
            self.state.add_log("✓ openEuler Intelligence 后端部署完成！")

            if progress_callback:
                progress_callback(self.state)

            logger.info("部署完成")
            return True

    async def _check_environment(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查系统环境和资源"""
        self.state.current_step = 1
        self.state.current_step_name = "检查系统环境"
        self.state.add_log("正在检查系统环境...")

        if progress_callback:
            progress_callback(self.state)

        # 检查操作系统
        if not self._detect_openeuler():
            self.state.add_log("✗ 错误: 仅支持 openEuler 操作系统")
            return False
        self.state.add_log("✓ 检测到 openEuler 操作系统")

        # 检查安装器资源
        if not self.resource_manager.check_installer_available():
            self.state.add_log("✗ 错误: openeuler-intelligence-installer 包未安装或资源缺失")
            self.state.add_log("请先安装: sudo dnf install -y openeuler-intelligence-installer")
            return False
        self.state.add_log("✓ openeuler-intelligence-installer 资源可用")

        # 检查权限
        if not await self._check_sudo_privileges():
            self.state.add_log("✗ 错误: 需要管理员权限")
            return False
        self.state.add_log("✓ 具有管理员权限")

        return True

    async def _generate_config_files(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """生成配置文件"""
        self.state.current_step = 2
        self.state.current_step_name = "更新配置文件"
        self.state.add_log("正在更新配置文件...")

        if progress_callback:
            progress_callback(self.state)

        try:
            # 更新 env 文件
            await self._update_env_file(config)
            self.state.add_log("✓ 更新 env 配置文件")

            # 更新 config.toml 文件
            await self._update_config_toml(config)
            self.state.add_log("✓ 更新 config.toml 配置文件")

        except Exception as e:
            self.state.add_log(f"✗ 更新配置文件失败: {e}")
            logger.exception("更新配置文件失败")
            return False
        else:
            return True

    async def _setup_deploy_mode(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """设置部署模式"""
        self.state.current_step = 3
        self.state.current_step_name = "设置部署模式"
        self.state.add_log("正在设置部署模式...")

        if progress_callback:
            progress_callback(self.state)

        try:
            # 生成部署模式文件内容
            mode_content = self.resource_manager.create_deploy_mode_content(config)

            # 写入系统配置文件
            cmd = [
                "sudo",
                "tee",
                str(self.resource_manager.INSTALL_MODEL_FILE),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(mode_content.encode())

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore").strip()
                self.state.add_log(f"✗ 设置部署模式失败: {error_msg}")
                return False

            web_status = "启用" if config.enable_web else "禁用"
            rag_status = "启用" if config.enable_rag else "禁用"
            self.state.add_log(f"✓ 部署模式设置完成 (Web界面: {web_status}, RAG: {rag_status})")

        except Exception as e:
            self.state.add_log(f"✗ 设置部署模式失败: {e}")
            logger.exception("设置部署模式失败")
            return False
        else:
            return True

    async def _run_deployment_script(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行部署脚本"""
        self.state.current_step = 4
        self.state.current_step_name = "执行部署脚本"
        self.state.add_log("正在运行部署脚本...")

        if progress_callback:
            progress_callback(self.state)

        try:
            # 运行部署脚本
            cmd = [
                "sudo",
                str(self.resource_manager.DEPLOY_SCRIPT),
                config.deployment_mode,
            ]

            # 设置环境变量，启用自动部署模式
            env = os.environ.copy()
            env["AUTO_DEPLOY"] = "1"

            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            # 读取输出
            async for line in self._read_process_output():
                self.state.add_log(line)
                if progress_callback:
                    progress_callback(self.state)

            # 等待进程结束
            return_code = await self._process.wait()
            self._process = None

            if return_code == 0:
                self.state.add_log("✓ 部署脚本执行成功")
                return True

        except Exception as e:
            self.state.add_log(f"✗ 运行部署脚本时发生错误: {e}")
            logger.exception("运行部署脚本失败")
            return False
        else:
            self.state.add_log(f"✗ 部署脚本执行失败，返回码: {return_code}")
            return False

    async def _update_env_file(self, config: DeploymentConfig) -> None:
        """更新 env 配置文件"""
        template_content = self.resource_manager.get_template_content(
            self.resource_manager.ENV_TEMPLATE,
        )

        updated_content = self.resource_manager.update_config_values(
            template_content,
            config,
        )

        # 备份原文件并写入新内容
        backup_cmd = [
            "sudo",
            "cp",
            str(self.resource_manager.ENV_TEMPLATE),
            f"{self.resource_manager.ENV_TEMPLATE}.backup",
        ]
        await asyncio.create_subprocess_exec(*backup_cmd)

        # 写入更新后的内容
        write_cmd = ["sudo", "tee", str(self.resource_manager.ENV_TEMPLATE)]
        process = await asyncio.create_subprocess_exec(
            *write_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate(updated_content.encode())

    async def _update_config_toml(self, config: DeploymentConfig) -> None:
        """更新 config.toml 配置文件"""
        template_content = self.resource_manager.get_template_content(
            self.resource_manager.CONFIG_TEMPLATE,
        )

        updated_content = self.resource_manager.update_toml_values(
            template_content,
            config,
        )

        # 备份原文件并写入新内容
        backup_cmd = [
            "sudo",
            "cp",
            str(self.resource_manager.CONFIG_TEMPLATE),
            f"{self.resource_manager.CONFIG_TEMPLATE}.backup",
        ]
        await asyncio.create_subprocess_exec(*backup_cmd)

        # 写入更新后的内容
        write_cmd = ["sudo", "tee", str(self.resource_manager.CONFIG_TEMPLATE)]
        process = await asyncio.create_subprocess_exec(
            *write_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate(updated_content.encode())

    async def _read_process_output(self) -> AsyncGenerator[str, None]:
        """读取进程输出"""
        if not self._process or not self._process.stdout:
            return

        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                if decoded_line:
                    yield decoded_line

            except OSError as e:
                logger.warning("读取进程输出时发生错误: %s", e)
                break

    def _detect_openeuler(self) -> bool:
        """检测是否为 openEuler 系统"""
        try:
            # 检查 /etc/os-release
            os_release_path = Path("/etc/os-release")
            if os_release_path.exists():
                content = os_release_path.read_text(encoding="utf-8").lower()
                if "openeuler" in content:
                    return True

            # 检查 /etc/openEuler-release
            openeuler_release_path = Path("/etc/openEuler-release")
            if openeuler_release_path.exists():
                return True

        except OSError as e:
            logger.warning("检测操作系统时发生错误: %s", e)
            return False

        else:
            # 检查 platform 信息
            system_info = platform.platform().lower()
            return "openeuler" in system_info

    async def _check_sudo_privileges(self) -> bool:
        """检查 sudo 权限"""
        try:
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "-n",
                "true",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return_code = await process.wait()
        except OSError:
            return False
        else:
            return return_code == 0

    def cancel_deployment(self) -> None:
        """取消部署"""
        if self._process:
            try:
                self._process.terminate()
                logger.info("部署进程已终止")
            except OSError as e:
                logger.warning("终止部署进程时发生错误: %s", e)
