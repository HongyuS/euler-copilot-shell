"""
获取认证信息
"""
import json
import sys
import requests
import urllib3
import subprocess
import argparse

urllib3.disable_warnings()


def get_user_token(auth_hub_url, username="administrator", password="changeme"):
    url = auth_hub_url + "/oauth2/manager-login"
    response = requests.post(
        url,
        json={"password": password, "username": username},
        headers={"Content-Type": "application/json"},
        verify=False,
        timeout=10
    )
    response.raise_for_status()
    return response.json()["data"]["user_token"]


def register_app(auth_hub_url, user_token, client_name, client_url, redirect_urls):
    response = requests.post(
        auth_hub_url + "/oauth2/applications/register",
        json={
            "client_name": client_name,
            "client_uri": client_url,
            "redirect_uris": redirect_urls,
            "register_callback_uris": [],  # 修复参数名中的空格
            "logout_callback_uris": [],  # 修复参数名中的空格
            "skip_authorization": True,
            "scope": ["email", "phone", "username", "openid", "offline_access"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none"
        },
        headers={"Authorization": user_token, "Content-Type": "application/json"},
        verify=False
    )
    response.raise_for_status()


def get_client_secret(auth_hub_url, user_token, target_client_name):
    response = requests.get(
        auth_hub_url + "/oauth2/applications",
        headers={"Authorization": user_token, "Content-Type": "application/json"},
        timeout=10
    )
    response.raise_for_status()
    apps_data = response.json()

    for app in apps_data["data"]["applications"]:
        client_metadata = app.get("client_metadata") or {}
        if isinstance(client_metadata, str):
            try:
                client_metadata = json.loads(client_metadata)
            except json.JSONDecodeError:
                client_metadata = {}

        candidate_names = [
            client_metadata.get("client_name"),
            app.get("client_name"),
            app.get("client_info", {}).get("client_name")
        ]

        if any(str(name).lower() == target_client_name.lower() for name in candidate_names if name):
            return {
                "client_id": app["client_info"]["client_id"],
                "client_secret": app["client_info"]["client_secret"]
            }

    raise ValueError(f"未找到匹配应用，请检查 client_name 是否准确（尝试使用全小写名称）")


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
    namespace = "euler-copilot"
    service_name = "authhub-web-service"
    auth_hub_url = f"http://127.0.0.1:8000"

    # 生成固定URL
    client_url = f"http://" + args.eulercopilot_domain + ":8080"
    redirect_urls = [f"http://" + args.eulercopilot_domain + ":8080/api/auth/login"]
    client_name = "EulerCopilot"  # 设置固定默认值

    # 认证流程
    try:
        print("\n正在获取用户令牌...")
        user_token = get_user_token(auth_hub_url)
        print("✓ 用户令牌获取成功")

        print(f"\n正在注册应用 [名称: {client_name}]...")
        register_app(auth_hub_url, user_token, client_name, client_url, redirect_urls)
        print("✓ 应用注册成功")

        print(f"\n正在查询客户端凭证 [名称: {client_name}]...")
        client_info = get_client_secret(auth_hub_url, user_token, client_name)

        print("\n✓ 认证信息获取成功：")
        print(f"client_id: {client_info['client_id']}")
        print(f"client_secret: {client_info['client_secret']}")

    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP 错误: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        sys.exit(1)
