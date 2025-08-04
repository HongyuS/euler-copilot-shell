#!/bin/bash
# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色

init_mcp_config(){
  local mcp_config_path="../5-resource/mcp_config"
  local target_path="/opt/copilot/semantics/mcp/template"

  echo -e "${COLOR_INFO}[Info] 开始初始化MCP配置文件...${COLOR_RESET}"

  # 检查源目录是否存在
  if [ ! -d "$mcp_config_path" ]; then
    echo -e "${COLOR_ERROR}[Error] 源目录不存在: $mcp_config_path${COLOR_RESET}"
    return 1
  fi

  # 创建目标目录（如果不存在）
  if [ ! -d "$target_path" ]; then
    echo -e "${COLOR_INFO}[Info] 目标目录不存在，创建: $target_path${COLOR_RESET}"
    mkdir -p "$target_path" || {
      echo -e "${COLOR_ERROR}[Error] 无法创建目标目录: $target_path${COLOR_RESET}"
      return 1
    }
  fi

  # 递归复制所有文件和子目录（保留权限和属性）
  echo -e "${COLOR_INFO}[Info] 正在复制配置文件到目标目录...${COLOR_RESET}"
  cp -R -p "$mcp_config_path"/* "$target_path/" || {
    echo -e "${COLOR_ERROR}[Error] 配置文件复制失败${COLOR_RESET}"
    return 1
  }

  echo -e "${COLOR_SUCCESS}[Success] MCP配置文件初始化完成${COLOR_RESET}"
  return 0
}
main(){
  # 获取脚本所在的绝对路径
  SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  if [ -z "$SCRIPT_DIR" ]; then
    echo -e "${COLOR_ERROR}[Error] 无法获取脚本所在目录路径${COLOR_RESET}"
    return 1
  fi

  # 切换到脚本所在目录
  echo -e "${COLOR_INFO}[Info] 切换到脚本目录: $SCRIPT_DIR${COLOR_RESET}"
  cd "$SCRIPT_DIR" || {
    echo -e "${COLOR_ERROR}[Error] 无法切换到脚本目录: $SCRIPT_DIR${COLOR_RESET}"
    return 1
  }

  # 执行MCP配置初始化
  echo -e "${COLOR_INFO}[Info] 开始执行MCP配置初始化...${COLOR_RESET}"
  init_mcp_config
  local init_result=$?
  if [ $init_result -ne 0 ]; then
    echo -e "${COLOR_ERROR}[Error] MCP配置初始化失败，终止执行${COLOR_RESET}"
    return $init_result
  fi

  # 重启framework服务
  echo -e "${COLOR_INFO}[Info] 开始重启framework服务...${COLOR_RESET}"
  if ! systemctl restart framework; then
    echo -e "${COLOR_ERROR}[Error] framework服务重启失败${COLOR_RESET}"
    return 1
  fi

  # 检查服务状态
  echo -e "${COLOR_INFO}[Info] 验证framework服务状态...${COLOR_RESET}"
  sleep 5
  if systemctl is-active --quiet framework; then
    echo -e "${COLOR_SUCCESS}[Success] framework服务重启成功并正常运行${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] framework服务重启后未正常运行${COLOR_RESET}"
    return 1
  fi
  sleep 10
  python3 "../4-other-script/init_agent.py"  > client_info.tmp 2>&1
}

main
