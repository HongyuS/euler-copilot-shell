"""Hermes HTTP 客户端基础管理器"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from log.manager import get_logger


class HermesHttpManager:
    """Hermes HTTP 客户端管理器"""

    def __init__(self, base_url: str, auth_token: str = "") -> None:
        """初始化 HTTP 管理器"""
        self.logger = get_logger(__name__)
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.client: httpx.AsyncClient | None = None

    def get_host_header(self) -> str:
        """
        从 base_url 中提取主机名用于 Host 请求头字段

        Returns:
            str: 主机名，如 'www.eulercopilot.io'

        """
        parsed_url = urlparse(self.base_url)
        return parsed_url.netloc

    async def get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self.client is None or self.client.is_closed:
            headers = {
                "Accept": "text/event-stream",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Content-Type": "application/json; charset=UTF-8",
            }
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            timeout = httpx.Timeout(
                connect=30.0,  # 连接超时，允许30秒建立连接
                read=None,  # 读取超时，无限制以支持超长时间SSE流
                write=30.0,  # 写入超时
                pool=30.0,  # 连接池超时
            )
            self.client = httpx.AsyncClient(headers=headers, timeout=timeout)
        return self.client

    def build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """构建请求的 HTTP 头部"""
        headers = {
            "Host": self.get_host_header(),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.logger.info("HTTP 客户端已关闭")
