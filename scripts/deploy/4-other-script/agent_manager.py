import json
import sys
import os
import shutil
import argparse
import logging
from typing import Optional, Dict, List, Any
from enum import Enum
from pydantic import BaseModel, Field, ValidationError

import aiohttp
import asyncio
from aiohttp import ClientError, ClientResponseError

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp_manager")

# 配置参数 - 可通过环境变量覆盖
BASE_URL = os.getenv("MCP_BASE_URL", "http://127.0.0.1:8002")
BASE_DIR = os.getenv("MCP_BASE_DIR", "/opt/copilot/semantics/mcp/template")
REQUEST_TIMEOUT = 30  # 请求超时时间(秒)
MAX_RETRY_COUNT = 3  # API请求重试次数
RETRY_DELAY = 2  # 重试延迟(秒)
SERVICE_WAIT_TIMEOUT = 60  # 服务等待超时时间(秒)


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
    users: Optional[List[str]] = Field(
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
    links: List[AppLink] = Field(default=[], description="相关链接", max_length=5)
    first_questions: List[str] = Field(
        default=[], alias="recommendedQuestions", description="推荐问题", max_length=3)
    history_len: int = Field(3, alias="dialogRounds", ge=1, le=10, description="对话轮次（1～10）")
    permission: AppPermissionData = Field(
        default_factory=lambda: AppPermissionData(authorizedUsers=None), description="权限配置")
    workflows: List[AppFlowInfo] = Field(default=[], description="工作流信息列表")
    mcp_service: List[str] = Field(default=[], alias="mcpService", description="MCP服务id列表")


class ApiClient:
    """API请求客户端封装"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭客户端会话"""
        await self.session.close()

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        带重试机制的异步API请求

        Args:
            method: HTTP方法
            path: API路径
            **kwargs: 传递给aiohttp的参数

        Returns:
            API响应的JSON数据

        Raises:
            ClientError: 当请求失败时
        """
        url = f"{self.base_url}{path}"
        for retry in range(MAX_RETRY_COUNT):
            try:
                async with self.session.request(
                        method, url, timeout=REQUEST_TIMEOUT, **kwargs
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except (ClientResponseError, ClientError) as e:
                logger.warning(
                    f"API请求失败(第{retry + 1}/{MAX_RETRY_COUNT}次) - {method} {url}: {str(e)}"
                )
                if retry < MAX_RETRY_COUNT - 1:
                    await asyncio.sleep(RETRY_DELAY)

        raise RuntimeError(f"API请求多次失败: {method} {url}")


def copy_folder(src_dir: str, dest_dir: str) -> None:
    """
    递归复制源文件夹到目标目录

    Args:
        src_dir: 源文件夹路径
        dest_dir: 目标目录路径

    Raises:
        NotADirectoryError: 源路径不是有效的文件夹
        RuntimeError: 复制过程中发生错误
    """
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(f"源路径 {src_dir} 不是一个有效的文件夹")

    src_folder_name = os.path.basename(src_dir)
    dest_full_path = os.path.join(dest_dir, src_folder_name)

    try:
        os.makedirs(dest_full_path, exist_ok=True)
        for item in os.listdir(src_dir):
            src_item = os.path.join(src_dir, item)
            dest_item = os.path.join(dest_full_path, item)

            if os.path.isdir(src_item):
                copy_folder(src_item, dest_full_path)
            else:
                shutil.copy2(src_item, dest_item)
                logger.debug(f"已复制文件: {src_item} -> {dest_item}")

    except PermissionError:
        raise RuntimeError(f"权限不足，无法操作文件: {src_item}")
    except Exception as e:
        raise RuntimeError(f"复制文件夹失败: {str(e)}")


def get_config(config_path: str) -> dict:
    """
    读取并验证配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        解析后的配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
        RuntimeError: 读取文件失败
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as reader:
            config = json.load(reader)

        if not isinstance(config, dict):
            raise ValueError("配置文件内容必须为JSON对象")

        logger.info(f"成功加载配置文件: {config_path}")
        return config

    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"读取配置文件失败: {str(e)}")


async def wait_for_mcp_service(api_client: ApiClient, service_id: str) -> Dict[str, Any]:
    """
    等待MCP服务就绪

    Args:
        api_client: API客户端实例
        service_id: MCP服务ID

    Returns:
        服务信息字典

    Raises:
        RuntimeError: 服务超时未就绪
    """
    logger.info(f"等待MCP服务就绪: {service_id}")
    for elapsed in range(SERVICE_WAIT_TIMEOUT):
        try:
            service = await query_mcp_server(api_client, service_id)
            if service and service.get("status") == "ready":
                logger.info(f"MCP服务 {service_id} 已就绪 (耗时 {elapsed} 秒)")
                return service

            await asyncio.sleep(1)

        except Exception as e:
            logger.warning(f"查询服务状态失败: {str(e)}，将继续等待")

    raise RuntimeError(f"MCP服务 {service_id} 等待超时 ({SERVICE_WAIT_TIMEOUT}秒) 未就绪")


async def delete_mcp_server(api_client: ApiClient, server_id: str) -> Dict[str, Any]:
    """删除mcp服务"""
    logger.info(f"删除MCP服务: {server_id}")
    return await api_client.request("DELETE", f"/api/mcp/{server_id}")


async def create_mcp_server(api_client: ApiClient, mcp_config: dict) -> str:
    """创建或更新mcp服务状态"""
    logger.info("创建MCP服务")
    response = await api_client.request("POST", "/api/mcp/", json=mcp_config)

    service_id = response.get("result", {}).get("serviceId")
    if not service_id:
        raise RuntimeError("创建MCP服务未返回有效的serviceId")

    logger.info(f"MCP服务创建成功，service_id: {service_id}")
    return service_id


async def process_mcp_config(api_client: ApiClient, config_path: str) -> str:
    """
    处理MCP配置文件：读取配置、创建服务器、保存server_id

    Args:
        api_client: API客户端实例
        config_path: 配置文件路径

    Returns:
        生成的server_id
    """
    config = get_config(config_path)

    # 先删除已存在的服务
    if 'serviceId' in config:
        try:
            await delete_mcp_server(api_client, config['serviceId'])
            del config['serviceId']
            logger.info("已删除旧的MCP服务ID")
        except Exception as e:
            logger.warning(f"删除旧MCP服务失败(可能不存在)，继续创建新服务: {str(e)}")

    # 创建新服务
    server_id = await create_mcp_server(api_client, config)

    # 保存更新后的配置文件
    try:
        config['serviceId'] = server_id
        with open(config_path, 'w', encoding='utf-8') as writer:
            json.dump(config, writer, ensure_ascii=False, indent=4)

        logger.info(f"配置文件已更新: {config_path}")
        return server_id

    except Exception as e:
        raise RuntimeError(f"保存配置文件失败: {str(e)}")


async def query_mcp_server(api_client: ApiClient, mcp_id: str) -> Optional[Dict[str, Any]]:
    """查询MCP服务状态"""
    logger.debug(f"查询MCP服务状态: {mcp_id}")
    response = await api_client.request("GET", "/api/mcp")

    if response.get("code") != 200:
        raise RuntimeError(f"查询MCP服务失败: {response.get('message', '未知错误')}")

    services = response.get("result", {}).get("services", [])
    for service in services:
        if service.get("mcpserviceId") == mcp_id:
            logger.debug(f"MCP服务 {mcp_id} 状态: {service.get('status')}")
            return service

    return None


async def install_mcp_server(api_client: ApiClient, mcp_id: str) -> Dict[str, Any]:
    """安装mcp服务"""
    logger.info(f"安装MCP服务: {mcp_id}")
    response = await api_client.request("GET", "/api/mcp")

    if response.get("code") != 200:
        raise RuntimeError(f"查询MCP服务列表失败: {response.get('message', '未知错误')}")

    services = response.get("result", {}).get("services", [])
    for service in services:
        if service.get("mcpserviceId") == mcp_id:
            logger.debug(f"MCP服务 {mcp_id} 状态: {service.get('status')}")
            if service.get('status') != "ready":
                logger.debug(f"开始安装MCP服务{mcp_id}")
                return await api_client.request("POST", f"/api/mcp/{mcp_id}/install")
            break


async def activate_mcp_server(api_client: ApiClient, mcp_id: str) -> Dict[str, Any]:
    """激活mcp服务"""
    logger.info(f"激活MCP服务: {mcp_id}")
    return await api_client.request("POST", f"/api/mcp/{mcp_id}", json={"active": "true"})


async def deploy_app(api_client: ApiClient, app_id: str) -> Dict[str, Any]:
    """发布应用"""
    logger.info(f"发布应用: {app_id}")
    return await api_client.request("POST", f"/api/app/{app_id}", json={})


async def call_app_api(api_client: ApiClient, appdata: AppData) -> str:
    """创建智能体应用agent"""
    try:
        app_data_dict = appdata.model_dump(by_alias=True)
        logger.debug(f"创建应用数据: {json.dumps(app_data_dict, ensure_ascii=False)}")

        response = await api_client.request("POST", "/api/app", json=app_data_dict)
        app_id = response.get("result", {}).get("appId")

        if not app_id:
            raise RuntimeError("创建应用未返回有效的appId")

        logger.info(f"应用创建成功，app_id: {app_id}")
        return app_id

    except ValidationError as e:
        raise ValueError(f"应用数据验证失败: {str(e)}")


async def get_app_list(api_client: ApiClient) -> str:
    """查询智能体应用agent list"""
    try:

        response = await api_client.request("GET", "/api/app")
        return str(response)

    except ValidationError as e:
        raise ValueError(f"应用数据验证失败: {str(e)}")


async def comb_create(api_client: ApiClient, config_path: str) -> None:
    """组合创建流程：安装多个MCP服务并创建应用"""
    config = get_config(config_path)
    mcp_services = config.get("mcpService", [])

    if not mcp_services:
        raise ValueError("配置文件中未找到mcpService列表")

    # 处理所有MCP服务
    for service in mcp_services:
        service_id = service.get("id")
        await install_mcp_server(api_client, service_id)
        mcp_server = await wait_for_mcp_service(api_client, service_id)

        # 激活服务（如果未激活）
        if not mcp_server.get("isActive"):
            await activate_mcp_server(api_client, service_id)

    # 创建并发布应用
    try:
        app_data = AppData(**config)
        app_id = await call_app_api(api_client, app_data)
        await deploy_app(api_client, app_id)
        logger.info("组合创建流程完成")
    except Exception as e:
        raise RuntimeError(f"组合创建失败: {str(e)}")


async def create_agent(api_client: ApiClient, config_path: str) -> None:
    """创建agent流程：处理单个MCP服务并创建应用"""
    config = get_config(config_path)
    service_id = config.get("serviceId")

    if not service_id:
        raise ValueError("配置文件中未找到serviceId")

    # 安装并等待服务就绪
    await install_mcp_server(api_client, service_id)
    mcp_server = await wait_for_mcp_service(api_client, service_id)

    # 激活服务（如果未激活）
    if not mcp_server.get("isActive"):
        await activate_mcp_server(api_client, service_id)

    # 创建应用数据
    app_name = mcp_server.get('name', f"agent_{service_id[:6]}")[:20]
    app_desc = mcp_server.get('description', f"Auto-created agent for {service_id}")[:150]

    app_data = AppData(
        appType=AppType.AGENT,
        description=app_desc,
        dialogRounds=3,
        icon="",
        mcpService=[service_id],
        name=app_name,
        permission=AppPermissionData(
            visibility=PermissionType.PUBLIC,
            authorizedUsers=[]
        )
    )

    # 创建并发布应用
    app_id = await call_app_api(api_client, app_data)
    await deploy_app(api_client, app_id)
    logger.info("Agent创建流程完成")


async def main_async():
    parser = argparse.ArgumentParser(description='MCP服务器管理工具')
    parser.add_argument(
        'operator',
        choices=['init', 'create', 'comb'],
        help='操作指令：init（初始化mcp server）、create（创建agent）、comb（创建组合mcp的agent）'
    )
    parser.add_argument(
        'config_path',
        help='MCP配置文件的路径（例如：/opt/mcp-servers/config.json）要求是全路径'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志信息'
    )
    parser.add_argument(
        '--url',
        help=f'MCP服务基础URL，默认: {BASE_URL}',
        default=BASE_URL
    )

    args = parser.parse_args()

    # 调整日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 验证配置文件路径
    if not args.config_path or not os.path.isfile(args.config_path):
        logger.error(f"无效的配置文件路径: {args.config_path}")
        sys.exit(1)

    # 创建API客户端
    api_client = ApiClient(args.url)

    try:
        if args.operator == 'init':
            await process_mcp_config(api_client, args.config_path)
        elif args.operator == 'create':
            await create_agent(api_client, args.config_path)
        elif args.operator == 'comb':
            await comb_create(api_client, args.config_path)
        logger.info("操作执行成功")
    except Exception as e:
        logger.error(f"操作失败: {str(e)}", exc_info=args.verbose)
        sys.exit(1)
    finally:
        await api_client.close()
        sys.exit(0)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)


if __name__ == '__main__':
    main()