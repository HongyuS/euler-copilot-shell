"""获取认证信息"""

import argparse
import json
import logging
import sys

import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)

HTTP_OK = 200


def get_user_token(auth_hub_url: str, username: str = "administrator", password: str = "changeme") -> str:  # noqa: S107
    """获取用户令牌"""
    url = auth_hub_url + "/oauth2/manager-login"
    response = requests.post(
        url,
        json={"password": password, "username": username},
        headers={"Content-Type": "application/json"},
        verify=False,  # noqa: S501
        timeout=10,
    )
    response.raise_for_status()
    if int(response.json().get("code")) != HTTP_OK:
        error_msg = f"获取用户令牌失败: {response.json().get('message', '未知错误')}"
        raise ValueError(error_msg)
    return response.json()["data"]["user_token"]


def register_app(
    auth_hub_url: str,
    user_token: str,
    client_name: str,
    client_url: str,
    redirect_urls: list[str],
) -> None:
    """注册应用"""
    payload = {
        "client_name": client_name,
        "client_uri": client_url,
        "redirect_uris": redirect_urls,
        "register_callback_uris": [],
        "logout_callback_uris": [],
        "skip_authorization": True,
        "scope": ["email", "phone", "username", "openid", "offline_access"],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    sys.stdout.write(f"调试: 发送 payload: {json.dumps(payload, indent=2)}\n")  # 添加调试
    sys.stdout.write(f"调试: Authorization 头: {user_token}\n")  # 添加调试
    response = requests.post(
        auth_hub_url + "/oauth2/applications/register",
        json=payload,
        headers={"Authorization": user_token, "Content-Type": "application/json"},
        verify=False,  # noqa: S501
        timeout=10,
    )
    response.raise_for_status()
    if int(response.json().get("code")) != HTTP_OK:
        error_msg = f"注册应用失败: {response.json().get('message', '未知错误')}"
        raise ValueError(error_msg)


def get_client_secret(auth_hub_url: str, user_token: str, target_client_name: str) -> dict[str, str]:
    """获取客户端密钥"""
    response = requests.get(
        auth_hub_url + "/oauth2/applications",
        headers={"Authorization": user_token, "Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    apps_data = response.json()
    if int(apps_data.get("code")) != HTTP_OK:
        error_msg = f"获取应用列表失败: {apps_data.get('message', '未知错误')}"
        raise ValueError(error_msg)

    candidate_names = []
    for app in apps_data["data"]["applications"]:
        client_metadata = app.get("client_metadata") or {}
        if isinstance(client_metadata, str):
            try:
                client_metadata = json.loads(client_metadata)
            except json.JSONDecodeError:
                logger.exception("无法解析 client_metadata JSON")
                client_metadata = {}

        candidate_names = [
            client_metadata.get("client_name"),
            app.get("client_name"),
            app.get("client_info", {}).get("client_name"),
        ]

        if any(str(name).lower() == target_client_name.lower() for name in candidate_names if name):
            return {"client_id": app["client_info"]["client_id"], "client_secret": app["client_info"]["client_secret"]}

    error_msg = "未找到匹配应用，请检查 client_name 是否准确（尝试使用全小写名称）"
    if candidate_names:
        error_msg += "\n已查询的应用名称包括: "
        error_msg += ", ".join(name for name in candidate_names if name)
    raise ValueError(error_msg)


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("eulercopilot_domain", help="EulerCopilot域名（例如：example.com）")
    args = parser.parse_args()

    # 检查参数是否为空
    if not args.eulercopilot_domain or args.eulercopilot_domain.strip() == "":
        sys.stderr.write("错误: 域名参数为空\n")
        sys.exit(1)

    # 获取服务信息
    namespace: str = "euler-copilot"
    service_name: str = "authhub-web-service"
    auth_hub_url: str = "http://127.0.0.1:8000"

    # 生成固定URL
    client_url: str = f"http://{args.eulercopilot_domain}:8080"
    redirect_urls: list[str] = [f"http://{args.eulercopilot_domain}:8080/api/auth/login"]
    client_name: str = "EulerCopilot"  # 设置固定默认值

    # 认证流程
    try:
        sys.stdout.write("\n正在获取用户令牌...\n")
        user_token = get_user_token(auth_hub_url)
        sys.stdout.write("✓ 用户令牌获取成功\n")

        sys.stdout.write(f"\n正在注册应用 [名称: {client_name}]...\n")
        register_app(auth_hub_url, user_token, client_name, client_url, redirect_urls)
        sys.stdout.write("✓ 应用注册成功\n")

        sys.stdout.write(f"\n正在查询客户端凭证 [名称: {client_name}]...\n")
        client_info = get_client_secret(auth_hub_url, user_token, client_name)

        sys.stdout.write("\n✓ 认证信息获取成功：\n")
        sys.stdout.write(f"client_id: {client_info['client_id']}\n")
        sys.stdout.write(f"client_secret: {client_info['client_secret']}\n")

    except requests.exceptions.HTTPError as e:
        sys.stdout.write(f"\nHTTP 错误: {e.response.status_code} - {e.response.text}\n")
        sys.exit(1)
    except Exception:
        logger.exception("错误: ")
        sys.exit(1)
