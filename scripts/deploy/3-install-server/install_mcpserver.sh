#!/bin/bash
set -eo pipefail  # 开启严格模式，命令失败时立即退出

# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色

# 日志输出函数
info() {
  echo -e "${COLOR_INFO}[Info] $1${COLOR_RESET}"
}

success() {
  echo -e "${COLOR_SUCCESS}[Success] $1${COLOR_RESET}"
}

warn() {
  echo -e "${COLOR_WARNING}[Warn] $1${COLOR_RESET}"
}

error() {
  echo -e "${COLOR_ERROR}[Error] $1${COLOR_RESET}" >&2  # 错误信息输出到 stderr
}

# 检查命令是否存在
check_command() {
  local cmd=$1
  if ! command -v "$cmd" &>/dev/null; then
    error "命令 '$cmd' 不存在，请先安装"
    return 1
  fi
  return 0
}

# 安装并启动服务的通用函数
install_and_start() {
  local package_name=$1
  local service_name=${2:-$package_name}  # 服务名默认与包名相同
  local description=$3

  info "开始${description}：${package_name}"

  # 安装包
  info "安装 ${package_name} 包..."
  if dnf install -y "$package_name"; then
    success "${package_name} 安装成功"
  else
    error "${package_name} 安装失败"
    return 1
  fi

  # 启用并启动服务
  info "启动 ${service_name} 服务..."
  if systemctl enable --now "$service_name"; then
    success "${service_name} 服务启动并设置为开机自启成功"
  else
    error "${service_name} 服务启动失败"
    return 1
  fi

  # 检查服务状态
  info "检查 ${service_name} 服务状态..."
  if systemctl is-active --quiet "$service_name"; then
    success "${service_name} 服务当前状态：运行中"
  else
    warn "${service_name} 服务当前状态：未运行（可能启动需要时间，建议稍后再次检查）"
  fi

  return 0
}

main() {
  info "===== 开始安装服务 ====="

  # 前置检查：确认 dnf 和 systemctl 可用
  info "检查系统工具..."
  if ! check_command "dnf" || ! check_command "systemctl"; then
    error "缺少必要的系统工具，无法继续"
  fi

  # 安装 systrace 相关服务
  if ! install_and_start "systrace" "" "安装基础组件"; then
    error "systrace 安装失败，请手动安装，终止流程"
  fi

  if ! install_and_start "systrace-failslow" "" "安装故障检测组件"; then
    error "systrace-failslow 安装失败，请手动安装，终止流程"
  fi

  if ! install_and_start "systrace-mcpserver" "" "安装systrace管理服务"; then
    error "systrace-mcpserver 安装失败，请手动安装，终止流程"
  fi

  # 安装 perf 服务
  if ! install_and_start "perf-mcpserver" "" "安装性能分析服务"; then
    error "perf-mcpserver 安装失败，请手动安装，终止流程"
  fi

  # 安装 cve 服务
  if ! install_and_start "cve-mcpserver" "" "安装漏洞检测服务"; then
    error "cve-mcpserver 安装失败，请手动安装，终止流程"
  fi

  # 等待服务稳定
  info "所有服务安装完成，等待5秒确认服务稳定..."
  sleep 5

  # 汇总状态检查
  info "===== 服务安装状态汇总 ====="
  local services=("systrace-mcpserver" "perf-mcpserver" "cve-mcpserver")
  for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
      success "${service}：运行中"
    else
      error "${service}：未运行（请检查日志：journalctl -u ${service} -xe）"
    fi
  done

  success "===== 所有服务安装流程已完成 ====="
  exit 0
}

# 执行主函数
main "$@"