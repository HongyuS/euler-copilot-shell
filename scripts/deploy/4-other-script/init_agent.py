import requests
from pydantic import BaseModel, Field
from enum import Enum

base_url = "http://127.0.0.1:8002"


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
    first_questions: list[str] = Field(
        default=[], alias="recommendedQuestions", description="推荐问题", max_length=3)
    history_len: int = Field(3, alias="dialogRounds", ge=1, le=10, description="对话轮次（1～10）")
    permission: AppPermissionData = Field(
        default_factory=lambda: AppPermissionData(authorizedUsers=None), description="权限配置")
    workflows: list[AppFlowInfo] = Field(default=[], description="工作流信息列表")
    mcp_service: list[str] = Field(default=[], alias="mcpService", description="MCP服务id列表")


def call_mcp_api():
    """
    调用MCP API获取服务列表信息

    返回:
        dict: 解析后的API响应数据，如果请求失败则返回None
    """
    # API地址
    url = base_url + "/api/mcp"

    try:
        # 发送GET请求
        response = requests.get(url, timeout=10)

        # 检查响应状态码
        if response.status_code == 200:
            # 解析JSON响应
            result = response.json()

            # 检查返回的code是否为200
            if result.get("code") == 200:
                print("API调用成功")
                return result
            else:
                print(f"API返回错误: {result.get('message', '未知错误')}")
                return None
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求发生异常: {str(e)}")
        return None


def call_app_api(appdata: AppData):
    """
    创建智能体应用agent

    返回:
        接口响应对象 app_id，如果请求失败则返回None
    """
    # 接口URL
    url = base_url + "/api/app"
    try:
        # 发送POST请求
        response = requests.post(url, json=appdata.model_dump(by_alias=True))

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        print(f"创建智能体应用agent成功，name: {appdata.name}")
        return response.json().get("result", {})["appId"]

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

    return None


def query_mcp_server(mcp_id: str):
    """
    查询mcp服务状态
    """
    url = base_url + "/api/mcp/" + mcp_id
    try:
        # 发送POST请求
        response = requests.get(url)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        print(f"请求成功，状态码: {response.status_code}")
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

    return None


def activate_mcp_server(mcp_id: str):
    """
    激活mcp服务
    """
    url = base_url + "/api/mcp/" + mcp_id
    body = {"active": "true"}
    try:
        # 发送POST请求
        response = requests.post(url, json=body)

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        print(f"激活mcp服务 mcp_id: {mcp_id} 成功")
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

    return None


def deploy_app(app_id:str):
    """
    发布应用
    """
    url = base_url + "/api/app/" + app_id
    try:
        # 发送POST请求
        response = requests.post(url, json={})

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        print(f"发布应用 app_id: {app_id} 成功")
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误，无法连接到服务器")
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

    return None

def create_agent():
    """
    主入口
    查询mcp服务，依次激活，根据mcp服务创建agent
    """
    api_result = call_mcp_api()
    if api_result:
        # 打印服务列表信息
        services = api_result.get("result", {}).get("services", [])
        print(f"\n共获取到 {len(services)} 个服务:")

        for service in services:
            print(f"\n服务ID: {service.get('mcpserviceId')}")
            print(f"服务名称: {service.get('name')}")
            print(f"服务状态: {service.get('status')}")
            print(f"服务描述: {service.get('description')}")
            app_data = AppData(
                appType=AppType.AGENT,
                description=service.get('description')[:150],
                dialogRounds=3,
                icon="",
                mcpService=[service.get('mcpserviceId')],
                name=service.get('name'),
                permission=AppPermissionData(
                    visibility="public",
                    authorizedUsers=[]
                )
            )
            if not service.get("isActive"):
                activate_mcp_server(service.get('mcpserviceId'))
            app_id = call_app_api(app_data)
            deploy_app(app_id)


# 使用示例
if __name__ == "__main__":
    create_agent()