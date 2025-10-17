"""自定义 Header 组件，简化版本"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from rich.text import Text
from textual.dom import NoScreen
from textual.reactive import Reactive
from textual.widget import Widget

if TYPE_CHECKING:
    from textual.app import ComposeResult, RenderResult
    from textual.events import Mount


class OIHeaderIcon(Widget):
    """在 Header 左侧显示一个装饰性圆圈图标"""

    DEFAULT_CSS = """
    OIHeaderIcon {
        dock: left;
        padding: 0 1;
        width: 3;
        content-align: left middle;
    }
    """

    def render(self) -> RenderResult:
        """渲染圆圈图标"""
        return "⭘"


class OIHeaderTitle(Widget):
    """在 Header 中央显示标题和副标题"""

    DEFAULT_CSS = """
    OIHeaderTitle {
        text-wrap: nowrap;
        text-overflow: ellipsis;
        content-align: center middle;
        width: 100%;
    }
    """

    text: Reactive[str] = Reactive("")
    """主标题文本"""

    sub_text: Reactive[str] = Reactive("")
    """副标题文本"""

    def render(self) -> RenderResult:
        """渲染标题和副标题"""
        text = Text(self.text, no_wrap=True, overflow="ellipsis")
        if self.sub_text:
            text.append(" — ")
            text.append(self.sub_text, "dim")
        return text


class OIHeader(Widget):
    """自定义 Header 组件，固定单行高度"""

    DEFAULT_CSS = """
    OIHeader {
        dock: top;
        width: 100%;
        background: $panel;
        color: $foreground;
        height: 1;
    }
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        id_: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        初始化自定义 Header 组件

        Args:
            name: Header 组件的名称
            id_: Header 组件的 DOM ID
            classes: Header 组件的 CSS 类

        """
        super().__init__(name=name, id=id_, classes=classes)

    def compose(self) -> ComposeResult:
        """组合 Header 的子组件"""
        yield OIHeaderIcon()
        yield OIHeaderTitle()

    @property
    def screen_title(self) -> str:
        """
        获取 Header 要显示的标题

        取决于 Screen.title 和 App.title

        """
        screen_title = self.screen.title
        return screen_title if screen_title is not None else self.app.title

    @property
    def screen_sub_title(self) -> str:
        """
        获取 Header 要显示的副标题

        取决于 Screen.sub_title 和 App.sub_title

        """
        screen_sub_title = self.screen.sub_title
        return (
            screen_sub_title if screen_sub_title is not None else self.app.sub_title
        )

    def _on_mount(self, event: Mount) -> None:
        """挂载时设置标题更新监听"""

        async def set_title() -> None:
            with contextlib.suppress(NoScreen):
                title_widget = self.query_one(OIHeaderTitle)
                title_widget.text = self.screen_title
                title_widget.sub_text = self.screen_sub_title

        # 立即更新标题（同步调用）
        with contextlib.suppress(NoScreen):
            title_widget = self.query_one(OIHeaderTitle)
            title_widget.text = self.screen_title
            title_widget.sub_text = self.screen_sub_title

        # 监听 app 和 screen 的标题变化
        self.watch(self.app, "title", set_title)
        self.watch(self.app, "sub_title", set_title)
        self.watch(self.screen, "title", set_title)
        self.watch(self.screen, "sub_title", set_title)
