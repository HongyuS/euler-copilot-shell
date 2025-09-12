"""
初始化智能体应用的脚本

此脚本用于查询MCP服务列表，激活未激活的服务，
并为每个服务创建对应的智能体应用。
"""

from __future__ import annotations

import logging
from enum import Enum

import requests
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_url = "http://127.0.0.1:8002"

# 常量定义
SUCCESS_CODE = 200
TIMEOUT = 10


class AppType(str, Enum):
    """应用中心应用类型"""

    FLOW = "flow"
    AGENT = "agent"


class AppLink(BaseModel):
    """App的相关链接"""

    title: str = Field(description="链接标题")
    url: str = Field(..., description="链接地址", pattern=r"^(https|http)://.*$")


class PermissionType(str, Enum):
    """权限类型"""

    PROTECTED = "protected"
    PUBLIC = "public"
    PRIVATE = "private"


class AppPermissionData(BaseModel):
    """应用权限数据结构"""

    type: PermissionType = Field(
        default=PermissionType.PRIVATE,
        alias="visibility",
        description="可见性（public/private/protected）",
    )
    users: list[str] | None = Field(
        None,
        alias="authorizedUsers",
        description="附加人员名单（如果可见性为部分人可见）",
    )


class AppFlowInfo(BaseModel):
    """应用工作流数据结构"""

    id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流简介")
    debug: bool = Field(..., description="是否经过调试")


class AppData(BaseModel):
    """应用信息数据结构"""

    app_type: AppType = Field(..., alias="appType", description="应用类型")
    icon: str = Field(default="", description="图标")
    name: str = Field(..., max_length=20, description="应用名称")
    description: str = Field(..., max_length=150, description="应用简介")
    links: list[AppLink] = Field(default=[], description="相关链接", max_length=5)
    first_questions: list[str] = Field(default=[], alias="recommendedQuestions", description="推荐问题", max_length=3)
    history_len: int = Field(3, alias="dialogRounds", ge=1, le=10, description="对话轮次（1～10）")
    permission: AppPermissionData = Field(
        default_factory=lambda: AppPermissionData(authorizedUsers=None),
        description="权限配置",
    )
    workflows: list[AppFlowInfo] = Field(default=[], description="工作流信息列表")
    mcp_service: list[str] = Field(default=[], alias="mcpService", description="MCP服务id列表")


def call_mcp_api() -> dict | None:
    """
    调用MCP API获取服务列表信息

    返回:
        dict: 解析后的API响应数据，如果请求失败则返回None
    """
    # API地址
    url = base_url + "/api/mcp"

    try:
        # 发送GET请求
        response = requests.get(url, timeout=TIMEOUT)

        # 检查响应状态码
        if response.status_code == SUCCESS_CODE:
            # 解析JSON响应
            result = response.json()

            # 检查返回的code是否为200
            if result.get("code") == SUCCESS_CODE:
                logger.info("API调用成功")
                return result
            logger.error("API返回错误: %s", result.get("message", "未知错误"))
            return None

        logger.error("请求失败，状态码: %s", response.status_code)

    except requests.exceptions.RequestException:
        logger.exception("请求发生异常")
        return None
    else:
        return None


def call_app_api(appdata: AppData) -> str | None:
    """
    创建智能体应用agent

    返回:
        接口响应对象 app_id，如果请求失败则返回None
    """
    # 接口URL
    url = base_url + "/api/app"
    try:
        # 发送POST请求
        response = requests.post(url, json=appdata.model_dump(by_alias=True), timeout=TIMEOUT)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        logger.info("创建智能体应用agent成功，name: %s", appdata.name)
        return response.json().get("result", {}).get("appId")

    except requests.exceptions.HTTPError:
        logger.exception("HTTP错误")
    except requests.exceptions.ConnectionError:
        logger.exception("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        logger.exception("请求超时")
    except requests.exceptions.RequestException:
        logger.exception("请求发生错误")

    return None


def query_mcp_server(mcp_id: str) -> dict | None:
    """查询mcp服务状态"""
    url = base_url + "/api/mcp/" + mcp_id
    try:
        # 发送POST请求
        response = requests.get(url, timeout=TIMEOUT)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        logger.info("请求成功，状态码: %s", response.status_code)
        return response.json()

    except requests.exceptions.HTTPError:
        logger.exception("HTTP错误")
    except requests.exceptions.ConnectionError:
        logger.exception("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        logger.exception("请求超时")
    except requests.exceptions.RequestException:
        logger.exception("请求发生错误")

    return None


def activate_mcp_server(mcp_id: str) -> dict | None:
    """激活mcp服务"""
    url = base_url + "/api/mcp/" + mcp_id
    body = {"active": "true"}
    try:
        # 发送POST请求
        response = requests.post(url, json=body, timeout=TIMEOUT)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        logger.info("激活mcp服务 mcp_id: %s 成功", mcp_id)
        return response.json()

    except requests.exceptions.HTTPError:
        logger.exception("HTTP错误")
    except requests.exceptions.ConnectionError:
        logger.exception("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        logger.exception("请求超时")
    except requests.exceptions.RequestException:
        logger.exception("请求发生错误")

    return None


def deploy_app(app_id: str) -> dict | None:
    """发布应用"""
    url = base_url + "/api/app/" + app_id
    try:
        # 发送POST请求
        response = requests.post(url, json={}, timeout=TIMEOUT)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        logger.info("发布应用 app_id: %s 成功", app_id)
        return response.json()

    except requests.exceptions.HTTPError:
        logger.exception("HTTP错误")
    except requests.exceptions.ConnectionError:
        logger.exception("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        logger.exception("请求超时")
    except requests.exceptions.RequestException:
        logger.exception("请求发生错误")

    return None


def create_agent() -> None:
    """
    主入口

    查询mcp服务，依次激活，根据mcp服务创建agent
    """
    api_result = call_mcp_api()
    if api_result:
        # 打印服务列表信息
        services = api_result.get("result", {}).get("services", [])
        logger.info("共获取到 %s 个服务", len(services))

        for service in services:
            logger.info("服务ID: %s", service.get("mcpserviceId"))
            logger.info("服务名称: %s", service.get("name"))
            logger.info("服务状态: %s", service.get("status"))
            logger.info("服务描述: %s", service.get("description"))
            app_data = AppData(
                appType=AppType.AGENT,
                description=service.get("description")[:150],
                dialogRounds=3,
                icon="",
                mcpService=[service.get("mcpserviceId")],
                name=service.get("name"),
                permission=AppPermissionData(visibility=PermissionType.PUBLIC, authorizedUsers=[]),
            )
            if not service.get("isActive"):
                activate_mcp_server(service.get("mcpserviceId"))
            app_id = call_app_api(app_data)
            if app_id:
                deploy_app(app_id)


# 使用示例
if __name__ == "__main__":
    create_agent()
