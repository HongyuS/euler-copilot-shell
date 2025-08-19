"""
部署服务模块

处理 openEuler Intelligence 后端部署的核心逻辑。
"""

from __future__ import annotations

import asyncio
import contextlib
import platform
import re
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import toml

from config.manager import ConfigManager
from log.manager import get_logger

from .agent import AgentManager
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
    INSTALL_MODE_FILE = Path("/etc/euler_Intelligence_install_mode")

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

        def safe_replace(pattern: str, replacement: str, text: str) -> str:
            """安全的正则表达式替换，避免反向引用问题"""
            # 使用 lambda 函数来避免反向引用问题
            return re.sub(pattern, lambda m: m.group(1) + replacement, text)

        # 更新 LLM 配置
        content = safe_replace(r"(MODEL_NAME\s*=\s*).*", config.llm.model, content)
        content = safe_replace(r"(OPENAI_API_BASE\s*=\s*).*", config.llm.endpoint, content)
        content = safe_replace(r"(OPENAI_API_KEY\s*=\s*).*", config.llm.api_key, content)
        content = safe_replace(r"(MAX_TOKENS\s*=\s*).*", str(config.llm.max_tokens), content)
        content = safe_replace(r"(TEMPERATURE\s*=\s*).*", str(config.llm.temperature), content)
        content = safe_replace(r"(REQUEST_TIMEOUT\s*=\s*).*", str(config.llm.request_timeout), content)

        # 更新 Embedding 配置
        content = safe_replace(r"(EMBEDDING_TYPE\s*=\s*).*", config.embedding.type, content)
        content = safe_replace(r"(EMBEDDING_API_KEY\s*=\s*).*", config.embedding.api_key, content)
        content = safe_replace(r"(EMBEDDING_ENDPOINT\s*=\s*).*", config.embedding.endpoint, content)
        return safe_replace(r"(EMBEDDING_MODEL_NAME\s*=\s*).*", config.embedding.model, content)

    @classmethod
    def update_toml_values(cls, content: str, config: DeploymentConfig) -> str:
        """更新 TOML 配置文件的值"""
        try:
            # 解析 TOML 内容
            toml_data = toml.loads(content)

            # 更新服务器 IP
            server_ip = str(config.server_ip)
            if "login" in toml_data and "settings" in toml_data["login"]:
                toml_data["login"]["settings"]["host"] = f"http://{server_ip}:8000"
                toml_data["login"]["settings"]["login_api"] = f"http://{server_ip}:8080/api/auth/login"

            # 更新 fastapi 域名
            if "fastapi" in toml_data:
                toml_data["fastapi"]["domain"] = server_ip

            # 更新 LLM 配置
            if "llm" in toml_data:
                toml_data["llm"]["endpoint"] = config.llm.endpoint
                toml_data["llm"]["key"] = config.llm.api_key
                toml_data["llm"]["model"] = config.llm.model
                toml_data["llm"]["max_tokens"] = config.llm.max_tokens
                toml_data["llm"]["temperature"] = config.llm.temperature

            # 更新 function_call 配置
            if "function_call" in toml_data:
                toml_data["function_call"]["backend"] = "function_call"
                toml_data["function_call"]["endpoint"] = config.llm.endpoint
                toml_data["function_call"]["api_key"] = config.llm.api_key
                toml_data["function_call"]["model"] = config.llm.model
                toml_data["function_call"]["max_tokens"] = config.llm.max_tokens
                toml_data["function_call"]["temperature"] = config.llm.temperature

            # 更新 Embedding 配置
            if "embedding" in toml_data:
                toml_data["embedding"]["type"] = config.embedding.type
                toml_data["embedding"]["api_key"] = config.embedding.api_key

            # 将更新后的数据转换回 TOML 格式
            return toml.dumps(toml_data)

        except toml.TomlDecodeError as e:
            logger.exception("解析 TOML 内容时出错")
            msg = f"TOML 格式错误: {e}"
            raise ValueError(msg) from e
        except Exception as e:
            logger.exception("更新 TOML 配置时发生错误")
            msg = f"更新 TOML 配置失败: {e}"
            raise RuntimeError(msg) from e

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

    # 公共方法

    async def check_and_install_dependencies(
        self,
        progress_callback: Callable[[DeploymentState], None] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        检查并自动安装部署依赖

        Returns:
            tuple[bool, list[str]]: (是否成功, 错误信息列表)

        """
        errors = []
        temp_state = DeploymentState()

        # 更新状态
        if progress_callback:
            temp_state.current_step_name = "检查部署依赖"
            temp_state.add_log("正在检查部署环境依赖...")
            progress_callback(temp_state)

        # 检查操作系统
        if not self.detect_openeuler():
            errors.append("仅支持 openEuler 操作系统")
            return False, errors

        # 检查并安装 openeuler-intelligence-installer
        if not self.resource_manager.check_installer_available():
            if progress_callback:
                temp_state.add_log("缺少 openeuler-intelligence-installer 包，正在尝试安装...")
                progress_callback(temp_state)

            success, install_errors = await self._install_intelligence_installer(progress_callback)
            if not success:
                errors.extend(install_errors)
                return False, errors

        # 检查 sudo 权限
        if not await self.check_sudo_privileges():
            errors.append("需要管理员权限，请确保可以使用 sudo")
            return False, errors

        if progress_callback:
            temp_state.add_log("✓ 部署环境依赖检查完成")
            progress_callback(temp_state)

        return True, []

    def detect_openeuler(self) -> bool:
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

    async def check_sudo_privileges(self) -> bool:
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
            # 根据部署模式设置总步数：轻量模式7步，全量模式6步
            self.state.total_steps = 7 if config.deployment_mode == "light" else 6

            # 执行部署步骤
            success = await self._execute_deployment_steps(config, progress_callback)

            if not success:
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

        # 部署完成，创建全局配置模板供其他用户使用
        self.state.is_running = False
        self.state.is_completed = True
        self.state.add_log("✓ openEuler Intelligence 后端部署完成！")

        # 创建全局配置模板，包含部署时的配置信息
        await self._create_global_config_template(config)

        if progress_callback:
            progress_callback(self.state)

        logger.info("部署完成")
        return True

    def cancel_deployment(self) -> None:
        """取消部署"""
        if self._process:
            try:
                self._process.terminate()
                logger.info("部署进程已终止")
            except OSError as e:
                logger.warning("终止部署进程时发生错误: %s", e)

    # 私有方法

    async def _install_intelligence_installer(
        self,
        progress_callback: Callable[[DeploymentState], None] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        安装 openeuler-intelligence-installer 包

        Returns:
            tuple[bool, list[str]]: (是否成功安装, 错误信息列表)

        """
        errors = []

        try:
            temp_state = DeploymentState()
            if progress_callback:
                temp_state.add_log("正在安装 openeuler-intelligence-installer...")
                progress_callback(temp_state)

            # 执行安装命令
            cmd = ["sudo", "dnf", "install", "-y", "openeuler-intelligence-installer"]
            success, output_lines = await self._execute_install_command(cmd, progress_callback, temp_state)

            if success:
                # 验证安装是否成功
                if self.resource_manager.check_installer_available():
                    if progress_callback:
                        temp_state.add_log("✓ openeuler-intelligence-installer 安装成功")
                        progress_callback(temp_state)
                    return True, []

                errors.append("openeuler-intelligence-installer 安装后资源文件仍然缺失")
                return False, errors

            errors.append("安装 openeuler-intelligence-installer 失败")
            # 添加安装输出到错误信息
            if output_lines:
                errors.append("安装输出:")
                errors.extend(output_lines[-5:])  # 只显示最后5行

        except Exception as e:
            errors.append(f"安装过程中发生异常: {e}")
            logger.exception("安装 openeuler-intelligence-installer 时发生异常")

        return False, errors

    async def _execute_deployment_steps(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """执行所有部署步骤"""
        # 检查并停止旧的 framework 服务
        if not await self._check_and_stop_old_service(progress_callback):
            return False

        # 定义基础部署步骤
        steps = [
            self._check_environment,
            self._run_env_check_script,
            self._run_install_dependency_script,
            self._generate_config_files,
            self._setup_deploy_mode,
            self._run_init_config_script,
        ]

        # 轻量化部署模式下才自动执行 Agent 初始化
        if config.deployment_mode == "light":
            steps.append(self._run_agent_init)

        # 依次执行每个步骤
        for step in steps:
            if not await step(config, progress_callback):
                return False

        # 如果是全量部署模式，提示用户到网页端完成 Agent 配置
        if config.deployment_mode == "full":
            self.state.add_log("✓ 基础服务部署完成")
            self.state.add_log("请访问网页管理界面完成 Agent 服务配置")
            self.state.add_log(f"管理界面地址: http://{config.server_ip}:8080")

        return True

    async def _execute_install_command(
        self,
        cmd: list[str],
        progress_callback: Callable[[DeploymentState], None] | None,
        temp_state: DeploymentState,
    ) -> tuple[bool, list[str]]:
        """执行安装命令"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # 读取安装输出
        output_lines = []
        if process.stdout:
            while True:
                try:
                    # 使用超时读取，避免长时间阻塞
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.1,  # 100ms 超时
                    )
                except TimeoutError:
                    # 超时时让出控制权给 UI 事件循环
                    await asyncio.sleep(0)
                    continue

                if not line:
                    break

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                if decoded_line:
                    output_lines.append(decoded_line)
                    if progress_callback:
                        temp_state.add_log(f"安装: {decoded_line}")
                        progress_callback(temp_state)

                # 每次读取后让出控制权
                await asyncio.sleep(0)

        # 等待进程结束
        return_code = await process.wait()
        return return_code == 0, output_lines

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
        if not self.detect_openeuler():
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
        if not await self.check_sudo_privileges():
            self.state.add_log("✗ 错误: 需要管理员权限")
            return False
        self.state.add_log("✓ 具有管理员权限")

        return True

    async def _run_env_check_script(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行环境检查脚本"""
        self.state.current_step = 2
        self.state.current_step_name = "环境检查"
        self.state.add_log("正在执行系统环境检查...")

        if progress_callback:
            progress_callback(self.state)

        try:
            script_path = self.resource_manager.INSTALLER_BASE_PATH / "1-check-env" / "check_env.sh"
            return await self._run_script(script_path, "环境检查脚本", progress_callback)
        except Exception as e:
            self.state.add_log(f"✗ 环境检查失败: {e}")
            logger.exception("环境检查脚本执行失败")
            return False

    async def _run_install_dependency_script(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行依赖安装脚本"""
        self.state.current_step = 3
        self.state.current_step_name = "安装依赖组件"
        self.state.add_log("正在安装 openEuler Intelligence 依赖组件...")

        if progress_callback:
            progress_callback(self.state)

        try:
            script_path = (
                self.resource_manager.INSTALLER_BASE_PATH / "2-install-dependency" / "install_openEulerIntelligence.sh"
            )
            return await self._run_script(script_path, "依赖安装脚本", progress_callback)
        except Exception as e:
            self.state.add_log(f"✗ 依赖安装失败: {e}")
            logger.exception("依赖安装脚本执行失败")
            return False

    async def _run_init_config_script(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行配置初始化脚本"""
        self.state.current_step = 6
        self.state.current_step_name = "初始化配置和服务"
        self.state.add_log("正在初始化配置和启动服务...")

        if progress_callback:
            progress_callback(self.state)

        try:
            script_path = self.resource_manager.INSTALLER_BASE_PATH / "3-install-server" / "init_config.sh"
            return await self._run_script(script_path, "配置初始化脚本", progress_callback)
        except Exception as e:
            self.state.add_log(f"✗ 配置初始化失败: {e}")
            logger.exception("配置初始化脚本执行失败")
            return False

    async def _run_script(
        self,
        script_path: Path,
        script_name: str,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行部署脚本"""
        if not script_path.exists():
            self.state.add_log(f"✗ 脚本文件不存在: {script_path}")
            return False

        try:
            # 切换到脚本所在目录
            script_dir = script_path.parent
            script_file = script_path.name

            cmd = ["sudo", "bash", script_file]

            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=script_dir,
            )

            # 创建心跳任务，定期更新界面
            heartbeat_task = asyncio.create_task(self._heartbeat_progress(progress_callback))

            try:
                # 读取输出
                async for line in self._read_process_output():
                    self.state.add_log(line)
                    if progress_callback:
                        progress_callback(self.state)

                # 等待进程结束
                return_code = await self._process.wait()
            finally:
                # 取消心跳任务
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

            self._process = None

            if return_code == 0:
                self.state.add_log(f"✓ {script_name}执行成功")
                return True

        except Exception as e:
            self.state.add_log(f"✗ 运行{script_name}时发生错误: {e}")
            logger.exception("运行脚本失败: %s", script_path)
            return False

        else:
            self.state.add_log(f"✗ {script_name}执行失败，返回码: {return_code}")
            return False

    async def _heartbeat_progress(self, progress_callback: Callable[[DeploymentState], None] | None) -> None:
        """心跳进度更新，确保界面不会卡死"""
        if not progress_callback:
            return

        with contextlib.suppress(asyncio.CancelledError):
            while True:
                await asyncio.sleep(1.0)  # 每秒更新一次
                if progress_callback:
                    progress_callback(self.state)

    async def _generate_config_files(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """生成配置文件"""
        self.state.current_step = 4
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

        return True

    async def _setup_deploy_mode(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """设置部署模式"""
        self.state.current_step = 5
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
                str(self.resource_manager.INSTALL_MODE_FILE),
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

        return True

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
        backup_process = await asyncio.create_subprocess_exec(
            *backup_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, backup_stderr = await backup_process.communicate()

        if backup_process.returncode != 0:
            error_msg = backup_stderr.decode("utf-8", errors="ignore").strip()
            msg = f"备份 env 文件失败: {error_msg}"
            raise RuntimeError(msg)

        # 写入更新后的内容
        write_cmd = ["sudo", "tee", str(self.resource_manager.ENV_TEMPLATE)]
        process = await asyncio.create_subprocess_exec(
            *write_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, write_stderr = await process.communicate(updated_content.encode())

        if process.returncode != 0:
            error_msg = write_stderr.decode("utf-8", errors="ignore").strip()
            msg = f"写入 env 文件失败: {error_msg}"
            raise RuntimeError(msg)

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
        backup_process = await asyncio.create_subprocess_exec(
            *backup_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, backup_stderr = await backup_process.communicate()

        if backup_process.returncode != 0:
            error_msg = backup_stderr.decode("utf-8", errors="ignore").strip()
            msg = f"备份 config.toml 文件失败: {error_msg}"
            raise RuntimeError(msg)

        # 写入更新后的内容
        write_cmd = ["sudo", "tee", str(self.resource_manager.CONFIG_TEMPLATE)]
        process = await asyncio.create_subprocess_exec(
            *write_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, write_stderr = await process.communicate(updated_content.encode())

        if process.returncode != 0:
            error_msg = write_stderr.decode("utf-8", errors="ignore").strip()
            msg = f"写入 config.toml 文件失败: {error_msg}"
            raise RuntimeError(msg)

    async def _read_process_output(self) -> AsyncGenerator[str, None]:
        """读取进程输出"""
        if not self._process or not self._process.stdout:
            return

        while True:
            try:
                # 使用超时读取，避免长时间阻塞
                try:
                    line = await asyncio.wait_for(
                        self._process.stdout.readline(),
                        timeout=0.1,  # 100ms 超时
                    )
                except TimeoutError:
                    # 超时时让出控制权给 UI 事件循环
                    await asyncio.sleep(0)
                    continue

                if not line:
                    break

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                if decoded_line:
                    yield decoded_line

                # 每次读取后让出控制权
                await asyncio.sleep(0)

            except OSError as e:
                logger.warning("读取进程输出时发生错误: %s", e)
                break

    async def _check_framework_service_health(
        self,
        server_ip: str,
        server_port: int,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查 framework 服务健康状态"""
        # 1. 检查 systemctl framework 服务状态
        if not await self._check_systemctl_service_status(progress_callback):
            return False

        # 2. 检查 HTTP API 接口连通性
        return await self._check_framework_api_health(server_ip, server_port, progress_callback)

    async def _check_systemctl_service_status(
        self,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查 systemctl framework 服务状态，每2秒检查一次，5次后超时"""
        max_attempts = 5
        check_interval = 2.0  # 2秒

        for attempt in range(1, max_attempts + 1):
            self.state.add_log(f"检查 framework 服务状态 ({attempt}/{max_attempts})...")

            if progress_callback:
                progress_callback(self.state)

            try:
                # 使用 systemctl is-active 检查服务状态
                process = await asyncio.create_subprocess_exec(
                    "systemctl",
                    "is-active",
                    "framework",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()
                status = stdout.decode("utf-8").strip()

                if process.returncode == 0 and status == "active":
                    self.state.add_log("✓ Framework 服务状态正常")
                    return True

                self.state.add_log(f"Framework 服务状态: {status}")

                if attempt < max_attempts:
                    self.state.add_log(f"等待 {check_interval} 秒后重试...")
                    await asyncio.sleep(check_interval)

            except (OSError, TimeoutError) as e:
                self.state.add_log(f"检查服务状态时发生错误: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(check_interval)

        self.state.add_log("✗ Framework 服务状态检查超时失败")
        return False

    async def _check_framework_api_health(
        self,
        server_ip: str,
        server_port: int,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查 framework API 健康状态，每10秒检查一次，5分钟后超时"""
        max_attempts = 30
        check_interval = 10.0  # 10秒
        api_url = f"http://{server_ip}:{server_port}/api/user"
        http_ok = 200  # HTTP OK 状态码

        self.state.add_log("等待 openEuler Intelligence 服务就绪")

        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            for attempt in range(1, max_attempts + 1):
                logger.debug("第 %d 次检查 openEuler Intelligence 服务状态...", attempt)
                if progress_callback:
                    progress_callback(self.state)

                try:
                    response = await client.get(api_url)

                    if response.status_code == http_ok:
                        self.state.add_log("✓ openEuler Intelligence 服务已就绪")
                        return True

                except httpx.ConnectError:
                    pass
                except httpx.TimeoutException:
                    self.state.add_log(f"连接 {api_url} 超时")
                except (httpx.RequestError, OSError) as e:
                    self.state.add_log(f"API 连通性检查时发生错误: {e}")

                if attempt < max_attempts:
                    await asyncio.sleep(check_interval)

        self.state.add_log("✗ openEuler Intelligence API 服务检查超时失败")
        return False

    async def _run_agent_init(
        self,
        config: DeploymentConfig,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """运行 Agent 初始化脚本"""
        self.state.current_step = 7
        self.state.current_step_name = "初始化 Agent 服务"
        self.state.add_log("正在检查 openEuler Intelligence 后端服务状态...")

        if progress_callback:
            progress_callback(self.state)

        # 使用配置中的服务器 IP 和默认端口
        server_ip = config.server_ip or "127.0.0.1"
        server_port = 8002

        # 检查 openEuler Intelligence 后端服务状态
        if not await self._check_framework_service_health(server_ip, server_port, progress_callback):
            self.state.add_log("✗ openEuler Intelligence 服务检查失败")
            return False

        self.state.add_log("✓ openEuler Intelligence 服务检查通过，开始初始化 Agent...")

        if progress_callback:
            progress_callback(self.state)

        # 初始化 Agent 和 MCP 服务
        agent_manager = AgentManager(server_ip=server_ip, server_port=server_port)
        success = await agent_manager.initialize_agents(progress_callback)

        if success:
            self.state.add_log("✓ Agent 初始化完成")
        else:
            self.state.add_log("✗ Agent 初始化失败")

        return success

    async def _create_global_config_template(self, config: DeploymentConfig) -> None:
        """
        创建全局配置模板

        基于当前 root 用户的实际配置创建全局配置模板，供其他用户使用
        这样可以确保模板包含部署过程中生成的所有配置信息（如 Agent AppID 等）
        同时将部署时经过验证的大模型配置设置为默认的 OpenAI 配置

        Args:
            config: 部署配置

        """
        try:
            # 获取当前root用户的实际配置（包含 Agent 初始化后的完整配置）
            current_config_manager = ConfigManager()

            # 创建专用的模板配置管理器
            template_manager = ConfigManager.create_deployment_manager()

            # 将当前root用户的完整配置复制到模板中
            template_manager.data = current_config_manager.data

            # 将部署时用户输入的经过验证的大模型信息设置为默认的 OpenAI 配置
            # 这样其他用户可以直接使用这些已验证的配置
            template_manager.set_base_url(config.llm.endpoint)
            template_manager.set_model(config.llm.model)
            template_manager.set_api_key(config.llm.api_key)

            # 创建全局配置模板文件
            success = template_manager.create_global_template()

            if success:
                self.state.add_log("✓ 全局配置模板创建成功，其他用户可正常使用")
                logger.info("全局配置模板创建成功，包含部署时的大模型配置")
            else:
                self.state.add_log("⚠ 全局配置模板创建失败，可能影响其他用户使用")
                logger.warning("全局配置模板创建失败")

        except Exception:
            logger.exception("创建全局配置模板时发生异常")
            self.state.add_log("⚠ 配置模板创建异常，可能影响其他用户使用")

    async def _check_and_stop_old_service(
        self,
        progress_callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """
        检查并停止旧的 framework 和 rag 服务

        Args:
            progress_callback: 进度回调函数

        Returns:
            bool: 处理是否成功

        """
        if progress_callback:
            progress_callback(self.state)

        services_to_check = ["framework", "rag"]

        for service_name in services_to_check:
            try:
                # 检查服务状态
                process = await asyncio.create_subprocess_exec(
                    "systemctl",
                    "is-active",
                    service_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()
                status = stdout.decode("utf-8").strip()

                if process.returncode == 0 and status == "active":
                    logger.info("发现正在运行的 %s 服务，正在停止...", service_name)

                    if progress_callback:
                        progress_callback(self.state)

                    # 停止服务
                    stop_process = await asyncio.create_subprocess_exec(
                        "sudo",
                        "systemctl",
                        "stop",
                        service_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    _, stop_stderr = await stop_process.communicate()

                    if stop_process.returncode == 0:
                        logger.info("旧的 %s 服务已停止", service_name)
                    else:
                        error_msg = stop_stderr.decode("utf-8", errors="ignore").strip()
                        logger.warning("⚠ 停止 %s 服务时出现警告: %s", service_name, error_msg)
                        # 继续部署，不因停止服务失败而中断

                    # 等待服务完全停止
                    await asyncio.sleep(1.0)

                elif status in ("inactive", "failed"):
                    logger.info("✓ 没有发现运行中的 %s 服务", service_name)
                else:
                    logger.warning("%s 服务状态: %s", service_name.capitalize(), status)

            except (OSError, TimeoutError) as e:
                # 如果系统中没有该服务，systemctl 命令可能会失败
                # 这种情况下我们记录信息但不阻止部署继续进行
                logger.warning("检查 %s 服务状态时发生错误: %s", service_name, e)
                continue

            except Exception:
                logger.exception("处理 %s 服务时发生异常", service_name)
                return False

        # 等待所有服务完全停止
        await asyncio.sleep(1.0)

        return True
