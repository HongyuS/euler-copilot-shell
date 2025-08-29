"""基于 Textual 的 TUI 应用"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from rich.markdown import Markdown as RichMarkdown
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.message import Message
from textual.widgets import Footer, Header, Input, Static

from app.dialogs import AgentSelectionDialog, BackendRequiredDialog, ExitDialog
from app.mcp_widgets import MCPConfirmResult, MCPConfirmWidget, MCPParameterResult, MCPParameterWidget
from app.settings import SettingsScreen
from app.tui_mcp_handler import TUIMCPEventHandler
from backend.factory import BackendFactory
from backend.hermes import HermesChatClient
from backend.hermes.mcp_helpers import (
    MCPTags,
    extract_mcp_tag,
    format_error_message,
    is_final_mcp_message,
    is_mcp_message,
)
from config import ConfigManager
from config.model import Backend
from log.manager import get_logger, log_exception
from tool.command_processor import process_command
from tool.validators import APIValidator, validate_oi_connection

if TYPE_CHECKING:
    from textual.events import Key as KeyEvent
    from textual.events import Mount
    from textual.visual import VisualType

    from backend.base import LLMClientBase


class ContentChunkParams(NamedTuple):
    """内容块处理参数"""

    content: str
    is_llm_output: bool
    current_content: str
    is_first_content: bool


class FocusableContainer(Container):
    """可聚焦的容器，用于接收键盘事件处理滚动"""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """初始化可聚焦的容器"""
        super().__init__(*args, **kwargs)
        # 设置为可聚焦
        self.can_focus = True

    def on_key(self, event: KeyEvent) -> None:
        """处理键盘事件"""
        key_handled = True

        if event.key == "up":
            # 向上滚动
            self.scroll_up()
        elif event.key == "down":
            # 向下滚动
            self.scroll_down()
        elif event.key == "page_up":
            # 向上翻页
            for _ in range(10):  # 模拟翻页效果
                self.scroll_up()
        elif event.key == "page_down":
            # 向下翻页
            for _ in range(10):  # 模拟翻页效果
                self.scroll_down()
        elif event.key == "home":
            # 滚动到顶部
            self.scroll_home()
        elif event.key == "end":
            # 滚动到底部
            self.scroll_end()
        else:
            # 其他按键不处理
            key_handled = False
            return

        # 只有当我们处理了按键时，才阻止事件传递
        if key_handled:
            event.prevent_default()
            event.stop()
            # 确保视图更新
            self.refresh()


class OutputLine(Static):
    """输出行组件"""

    def __init__(self, text: str = "", *, command: bool = False) -> None:
        """初始化输出行组件"""
        # 禁用富文本标记解析，防止LLM输出中的特殊字符导致渲染错误
        super().__init__(text, markup=False)
        if command:
            self.add_class("command-line")
        self.text_content = text

    def update(self, content: VisualType = "", *, layout: bool = False) -> None:
        """更新组件内容，确保禁用富文本标记解析"""
        # 如果是字符串，更新内部存储的文本内容
        if isinstance(content, str):
            self.text_content = content
        # 调用父类方法进行实际更新
        super().update(content, layout=layout)

    def get_content(self) -> str:
        """获取组件内容的纯文本表示"""
        return self.text_content


class MarkdownOutputLine(Static):
    """Markdown输出行组件，使用rich库渲染富文本"""

    def __init__(self, markdown_content: str = "") -> None:
        """初始化支持真正富文本的Markdown输出组件"""
        super().__init__("")
        # 存储原始内容
        self.current_content = markdown_content
        self.update_markdown(markdown_content)

    def update_markdown(self, markdown_content: str) -> None:
        """更新Markdown内容"""
        self.current_content = markdown_content

        # 使用rich的Markdown渲染器
        md = RichMarkdown(
            markdown_content,
            code_theme=self._get_code_theme(),
            hyperlinks=True,
        )

        # 使用rich渲染后的内容更新组件
        super().update(md)

    def get_content(self) -> str:
        """获取当前Markdown原始内容"""
        return self.current_content

    def _get_code_theme(self) -> str:
        """根据当前Textual主题获取适合的代码主题"""
        return "material" if self.app.current_theme.dark else "xcode"

    def _on_mount(self, event: Mount) -> None:
        """组件挂载时设置主题监听"""
        super()._on_mount(event)
        self.watch(self.app, "theme", self._retheme)

    def _retheme(self) -> None:
        """主题变化时重新应用主题"""
        self.update_markdown(self.current_content)


class ProgressOutputLine(MarkdownOutputLine):
    """可替换的进度输出行组件，用于 MCP 工具进度显示"""

    def __init__(self, markdown_content: str = "", *, step_id: str = "") -> None:
        """初始化进度输出组件"""
        super().__init__(markdown_content)
        self.step_id = step_id
        self.add_class("progress-line")

    def get_step_id(self) -> str:
        """获取步骤ID"""
        return self.step_id

    def update_markdown(self, markdown_content: str) -> None:
        """更新Markdown内容"""
        self.current_content = markdown_content

        # 使用rich的Markdown渲染器
        md = RichMarkdown(
            markdown_content,
            code_theme=self._get_code_theme(),
            hyperlinks=True,
        )

        # 使用rich渲染后的内容更新组件
        super().update(md)

    def get_content(self) -> str:
        """获取当前Markdown原始内容"""
        return self.current_content

    def _get_code_theme(self) -> str:
        """根据当前Textual主题获取适合的代码主题"""
        return "material" if self.app.current_theme.dark else "xcode"

    def _on_mount(self, event: Mount) -> None:
        """组件挂载时设置主题监听"""
        super()._on_mount(event)
        self.watch(self.app, "theme", self._retheme)

    def _retheme(self) -> None:
        """主题变化时重新应用主题"""
        self.update_markdown(self.current_content)


class CommandInput(Input):
    """命令输入组件"""

    def __init__(self) -> None:
        """初始化命令输入组件"""
        super().__init__(placeholder="输入命令或问题...", id="command-input")


class IntelligentTerminal(App):
    """基于 Textual 的智能终端应用"""

    CSS_PATH = "css/styles.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding(key="ctrl+q", action="request_quit", description="退出"),
        Binding(key="ctrl+s", action="settings", description="设置"),
        Binding(key="ctrl+r", action="reset_conversation", description="重置对话"),
        Binding(key="ctrl+t", action="choose_agent", description="选择智能体"),
        Binding(key="tab", action="toggle_focus", description="切换焦点"),
    ]

    class SwitchToMCPConfirm(Message):
        """切换到 MCP 确认界面的消息"""

        def __init__(self, event) -> None:  # noqa: ANN001
            """初始化消息"""
            super().__init__()
            self.event = event

    class SwitchToMCPParameter(Message):
        """切换到 MCP 参数输入界面的消息"""

        def __init__(self, event) -> None:  # noqa: ANN001
            """初始化消息"""
            super().__init__()
            self.event = event

    def __init__(self) -> None:
        """初始化应用"""
        super().__init__()
        # 设置应用标题
        self.title = "openEuler Intelligence"
        self.config_manager = ConfigManager()
        self.processing: bool = False
        # 添加保存任务的集合到类属性
        self.background_tasks: set[asyncio.Task] = set()
        # 创建并保持单一的 LLM 客户端实例以维持对话历史
        self._llm_client: LLMClientBase | None = None
        # 当前选择的智能体 - 根据配置的 default_app 初始化
        self.current_agent: tuple[str, str] = self._get_initial_agent()
        # MCP 状态
        self._mcp_mode: str = "normal"  # "normal", "confirm", "parameter"
        self._current_mcp_task_id: str = ""
        # 创建日志实例
        self.logger = get_logger(__name__)
        # 进度消息跟踪
        self._current_progress_lines: dict[str, ProgressOutputLine] = {}  # step_id -> ProgressOutputLine

    def compose(self) -> ComposeResult:
        """构建界面"""
        yield Header(show_clock=True)
        yield FocusableContainer(id="output-container")
        with Container(id="input-container", classes="normal-mode"):
            yield CommandInput()
        yield Footer(show_command_palette=False)

    def action_settings(self) -> None:
        """打开设置页面"""
        # 只有在主界面（无其他屏幕）时才响应
        if not self._is_in_main_interface():
            return
        self.push_screen(SettingsScreen(self.config_manager, self.get_llm_client()))

    def action_request_quit(self) -> None:
        """请求退出应用"""
        # 检查是否已经在退出对话框
        if self._is_exit_dialog_open():
            return
        self.push_screen(ExitDialog())

    def action_reset_conversation(self) -> None:
        """重置对话历史记录的动作"""
        # 只有在主界面（无其他屏幕）时才响应
        if not self._is_in_main_interface():
            return
        if self._llm_client is not None and hasattr(self._llm_client, "reset_conversation"):
            self._llm_client.reset_conversation()
        # 清除屏幕上的所有内容
        output_container = self.query_one("#output-container")
        output_container.remove_children()
        # 清理进度消息跟踪
        self._current_progress_lines.clear()

    def action_choose_agent(self) -> None:
        """选择智能体的动作"""
        # 只有在主界面（无其他屏幕）时才响应
        if not self._is_in_main_interface():
            return
        # 获取 Hermes 客户端
        llm_client = self.get_llm_client()

        # 检查客户端类型
        if not hasattr(llm_client, "get_available_agents"):
            # 显示后端要求提示对话框
            self.push_screen(BackendRequiredDialog())
            return

        # 异步获取智能体列表
        task = asyncio.create_task(self._show_agent_selection())
        self.background_tasks.add(task)
        task.add_done_callback(self._task_done_callback)

    def action_toggle_focus(self) -> None:
        """在命令输入框和文本区域之间切换焦点"""
        # 获取当前聚焦的组件
        focused = self.focused

        # 检查是否聚焦在输入组件（包括 MCP 组件）
        is_input_focused = isinstance(focused, CommandInput) or (
            focused is not None and hasattr(focused, "id") and focused.id in ["mcp-confirm", "mcp-parameter"]
        )

        if is_input_focused:
            # 如果当前聚焦在输入组件，则聚焦到输出容器
            output_container = self.query_one("#output-container", FocusableContainer)
            output_container.focus()
        else:
            # 否则聚焦到当前的输入组件
            self._focus_current_input_widget()

    def on_mount(self) -> None:
        """初始化完成时设置焦点和绑定"""
        # 确保初始状态是正常模式
        self._mcp_mode = "normal"
        self._current_mcp_task_id = ""

        # 清理任何可能的重复组件
        try:
            # 移除任何可能的重复ID组件
            existing_widgets = self.query("#command-input")
            if len(existing_widgets) > 1:
                # 如果有多个相同ID的组件，移除多余的
                for widget in existing_widgets[1:]:
                    widget.remove()
        except Exception:
            # 忽略清理过程中的异常
            self.logger.exception("清理重复组件失败")

        self._focus_current_input_widget()

        # 初始化默认智能体
        self._initialize_default_agent()

    def get_llm_client(self) -> LLMClientBase:
        """获取大模型客户端，使用单例模式维持对话历史"""
        if self._llm_client is None:
            self._llm_client = BackendFactory.create_client(self.config_manager)

        # 为 Hermes 客户端设置 MCP 事件处理器以支持 MCP 交互
        if isinstance(self._llm_client, HermesChatClient):
            mcp_handler = TUIMCPEventHandler(self, self._llm_client)
            self._llm_client.set_mcp_handler(mcp_handler)

        return self._llm_client

    def refresh_llm_client(self) -> None:
        """刷新 LLM 客户端实例，用于配置更改后重新创建客户端"""
        self._llm_client = BackendFactory.create_client(self.config_manager)

        # 后端切换时重新初始化智能体状态
        self._reinitialize_agent_state()

    def exit(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """退出应用前取消所有后台任务"""
        # 取消所有正在运行的后台任务
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # 清理 LLM 客户端连接
        if self._llm_client is not None:
            # 创建清理任务并在当前事件循环中执行
            cleanup_task = asyncio.create_task(self._cleanup_llm_client())
            self.background_tasks.add(cleanup_task)
            cleanup_task.add_done_callback(self._cleanup_task_done_callback)

        # 调用父类的exit方法
        super().exit(*args, **kwargs)

    @on(Input.Submitted, "#command-input")
    def handle_input(self, event: Input.Submitted) -> None:
        """处理命令输入"""
        user_input = event.value.strip()
        if not user_input or self.processing:
            return

        # 清空输入框
        input_widget = self.query_one(CommandInput)
        input_widget.value = ""

        # 显示命令
        output_container = self.query_one("#output-container")
        output_container.mount(OutputLine(f"> {user_input}", command=True))

        # 滚动到输出容器的底部
        output_container.scroll_end(animate=False)

        # 异步处理命令
        self.processing = True
        # 创建任务并保存到类属性中的任务集合
        task = asyncio.create_task(self._process_command(user_input))
        self.background_tasks.add(task)
        # 添加完成回调，自动从集合中移除
        task.add_done_callback(self._task_done_callback)

    @on(SwitchToMCPConfirm)
    def handle_switch_to_mcp_confirm(self, message: SwitchToMCPConfirm) -> None:
        """处理切换到 MCP 确认界面的消息"""
        self._mcp_mode = "confirm"
        self._current_mcp_task_id = message.event.get_task_id()
        self._replace_input_with_mcp_widget(MCPConfirmWidget(message.event, widget_id="mcp-confirm"))

    @on(SwitchToMCPParameter)
    def handle_switch_to_mcp_parameter(self, message: SwitchToMCPParameter) -> None:
        """处理切换到 MCP 参数输入界面的消息"""
        self._mcp_mode = "parameter"
        self._current_mcp_task_id = message.event.get_task_id()
        self._replace_input_with_mcp_widget(MCPParameterWidget(message.event, widget_id="mcp-parameter"))

    @on(MCPConfirmResult)
    def handle_mcp_confirm_result(self, message: MCPConfirmResult) -> None:
        """处理 MCP 确认结果"""
        # 检查是否是当前任务且未在处理中
        if message.task_id == self._current_mcp_task_id and not self.processing:
            self.processing = True  # 设置处理标志，防止重复处理
            # 立即恢复正常输入界面
            self._restore_normal_input()
            # 发送 MCP 响应并处理结果
            task = asyncio.create_task(self._send_mcp_response(message.task_id, params=message.confirmed))
            self.background_tasks.add(task)
            task.add_done_callback(self._task_done_callback)

    @on(MCPParameterResult)
    def handle_mcp_parameter_result(self, message: MCPParameterResult) -> None:
        """处理 MCP 参数结果"""
        # 检查是否是当前任务且未在处理中
        if message.task_id == self._current_mcp_task_id and not self.processing:
            self.processing = True  # 设置处理标志，防止重复处理
            # 立即恢复正常输入界面
            self._restore_normal_input()
            # 发送 MCP 响应并处理结果
            params = message.params if message.params is not None else False
            task = asyncio.create_task(self._send_mcp_response(message.task_id, params=params))
            self.background_tasks.add(task)
            task.add_done_callback(self._task_done_callback)

    def _is_in_main_interface(self) -> bool:
        """检查是否在主界面（没有其他屏幕弹出）"""
        # 检查是否有活动的屏幕栈，除了主屏幕外没有其他屏幕
        return len(self.screen_stack) <= 1

    def _is_exit_dialog_open(self) -> bool:
        """检查是否已经打开了退出对话框"""
        # 检查当前活动屏幕是否是退出对话框
        current_screen = self.screen
        return hasattr(current_screen, "__class__") and current_screen.__class__.__name__ == "ExitDialog"

    def _task_done_callback(self, task: asyncio.Task) -> None:
        """任务完成回调，从任务集合中移除"""
        if task in self.background_tasks:
            self.background_tasks.remove(task)
        # 捕获任务中的异常，防止未处理异常
        try:
            task.result()
        except asyncio.CancelledError:
            # 任务被取消是正常情况，不需要记录错误
            pass
        except Exception as e:
            # 记录错误日志
            self.logger.exception("Task execution error occurred")
            # 尝试在前端显示错误信息
            self._display_error_in_ui(e)
        finally:
            # 确保处理标志被重置
            self.processing = False

    async def _process_command(self, user_input: str) -> None:
        """异步处理命令"""
        try:
            output_container = self.query_one("#output-container", Container)
            received_any_content = await self._handle_command_stream(user_input, output_container)

            # 如果没有收到任何内容且应用仍在运行，显示错误信息
            if not received_any_content and hasattr(self, "is_running") and self.is_running:
                output_container.mount(
                    OutputLine("没有收到响应，请检查网络连接或稍后重试", command=False),
                )

        except asyncio.CancelledError:
            # 任务被取消，通常是因为应用退出
            self.logger.info("Command processing cancelled")
        except Exception as e:
            # 记录错误日志
            self.logger.exception("Command processing error occurred")
            # 添加异常处理，显示错误信息
            try:
                output_container = self.query_one("#output-container", Container)
                error_msg = self._format_error_message(e)
                # 检查应用是否已经开始退出
                if hasattr(self, "is_running") and self.is_running:
                    output_container.mount(OutputLine(format_error_message(error_msg), command=False))
            except (AttributeError, ValueError, RuntimeError):
                # 如果UI组件已不可用，只记录错误日志
                self.logger.exception("Failed to display error message")
        finally:
            # 重新聚焦到输入框（如果应用仍在运行）
            try:
                if hasattr(self, "is_running") and self.is_running:
                    self._focus_current_input_widget()
            except (AttributeError, ValueError, RuntimeError):
                # 应用可能正在退出，忽略聚焦错误
                self.logger.debug("[TUI] Failed to focus input widget, app may be exiting")
            # 注意：不在这里重置processing标志，由回调函数处理

    async def _handle_command_stream(self, user_input: str, output_container: Container) -> bool:
        """处理命令流式响应"""
        # 在新的命令会话开始时重置MCP状态跟踪
        if self._llm_client and isinstance(self._llm_client, HermesChatClient):
            self._llm_client.stream_processor.reset_status_tracking()

        stream_state = self._init_stream_state()

        try:
            received_any_content = await self._process_stream(
                user_input,
                output_container,
                stream_state,
            )
        except TimeoutError:
            received_any_content = self._handle_timeout_error(output_container, stream_state)
        except asyncio.CancelledError:
            received_any_content = self._handle_cancelled_error(output_container, stream_state)

        return received_any_content

    def _init_stream_state(self) -> dict:
        """初始化流处理状态"""
        start_time = asyncio.get_event_loop().time()
        return {
            "current_line": None,
            "current_content": "",
            "is_first_content": True,
            "received_any_content": False,
            "start_time": start_time,
            "timeout_seconds": 1800.0,  # 30分钟超时，与HTTP层面保持一致
            "last_content_time": start_time,
            "no_content_timeout": 300.0,  # 5分钟无内容超时
        }

    async def _process_stream(
        self,
        user_input: str,
        output_container: Container,
        stream_state: dict,
    ) -> bool:
        """处理命令输出流"""
        async for output_tuple in process_command(user_input, self.get_llm_client()):
            content, is_llm_output = output_tuple
            stream_state["received_any_content"] = True
            current_time = asyncio.get_event_loop().time()

            # 更新最后收到内容的时间
            if content.strip():
                stream_state["last_content_time"] = current_time

            # 检查超时
            if self._check_timeouts(current_time, stream_state, output_container):
                break

            # 处理内容
            await self._process_stream_content(
                content,
                stream_state,
                output_container,
                is_llm_output=is_llm_output,
            )

            # 滚动到底部
            await self._scroll_to_end()

        return stream_state["received_any_content"]

    def _check_timeouts(
        self,
        current_time: float,
        stream_state: dict,
        output_container: Container,
    ) -> bool:
        """检查各种超时条件，返回是否应该中断处理"""
        # 检查总体超时
        if current_time - stream_state["start_time"] > stream_state["timeout_seconds"]:
            output_container.mount(OutputLine("请求超时，已停止处理", command=False))
            return True

        # 检查无内容超时
        received_any_content = stream_state["received_any_content"]
        time_since_last_content = current_time - stream_state["last_content_time"]
        if received_any_content and time_since_last_content > stream_state["no_content_timeout"]:
            output_container.mount(OutputLine("长时间无响应，已停止处理", command=False))
            return True

        return False

    async def _process_stream_content(
        self,
        content: str,
        stream_state: dict,
        output_container: Container,
        *,
        is_llm_output: bool,
    ) -> None:
        """处理流式内容"""
        params = ContentChunkParams(
            content=content,
            is_llm_output=is_llm_output,
            current_content=stream_state["current_content"],
            is_first_content=stream_state["is_first_content"],
        )

        processed_line = await self._process_content_chunk(
            params,
            stream_state["current_line"],
            output_container,
        )

        # 检查是否是 MCP 消息处理（返回值为 None 表示是 MCP 消息）
        tool_name, _ = extract_mcp_tag(content)
        is_mcp_detected = processed_line is None and tool_name is not None

        # 只有当返回值不为None时才更新current_line
        if processed_line is not None:
            stream_state["current_line"] = processed_line

        # 更新状态 - 但是不要让 MCP 消息影响流状态
        if not is_mcp_detected:
            if stream_state["is_first_content"]:
                stream_state["is_first_content"] = False
                # 第一次内容直接设置为当前内容，不需要累积
                if is_llm_output:
                    stream_state["current_content"] = content
                else:
                    # 非LLM输出，重置累积内容
                    stream_state["current_content"] = ""
            elif isinstance(stream_state["current_line"], MarkdownOutputLine) and is_llm_output:
                # 只有在LLM输出且有有效的 MarkdownOutputLine 时才累积
                stream_state["current_content"] += content

    def _handle_timeout_error(self, output_container: Container, stream_state: dict) -> bool:
        """处理超时错误"""
        self.logger.warning("Command stream timed out")
        if hasattr(self, "is_running") and self.is_running:
            output_container.mount(OutputLine("请求超时，请稍后重试", command=False))
        return stream_state["received_any_content"]

    def _handle_cancelled_error(self, output_container: Container, stream_state: dict) -> bool:
        """处理取消错误"""
        self.logger.info("Command stream was cancelled")
        received_any_content = stream_state["received_any_content"]
        if received_any_content and hasattr(self, "is_running") and self.is_running:
            output_container.mount(OutputLine("[处理被中断]", command=False))
        return received_any_content

    async def _process_content_chunk(
        self,
        params: ContentChunkParams,
        current_line: OutputLine | MarkdownOutputLine | None,
        output_container: Container,
    ) -> OutputLine | MarkdownOutputLine | None:
        """处理单个内容块"""
        content = params.content
        is_llm_output = params.is_llm_output
        current_content = params.current_content
        is_first_content = params.is_first_content

        # 检查是否包含MCP标记（替换标记或MCP标记）
        tool_name, cleaned_content = extract_mcp_tag(content)
        replace_tool_name = None
        mcp_tool_name = None

        # 根据原始内容判断标记类型
        if tool_name:
            if MCPTags.REPLACE_PREFIX in content:
                replace_tool_name = tool_name
            elif MCPTags.MCP_PREFIX in content:
                mcp_tool_name = tool_name

        # 检查是否为 MCP 进度消息
        tool_name = replace_tool_name or mcp_tool_name
        is_progress_message = tool_name is not None and is_mcp_message(content)

        # 如果是进度消息，使用专门的处理方法，无论 is_llm_output 的值
        if is_progress_message and tool_name:
            return self._handle_mcp_progress_message(
                cleaned_content,
                tool_name,
                replace_tool_name,
                mcp_tool_name,
                output_container,
            )

        # 使用清理后的内容进行后续处理
        content = cleaned_content

        self.logger.debug("[TUI] 处理内容: %s", content.strip()[:50])

        # 处理第一段内容，创建适当的输出组件
        if is_first_content:
            new_line: OutputLine | MarkdownOutputLine = (
                MarkdownOutputLine(content) if is_llm_output else OutputLine(content)
            )
            output_container.mount(new_line)
            return new_line

        # 处理后续内容
        if is_llm_output and isinstance(current_line, MarkdownOutputLine):
            # 继续累积LLM富文本内容
            # 注意：current_content 已经包含了之前的所有内容，包括第一次的内容
            updated_content = current_content + content
            current_line.update_markdown(updated_content)
            return current_line

        if not is_llm_output and isinstance(current_line, OutputLine):
            # 继续累积命令输出纯文本
            current_text = current_line.get_content()
            current_line.update(current_text + content)
            return current_line

        # 输出类型发生变化，创建新的输出组件
        # 对于输出类型变化，如果是LLM输出，应该包含累积的内容；否则只包含当前内容
        if is_llm_output:
            # 如果切换到LLM输出，使用累积的内容（如果有的话）
            content_to_display = current_content + content if current_content else content
            new_line = MarkdownOutputLine(content_to_display)
        else:
            # 如果切换到非LLM输出，只使用当前内容
            new_line = OutputLine(content)
        output_container.mount(new_line)
        return new_line

    def _handle_mcp_progress_message(
        self,
        content: str,
        tool_name: str,
        replace_tool_name: str | None,
        mcp_tool_name: str | None,
        output_container: Container,
    ) -> None:
        """处理 MCP 进度消息"""
        # 检查是否为最终状态消息
        is_final_message = is_final_mcp_message(content)

        # 检查是否有现有的进度消息
        existing_progress = self._current_progress_lines.get(tool_name)

        # 如果有替换标记，则尝试替换现有消息
        if replace_tool_name and existing_progress is not None:
            # 替换现有的进度消息
            existing_progress.update_markdown(content)
            self.logger.debug("[TUI] 替换工具 %s 的进度消息: %s", tool_name, content.strip()[:50])

            # 如果是最终状态，清理进度跟踪
            if is_final_message:
                self._current_progress_lines.pop(tool_name, None)
                self.logger.debug("[TUI] 工具 %s 到达最终状态，清理进度跟踪", tool_name)

            return

        # 如果有MCP标记但已存在相同工具的进度消息，则替换而不是创建新的
        if mcp_tool_name and existing_progress is not None:
            # 这种情况可能是因为消息处理顺序问题导致的重复，应该替换现有消息
            existing_progress.update_markdown(content)
            self.logger.debug("[TUI] 替换已存在的工具 %s 进度消息: %s", tool_name, content.strip()[:50])

            # 如果是最终状态，清理进度跟踪
            if is_final_message:
                self._current_progress_lines.pop(tool_name, None)
                self.logger.debug("[TUI] 工具 %s 到达最终状态，清理进度跟踪", tool_name)

            return

        # 创建新的进度消息
        new_progress_line = ProgressOutputLine(content, step_id=tool_name)

        # 如果不是最终状态，加入进度跟踪
        if not is_final_message:
            self._current_progress_lines[tool_name] = new_progress_line

        output_container.mount(new_progress_line)
        self.logger.debug("[TUI] 创建工具 %s 的新进度消息: %s", tool_name, content.strip()[:50])

    def _format_error_message(self, error: BaseException) -> str:
        """格式化错误消息"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # 处理 HermesAPIError 特殊情况
        if hasattr(error, "status_code") and hasattr(error, "message"):
            if error.status_code == 500:  # type: ignore[attr-defined]  # noqa: PLR2004
                return f"服务端错误: {error.message}"  # type: ignore[attr-defined]
            if error.status_code >= 400:  # type: ignore[attr-defined]  # noqa: PLR2004
                return f"请求失败: {error.message}"  # type: ignore[attr-defined]

        # 定义错误匹配规则和对应的用户友好消息
        error_patterns = {
            "网络连接异常中断，请检查网络连接后重试": [
                "remoteprotocolerror",
                "server disconnected",
                "peer closed connection",
                "connection reset",
                "connection refused",
                "broken pipe",
            ],
            "请求超时，请稍后重试": [
                "timeout",
                "timed out",
            ],
            "网络连接错误，请检查网络后重试": [
                "network",
                "connection",
                "unreachable",
                "resolve",
                "dns",
                "httperror",
                "requestserror",
            ],
            "服务端响应异常，请稍后重试": [
                "http",
                "status",
                "response",
            ],
            "数据格式错误，请稍后重试": [
                "json",
                "decode",
                "parse",
                "invalid",
                "malformed",
            ],
            "认证失败，请检查配置": [
                "auth",
                "unauthorized",
                "forbidden",
                "token",
            ],
        }

        # 检查错误字符串匹配
        for message, patterns in error_patterns.items():
            if any(pattern in error_str for pattern in patterns):
                return message

        # 检查错误类型匹配（用于服务端响应异常）
        if any(
            keyword in error_type
            for keyword in [
                "httperror",
                "httpstatuserror",
                "requesterror",
            ]
        ):
            return "服务端响应异常，请稍后重试"

        return f"处理命令时出错: {error!s}"

    def _display_error_in_ui(self, error: BaseException) -> None:
        """在UI界面显示错误信息"""
        try:
            # 检查应用是否仍在运行
            if not (hasattr(self, "is_running") and self.is_running):
                return

            # 获取输出容器
            output_container = self.query_one("#output-container", Container)

            # 格式化错误消息
            error_msg = self._format_error_message(error)

            # 显示错误信息
            output_container.mount(OutputLine(f"❌ {error_msg}", command=False))

            # 滚动到底部以确保用户看到错误信息
            self.call_after_refresh(lambda: output_container.scroll_end(animate=False))

        except Exception:
            # 如果UI显示失败，至少记录错误日志
            self.logger.exception("无法在UI中显示错误信息")

    def _focus_current_input_widget(self) -> None:
        """聚焦到当前的输入组件，考虑 MCP 模式状态"""
        try:
            if self._mcp_mode == "normal":
                # 正常模式，聚焦到 CommandInput
                self.query_one(CommandInput).focus()
            elif self._mcp_mode == "confirm":
                # MCP 确认模式，聚焦到 MCP 确认组件
                try:
                    mcp_widget = self.query_one("#mcp-confirm")
                    mcp_widget.focus()
                except (AttributeError, ValueError, RuntimeError):
                    # 如果MCP组件不存在，回退到正常模式
                    self._mcp_mode = "normal"
                    self.query_one(CommandInput).focus()
            elif self._mcp_mode == "parameter":
                # MCP 参数模式，聚焦到 MCP 参数组件
                try:
                    mcp_widget = self.query_one("#mcp-parameter")
                    mcp_widget.focus()
                except (AttributeError, ValueError, RuntimeError):
                    # 如果MCP组件不存在，回退到正常模式
                    self._mcp_mode = "normal"
                    self.query_one(CommandInput).focus()
            else:
                # 未知模式，重置为正常模式并聚焦到 CommandInput
                self.logger.warning("未知的 MCP 模式: %s，重置为正常模式", self._mcp_mode)
                self._mcp_mode = "normal"
                self.query_one(CommandInput).focus()
        except (AttributeError, ValueError, RuntimeError) as e:
            # 聚焦失败时记录调试信息，但不抛出异常
            self.logger.debug("[TUI] Failed to focus input widget: %s", str(e))

    async def _scroll_to_end(self) -> None:
        """滚动到容器底部的辅助方法"""
        # 获取输出容器
        output_container = self.query_one("#output-container")
        # 使用同步方法滚动，确保UI更新
        output_container.scroll_end(animate=False)
        # 等待一个小的延迟，确保UI有时间更新
        await asyncio.sleep(0.01)

    async def _cleanup_llm_client(self) -> None:
        """异步清理 LLM 客户端"""
        if self._llm_client is not None:
            try:
                await self._llm_client.close()
                self.logger.info("LLM 客户端已安全关闭")
            except (OSError, RuntimeError, ValueError) as e:
                log_exception(self.logger, "关闭 LLM 客户端时出错", e)

    def _cleanup_task_done_callback(self, task: asyncio.Task) -> None:
        """清理任务完成回调"""
        if task in self.background_tasks:
            self.background_tasks.remove(task)
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except (OSError, ValueError, RuntimeError):
            self.logger.exception("LLM client cleanup error")

    async def _show_agent_selection(self) -> None:
        """显示智能体选择对话框"""
        try:
            llm_client = self.get_llm_client()

            # 构建智能体列表 - 默认第一项为"智能问答"（无智能体）
            agent_list = [("", "智能问答")]

            # 尝试获取可用智能体
            if hasattr(llm_client, "get_available_agents"):
                try:
                    available_agents = await llm_client.get_available_agents()  # type: ignore[attr-defined]
                    # 添加获取到的智能体
                    agent_list.extend(
                        [
                            (agent.app_id, agent.name)
                            for agent in available_agents
                            if hasattr(agent, "app_id") and hasattr(agent, "name")
                        ],
                    )
                except (AttributeError, OSError, ValueError, RuntimeError) as e:
                    self.logger.warning("获取智能体列表失败，使用默认选项: %s", str(e))
                    # 继续使用默认的智能问答选项
            else:
                self.logger.info("当前客户端不支持智能体功能，显示默认选项")

            # 使用当前智能体状态，不重新读取配置
            await self._display_agent_dialog(agent_list, llm_client)

        except (OSError, ValueError, RuntimeError) as e:
            log_exception(self.logger, "显示智能体选择对话框失败", e)
            # 即使出错也显示默认选项
            agent_list = [("", "智能问答")]
            try:
                llm_client = self.get_llm_client()
                await self._display_agent_dialog(agent_list, llm_client)
            except (OSError, ValueError, RuntimeError, AttributeError):
                self.logger.exception("无法显示智能体选择对话框")

    async def _display_agent_dialog(
        self,
        agent_list: list[tuple[str, str]],
        llm_client: LLMClientBase,
    ) -> None:
        """显示智能体选择对话框"""

        def on_agent_selected(selected_agent: tuple[str, str]) -> None:
            """智能体选择回调"""
            self.current_agent = selected_agent
            app_id, name = selected_agent

            # 设置智能体到客户端
            if hasattr(llm_client, "set_current_agent"):
                llm_client.set_current_agent(app_id)  # type: ignore[attr-defined]

        dialog = AgentSelectionDialog(agent_list, on_agent_selected, self.current_agent)
        self.push_screen(dialog)

    def _replace_input_with_mcp_widget(self, widget) -> None:  # noqa: ANN001
        """替换输入容器中的组件为 MCP 交互组件"""
        try:
            input_container = self.query_one("#input-container")

            # 切换到 MCP 模式样式
            input_container.remove_class("normal-mode")
            input_container.add_class("mcp-mode")

            # 移除所有子组件
            input_container.remove_children()

            # 添加新的 MCP 组件
            input_container.mount(widget)

            # 延迟聚焦，确保组件完全挂载
            self.set_timer(0.05, lambda: widget.focus())

        except Exception:
            self.logger.exception("替换输入组件失败")
            # 如果替换失败，尝试恢复正常输入
            try:
                self._restore_normal_input()
            except Exception:
                self.logger.exception("恢复正常输入失败")

    def _restore_normal_input(self) -> None:
        """恢复正常的命令输入组件"""
        try:
            input_container = self.query_one("#input-container")

            # 重置 MCP 状态
            self._mcp_mode = "normal"
            self._current_mcp_task_id = ""

            # 切换回正常模式样式
            input_container.remove_class("mcp-mode")
            input_container.add_class("normal-mode")

            # 移除所有子组件
            input_container.remove_children()

            # 添加正常的命令输入组件
            command_input = CommandInput()
            input_container.mount(command_input)

            # 聚焦到输入框
            self._focus_current_input_widget()

        except Exception:
            self.logger.exception("恢复正常输入组件失败")
            # 如果恢复失败，至少要重置状态
            self._mcp_mode = "normal"
            self._current_mcp_task_id = ""

    async def _send_mcp_response(self, task_id: str, *, params: bool | dict[str, Any]) -> None:
        """发送 MCP 响应并处理结果"""
        output_container: Container | None = None

        try:
            # 先获取输出容器，确保可以显示错误信息
            output_container = self.query_one("#output-container", Container)

            # 发送 MCP 响应并处理流式回复
            llm_client = self.get_llm_client()
            if hasattr(llm_client, "send_mcp_response"):
                success = await self._handle_mcp_response_stream(
                    task_id,
                    params=params,
                    output_container=output_container,
                    llm_client=llm_client,
                )
                if not success:
                    # 如果没有收到任何响应内容，显示默认消息
                    output_container.mount(OutputLine("💡 MCP 响应已发送"))
            else:
                self.logger.error("当前客户端不支持 MCP 响应功能")
                output_container.mount(OutputLine("❌ 当前客户端不支持 MCP 响应功能"))

        except Exception as e:
            self.logger.exception("发送 MCP 响应失败")
            # 显示错误信息
            if output_container is not None:
                try:
                    error_message = self._format_error_message(e)
                    output_container.mount(OutputLine(f"❌ 发送 MCP 响应失败: {error_message}"))
                except Exception:
                    # 如果连显示错误信息都失败了，至少记录日志
                    self.logger.exception("无法显示错误信息")
        finally:
            # 重置处理标志，不再在这里恢复输入界面
            self.processing = False

    async def _handle_mcp_response_stream(
        self,
        task_id: str,
        *,
        params: bool | dict[str, Any],
        output_container: Container,
        llm_client: LLMClientBase,
    ) -> bool:
        """处理 MCP 响应的流式回复"""
        if not isinstance(llm_client, HermesChatClient):
            self.logger.error("当前客户端不支持 MCP 响应功能")
            output_container.mount(OutputLine("❌ 当前客户端不支持 MCP 响应功能"))
            return False

        # 使用统一的流状态管理，与 _handle_command_stream 保持一致
        stream_state = self._init_stream_state()
        timeout_seconds = 1800.0  # 30分钟超时，与HTTP层面保持一致

        try:
            # 使用 asyncio.wait_for 包装整个流处理过程
            async def _process_stream() -> bool:
                async for content in llm_client.send_mcp_response(task_id, params=params):
                    if not content.strip():
                        continue

                    stream_state["received_any_content"] = True
                    current_time = asyncio.get_event_loop().time()

                    # 更新最后收到内容的时间
                    if content.strip():
                        stream_state["last_content_time"] = current_time

                    # 检查超时
                    if self._check_timeouts(current_time, stream_state, output_container):
                        break

                    # 判断是否为 LLM 输出内容
                    tool_name, _ = extract_mcp_tag(content)
                    is_llm_output = tool_name is None

                    # 处理内容
                    await self._process_stream_content(
                        content,
                        stream_state,
                        output_container,
                        is_llm_output=is_llm_output,
                    )

                    # 滚动到底部
                    await self._scroll_to_end()

                return stream_state["received_any_content"]

            # 执行流处理，添加超时
            return await asyncio.wait_for(_process_stream(), timeout=timeout_seconds)

        except TimeoutError:
            output_container.mount(OutputLine(f"⏱️ MCP 响应超时 ({timeout_seconds}秒)"))
            return stream_state["received_any_content"]
        except asyncio.CancelledError:
            output_container.mount(OutputLine("🚫 MCP 响应被取消"))
            raise

    def _get_initial_agent(self) -> tuple[str, str]:
        """根据配置获取初始智能体，只在应用启动时调用"""
        default_app = self.config_manager.get_default_app()
        if default_app:
            # 如果配置了默认智能体，尝试获取对应的名称
            # 这里先返回 ID 和 ID 作为临时方案，后续在智能体列表加载后更新名称
            return (default_app, default_app)
        # 如果没有配置默认智能体，使用智能问答
        return ("", "智能问答")

    def _reinitialize_agent_state(self) -> None:
        """重新初始化智能体状态，用于后端切换时"""
        # 尝试异步更新智能体信息（如果新后端支持智能体功能）
        self._initialize_default_agent()

    def _initialize_default_agent(self) -> None:
        """初始化默认智能体，包含配置验证"""
        # 首先验证后端配置
        validation_task = asyncio.create_task(self._validate_and_setup_configuration())
        self.background_tasks.add(validation_task)
        validation_task.add_done_callback(self._task_done_callback)

    async def _validate_and_setup_configuration(self) -> None:
        """验证配置并设置智能体，如果配置无效则弹出设置页面"""
        try:
            # 获取当前后端配置
            backend = self.config_manager.get_backend()

            # 验证配置
            is_valid = await self._validate_backend_configuration(backend)

            if is_valid:
                # 配置验证通过，继续初始化智能体
                await self._setup_agent_after_validation()
            else:
                # 配置验证失败，显示通知并弹出设置页面
                self._show_config_validation_notification()
                await self._show_settings_for_config_fix()

        except Exception:
            self.logger.exception("配置验证过程中发生错误")
            # 即使验证出错，也弹出设置页面让用户手动配置
            self._show_config_validation_notification()
            await self._show_settings_for_config_fix()

    async def _validate_backend_configuration(self, backend: Backend) -> bool:
        """验证后端配置"""
        try:
            validator = APIValidator()

            if backend == Backend.OPENAI:
                # 验证 OpenAI 配置
                base_url = self.config_manager.get_base_url()
                api_key = self.config_manager.get_api_key()
                model = self.config_manager.get_model()
                valid, _, _ = await validator.validate_llm_config(
                    endpoint=base_url,
                    api_key=api_key,
                    model=model,
                    timeout=10,
                )
                return valid

            if backend == Backend.EULERINTELLI:
                # 验证 openEuler Intelligence 配置
                base_url = self.config_manager.get_eulerintelli_url()
                api_key = self.config_manager.get_eulerintelli_key()
                valid, _ = await validate_oi_connection(base_url, api_key)
                return valid

        except Exception:
            self.logger.exception("验证后端配置时发生错误")
            return False

        else:
            return False

    def _show_config_validation_notification(self) -> None:
        """显示配置验证失败的通知"""
        self.notify(
            "后端配置验证失败，请检查并修改配置",
            title="配置错误",
            severity="error",
            timeout=0.5,
        )

    async def _show_settings_for_config_fix(self) -> None:
        """弹出设置页面让用户修改配置"""
        try:
            # 弹出设置页面
            settings_screen = SettingsScreen(self.config_manager, self.get_llm_client())
            self.push_screen(settings_screen)

            # 等待设置页面退出
            await self._wait_for_settings_screen_exit()

            # 设置页面退出后，重新验证配置
            backend = self.config_manager.get_backend()
            is_valid = await self._validate_backend_configuration(backend)

            if not is_valid:
                # 如果还是无效，递归调用自己再次弹出设置页面
                self._show_config_validation_notification()
                await self._show_settings_for_config_fix()
            else:
                # 配置验证通过，继续初始化智能体
                await self._setup_agent_after_validation()

        except Exception:
            self.logger.exception("显示设置页面时发生错误")

    async def _wait_for_settings_screen_exit(self) -> None:
        """等待设置页面退出"""
        # 使用事件来等待设置页面退出，而不是轮询
        exit_event = asyncio.Event()

        # 创建一个任务来监控屏幕栈变化
        async def monitor_screen_stack() -> None:
            current_stack_length = len(self.screen_stack)
            while current_stack_length > 1:
                await asyncio.sleep(0.05)  # 短暂等待后重新检查
                current_stack_length = len(self.screen_stack)
            exit_event.set()

        # 启动监控任务
        monitor_task = asyncio.create_task(monitor_screen_stack())

        # 等待退出事件或超时（5分钟）
        try:
            await asyncio.wait_for(exit_event.wait(), timeout=300.0)
        except TimeoutError:
            self.logger.warning("等待设置页面退出超时")
        finally:
            # 取消监控任务
            if not monitor_task.done():
                monitor_task.cancel()

    async def _setup_agent_after_validation(self) -> None:
        """配置验证通过后设置智能体"""
        try:
            # 如果当前智能体是基于 default_app 配置的，且需要更新名称
            app_id, name = self.current_agent
            if app_id and app_id == name:  # 这表示我们在 _get_initial_agent 中使用了临时方案
                # 异步获取智能体信息并更新名称
                await self._update_agent_name_from_list()
        except Exception:
            self.logger.exception("设置智能体时发生错误")

    async def _update_agent_name_from_list(self) -> None:
        """从智能体列表中更新当前智能体的名称"""
        try:
            llm_client = self.get_llm_client()
            if hasattr(llm_client, "get_available_agents"):
                available_agents = await llm_client.get_available_agents()  # type: ignore[attr-defined]
                app_id, _ = self.current_agent

                # 查找匹配的智能体
                agent_found = False
                for agent in available_agents:
                    if hasattr(agent, "app_id") and hasattr(agent, "name") and agent.app_id == app_id:
                        # 更新智能体信息
                        self.current_agent = (agent.app_id, agent.name)
                        # 设置智能体到客户端
                        if hasattr(llm_client, "set_current_agent"):
                            llm_client.set_current_agent(app_id)  # type: ignore[attr-defined]
                        agent_found = True
                        break

                # 如果没有找到匹配的智能体，说明配置的默认智能体ID已无效
                if not agent_found and app_id:
                    self.logger.warning("配置的默认智能体 '%s' 不存在，回退到智能问答并清理配置", app_id)
                    # 回退到智能问答
                    self.current_agent = ("", "智能问答")
                    # 清理配置中的无效ID
                    self.config_manager.set_default_app("")
                    # 确保客户端也切换到智能问答
                    if hasattr(llm_client, "set_current_agent"):
                        llm_client.set_current_agent("")  # type: ignore[attr-defined]
        except (AttributeError, OSError, ValueError, RuntimeError) as e:
            self.logger.warning("无法更新智能体名称: %s", str(e))
