"""
Agent 管理模块。

处理 MCP 服务和智能体的注册、安装、激活和管理。

该模块提供:
- McpConfig: MCP 配置数据模型
- McpConfigLoader: MCP 配置文件加载器
- ApiClient: HTTP API 客户端
- AgentManager: 智能体管理器主类
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from config.manager import ConfigManager
from log.manager import get_logger

from .models import AgentInitStatus, DeploymentState

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# HTTP 状态码常量
HTTP_OK = 200


class ConfigError(Exception):
    """配置错误异常"""


class ApiError(Exception):
    """API 错误异常"""


@dataclass
class McpConfig:
    """MCP 配置模型"""

    name: str
    description: str
    overview: str
    config: dict[str, Any]
    mcp_type: str


@dataclass
class McpServerInfo:
    """MCP 服务信息"""

    service_id: str
    name: str
    config_path: Path
    config: McpConfig


@dataclass
class AgentInfo:
    """智能体信息"""

    app_id: str
    name: str
    description: str
    mcp_services: list[str]


class McpConfigLoader:
    """MCP 配置加载器"""

    def __init__(self, config_dir: Path) -> None:
        """初始化配置加载器"""
        self.config_dir = config_dir

    def load_all_configs(self) -> list[tuple[Path, McpConfig]]:
        """加载所有 MCP 配置"""
        configs = []
        if not self.config_dir.exists():
            msg = f"配置目录不存在: {self.config_dir}"
            logger.error(msg)
            raise ConfigError(msg)

        for subdir in self.config_dir.iterdir():
            if subdir.is_dir():
                config_file = subdir / "config.json"
                if config_file.exists():
                    try:
                        config = self._load_config(config_file, subdir.name)
                        configs.append((config_file, config))
                        logger.info("加载 MCP 配置: %s", subdir.name)
                    except (json.JSONDecodeError, KeyError):
                        logger.exception("加载配置文件失败: %s", config_file)
                        continue

        if not configs:
            msg = f"未找到有效的 MCP 配置文件在: {self.config_dir}"
            logger.warning(msg)

        return configs

    def _load_config(self, config_file: Path, name: str) -> McpConfig:
        """加载单个配置文件"""
        with config_file.open(encoding="utf-8") as f:
            config_data = json.load(f)

        return McpConfig(
            name=config_data.get("name", name),
            description=config_data.get("description", name),
            overview=config_data.get("overview", name),
            config=config_data.get("config", {}),
            mcp_type=config_data.get("mcpType", "sse"),
        )


class ApiClient:
    """API 客户端"""

    def __init__(self, server_ip: str, server_port: int) -> None:
        """初始化 API 客户端"""
        self.base_url = f"http://{server_ip}:{server_port}"
        self.timeout = 60.0  # httpx 使用浮点数作为超时

    async def register_mcp_service(self, config: McpConfig) -> str:
        """注册 MCP 服务"""
        url = f"{self.base_url}/api/mcp"
        payload = {
            "name": config.name,
            "description": config.description,
            "overview": config.overview,
            "config": config.config,
            "mcpType": config.mcp_type,
        }

        logger.info("注册 MCP 服务: %s", config.name)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("code") != HTTP_OK:
                    msg = f"注册 MCP 服务失败: {result.get('message', 'Unknown error')}"
                    logger.error(msg)
                    raise ApiError(msg)

                service_id = result["result"]["serviceId"]
                logger.info("MCP 服务注册成功: %s -> %s", config.name, service_id)

            except httpx.RequestError as e:
                msg = f"注册 MCP 服务网络错误: {e}"
                logger.exception(msg)
                raise ApiError(msg) from e

            else:
                return service_id

    async def install_mcp_service(self, service_id: str) -> None:
        """安装 MCP 服务"""
        url = f"{self.base_url}/api/mcp/{service_id}/install?install=true"

        logger.info("安装 MCP 服务: %s", service_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url)
                response.raise_for_status()
                logger.info("MCP 服务安装请求已发送: %s", service_id)
            except httpx.RequestError as e:
                msg = f"安装 MCP 服务网络错误: {e}"
                logger.exception(msg)
                raise ApiError(msg) from e

    async def check_mcp_service_status(self, service_id: str) -> str | None:
        """
        检查 MCP 服务状态

        返回值:
        - "ready": 安装完成且成功
        - "failed": 安装失败
        - "cancelled": 安装取消
        - "init": 初始化中
        - "installing": 安装中
        - None: 网络错误或无法获取状态
        """
        url = f"{self.base_url}/api/mcp/{service_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                result = response.json()
                # 检查 API 调用是否成功
                if result.get("code") != HTTP_OK:
                    logger.warning("获取 MCP 服务状态失败: %s", result.get("message", "Unknown error"))
                    return None

                # 获取服务状态
                service_result = result.get("result", {})
                status = service_result.get("status")

                if status in ("ready", "failed", "cancelled", "init", "installing"):
                    return status

                logger.warning("未知的 MCP 服务状态: %s", status)

            except httpx.RequestError as e:
                logger.debug("检查 MCP 服务状态网络错误: %s", e)

            return None

    async def wait_for_installation(
        self,
        service_id: str,
        max_wait_time: int = 300,
        check_interval: int = 10,
    ) -> bool:
        """
        等待 MCP 服务安装完成

        只要接口能打通、后端返回的状态没有明确成功或失败或取消，就会一直等下去。
        只有在明确失败或取消时才返回 False。
        """
        logger.info("等待 MCP 服务安装完成: %s", service_id)

        attempt = 0
        while True:
            status = await self.check_mcp_service_status(service_id)

            if status == "ready":
                logger.info("MCP 服务安装完成: %s", service_id)
                return True

            if status in ("failed", "cancelled"):
                logger.error("MCP 服务安装失败或被取消: %s (状态: %s)", service_id, status)
                return False

            if status in ("init", "installing"):
                logger.debug(
                    "MCP 服务 %s %s中... (第 %d 次检查)",
                    service_id,
                    "初始化" if status == "init" else "安装",
                    attempt + 1,
                )
            elif status is None:
                logger.debug("MCP 服务 %s 状态检查失败，继续等待... (第 %d 次检查)", service_id, attempt + 1)
            else:
                logger.debug("MCP 服务 %s 状态未知: %s，继续等待... (第 %d 次检查)", service_id, status, attempt + 1)

            # 只有在超过最大等待时间时才超时返回，但仅在没有明确失败的情况下
            attempt += 1
            if attempt * check_interval >= max_wait_time:
                # 这里不返回 False，而是继续等待，因为要求只要接口能打通就一直等
                logger.warning("MCP 服务安装等待超时: %s (已等待 %d 秒，但将继续尝试)", service_id, max_wait_time)

            await asyncio.sleep(check_interval)

    async def activate_mcp_service(self, service_id: str) -> None:
        """激活 MCP 服务"""
        url = f"{self.base_url}/api/mcp/{service_id}"
        payload = {"active": True}

        logger.info("激活 MCP 服务: %s", service_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("code") != HTTP_OK:
                    msg = f"激活 MCP 服务失败: {result.get('message', 'Unknown error')}"
                    logger.error(msg)
                    raise ApiError(msg)

                logger.info("MCP 服务激活成功: %s", service_id)

            except httpx.RequestError as e:
                msg = f"激活 MCP 服务网络错误: {e}"
                logger.exception(msg)
                raise ApiError(msg) from e

    async def create_agent(
        self,
        name: str,
        description: str,
        mcp_service_ids: list[str],
    ) -> str:
        """创建智能体"""
        url = f"{self.base_url}/api/app"
        payload = {
            "appType": "agent",
            "name": name,
            "description": description,
            "mcpService": mcp_service_ids,
        }

        logger.info("创建智能体: %s (包含 %d 个 MCP 服务)", name, len(mcp_service_ids))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("code") != HTTP_OK:
                    msg = f"创建智能体失败: {result.get('message', 'Unknown error')}"
                    logger.error(msg)
                    raise ApiError(msg)

                app_id = result["result"]["appId"]
                logger.info("智能体创建成功: %s -> %s", name, app_id)

            except httpx.RequestError as e:
                msg = f"创建智能体网络错误: {e}"
                logger.exception(msg)
                raise ApiError(msg) from e

            else:
                return app_id

    async def publish_agent(self, app_id: str) -> None:
        """发布智能体"""
        url = f"{self.base_url}/api/app/{app_id}"

        logger.info("发布智能体: %s", app_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url)
                response.raise_for_status()

                result = response.json()
                if result.get("code") != HTTP_OK:
                    msg = f"发布智能体失败: {result.get('message', 'Unknown error')}"
                    logger.error(msg)
                    raise ApiError(msg)

                logger.info("智能体发布成功: %s", app_id)

            except httpx.RequestError as e:
                msg = f"发布智能体网络错误: {e}"
                logger.exception(msg)
                raise ApiError(msg) from e


class AgentManager:
    """智能体管理器"""

    def __init__(self, server_ip: str = "127.0.0.1", server_port: int = 8002) -> None:
        """初始化智能体管理器"""
        self.api_client = ApiClient(server_ip, server_port)
        self.config_manager = ConfigManager()

        resource_paths = [
            Path("/usr/lib/openeuler-intelligence/scripts/5-resource"),  # 生产环境
            Path("scripts/deploy/5-resource"),  # 开发环境（相对路径）
            Path(__file__).parent.parent.parent / "scripts/deploy/5-resource",  # 开发环境（绝对路径）
        ]

        self.resource_dir = next((p for p in resource_paths if p.exists()), None)
        if not self.resource_dir:
            logger.error("[DeploymentHelper] 未找到有效的资源路径")
            return
        logger.info("[DeploymentHelper] 使用资源路径: %s", self.resource_dir)

        self.mcp_config_dir = self.resource_dir / "mcp_config"

    async def initialize_agents(
        self,
        progress_callback: Callable[[DeploymentState], None] | None = None,
    ) -> AgentInitStatus:
        """
        初始化智能体

        Returns:
            AgentInitStatus: 初始化状态 (SUCCESS/SKIPPED/FAILED)

        """
        state = DeploymentState()
        self._report_progress(state, "[bold blue]开始初始化智能体...[/bold blue]", progress_callback)

        try:
            # 预处理：检查必要的 RPM 包可用性
            rpm_availability_result = await self._check_prerequisite_packages_availability(state, progress_callback)
            if rpm_availability_result == AgentInitStatus.SKIPPED:
                return AgentInitStatus.SKIPPED

            # 安装必要的 RPM 包
            if not await self._install_prerequisite_packages(state, progress_callback):
                return AgentInitStatus.FAILED

            # 加载配置
            configs = await self._load_mcp_configs(state, progress_callback)
            if not configs:
                return AgentInitStatus.FAILED

            # 处理 MCP 服务
            os_service_ids, systrace_service_ids = await self._process_all_mcp_services(
                configs,
                state,
                progress_callback,
            )

            if not os_service_ids and not systrace_service_ids:
                self._report_progress(state, "[red]所有 MCP 服务处理失败[/red]", progress_callback)
                return AgentInitStatus.FAILED

            # 创建智能体
            default_app_id = await self._create_multiple_agents(
                os_service_ids,
                systrace_service_ids,
                state,
                progress_callback,
            )

            self._report_progress(
                state,
                f"[bold green]智能体初始化完成! 默认 App ID: {default_app_id}[/bold green]",
                progress_callback,
            )
            logger.info("智能体初始化成功完成，默认 App ID: %s", default_app_id)

        except Exception as e:
            error_msg = f"智能体初始化失败: {e}"
            self._report_progress(state, f"[red]{error_msg}[/red]", progress_callback)
            logger.exception(error_msg)
            return AgentInitStatus.FAILED

        else:
            return AgentInitStatus.SUCCESS

    def _report_progress(
        self,
        state: DeploymentState,
        message: str,
        callback: Callable[[DeploymentState], None] | None = None,
    ) -> None:
        """报告进度"""
        state.add_log(message)
        if callback:
            callback(state)

    async def _load_mcp_configs(
        self,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> list[tuple[Path, McpConfig]]:
        """加载 MCP 配置"""
        self._report_progress(state, "[cyan]加载 MCP 配置文件...[/cyan]", callback)

        config_loader = McpConfigLoader(self.mcp_config_dir)
        configs = config_loader.load_all_configs()

        if not configs:
            self._report_progress(state, "[yellow]未找到 MCP 配置文件[/yellow]", callback)
            return []

        self._report_progress(state, f"[green]成功加载 {len(configs)} 个 MCP 配置[/green]", callback)
        return configs

    async def _process_all_mcp_services(
        self,
        configs: list[tuple[Path, McpConfig]],
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> tuple[list[str], list[str]]:
        """
        处理所有 MCP 服务

        Returns:
            tuple[list[str], list[str]]: (os_service_ids, systrace_service_ids)

        """
        os_service_ids = []
        systrace_service_ids = []

        for config_path, config in configs:
            self._report_progress(state, f"[magenta]处理 MCP 服务: {config.name}[/magenta]", callback)

            service_id = await self._process_mcp_service(config, state, callback)
            if service_id:
                # 根据配置路径判断是否为 sysTrace 相关服务
                if "systrace" in config_path.parent.name.lower() or "systrace" in config.name.lower():
                    systrace_service_ids.append(service_id)
                else:
                    os_service_ids.append(service_id)
            else:
                self._report_progress(state, f"[red]MCP 服务 {config.name} 处理失败[/red]", callback)

        return os_service_ids, systrace_service_ids

    async def _create_multiple_agents(
        self,
        os_service_ids: list[str],
        systrace_service_ids: list[str],
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> str:
        """创建多个智能体，返回默认智能体 ID"""
        default_app_id = None

        # 创建 OS 智能助手（如果有相应的服务）
        if os_service_ids:
            self._report_progress(
                state,
                f"[bold cyan]创建 OS 智能助手 (包含 {len(os_service_ids)} 个 MCP 服务)[/bold cyan]",
                callback,
            )

            os_app_id = await self.api_client.create_agent(
                "OS 智能助手",
                "openEuler 智能助手",
                os_service_ids,
            )
            await self.api_client.publish_agent(os_app_id)

            self._report_progress(state, "[green]OS 智能助手创建成功[/green]", callback)
            default_app_id = os_app_id  # OS 智能助手作为默认应用

        # 创建慢卡检测智能助手（如果有相应的服务）
        if systrace_service_ids:
            self._report_progress(
                state,
                f"[bold magenta]创建慢卡检测智能助手 (包含 {len(systrace_service_ids)} 个 MCP 服务)[/bold magenta]",
                callback,
            )

            systrace_app_id = await self.api_client.create_agent(
                "慢卡检测智能助手",
                "检测集群中的慢卡问题",
                systrace_service_ids,
            )
            await self.api_client.publish_agent(systrace_app_id)

            self._report_progress(state, "[green]慢卡检测智能助手创建成功[/green]", callback)

        if default_app_id:
            self._report_progress(state, "[dim]保存默认智能体配置...[/dim]", callback)
            self.config_manager.set_default_app(default_app_id)

        return default_app_id or ""

    async def _register_mcp_service(
        self,
        config: McpConfig,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> str:
        """注册 MCP 服务"""
        self._report_progress(state, f"  [blue]注册 {config.name}...[/blue]", callback)
        return await self.api_client.register_mcp_service(config)

    async def _install_and_wait_mcp_service(
        self,
        service_id: str,
        config_name: str,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """安装并等待 MCP 服务完成"""
        self._report_progress(state, f"  [cyan]安装 {config_name} (ID: {service_id})...[/cyan]", callback)
        await self.api_client.install_mcp_service(service_id)

        self._report_progress(state, f"  [dim]等待 {config_name} 安装完成...[/dim]", callback)
        if not await self.api_client.wait_for_installation(service_id):
            self._report_progress(state, f"  [red]{config_name} 安装超时[/red]", callback)
            return False

        return True

    async def _activate_mcp_service(
        self,
        service_id: str,
        config_name: str,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> None:
        """激活 MCP 服务"""
        self._report_progress(state, f"  [yellow]激活 {config_name}...[/yellow]", callback)
        await self.api_client.activate_mcp_service(service_id)
        self._report_progress(state, f"  [green]{config_name} 处理完成[/green]", callback)

    async def _process_mcp_service(
        self,
        config: McpConfig,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> str | None:
        """处理单个 MCP 服务"""
        # 如果是 SSE 类型，先验证 URL可用且为SSE
        if config.mcp_type == "sse":
            valid = await self._validate_sse_endpoint(config, state, callback)
            if not valid:
                self._report_progress(
                    state,
                    f"  [red]MCP 服务 {config.name} SSE Endpoint 验证失败[/red]",
                    callback,
                )
                return None
        try:
            # 注册服务
            service_id = await self._register_mcp_service(config, state, callback)

            # 安装并等待完成
            if not await self._install_and_wait_mcp_service(service_id, config.name, state, callback):
                return None

            # 激活服务
            await self._activate_mcp_service(service_id, config.name, state, callback)

        except (ApiError, httpx.RequestError, Exception) as e:
            self._report_progress(state, f"  [red]{config.name} 处理失败: {e}[/red]", callback)
            logger.exception("MCP 服务 %s 处理失败", config.name)
            return None

        else:
            return service_id

    async def _validate_sse_endpoint(
        self,
        config: McpConfig,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """验证 SSE Endpoint 是否可用"""
        url = config.config.get("url") or ""
        self._report_progress(
            state,
            f"[magenta]验证 SSE Endpoint: {config.name} -> {url}[/magenta]",
            callback,
        )
        try:
            async with httpx.AsyncClient(timeout=self.api_client.timeout) as client:
                response = await client.get(
                    url,
                    headers={"Accept": "text/event-stream"},
                )
                if response.status_code != HTTP_OK:
                    self._report_progress(
                        state,
                        f"  [red]{config.name} URL 响应码非 200: {response.status_code}[/red]",
                        callback,
                    )
                    return False
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    self._report_progress(
                        state,
                        f"  [red]{config.name} Content-Type 非 SSE: {content_type}[/red]",
                        callback,
                    )
                    return False
                self._report_progress(state, f"  [green]{config.name} SSE Endpoint 验证通过[/green]", callback)
                return True
        except Exception as e:
            self._report_progress(state, f"  [red]{config.name} SSE 验证失败: {e}[/red]", callback)
            logger.exception("验证 SSE Endpoint 失败: %s", url)
            return False

    async def _install_prerequisite_packages(
        self,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """安装必要的 RPM 包（已知包可用的情况下）"""
        try:
            # 检查是否存在以 "systrace" 开头的子目录（不区分大小写）
            systrace_exists = self._check_systrace_config(state, callback)

            # 安装包（此时已知包是可用的）
            if systrace_exists:
                # 安装 sysTrace.rpmlist 中的包
                if not await self._install_rpm_packages("sysTrace.rpmlist", state, callback):
                    return False

                # 设置 systrace-mcpserver 服务开机启动并立即启动
                if not await self._setup_systrace_service(state, callback):
                    return False

            # 安装 mcp-servers.rpmlist 中的包
            return await self._install_rpm_packages("mcp-servers.rpmlist", state, callback)

        except Exception as e:
            error_msg = f"安装必要包失败: {e}"
            self._report_progress(state, f"[red]{error_msg}[/red]", callback)
            logger.exception(error_msg)
            return False

    async def _check_rpm_packages_availability(
        self,
        rpm_list_files: list[str],
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查 RPM 包是否在 yum 源中可用"""
        self._report_progress(state, "[cyan]检查 RPM 包在 yum 源中的可用性...[/cyan]", callback)

        if not self.resource_dir:
            self._report_progress(
                state,
                "[red]资源目录未找到，无法检查 RPM 包可用性[/red]",
                callback,
            )
            logger.error("资源目录未找到，无法检查 RPM 包可用性")
            return False

        all_packages = []

        # 收集所有需要检查的包
        for rpm_list_file in rpm_list_files:
            rpm_list_path = self.resource_dir / rpm_list_file

            if not rpm_list_path.exists():
                self._report_progress(
                    state,
                    f"[yellow]RPM 列表文件不存在: {rpm_list_file}，跳过检查[/yellow]",
                    callback,
                )
                logger.warning("RPM 列表文件不存在: %s", rpm_list_path)
                continue

            try:
                with rpm_list_path.open(encoding="utf-8") as f:
                    packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    all_packages.extend(packages)
            except Exception as e:
                self._report_progress(
                    state,
                    f"[red]读取 RPM 列表文件失败: {rpm_list_file} - {e}[/red]",
                    callback,
                )
                logger.exception("读取 RPM 列表文件失败: %s", rpm_list_path)
                return False

        if not all_packages:
            self._report_progress(state, "[dim]没有要检查的 RPM 包[/dim]", callback)
            return True

        # 检查每个包的可用性
        unavailable_packages = []

        for package in all_packages:
            # 使用 dnf list available 检查包是否可用
            check_cmd = f"dnf list available {package}"

            try:
                process = await asyncio.create_subprocess_shell(
                    check_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    unavailable_packages.append(package)
                    logger.warning("RPM 包不可用: %s", package)

            except Exception as e:
                self._report_progress(
                    state,
                    f"  [red]检查包 {package} 失败: {e}[/red]",
                    callback,
                )
                logger.exception("检查 RPM 包可用性失败: %s", package)
                unavailable_packages.append(package)

        # 如果有不可用的包，返回 False
        if unavailable_packages:
            self._report_progress(
                state,
                f"[dim]以下 RPM 包不可用，跳过智能体初始化: {', '.join(unavailable_packages)}[/dim]",
                callback,
            )
            logger.error("发现不可用的 RPM 包，跳过智能体初始化: %s", unavailable_packages)
            return False

        self._report_progress(
            state,
            "[green]所有 RPM 包均可用，继续智能体初始化[/green]",
            callback,
        )
        logger.info("所有 RPM 包均可用")
        return True

    async def _check_prerequisite_packages_availability(
        self,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> AgentInitStatus:
        """
        检查必要的 RPM 包是否在 yum 源中可用

        Returns:
            AgentInitStatus: SUCCESS 表示所有包可用，SKIPPED 表示有包不可用应跳过

        """
        try:
            # 准备要检查的 RPM 列表文件
            rpm_files_to_check = ["mcp-servers.rpmlist"]

            # 检查是否存在以 "systrace" 开头的子目录（不区分大小写）
            systrace_exists = self._check_systrace_config(state, callback)
            if systrace_exists:
                rpm_files_to_check.append("sysTrace.rpmlist")

            # 检查包可用性
            packages_available = await self._check_rpm_packages_availability(rpm_files_to_check, state, callback)

            if not packages_available:
                self._report_progress(
                    state,
                    "[yellow]MCP Server 相关 RPM 包可用性检查失败，跳过智能体初始化，其他部署步骤将继续进行[/yellow]",
                    callback,
                )
                return AgentInitStatus.SKIPPED

        except Exception as e:
            error_msg = f"检查 RPM 包可用性失败: {e}"
            self._report_progress(state, f"[red]{error_msg}[/red]", callback)
            logger.exception(error_msg)
            return AgentInitStatus.SKIPPED  # 检查失败也视为跳过，而不是整个部署失败

        else:
            return AgentInitStatus.SUCCESS

    def _check_systrace_config(
        self,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """检查是否存在以 systrace 开头的配置目录"""
        self._report_progress(state, "[cyan]检查 sysTrace 配置...[/cyan]", callback)

        if not self.resource_dir or not self.mcp_config_dir:
            self._report_progress(state, "[yellow]资源目录或 MCP 配置目录不存在[/yellow]", callback)
            return False

        if not self.mcp_config_dir.exists():
            self._report_progress(state, "[yellow]MCP 配置目录不存在[/yellow]", callback)
            return False

        for subdir in self.mcp_config_dir.iterdir():
            if subdir.is_dir() and subdir.name.lower().startswith("systrace"):
                self._report_progress(state, f"[green]发现 sysTrace 配置: {subdir.name}[/green]", callback)
                logger.info("发现 sysTrace 配置目录: %s", subdir.name)
                return True

        self._report_progress(state, "[dim]未发现 sysTrace 配置[/dim]", callback)
        return False

    async def _install_rpm_packages(
        self,
        rpm_list_file: str,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """安装指定 RPM 列表文件中的包"""
        if not self.resource_dir:
            self._report_progress(
                state,
                f"[red]资源目录未找到，无法安装 {rpm_list_file}[/red]",
                callback,
            )
            logger.error("资源目录未找到，无法安装 RPM 包: %s", rpm_list_file)
            return False

        rpm_list_path = self.resource_dir / rpm_list_file

        if not rpm_list_path.exists():
            self._report_progress(
                state,
                f"[yellow]RPM 列表文件不存在: {rpm_list_file}[/yellow]",
                callback,
            )
            logger.warning("RPM 列表文件不存在: %s", rpm_list_path)
            return True  # 文件不存在不算失败，继续执行

        self._report_progress(state, f"[cyan]安装 {rpm_list_file} 中的 RPM 包...[/cyan]", callback)

        try:
            # 读取 RPM 包列表
            with rpm_list_path.open(encoding="utf-8") as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

            if not packages:
                self._report_progress(state, f"[dim]{rpm_list_file} 中没有要安装的包[/dim]", callback)
                return True

            # 使用 dnf 安装包
            package_list = " ".join(packages)
            install_cmd = f"sudo dnf install -y {package_list}"

            self._report_progress(
                state,
                f"  [blue]执行安装命令: {install_cmd}[/blue]",
                callback,
            )
            logger.info("执行 RPM 包安装命令: %s", install_cmd)

            # 使用 asyncio.create_subprocess_shell 执行命令
            process = await asyncio.create_subprocess_shell(
                install_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""

            if process.returncode == 0:
                self._report_progress(
                    state,
                    f"  [green]{rpm_list_file} 中的包安装成功[/green]",
                    callback,
                )
                logger.info("RPM 包安装成功: %s", package_list)
            else:
                self._report_progress(
                    state,
                    f"  [red]{rpm_list_file} 中的包安装失败 (返回码: {process.returncode})[/red]",
                    callback,
                )
                logger.error("RPM 包安装失败: %s, 输出: %s", package_list, output)
                return False

        except Exception as e:
            error_msg = f"安装 {rpm_list_file} 失败: {e}"
            self._report_progress(state, f"  [red]{error_msg}[/red]", callback)
            logger.exception(error_msg)
            return False

        return True

    async def _setup_systrace_service(
        self,
        state: DeploymentState,
        callback: Callable[[DeploymentState], None] | None,
    ) -> bool:
        """设置 systrace-mcpserver 服务"""
        service_name = "systrace-mcpserver"
        self._report_progress(state, f"[magenta]设置 {service_name} 服务...[/magenta]", callback)

        try:
            # 启用服务开机启动
            enable_cmd = f"sudo systemctl enable {service_name}"
            self._report_progress(state, f"  [cyan]设置开机启动: {enable_cmd}[/cyan]", callback)

            process = await asyncio.create_subprocess_shell(
                enable_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""

            if process.returncode != 0:
                self._report_progress(
                    state,
                    f"  [red]设置 {service_name} 开机启动失败: {output}[/red]",
                    callback,
                )
                logger.error("设置服务开机启动失败: %s, 输出: %s", service_name, output)
                return False

            # 启动服务
            start_cmd = f"sudo systemctl start {service_name}"
            self._report_progress(state, f"  [blue]启动服务: {start_cmd}[/blue]", callback)

            process = await asyncio.create_subprocess_shell(
                start_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""

            if process.returncode == 0:
                self._report_progress(
                    state,
                    f"  [green]{service_name} 服务启动成功[/green]",
                    callback,
                )
                logger.info("sysTrace 服务启动成功: %s", service_name)
            else:
                self._report_progress(
                    state,
                    f"  [red]{service_name} 服务启动失败: {output}[/red]",
                    callback,
                )
                logger.error("sysTrace 服务启动失败: %s, 输出: %s", service_name, output)
                return False

        except Exception as e:
            error_msg = f"设置 {service_name} 服务失败: {e}"
            self._report_progress(state, f"  [red]{error_msg}[/red]", callback)
            logger.exception(error_msg)
            return False

        return True
