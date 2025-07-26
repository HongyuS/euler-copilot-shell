#!/bin/bash
# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色

install_rag() {
  echo -e "${COLOR_INFO}[Info] === 开始初始化配置 euler-copilot-rag ===${COLOR_RESET}"

  # 2. 配置文件处理
  local env_file="../5-resource/env"
  local env_target="/etc/euler-copilot-rag/data_chain/env"
  local service_file="../5-resource/rag.service"
  local service_target="/etc/systemd/system/rag.service"

  # 复制配置文件（验证文件存在性）
  if [[ -f "$env_file" ]]; then
    cp -v "$env_file" "$env_target" || {
      echo -e "${COLOR_ERROR}[Error] 复制 env 文件失败！${COLOR_RESET}"
      return 1
    }
  else
    echo -e "${COLOR_WARNING}[Warning] 未找到 env 文件：$env_file${COLOR_RESET}"
  fi

  if [[ -f "$service_file" ]]; then
    cp -v "$service_file" "$service_target" || {
      echo -e "${COLOR_ERROR}[Error] 复制 service 文件失败！${COLOR_RESET}"
      return 1
    }
  else
    echo -e "${COLOR_WARNING}[Warning] 未找到 service 文件：$service_file${COLOR_RESET}"
  fi

  # 3. 安装图形库依赖（OpenGL）
  if ! dnf install -y mesa-libGL >/dev/null; then
    echo -e "${COLOR_WARNING}[Warning] mesa-libGL 安装失败，可能影响图形功能${COLOR_RESET}"
  fi

  # 5. 启动服务
  echo -e "${COLOR_INFO}[Info] 设置并启动rag服务...${COLOR_RESET}"
  systemctl daemon-reload
  systemctl enable --now rag || {
    echo -e "${COLOR_ERROR}[Error] rag服务启动失败！${COLOR_RESET}"
    systemctl status rag --no-pager
    return 1
  }

  # 6. 验证服务状态
  echo -e "${COLOR_INFO}[Info] 验证rag服务状态...${COLOR_RESET}"
  if systemctl is-active --quiet rag; then
    echo -e "${COLOR_SUCCESS}[Success] rag服务运行正常${COLOR_RESET}"
    systemctl status rag --no-pager | grep -E "Active:|Loaded:"
  else
    echo -e "${COLOR_ERROR}[Error] rag服务未运行！${COLOR_RESET}"
    journalctl -u rag --no-pager -n 20
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] euler-copilot-rag 安装完成${COLOR_RESET}"
  return 0
}
# 网络检测函数
check_network_reachable() {
  local test_url="https://openaipublic.blob.core.windows.net"
  local timeout=3

  echo -e "${COLOR_INFO}[Info] 检测网络连通性 (测试地址: $test_url)...${COLOR_RESET}"

  # 使用curl检测
  if curl --silent --connect-timeout $timeout --head $test_url >/dev/null; then
    echo -e "${COLOR_SUCCESS}[Success] 网络连接正常${COLOR_RESET}"
    return 0
  fi

  # 使用ping二次验证
  if ping -c 1 -W $timeout openaipublic.blob.core.windows.net >/dev/null 2>&1; then
    echo -e "${COLOR_SUCCESS}[Success] 网络连接正常 (ping检测)${COLOR_RESET}"
    return 0
  fi

  echo -e "${COLOR_WARNING}[Warning] 网络不可达${COLOR_RESET}"
  return 1
}
setup_tiktoken_cache() {
  # 预置的本地资源路径
  local local_tiktoken_file="../5-resource/9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
  local cache_dir="/root/.cache/tiktoken"
  local target_file="$cache_dir/9b5ad71b2ce5302211f9c61530b329a4922fc6a4"

  # 1. 检查本地资源文件是否存在
  if [[ ! -f "$local_tiktoken_file" ]]; then
    echo -e "${COLOR_ERROR}[Error] 本地tiktoken资源文件不存在: $local_tiktoken_file${COLOR_RESET}"
    return 1
  fi

  # 2. 创建缓存目录
  echo -e "${COLOR_INFO}[Info] 创建tiktoken缓存目录...${COLOR_RESET}"
  if ! mkdir -p "$cache_dir"; then
    echo -e "${COLOR_ERROR}[Error] 无法创建缓存目录: $cache_dir${COLOR_RESET}"
    return 1
  fi

  # 3. 复制文件到缓存目录
  # 解压tar文件
  dos2unix "$local_tiktoken_file"
  if ! cp -r "$local_tiktoken_file" "$target_file"; then
    echo -e "${COLOR_ERROR}[Error] tiktoken.tar 解压失败${COLOR_RESET}"
    return 1
  fi

  # 4. 设置权限（确保可读）
  chmod 644 "$target_file" || {
    echo -e "${COLOR_WARNING}[Warning] 无法设置文件权限${COLOR_RESET}"
  }

  # 6. 设置环境变量（影响当前进程）
  #特殊处理改token代码
  FILE="/usr/lib/euler-copilot-framework/apps/llm/token.py"
  token_py_file="../5-resource/token.py"
  cp $token_py_file $FILE
  echo -e "${COLOR_SUCCESS}[Success] tiktoken缓存已配置: $target_file${COLOR_RESET}"
}
install_framework() {
  # 安装前检查
  echo -e "${COLOR_INFO}[Info] 开始初始化配置 euler-copilot-framework...${COLOR_RESET}"

  # 2. 检查并创建必要目录
  echo -e "${COLOR_INFO}[Info] 创建数据目录...${COLOR_RESET}"
  mkdir -p /opt/copilot || {
    echo -e "${COLOR_ERROR}[Error] 无法创建数据目录 /opt/copilot${COLOR_RESET}"
    return 1
  }

  # 3. 获取本机IP
  local ip_address
  config_toml_path="../5-resource/config.toml"
  # 提取 domain 的值（假设文件为 config.ini）
  ip_address=$(grep -E "^\s*domain\s*=" $config_toml_path | awk -F"'" '{print $2}')
  echo -e "${COLOR_INFO} [Info] 提取的IP地址: $ip_address"

  # 4. 获取客户端信息
  #针对代理服务器做特殊处理
  unset http_proxy https_proxy

  echo -e "${COLOR_INFO}[Info] 获取客户端凭证...${COLOR_RESET}"
  if ! get_client_info_auto $ip_address; then
    echo -e "${COLOR_ERROR}[Error] 获取客户端凭证失败${COLOR_RESET}"
    return 1
  fi
  # 5. 配置文件处理
  local framework_file="../5-resource/config.toml"
  local framework_target="/etc/euler-copilot-framework/config.toml"
  local framework_service_file="../5-resource/framework.service"
  local framework_service_target="/etc/systemd/system/framework.service"

  # 检查源文件是否存在
  for file in "$framework_file" "$framework_service_file"; do
    if [[ ! -f "$file" ]]; then
      echo -e "${COLOR_ERROR}[Error] 找不到配置文件: $file${COLOR_RESET}"
      return 1
    fi
  done

  # 备份原文件
  echo -e "${COLOR_INFO}[Info] 备份配置文件...${COLOR_RESET}"
  cp -v "$framework_file" "${framework_file}.bak" || {
    echo -e "${COLOR_ERROR}[Error] 无法备份配置文件${COLOR_RESET}"
    return 1
  }

  # 替换配置参数
  echo -e "${COLOR_INFO}[Info] 更新配置文件参数...${COLOR_RESET}"
  sed -i "s/app_id = '.*'/app_id = '$client_id'/" $framework_file
  sed -i "s/app_secret = '.*'/app_secret = '$client_secret'/" $framework_file
  sed -i "/\[login\.settings\]/,/^\[/ s|host = '.*'|host = 'http://${ip_address}:8000'|" "$framework_file"
  sed -i "s|login_api = '.*'|login_api = 'http://${ip_address}:8080/api/auth/login'|" $framework_file
  sed -i "s/domain = '.*'/domain = '$ip_address'/" $framework_file

  # 验证替换结果
  if ! grep -q "app_id = '$client_id'" "$framework_file" || ! grep -q "app_secret = '$client_secret'" "$framework_file"; then
    echo -e "${COLOR_ERROR}[Error] 配置文件验证失败${COLOR_RESET}"
    mv -v "${framework_file}.bak" "$framework_file"
    return 1
  fi

  # 6. 部署配置文件
  echo -e "${COLOR_INFO}[Info] 部署配置文件...${COLOR_RESET}"
  mkdir -p "$(dirname "$framework_target")"
  if ! cp -v "$framework_file" "$framework_target"; then
    echo -e "${COLOR_ERROR}[Error] 无法复制配置文件到 $framework_target${COLOR_RESET}"
    return 1
  fi

  if ! cp -v "$framework_service_file" "$framework_service_target"; then
    echo -e "${COLOR_ERROR}[Error] 无法复制服务文件到 $framework_service_target${COLOR_RESET}"
    return 1
  fi

  # 7. 设置文件权限
  echo -e "${COLOR_INFO}[Info] 设置文件权限...${COLOR_RESET}"
  chmod 640 "$framework_target" || {
    echo -e "${COLOR_WARNING}[Warning] 无法设置配置文件权限${COLOR_RESET}"
  }
  chmod 644 "$framework_service_target" || {
    echo -e "${COLOR_WARNING}[Warning] 无法设置服务文件权限${COLOR_RESET}"
  }

  #特殊处理，如果 openaipublic.blob.core.windows.net 网络不可达
  # 创建缓存目录（通常是 ~/.cache/tiktoken）
  check_network_reachable || {
    setup_tiktoken_cache || echo -e "${COLOR_WARNING}[Warning] 无网络 cl100k_base.tiktoken  文件下载失败,请检查网络${COLOR_RESET}"
  }

  # 8. 启动服务
  echo -e "${COLOR_INFO}[Info] 启动 framework 服务...${COLOR_RESET}"
  systemctl daemon-reload || {
    echo -e "${COLOR_ERROR}[Error] systemd 配置重载失败${COLOR_RESET}"
    return 1
  }

  if ! systemctl enable --now framework; then
    echo -e "${COLOR_ERROR}[Error] 无法启动 framework 服务${COLOR_RESET}"
    systemctl status framework --no-pager
    return 1
  fi

  # 9. 验证服务状态
  echo -e "${COLOR_INFO}[Info] 检查服务状态...${COLOR_RESET}"
  if ! systemctl is-active --quiet framework; then
    echo -e "${COLOR_ERROR}[Error] framework 服务未运行${COLOR_RESET}"
    journalctl -u framework --no-pager -n 20
    return 1
  fi

  # 10. 清理备份文件
  rm -f "${framework_file}.bak"

  echo -e "${COLOR_SUCCESS}[Success] euler-copilot-framework 安装完成${COLOR_RESET}"
  echo -e "${COLOR_INFO}[Info] 服务访问地址: http://${ip_address}:8080${COLOR_RESET}"
  return 0
}

uninstall_pkg() {
  dnf remove -y euler-copilot-rag
  dnf remove -y euler-copilot-framework
}
get_client_info_auto() {

  # 声明全局变量
  declare -g client_id=""
  declare -g client_secret=""

  # 直接调用Python脚本并传递域名参数
  python3 "../4-other-script/get_client_id_and_secret.py" $1 >client_info.tmp 2>&1

  # 检查Python脚本执行结果
  if [ $? -ne 0 ]; then
    echo -e "${RED}错误：Python脚本执行失败${NC}"
    cat client_info.tmp
    rm -f client_info.tmp
    return 1
  fi

  # 提取凭证信息
  client_id=$(grep "client_id: " client_info.tmp | awk '{print $2}')
  client_secret=$(grep "client_secret: " client_info.tmp | awk '{print $2}')
  rm -f client_info.tmp

  # 验证结果
  if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
    echo -e "${RED}错误：无法获取有效的客户端凭证${NC}" >&2
    return 1
  fi
}
# 主函数
main() {
  # 获取脚本所在的绝对路径
  SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  cd "$SCRIPT_DIR" || exit 1
  install_rag || return 1
  # 切换到脚本所在目录
  install_framework || return 1
  echo -e "${COLOR_SUCCESS}[Success] openEuler intelligence 安装部署完成${COLOR_RESET}"
}

main "$@"
