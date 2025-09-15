"""
LLM 配置管理工具

允许用户通过 TUI 界面修改已部署系统的 LLM 和 Embedding 配置。
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import toml
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Input, Label, Static, TabbedContent, TabPane

from app.deployment.models import EmbeddingConfig, LLMConfig
from log.manager import get_logger
from tool.validators import APIValidator

logger = get_logger(__name__)


@dataclass
class LLMSystemConfig:
    """
    系统 LLM 配置

    管理已部署系统的 LLM 和 Embedding 配置。
    """

    # 系统配置文件路径
    FRAMEWORK_CONFIG_PATH = Path("/etc/euler-copilot-framework/config.toml")
    RAG_ENV_PATH = Path("/etc/euler-copilot-rag/data_chain/env")

    # systemctl 服务名称
    RUNTIME_SERVICE = "oi-runtime"
    RAG_SERVICE = "oi-rag"

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    @classmethod
    def check_prerequisites(cls) -> tuple[bool, list[str]]:
        """
        检查前置条件

        Returns:
            tuple[bool, list[str]]: (是否满足条件, 错误消息列表)

        """
        errors = []

        # 检查是否以管理员权限运行
        if os.geteuid() != 0:
            errors.append("需要管理员权限才能修改系统配置文件")

        # 检查配置文件是否存在
        if not cls.FRAMEWORK_CONFIG_PATH.exists():
            errors.append(f"配置文件不存在: {cls.FRAMEWORK_CONFIG_PATH}")

        if not cls.RAG_ENV_PATH.exists():
            errors.append(f"配置文件不存在: {cls.RAG_ENV_PATH}")

        # 检查配置文件是否可写
        if cls.FRAMEWORK_CONFIG_PATH.exists() and not os.access(cls.FRAMEWORK_CONFIG_PATH, os.W_OK):
            errors.append(f"配置文件不可写: {cls.FRAMEWORK_CONFIG_PATH}")

        if cls.RAG_ENV_PATH.exists() and not os.access(cls.RAG_ENV_PATH, os.W_OK):
            errors.append(f"配置文件不可写: {cls.RAG_ENV_PATH}")

        return len(errors) == 0, errors

    @classmethod
    def load_current_config(cls) -> LLMSystemConfig:
        """
        从系统配置文件加载当前配置

        Returns:
            LLMSystemConfig: 当前系统配置

        """
        config = cls()

        try:
            # 从 config.toml 加载配置
            if cls.FRAMEWORK_CONFIG_PATH.exists():
                config._load_from_toml()

            # 从 env 文件加载配置（优先级更高）
            if cls.RAG_ENV_PATH.exists():
                config._load_from_env()

        except (OSError, ValueError, toml.TomlDecodeError) as e:
            logger.warning("加载系统配置时出现警告: %s", e)

        return config

    def _load_from_toml(self) -> None:
        """从 TOML 文件加载配置"""
        try:
            with self.FRAMEWORK_CONFIG_PATH.open(encoding="utf-8") as f:
                data = toml.load(f)

            # 加载 LLM 配置
            if "llm" in data:
                llm_data = data["llm"]
                self.llm.endpoint = llm_data.get("endpoint", "")
                self.llm.api_key = llm_data.get("key", "")
                self.llm.model = llm_data.get("model", "")
                self.llm.max_tokens = llm_data.get("max_tokens", 8192)
                self.llm.temperature = llm_data.get("temperature", 0.7)
                # TOML 中没有 request_timeout，使用默认值

            # 加载 Embedding 配置
            if "embedding" in data:
                embed_data = data["embedding"]
                self.embedding.type = embed_data.get("type", "openai")
                self.embedding.endpoint = embed_data.get("endpoint", "")
                self.embedding.api_key = embed_data.get("api_key", "")
                self.embedding.model = embed_data.get("model", "")

        except (OSError, toml.TomlDecodeError):
            logger.exception("从 TOML 文件加载配置失败")
            raise

    def _load_from_env(self) -> None:
        """从 ENV 文件加载配置（覆盖 TOML 配置）"""
        try:
            env_vars = {}
            with self.RAG_ENV_PATH.open(encoding="utf-8") as f:
                for file_line in f:
                    stripped_line = file_line.strip()
                    if stripped_line and not stripped_line.startswith("#") and "=" in stripped_line:
                        key, value = stripped_line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

            # 加载 LLM 配置
            self.llm.model = env_vars.get("MODEL_NAME", self.llm.model)
            self.llm.endpoint = env_vars.get("OPENAI_API_BASE", self.llm.endpoint)
            self.llm.api_key = env_vars.get("OPENAI_API_KEY", self.llm.api_key)

            with contextlib.suppress(ValueError):
                self.llm.max_tokens = int(env_vars["MAX_TOKENS"])

            with contextlib.suppress(ValueError):
                self.llm.temperature = float(env_vars["TEMPERATURE"])

            with contextlib.suppress(ValueError):
                self.llm.request_timeout = int(env_vars["REQUEST_TIMEOUT"])

            # 加载 Embedding 配置
            self.embedding.type = env_vars.get("EMBEDDING_TYPE", self.embedding.type)
            self.embedding.endpoint = env_vars.get("EMBEDDING_ENDPOINT", self.embedding.endpoint)
            self.embedding.api_key = env_vars.get("EMBEDDING_API_KEY", self.embedding.api_key)
            self.embedding.model = env_vars.get("EMBEDDING_MODEL_NAME", self.embedding.model)

        except OSError:
            logger.exception("从 ENV 文件加载配置失败")
            raise

    def save_config(self) -> None:
        """
        保存配置到系统文件

        Raises:
            OSError: 文件操作失败
            ValueError: 配置值无效

        """
        try:
            # 保存到 config.toml
            self._save_to_toml()

            # 保存到 env 文件
            self._save_to_env()

            logger.info("系统配置保存成功")

        except (OSError, ValueError, toml.TomlDecodeError):
            logger.exception("保存系统配置失败")
            raise

    def _save_to_toml(self) -> None:
        """保存配置到 TOML 文件"""
        try:
            # 读取现有配置
            with self.FRAMEWORK_CONFIG_PATH.open(encoding="utf-8") as f:
                data = toml.load(f)

            # 更新 LLM 配置
            if "llm" not in data:
                data["llm"] = {}
            data["llm"].update(
                {
                    "endpoint": self.llm.endpoint,
                    "key": self.llm.api_key,
                    "model": self.llm.model,
                    "max_tokens": self.llm.max_tokens,
                    "temperature": self.llm.temperature,
                },
            )

            # 更新 Embedding 配置
            if "embedding" not in data:
                data["embedding"] = {}
            data["embedding"].update(
                {
                    "type": self.embedding.type,
                    "endpoint": self.embedding.endpoint,
                    "api_key": self.embedding.api_key,
                    "model": self.embedding.model,
                },
            )

            # 写回文件
            with self.FRAMEWORK_CONFIG_PATH.open("w", encoding="utf-8") as f:
                toml.dump(data, f)

        except (OSError, toml.TomlDecodeError):
            logger.exception("保存到 TOML 文件失败")
            raise

    def _save_to_env(self) -> None:
        """保存配置到 ENV 文件"""
        try:
            # 读取现有文件内容
            lines = []
            with self.RAG_ENV_PATH.open(encoding="utf-8") as f:
                lines = f.readlines()

            # 更新配置值
            updated_vars = {
                "MODEL_NAME": self.llm.model,
                "OPENAI_API_BASE": self.llm.endpoint,
                "OPENAI_API_KEY": self.llm.api_key,
                "MAX_TOKENS": str(self.llm.max_tokens),
                "TEMPERATURE": str(self.llm.temperature),
                "REQUEST_TIMEOUT": str(self.llm.request_timeout),
                "EMBEDDING_TYPE": self.embedding.type,
                "EMBEDDING_ENDPOINT": self.embedding.endpoint,
                "EMBEDDING_API_KEY": self.embedding.api_key,
                "EMBEDDING_MODEL_NAME": self.embedding.model,
            }

            # 处理每一行
            new_lines = []
            updated_keys = set()

            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in updated_vars:
                        new_lines.append(f"{key} = {updated_vars[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # 添加没有更新的新配置项
            for key, value in updated_vars.items():
                if key not in updated_keys:
                    new_lines.append(f"{key} = {value}\n")

            # 写回文件
            with self.RAG_ENV_PATH.open("w", encoding="utf-8") as f:
                f.writelines(new_lines)

        except OSError:
            logger.exception("保存到 ENV 文件失败")
            raise

    def restart_services(self) -> tuple[bool, list[str]]:
        """
        重启相关 systemctl 服务

        Returns:
            tuple[bool, list[str]]: (是否成功, 错误消息列表)

        """
        errors = []

        for service in [self.RUNTIME_SERVICE, self.RAG_SERVICE]:
            try:
                # 验证服务名称以防止代码注入
                if service not in {self.RUNTIME_SERVICE, self.RAG_SERVICE}:
                    error_msg = f"无效的服务名称: {service}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                logger.info("正在重启服务: %s", service)
                # subprocess 调用是安全的，因为我们已经验证了服务名称
                subprocess.run(  # noqa: S603
                    ["/usr/bin/systemctl", "restart", service],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                logger.info("服务 %s 重启成功", service)

            except subprocess.CalledProcessError as e:
                error_msg = f"重启服务 {service} 失败: {e.stderr.strip() if e.stderr else str(e)}"
                logger.warning(error_msg)  # 不使用 exception，因为这是预期可能的错误
                errors.append(error_msg)

            except subprocess.TimeoutExpired:
                error_msg = f"重启服务 {service} 超时"
                logger.warning(error_msg)  # 不使用 exception，因为这是预期可能的错误
                errors.append(error_msg)

            except (OSError, FileNotFoundError) as e:
                error_msg = f"重启服务 {service} 时发生异常: {e}"
                logger.exception(error_msg)
                errors.append(error_msg)

        return len(errors) == 0, errors

    async def validate_llm_connectivity(self) -> tuple[bool, str, dict]:
        """
        验证 LLM API 连接性

        Returns:
            tuple[bool, str, dict]: (是否验证成功, 消息, 验证详细信息)

        """
        if not self.llm.endpoint.strip():
            return False, "LLM API 端点不能为空", {}

        validator = APIValidator()
        return await validator.validate_llm_config(
            self.llm.endpoint,
            self.llm.api_key,
            self.llm.model,
            self.llm.request_timeout,
        )

    async def validate_embedding_connectivity(self) -> tuple[bool, str, dict]:
        """
        验证 Embedding API 连接性

        Returns:
            tuple[bool, str, dict]: (是否验证成功, 消息, 验证详细信息)

        """
        if not self.embedding.endpoint.strip():
            return False, "Embedding API 端点不能为空", {}

        validator = APIValidator()
        return await validator.validate_embedding_config(
            self.embedding.endpoint,
            self.embedding.api_key,
            self.embedding.model,
            self.llm.request_timeout,
        )


class LLMConfigScreen(ModalScreen[bool]):
    """
    LLM 配置屏幕

    允许用户修改已部署系统的 LLM 和 Embedding 配置。
    """

    CSS = """
    LLMConfigScreen {
        align: center middle;
    }

    .config-container {
        width: 95%;
        max-width: 130;
        height: 95%;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }

    .form-row {
        height: 3;
        margin: 0;
    }

    .form-label {
        width: 18;
        text-align: left;
        text-style: bold;
        content-align: left middle;
    }

    .form-input {
        width: 1fr;
        margin-left: 1;
    }

    .button-row {
        height: 3;
        margin: 1 0 0 0;
        align: center middle;
    }

    #llm_validation_status, #embedding_validation_status {
        text-style: italic;
    }

    #save, #cancel {
        margin: 0 1;
        width: auto;
        min-height: 3;
        height: 3;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        height: auto;
        scrollbar-size: 1 1;
        overflow: auto;
    }

    .llm-config-container, .embedding-config-container {
        height: 1fr;
        scrollbar-size: 1 1;
        overflow-y: auto;
        overflow-x: hidden;
    }
    """

    def __init__(self) -> None:
        """初始化 LLM 配置屏幕"""
        super().__init__()
        self.config = LLMSystemConfig()
        self._llm_validation_task: asyncio.Task[None] | None = None
        self._embedding_validation_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(classes="config-container"):
            yield Header()

            with TabbedContent():
                with TabPane("LLM 配置", id="llm_tab"):
                    yield from self._compose_llm_config()

                with TabPane("Embedding 配置", id="embedding_tab"):
                    yield from self._compose_embedding_config()

            with Horizontal(classes="button-row"):
                yield Button("保存配置", id="save", variant="primary")
                yield Button("取消", id="cancel")

    def _compose_llm_config(self) -> ComposeResult:
        """组合 LLM 配置组件"""
        with Vertical(classes="llm-config-container"):
            yield Static("大语言模型配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("API 端点:", classes="form-label")
                yield Input(
                    value=self.config.llm.endpoint,
                    placeholder="模型 API 访问地址，如 ollama: http://localhost:11434/v1",
                    id="llm_endpoint",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("API 密钥:", classes="form-label")
                yield Input(
                    value=self.config.llm.api_key,
                    placeholder="API 访问密钥，可选，请根据模型提供商指引填写",
                    password=True,
                    id="llm_api_key",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("模型名称:", classes="form-label")
                yield Input(
                    value=self.config.llm.model,
                    placeholder="模型名称，可选，请根据模型提供商指引填写",
                    id="llm_model",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("最大令牌数:", classes="form-label")
                yield Input(
                    value=str(self.config.llm.max_tokens),
                    placeholder="8192",
                    id="llm_max_tokens",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("温度参数:", classes="form-label")
                yield Input(
                    value=str(self.config.llm.temperature),
                    placeholder="0.7",
                    id="llm_temperature",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("请求超时(秒):", classes="form-label")
                yield Input(
                    value=str(self.config.llm.request_timeout),
                    placeholder="300",
                    id="llm_timeout",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("验证状态:", classes="form-label")
                yield Static("未验证", id="llm_validation_status", classes="form-input")

    def _compose_embedding_config(self) -> ComposeResult:
        """组合 Embedding 配置组件"""
        with Vertical(classes="embedding-config-container"):
            yield Static("嵌入模型配置", classes="form-label")

            with Horizontal(classes="form-row"):
                yield Label("API 端点:", classes="form-label")
                yield Input(
                    value=self.config.embedding.endpoint,
                    placeholder="模型 API 访问地址，如 ollama: http://localhost:11434/v1",
                    id="embedding_endpoint",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("API 密钥:", classes="form-label")
                yield Input(
                    value=self.config.embedding.api_key,
                    placeholder="API 访问密钥，可选，请根据模型提供商指引填写",
                    password=True,
                    id="embedding_api_key",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("模型名称:", classes="form-label")
                yield Input(
                    value=self.config.embedding.model,
                    placeholder="模型名称，可选，请根据模型提供商指引填写",
                    id="embedding_model",
                    classes="form-input",
                )

            with Horizontal(classes="form-row"):
                yield Label("验证状态:", classes="form-label")
                yield Static("未验证", id="embedding_validation_status", classes="form-input")

    async def on_mount(self) -> None:
        """界面挂载时加载当前配置"""
        try:
            # 加载当前系统配置
            self.config = LLMSystemConfig.load_current_config()

            # 更新界面显示的值
            self._update_form_values()

        except (OSError, ValueError, AttributeError) as e:
            logger.exception("加载系统配置失败")
            self.notify(f"加载系统配置失败: {e}", severity="error")

    def _update_form_values(self) -> None:
        """更新表单显示的值"""
        try:
            # 更新 LLM 配置显示
            self.query_one("#llm_endpoint", Input).value = self.config.llm.endpoint
            self.query_one("#llm_api_key", Input).value = self.config.llm.api_key
            self.query_one("#llm_model", Input).value = self.config.llm.model
            self.query_one("#llm_max_tokens", Input).value = str(self.config.llm.max_tokens)
            self.query_one("#llm_temperature", Input).value = str(self.config.llm.temperature)
            self.query_one("#llm_timeout", Input).value = str(self.config.llm.request_timeout)

            # 更新 Embedding 配置显示
            self.query_one("#embedding_endpoint", Input).value = self.config.embedding.endpoint
            self.query_one("#embedding_api_key", Input).value = self.config.embedding.api_key
            self.query_one("#embedding_model", Input).value = self.config.embedding.model

        except (OSError, ValueError, AttributeError):
            logger.warning("更新表单值时出现警告")

    @on(Button.Pressed, "#save")
    async def on_save_button_pressed(self) -> None:
        """处理保存按钮点击"""
        if await self._collect_and_save_config():
            self.dismiss(result=True)

    @on(Button.Pressed, "#cancel")
    def on_cancel_button_pressed(self) -> None:
        """处理取消按钮点击"""
        self.dismiss(result=False)

    @on(Input.Changed, "#llm_endpoint, #llm_api_key, #llm_model")
    async def on_llm_field_changed(self, event: Input.Changed) -> None:
        """处理 LLM 字段变化，检查是否需要自动验证"""
        # 取消之前的验证任务
        if self._llm_validation_task and not self._llm_validation_task.done():
            self._llm_validation_task.cancel()

        # 检查是否所有核心字段都已填写
        if self._should_validate_llm():
            # 延迟验证，避免用户输入时频繁验证
            self._llm_validation_task = asyncio.create_task(self._delayed_llm_validation())

    @on(Input.Changed, "#embedding_endpoint, #embedding_api_key, #embedding_model")
    async def on_embedding_field_changed(self, event: Input.Changed) -> None:
        """处理 Embedding 字段变化，检查是否需要自动验证"""
        # 取消之前的验证任务
        if self._embedding_validation_task and not self._embedding_validation_task.done():
            self._embedding_validation_task.cancel()

        # 检查是否所有核心字段都已填写
        if self._should_validate_embedding():
            # 延迟验证，避免用户输入时频繁验证
            self._embedding_validation_task = asyncio.create_task(self._delayed_embedding_validation())

    def _should_validate_llm(self) -> bool:
        """检查是否应该验证 LLM 配置"""
        try:
            endpoint = self.query_one("#llm_endpoint", Input).value.strip()
            api_key = self.query_one("#llm_api_key", Input).value.strip()
            model = self.query_one("#llm_model", Input).value.strip()
            return bool(endpoint and api_key and model)
        except (ValueError, AttributeError):
            return False

    def _should_validate_embedding(self) -> bool:
        """检查是否应该验证 Embedding 配置"""
        try:
            endpoint = self.query_one("#embedding_endpoint", Input).value.strip()
            api_key = self.query_one("#embedding_api_key", Input).value.strip()
            model = self.query_one("#embedding_model", Input).value.strip()
            return bool(endpoint and api_key and model)
        except (ValueError, AttributeError):
            return False

    async def _delayed_llm_validation(self) -> None:
        """延迟 LLM 验证"""
        try:
            await asyncio.sleep(1)  # 等待 1 秒
            await self._validate_llm_config()
        except asyncio.CancelledError:
            pass

    async def _delayed_embedding_validation(self) -> None:
        """延迟 Embedding 验证"""
        try:
            await asyncio.sleep(1)  # 等待 1 秒
            await self._validate_embedding_config()
        except asyncio.CancelledError:
            pass

    async def _validate_llm_config(self) -> None:
        """验证 LLM 配置"""
        # 更新状态为验证中
        status_widget = self.query_one("#llm_validation_status", Static)
        status_widget.update("[yellow]验证中...[/yellow]")

        # 收集当前 LLM 配置
        self._collect_llm_config()

        try:
            # 执行验证
            is_valid, message, info = await self.config.validate_llm_connectivity()

            # 更新验证状态
            if is_valid:
                status_widget.update(f"[green]✓ {message}[/green]")
            else:
                status_widget.update(f"[red]✗ {message}[/red]")

        except (ValueError, AttributeError, OSError) as e:
            status_widget.update(f"[red]✗ 验证异常: {e}[/red]")
            self.notify(f"LLM 验证过程中出现异常: {e}", severity="error")

    async def _validate_embedding_config(self) -> None:
        """验证 Embedding 配置"""
        # 更新状态为验证中
        status_widget = self.query_one("#embedding_validation_status", Static)
        status_widget.update("[yellow]验证中...[/yellow]")

        # 收集当前 Embedding 配置
        self._collect_embedding_config()

        try:
            # 执行验证
            is_valid, message, info = await self.config.validate_embedding_connectivity()

            # 更新验证状态
            if is_valid:
                status_widget.update(f"[green]✓ {message}[/green]")
            else:
                status_widget.update(f"[red]✗ {message}[/red]")

        except (ValueError, AttributeError, OSError) as e:
            status_widget.update(f"[red]✗ 验证异常: {e}[/red]")
            self.notify(f"Embedding 验证过程中出现异常: {e}", severity="error")

    def _collect_llm_config(self) -> None:
        """收集 LLM 配置"""
        try:
            self.config.llm.endpoint = self.query_one("#llm_endpoint", Input).value.strip()
            self.config.llm.api_key = self.query_one("#llm_api_key", Input).value.strip()
            self.config.llm.model = self.query_one("#llm_model", Input).value.strip()
            self.config.llm.max_tokens = int(self.query_one("#llm_max_tokens", Input).value or "8192")
            self.config.llm.temperature = float(self.query_one("#llm_temperature", Input).value or "0.7")
            self.config.llm.request_timeout = int(self.query_one("#llm_timeout", Input).value or "300")
        except (ValueError, AttributeError):
            # 如果转换失败，使用默认值
            pass

    def _collect_embedding_config(self) -> None:
        """收集 Embedding 配置"""
        try:
            self.config.embedding.type = "openai"  # 固定使用 openai 类型
            self.config.embedding.endpoint = self.query_one("#embedding_endpoint", Input).value.strip()
            self.config.embedding.api_key = self.query_one("#embedding_api_key", Input).value.strip()
            self.config.embedding.model = self.query_one("#embedding_model", Input).value.strip()
        except (ValueError, AttributeError):
            # 如果获取失败，记录警告并使用默认值
            logger.warning("获取 Embedding 配置失败，使用默认值")

    async def _collect_and_save_config(self) -> bool:
        """收集用户配置并保存"""
        try:
            # 收集配置
            self._collect_llm_config()
            self._collect_embedding_config()

            # 验证配置
            if not self.config.llm.endpoint.strip():
                self.notify("LLM API 端点不能为空", severity="error")
                return False

            # 保存配置
            self.config.save_config()
            self.notify("配置保存成功", severity="information")

            # 重启服务
            success, errors = self.config.restart_services()
            if success:
                self.notify("服务重启成功", severity="information")
            else:
                error_msg = "服务重启失败:\n" + "\n".join(errors)
                self.notify(error_msg, severity="error")

        except Exception as e:
            self.notify(f"保存配置失败: {e}", severity="error")
            logger.exception("保存配置失败:")
            return False
        else:
            return True


class LLMConfigApp(App[bool]):
    """LLM 配置应用"""

    def on_mount(self) -> None:
        """应用启动时显示配置屏幕"""
        self.push_screen(LLMConfigScreen(), self._handle_screen_result)

    def _handle_screen_result(self, result: bool | None) -> None:  # noqa: FBT001
        """处理配置屏幕结果"""
        self.exit(return_code=0 if result else 1)


def llm_config_main() -> None:
    """
    LLM 配置主函数

    --llm-config 参数的入口点。
    """
    logger.info("启动 LLM 配置工具")

    try:
        # 检查前置条件
        ok, errors = LLMSystemConfig.check_prerequisites()
        if not ok:
            sys.stderr.write("错误：无法启动 LLM 配置工具\n")
            for error in errors:
                sys.stderr.write(f"  - {error}\n")
            sys.exit(1)

        # 启动 TUI 应用
        app = LLMConfigApp()
        result = app.run()

        if result == 0:
            sys.stdout.write("✓ LLM 配置更新完成\n")
        else:
            sys.stdout.write("配置更新已取消\n")

    except KeyboardInterrupt:
        sys.stderr.write("\n配置已取消\n")
        sys.exit(1)
    except (OSError, ValueError, RuntimeError) as e:
        logger.exception("LLM 配置工具发生异常")
        sys.stderr.write(f"错误：{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    llm_config_main()
