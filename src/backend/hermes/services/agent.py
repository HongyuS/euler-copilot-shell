"""Hermes 智能体管理器"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx

from backend.hermes.constants import HTTP_OK, ITEMS_PER_PAGE, MAX_PAGES
from backend.hermes.models import HermesAgent
from log.manager import get_logger, log_api_request, log_exception

if TYPE_CHECKING:
    from typing import Any

    from .http import HermesHttpManager


class HermesAgentManager:
    """Hermes 智能体管理器"""

    def __init__(self, http_manager: HermesHttpManager) -> None:
        """初始化智能体管理器"""
        self.logger = get_logger(__name__)
        self.http_manager = http_manager

    async def get_available_agents(self) -> list[HermesAgent]:
        """
        获取当前用户可用的智能体列表

        通过调用 /api/app 接口获取当前用户可用的智能体列表。
        支持分页获取所有智能体，每页最多16项，会自动请求所有页面。
        这些智能体可以在聊天中使用，选择的智能体 ID 需要在 chat 接口中填入 appId 字段。
        如果调用失败或没有返回，使用空列表。

        Returns:
            list[HermesAgent]: 可用的智能体列表（仅包含已发布的智能体）

        """
        start_time = time.time()
        self.logger.info("开始请求 Hermes 智能体列表 API")

        all_agents = []
        current_page = 1
        total_apps = 0

        try:
            while True:
                # 请求当前页
                page_agents, page_info = await self._get_agents_page(current_page)

                # 添加到总列表中
                all_agents.extend(page_agents)

                # 更新总数信息（第一次获取时）
                if current_page == 1:
                    total_apps = page_info.get("total_apps", 0)
                    self.logger.info("总共有 %d 个应用需要获取", total_apps)

                current_page_from_response = page_info.get("current_page", current_page)
                self.logger.info("获取第 %d 页完成，本页获得 %d 个智能体", current_page_from_response, len(page_agents))

                # 检查是否还有更多页面
                # 每页最多16项，如果本页获取的数量少于16，说明是最后一页
                if len(page_agents) < ITEMS_PER_PAGE:
                    self.logger.info("已获取所有页面，共 %d 页", current_page)
                    break

                # 继续请求下一页
                current_page += 1

                # 安全检查：避免无限循环
                if current_page > MAX_PAGES:
                    self.logger.warning("已达到最大页数限制(%d页)，停止请求", MAX_PAGES)
                    break

            # 过滤已发布的智能体
            published_agents = [agent for agent in all_agents if agent.published is True]

            duration = time.time() - start_time
            self.logger.info(
                "获取智能体列表完成 - 总耗时: %.3fs, 总应用数: %d, 智能体数: %d, 已发布智能体: %d",
                duration,
                total_apps,
                len(all_agents),
                len(published_agents),
            )

        except (httpx.HTTPError, httpx.InvalidURL) as e:
            # 网络请求异常
            duration = time.time() - start_time
            log_exception(self.logger, "Hermes 智能体列表 API 请求异常", e)
            log_api_request(
                self.logger,
                "GET",
                f"{self.http_manager.base_url}/api/app",
                500,
                duration,
                error=str(e),
            )
            self.logger.warning("Hermes 智能体列表 API 请求异常，返回空列表")
            return []
        else:
            return published_agents

    async def _get_agents_page(self, page: int) -> tuple[list[HermesAgent], dict[str, Any]]:
        """
        获取指定页的智能体列表

        Args:
            page: 页码，从1开始

        Returns:
            tuple[list[HermesAgent], dict[str, Any]]: (智能体列表, 页面信息)
            页面信息包含: {"current_page": int, "total_apps": int}

        Raises:
            httpx.HTTPError: 网络请求错误
            httpx.InvalidURL: URL错误

        """
        client = await self.http_manager.get_client()
        app_url = urljoin(self.http_manager.base_url, "/api/app")

        # 构建查询参数
        params = {
            "appType": "agent",  # 只获取智能体类型的应用
            "page": page,  # 当前页码
        }

        headers = self.http_manager.build_headers()
        response = await client.get(app_url, headers=headers, params=params)

        # 处理HTTP错误状态
        if response.status_code != HTTP_OK:
            error_msg = f"API 调用失败，状态码: {response.status_code}"
            self.logger.warning("获取第 %d 页失败: %s", page, error_msg)
            raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)

        # 解析响应数据
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_msg = "响应 JSON 格式无效"
            self.logger.warning("获取第 %d 页失败: %s", page, error_msg)
            raise httpx.DecodingError(error_msg) from e

        # 验证响应结构
        if not self._validate_agent_response_structure_for_page(data, page):
            return [], {}

        # 解析智能体列表和页面信息
        result = data["result"]
        agents = self._parse_agent_list(result)

        page_info = {
            "current_page": result.get("currentPage", page),
            "total_apps": result.get("totalApps", 0),
        }

        return agents, page_info

    def _validate_agent_response_structure_for_page(self, data: dict[str, Any], page: int) -> bool:
        """验证单页智能体 API 响应结构"""
        if not isinstance(data, dict):
            self.logger.warning("第 %d 页响应格式无效：不是字典", page)
            return False

        # 检查响应码
        code = data.get("code")
        if code != 0:
            message = data.get("message", "未知错误")
            self.logger.warning("第 %d 页 API 返回错误: code=%s, message=%s", page, code, message)
            return False

        # 检查result字段
        result = data.get("result")
        if not isinstance(result, dict):
            self.logger.warning("第 %d 页 result 字段不是对象", page)
            return False

        # 检查applications字段
        applications = result.get("applications")
        if not isinstance(applications, list):
            self.logger.warning("第 %d 页 applications 字段不是数组", page)
            return False

        return True

    def _parse_agent_list(self, result: dict[str, Any]) -> list[HermesAgent]:
        """解析智能体列表数据（所有 Agent 类型应用，不过滤发布状态）"""
        try:
            agents = []
            applications = result.get("applications", [])

            if not isinstance(applications, list):
                self.logger.warning("applications 字段不是列表类型")
                return []

            for app_data in applications:
                if not isinstance(app_data, dict):
                    continue

                # 只处理Agent类型的应用
                app_type = app_data.get("appType")
                if app_type != "agent":
                    continue

                try:
                    agent = HermesAgent.from_dict(app_data)
                    if agent.app_id and agent.name:  # 确保必要字段存在
                        agents.append(agent)
                    else:
                        self.logger.debug("跳过无效的智能体信息: %s", app_data)
                except (KeyError, TypeError, ValueError) as e:
                    self.logger.warning("解析智能体信息失败: %s, 错误: %s", app_data, e)

        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning("解析智能体列表数据失败: %s, 错误: %s", result, e)
            return []
        else:
            return agents
