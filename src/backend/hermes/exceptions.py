"""Hermes 异常定义"""


class HermesAPIError(Exception):
    """Hermes API 错误异常"""

    def __init__(self, status_code: int, message: str) -> None:
        """初始化 Hermes API 错误异常"""
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")
