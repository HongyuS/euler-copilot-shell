"""基于 Textual 的 TUI 应用"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar, NamedTuple

from rich.markdown import Markdown as RichMarkdown
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.widgets import Footer, Header, Input, Static

from app.dialogs import AgentSelectionDialog, BackendRequiredDialog, ExitDialog
from app.settings import SettingsScreen
from backend.factory import BackendFactory
from config import ConfigManager
from log.manager import get_logger, log_exception
from tool.command_processor import process_command

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

    def update(self, content: VisualType = "") -> None:
        """更新组件内容，确保禁用富文本标记解析"""
        # 如果是字符串，更新内部存储的文本内容
        if isinstance(content, str):
            self.text_content = content
        # 调用父类方法进行实际更新
        super().update(content)

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


class CommandInput(Input):
    """命令输入组件"""

    def __init__(self) -> None:
        """初始化命令输入组件"""
        super().__init__(placeholder="输入命令或问题...", id="command-input")


class IntelligentTerminal(App):
    """基于 Textual 的智能终端应用"""

    CSS_PATH = "css/styles.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding(key="ctrl+s", action="settings", description="设置"),
        Binding(key="ctrl+r", action="reset_conversation", description="重置对话"),
        Binding(key="ctrl+t", action="choose_agent", description="选择智能体"),
        Binding(key="esc", action="request_quit", description="退出"),
        Binding(key="tab", action="toggle_focus", description="切换焦点"),
    ]

    def __init__(self) -> None:
        """初始化应用"""
        super().__init__()
        # 设置应用标题
        self.title = "openEuler 智能 Shell"
        self.config_manager = ConfigManager()
        self.processing: bool = False
        # 添加保存任务的集合到类属性
        self.background_tasks: set[asyncio.Task] = set()
        # 创建并保持单一的 LLM 客户端实例以维持对话历史
        self._llm_client: LLMClientBase | None = None
        # 当前选择的智能体
        self.current_agent: tuple[str, str] = ("", "智能问答")
        # 创建日志实例
        self.logger = get_logger(__name__)

    def compose(self) -> ComposeResult:
        """构建界面"""
        yield Header(show_clock=True)
        yield FocusableContainer(id="output-container")
        with Container(id="input-container"):
            yield CommandInput()
        yield Footer()

    def action_settings(self) -> None:
        """打开设置页面"""
        self.push_screen(SettingsScreen(self.config_manager, self._get_llm_client()))

    def action_request_quit(self) -> None:
        """请求退出应用"""
        self.push_screen(ExitDialog())

    def action_reset_conversation(self) -> None:
        """重置对话历史记录的动作"""
        if self._llm_client is not None and hasattr(self._llm_client, "reset_conversation"):
            self._llm_client.reset_conversation()
        # 清除屏幕上的所有内容
        output_container = self.query_one("#output-container")
        output_container.remove_children()

    def action_choose_agent(self) -> None:
        """选择智能体的动作"""
        # 获取 Hermes 客户端
        llm_client = self._get_llm_client()

        # 检查客户端类型
        if not hasattr(llm_client, "get_available_agents"):
            # 显示后端要求提示对话框
            self.push_screen(BackendRequiredDialog())
            return

        # 异步获取智能体列表
        task = asyncio.create_task(self._show_agent_selection())
        self.background_tasks.add(task)
        task.add_done_callback(self._task_done_callback)

    async def _show_agent_selection(self) -> None:
        """显示智能体选择对话框"""
        try:
            llm_client = self._get_llm_client()

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

            # 显示选择对话框（至少包含"智能问答"选项）
            await self._display_agent_dialog(agent_list, llm_client)

        except (OSError, ValueError, RuntimeError) as e:
            log_exception(self.logger, "显示智能体选择对话框失败", e)
            # 即使出错也显示默认选项
            agent_list = [("", "智能问答")]
            try:
                llm_client = self._get_llm_client()
                await self._display_agent_dialog(agent_list, llm_client)
            except (OSError, ValueError, RuntimeError, AttributeError):
                self._show_error_message("无法显示智能体选择对话框")

    async def _display_agent_dialog(self, agent_list: list[tuple[str, str]], llm_client: LLMClientBase) -> None:
        """显示智能体选择对话框"""

        def on_agent_selected(selected_agent: tuple[str, str]) -> None:
            """智能体选择回调"""
            self.current_agent = selected_agent
            app_id, name = selected_agent

            # 设置智能体到客户端
            if hasattr(llm_client, "set_current_agent"):
                llm_client.set_current_agent(app_id)  # type: ignore[attr-defined]

            # 显示选择结果
            self._show_info_message(f"已选择智能体: {name}")

        dialog = AgentSelectionDialog(agent_list, on_agent_selected)
        self.push_screen(dialog)

    def _show_error_message(self, message: str) -> None:
        """显示错误消息"""
        try:
            output_container = self.query_one("#output-container")
            output_container.mount(OutputLine(message, command=False))
        except (AttributeError, ValueError, RuntimeError):
            # 如果UI组件已不可用，只记录错误日志
            self.logger.exception("Failed to display error message")

    def _show_info_message(self, message: str) -> None:
        """显示信息消息"""
        try:
            output_container = self.query_one("#output-container")
            output_container.mount(OutputLine(message, command=False))
        except (AttributeError, ValueError, RuntimeError):
            # 如果UI组件已不可用，只记录错误日志
            self.logger.exception("Failed to display info message")

    def action_toggle_focus(self) -> None:
        """在命令输入框和文本区域之间切换焦点"""
        # 获取当前聚焦的组件
        focused = self.focused
        if isinstance(focused, CommandInput):
            # 如果当前聚焦在命令输入框，则聚焦到输出容器
            output_container = self.query_one("#output-container", FocusableContainer)
            output_container.focus()
        else:
            # 否则聚焦到命令输入框
            self.query_one(CommandInput).focus()

    def on_mount(self) -> None:
        """初始化完成时设置焦点和绑定"""
        self.query_one(CommandInput).focus()
        self._update_bindings()

    def _update_bindings(self) -> None:
        """根据后端类型更新键绑定"""
        from config.model import Backend

        # 移除现有的智能体选择绑定
        bindings_to_keep = [binding for binding in self.BINDINGS if getattr(binding, "action", None) != "choose_agent"]

        # 只有 Hermes 后端才添加智能体选择
        if self.config_manager.get_backend() == Backend.EULERINTELLI:
            # 在"重置对话"后插入智能体选择
            agent_binding = Binding(key="ctrl+t", action="choose_agent", description="选择智能体")
            # 找到重置对话的位置
            for i, binding in enumerate(bindings_to_keep):
                if getattr(binding, "action", None) == "reset_conversation":
                    bindings_to_keep.insert(i + 1, agent_binding)
                    break

        # 更新绑定列表
        self.BINDINGS.clear()
        self.BINDINGS.extend(bindings_to_keep)

    def refresh_llm_client(self) -> None:
        """刷新 LLM 客户端实例，用于配置更改后重新创建客户端"""
        self._llm_client = BackendFactory.create_client(self.config_manager)
        # 配置更改后重新更新绑定
        self._update_bindings()

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

        # 异步处理命令
        self.processing = True
        # 创建任务并保存到类属性中的任务集合
        task = asyncio.create_task(self._process_command(user_input))
        self.background_tasks.add(task)
        # 添加完成回调，自动从集合中移除
        task.add_done_callback(self._task_done_callback)

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
        except (OSError, ValueError, RuntimeError):
            self.logger.exception("Command processing error")
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
        except (OSError, ValueError) as e:
            # 添加异常处理，显示错误信息
            try:
                output_container = self.query_one("#output-container", Container)
                error_msg = self._format_error_message(e)
                # 检查应用是否已经开始退出
                if hasattr(self, "is_running") and self.is_running:
                    output_container.mount(OutputLine(error_msg, command=False))
            except (AttributeError, ValueError, RuntimeError):
                # 如果UI组件已不可用，只记录错误日志
                self.logger.exception("Failed to display error message")
        finally:
            # 重新聚焦到输入框（如果应用仍在运行）
            try:
                if hasattr(self, "is_running") and self.is_running:
                    self.query_one(CommandInput).focus()
            except (AttributeError, ValueError, RuntimeError):
                # 应用可能正在退出，忽略聚焦错误
                self.logger.debug("Failed to focus input widget, app may be exiting")
            # 注意：不在这里重置processing标志，由回调函数处理

    async def _handle_command_stream(self, user_input: str, output_container: Container) -> bool:
        """处理命令流式响应"""
        current_line: OutputLine | MarkdownOutputLine | None = None
        current_content = ""  # 用于累积内容
        is_first_content = True  # 标记是否是第一段内容
        received_any_content = False  # 标记是否收到任何内容
        start_time = asyncio.get_event_loop().time()
        timeout_seconds = 60.0  # 60秒超时

        try:
            # 通过 process_command 获取命令处理结果和输出类型
            async for output_tuple in process_command(user_input, self._get_llm_client()):
                content, is_llm_output = output_tuple  # 解包输出内容和类型标志
                received_any_content = True

                # 检查超时
                if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                    output_container.mount(OutputLine("请求超时，已停止处理", command=False))
                    break

                # 处理内容
                params = ContentChunkParams(
                    content=content,
                    is_llm_output=is_llm_output,
                    current_content=current_content,
                    is_first_content=is_first_content,
                )
                current_line = await self._process_content_chunk(
                    params,
                    current_line,
                    output_container,
                )

                # 更新状态
                if is_first_content:
                    is_first_content = False
                    current_content = content
                elif isinstance(current_line, MarkdownOutputLine) and is_llm_output:
                    current_content += content

                # 滚动到底部
                await self._scroll_to_end()

        except asyncio.TimeoutError:
            self.logger.warning("Command stream timed out")
            if hasattr(self, "is_running") and self.is_running:
                output_container.mount(OutputLine("请求超时，请稍后重试", command=False))
        except asyncio.CancelledError:
            self.logger.info("Command stream was cancelled")
            if received_any_content and hasattr(self, "is_running") and self.is_running:
                output_container.mount(OutputLine("[处理被中断]", command=False))

        return received_any_content

    async def _process_content_chunk(
        self,
        params: ContentChunkParams,
        current_line: OutputLine | MarkdownOutputLine | None,
        output_container: Container,
    ) -> OutputLine | MarkdownOutputLine:
        """处理单个内容块"""
        content = params.content
        is_llm_output = params.is_llm_output
        current_content = params.current_content
        is_first_content = params.is_first_content

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
            updated_content = current_content + content
            current_line.update_markdown(updated_content)
            return current_line

        if not is_llm_output and isinstance(current_line, OutputLine):
            # 继续累积命令输出纯文本
            current_text = current_line.get_content()
            current_line.update(current_text + content)
            return current_line

        # 输出类型发生变化，创建新的输出组件
        new_line = MarkdownOutputLine(content) if is_llm_output else OutputLine(content)
        output_container.mount(new_line)
        return new_line

    def _format_error_message(self, error: BaseException) -> str:
        """格式化错误消息"""
        error_str = str(error).lower()
        if "timeout" in error_str:
            return "请求超时，请稍后重试"
        if any(keyword in error_str for keyword in ["network", "connection"]):
            return "网络连接错误，请检查网络后重试"
        return f"处理命令时出错: {error!s}"

    async def _scroll_to_end(self) -> None:
        """滚动到容器底部的辅助方法"""
        # 获取输出容器
        output_container = self.query_one("#output-container")
        # 使用同步方法滚动，确保UI更新
        output_container.scroll_end(animate=False)
        # 等待一个小的延迟，确保UI有时间更新
        await asyncio.sleep(0.01)

    def _get_llm_client(self) -> LLMClientBase:
        """获取大模型客户端，使用单例模式维持对话历史"""
        if self._llm_client is None:
            self._llm_client = BackendFactory.create_client(self.config_manager)
        return self._llm_client
