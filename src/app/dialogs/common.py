"""通用对话框组件"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import ComposeResult

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ExitDialog(ModalScreen):
    """退出确认对话框"""

    def compose(self) -> ComposeResult:
        """构建退出确认对话框"""
        yield Container(
            Container(
                Label("确认退出吗？", id="dialog-text"),
                Horizontal(
                    Button("取消", classes="dialog-button", id="cancel"),
                    Button("确认", classes="dialog-button", id="confirm"),
                    id="dialog-buttons",
                ),
                id="exit-dialog",
            ),
            id="exit-dialog-screen",
        )

    @on(Button.Pressed, "#cancel")
    def cancel_exit(self) -> None:
        """取消退出"""
        self.app.pop_screen()

    @on(Button.Pressed, "#confirm")
    def confirm_exit(self) -> None:
        """确认退出"""
        self.app.exit()
