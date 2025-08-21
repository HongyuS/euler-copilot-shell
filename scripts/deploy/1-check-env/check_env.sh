#!/bin/bash
# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色
INSTALL_MODE_FILE="/etc/euler_Intelligence_install_mode"
# 全局模式标记
OFFLINE_MODE=false

is_x86_architecture() {
  # 获取系统架构信息（使用 uname -m 或 arch 命令）
  local arch
  arch=$(uname -m) # 多数系统支持，返回架构名称（如 x86_64、i686、aarch64 等）
  # 备选：arch 命令，输出与 uname -m 类似
  # arch=$(arch)

  # x86 架构的常见标识：i386、i686（32位），x86_64（64位）
  if [[ $arch == i386 || $arch == i686 || $arch == x86_64 ]]; then
    return 0 # 是 x86 架构，返回 0（成功）
  else
    return 1 # 非 x86 架构，返回 1（失败）
  fi
}
# 安装wget工具
install_wget() {
  echo -e "${COLOR_INFO}[INFO] 正在尝试安装wget...${COLOR_RESET}"

  # 检查包管理器并安装
  if command -v apt-get &>/dev/null; then
    sudo apt-get update && sudo apt-get install -y wget
  elif command -v yum &>/dev/null; then
    sudo yum install -y wget
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y wget
  elif command -v zypper &>/dev/null; then
    sudo zypper install -y wget
  else
    echo -e "${COLOR_FAILURE}[ERROR] 无法确定包管理器，请手动安装wget${COLOR_RESET}"
    return 1
  fi

  # 验证安装是否成功
  if command -v wget &>/dev/null; then
    echo -e "${COLOR_SUCCESS}[SUCCESS] wget安装成功${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_FAILURE}[ERROR] wget安装失败${COLOR_RESET}"
    return 1
  fi
}

# 基础URL列表（无论RAG是否启用都需要检测）
base_urls_x86=(
  "https://downloads.mongodb.com/compass/mongodb-mongosh-2.5.2.x86_64.rpm"
  "https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/x86_64/RPMS/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
)

base_urls_arm=(
  "https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/aarch64/RPMS/mongodb-org-server-7.0.21-1.el9.aarch64.rpm"
  "https://downloads.mongodb.com/compass/mongodb-mongosh-2.5.2.aarch64.rpm"
)

# RAG专用URL列表（仅当RAG启用时检测）
rag_urls=(
  "https://bgithub.xyz/pgvector/pgvector.git"
  "https://bgithub.xyz/amutu/zhparser.git"
)

# 检测URL可达性的函数
check_url_accessibility() {
  # 首先检查wget是否安装
  if ! command -v wget &>/dev/null; then
    echo -e "${COLOR_WARNING}[WARN] wget未安装，尝试自动安装...${COLOR_RESET}"
    if ! install_wget; then
      echo -e "${COLOR_ERROR}[ERROR] URL检测中止：wget安装失败${COLOR_RESET}"
      return 1
    fi
  fi

  # 读取RAG安装状态（依赖之前的read_install_mode函数设置RAG_INSTALL变量）
  if ! read_install_mode; then
    echo -e "${COLOR_WARNING}[WARN] 无法读取安装模式，默认按RAG未启用检测${COLOR_RESET}"
    local RAG_INSTALL="n"
  fi

  # 根据架构和RAG状态组合最终需要检测的URL列表
  local detect_urls=()
  if is_x86_architecture; then
    detect_urls+=("${base_urls_x86[@]}")
  else
    detect_urls+=("${base_urls_arm[@]}")
  fi

  # 如果启用RAG，添加RAG专用URL
  if [ "$RAG_INSTALL" = "y" ]; then
    detect_urls+=("${rag_urls[@]}")
    echo -e "${COLOR_INFO} RAG组件已启用，将检测所有必要URL（共${#detect_urls[@]}个）${COLOR_RESET}"
  else
    echo -e "${COLOR_INFO} RAG组件未启用，仅检测基础URL（共${#detect_urls[@]}个）${COLOR_RESET}"
  fi

  local all_success=true
  local timeout_seconds=15  # 设置超时时间
  local temp_file=$(mktemp) # 创建临时文件
  local failed_urls=()      # 存储失败的URL

  echo -e "${COLOR_INFO}开始检测URL可达性...${COLOR_RESET}"
  echo -e "${COLOR_INFO}超时时间: ${timeout_seconds}秒${COLOR_RESET}"

  for url in "${detect_urls[@]}"; do
    # 格式化输出，保持对齐
    printf "%-80s" "检测: $url"

    # 使用timeout命令控制超时，--spider只检查URL是否存在不下载
    if timeout $timeout_seconds wget --spider --timeout=$timeout_seconds --tries=1 --no-check-certificate "$url" >"$temp_file" 2>&1; then
      echo -e "${COLOR_SUCCESS} [OK]${COLOR_RESET}"
    else
      echo -e "${COLOR_ERROR} [FAIL]${COLOR_RESET}"

      # 提取错误原因
      if grep -q "timed out" "$temp_file"; then
        error_msg="操作超时 (${timeout_seconds}秒)"
      else
        error_msg=$(grep -i "error\|failed\|timeout" "$temp_file" | head -1 | cut -d' ' -f4- | sed 's/[[:cntrl:]]//g')
      fi

      echo -e "  ${COLOR_WARNING}原因: ${error_msg:-未知错误}${COLOR_RESET}"
      all_success=false
      failed_urls+=("$url")
    fi
  done

  # 清理临时文件
  rm -rf "$temp_file"

  # 结果汇总
  echo -e "\n${COLOR_INFO}====== 检测结果 ======${COLOR_RESET}"
  if $all_success; then
    echo -e "${COLOR_SUCCESS}[Success] 所有必要URL均可访问${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] ${#failed_urls[@]}个URL不可访问:${COLOR_RESET}"
    printf "  - %s\n" "${failed_urls[@]}"
    echo -e "${COLOR_INFO}建议检查:${COLOR_RESET}"
    echo -e "  1. 网络连接是否正常"
    echo -e "  2. 是否需要配置代理(export http_proxy=...)"
    return 1
  fi
}

# 全局变量：默认端口列表（未启用Web时）
PORTS=(8002)

# 读取安装模式并设置端口列表的函数
init_ports_based_on_web() {
  if ! read_install_mode; then
    echo -e "${COLOR_WARNING}[Warning] 无法读取安装模式，使用默认端口配置${COLOR_RESET}"
    return 1
  fi

  # 根据Web组件状态更新全局PORTS变量
  if [ "$WEB_INSTALL" = "y" ]; then
    PORTS=(8080 9888 8000 11120)
    echo -e "${COLOR_INFO} Web组件已启用，端口列表: ${PORTS[*]}${COLOR_RESET}"
  else
    PORTS=(8002)
    echo -e "${COLOR_INFO} Web组件未启用，端口列表: ${PORTS[*]}${COLOR_RESET}"
  fi
}

function check_user {
  if [[ $(id -u) -ne 0 ]]; then
    echo -e "${COLOR_ERROR}[Error] 请以root权限运行该脚本！${COLOR_RESET}"
    return 1
  fi
  return 0
}

function check_version {
  local current_version_id="$1"
  local supported_versions=("${@:2}")
  local sp="$3"
  echo -e "${COLOR_INFO}[Info] 当前操作系统版本为：$current_version_id LTS-$sp${COLOR_RESET}"
  for version_id in "${supported_versions[@]}"; do
    if [[ "$current_version_id" == "$version_id" ]]; then
      if [[ "$sp" == "SP2" ]]; then
        echo -e "${COLOR_SUCCESS}[Success] 操作系统满足兼容性要求${COLOR_RESET}"
        return 0
      fi
    fi
  done

  echo -e "${COLOR_ERROR}[Error] 操作系统不满足兼容性要求，脚本将退出${COLOR_RESET}"
  return 1
}

function check_os_version {
  local id=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
  local version=$(grep -E "^VERSION_ID=" /etc/os-release | cut -d '"' -f 2)
  local sp=$(grep -E "^VERSION=" /etc/os-release | grep -oP 'SP\d+')

  echo -e "${COLOR_INFO}[Info] 当前发行版为：$id${COLOR_RESET}"

  case $id in
  "openEuler")
    local supported_versions=("24.03")
    check_version "$version" "${supported_versions[@]}" "$sp"
    ;;
  *)
    echo -e "${COLOR_ERROR}[Error] 发行版不受支持，脚本将退出${COLOR_RESET}"
    return 1
    ;;
  esac
  return $?
}

function check_hostname {
  local current_hostname=$(cat /etc/hostname)
  if [[ -z "$current_hostname" ]]; then
    echo -e "${COLOR_WARNING}[Warning] 未设置主机名，自动设置为localhost${COLOR_RESET}"
    set_hostname "localhost"
    return $?
  else
    echo -e "${COLOR_INFO}[Info] 当前主机名为：$current_hostname${COLOR_RESET}"
    echo -e "${COLOR_SUCCESS}[Success] 主机名已设置${COLOR_RESET}"
    return 0
  fi
}

function set_hostname {
  if ! command -v hostnamectl &>/dev/null; then
    echo -e "$1" >/etc/hostname
    echo -e "${COLOR_SUCCESS}[Success] 手动设置主机名成功${COLOR_RESET}"
    return 0
  fi

  if hostnamectl set-hostname "$1"; then
    echo -e "${COLOR_SUCCESS}[Success] 主机名设置成功${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] 主机名设置失败${COLOR_RESET}"
    return 1
  fi
}

# 检查单个软件包是否可用
check_package() {
  local pkg=$1
  if dnf list "$pkg" &>/dev/null; then
    echo -e "${COLOR_INFO}[Info] $(printf '%-30s' "$pkg") \t(可用)${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] $(printf '%-30s' "$pkg") \t(不可用)${COLOR_RESET}"
    return 1
  fi
}
# 需要检查的软件包列表
PACKAGES=(
  "euler-copilot-web"
  "euler-copilot-witchaind-web"
  "authHub"
  "authhub-web"
  "euler-copilot-rag"
  "euler-copilot-framework"
  "nginx"
  "redis"
  "mysql"
  "mysql-server"
  "java-17-openjdk"
  "postgresql-server"
  "postgresql-server-devel"
  "postgresql"
  "libpq-devel"
  "git"
  "make"
  "gcc"
  "gcc-c++"
  "clang"
  "llvm"
  "tar"
  "python3-pip"
)
all_available=true
# 检查所有软件包
check_all_packages() {
  local PACKAGES=("$@")

  local timeout_seconds=30
  local start_time=$(date +%s)

  echo -e "${COLOR_INFO}--------------------------------${COLOR_RESET}"

  for pkg in "${PACKAGES[@]}"; do
    # 检查是否超时
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))

    if [ $elapsed -ge $timeout_seconds ]; then
      echo -e "${COLOR_ERROR}[Error] 检查操作已超时(${timeout_seconds}s)${COLOR_RESET}"
      echo -e "${COLOR_INFO}--------------------------------${COLOR_RESET}"
      return 2
    fi
    if ! check_package "$pkg"; then
      all_available=false
    fi
    sleep 0.1 # 避免请求过快
  done

}
check_web_pkg() {
  local pkgs=(
    "nginx"
    "redis"
    "mysql"
    "mysql-server"
    "authHub"
    "authhub-web"
    "euler-copilot-web"
    "euler-copilot-witchaind-web"
  )
  if ! check_all_packages "${pkgs[@]}"; then
    return 1
  fi
}
check_framework_pkg() {
  local pkgs=(
    "euler-copilot-framework"
    "git"
    "make"
    "gcc"
    "gcc-c++"
    "tar"
    "python3-pip"
  )
  if ! check_all_packages "${pkgs[@]}"; then
    return 1
  fi
}
check_rag_pkg() {
  local pkgs=(
    "euler-copilot-rag"
    "clang"
    "llvm"
    "java-17-openjdk"
    "postgresql"
    "postgresql-server"
    "postgresql-server-devel"
    "libpq-devel"
  )
  if ! check_all_packages "${pkgs[@]}"; then
    return 1
  fi
}
function check_network {
  echo -e "${COLOR_INFO}[Info] 检查网络连接...${COLOR_RESET}"

  # 使用TCP检查代替curl
  if timeout 5 bash -c 'cat < /dev/null > /dev/tcp/www.baidu.com/80' 2>/dev/null; then
    echo -e "${COLOR_SUCCESS}[Success] 网络连接正常${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] 无法访问外部网络，请检查网络环境 ${COLOR_RESET}"
    return 1
  fi
}

function check_dns {
  echo -e "${COLOR_INFO}[Info] 检查DNS设置${COLOR_RESET}"
  if grep -q "^nameserver" /etc/resolv.conf; then
    echo -e "${COLOR_SUCCESS}[Success] DNS已配置${COLOR_RESET}"
    return 0
  fi

  if $OFFLINE_MODE; then
    echo -e "${COLOR_WARNING}[Warning] 离线模式：请手动配置内部DNS服务器${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] DNS未配置，自动设置为8.8.8.8${COLOR_RESET}"
    set_dns "8.8.8.8"
    return $?
  fi
}

function check_ram {
  local RAM_THRESHOLD=1024
  local current_mem=$(free -m | awk '/Mem/{print $2}')

  echo -e "${COLOR_INFO}[Info] 当前内存：$current_mem MB${COLOR_RESET}"
  if ((current_mem < RAM_THRESHOLD)); then
    echo -e "${COLOR_ERROR}[Error] 内存不足 ${RAM_THRESHOLD} MB${COLOR_RESET}"
    return 1
  fi
  echo -e "${COLOR_SUCCESS}[Success] 内存满足要求${COLOR_RESET}"
  return 0
}

check_disk_space() {
  local DIR="$1"
  local THRESHOLD="$2"

  local USAGE=$(df --output=pcent "$DIR" | tail -n 1 | sed 's/%//g' | tr -d ' ')

  if [ "$USAGE" -ge "$THRESHOLD" ]; then
    echo -e "${COLOR_WARNING}[Warning] $DIR 的磁盘使用率已达到 ${USAGE}%，超过阈值 ${THRESHOLD}%${COLOR_RESET}"
    return 1
  else
    echo -e "${COLOR_INFO}[Info] $DIR 的磁盘使用率为 ${USAGE}%，低于阈值 ${THRESHOLD}%${COLOR_RESET}"
    return 0
  fi
}

function check_selinux {
  sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config
  echo -e "${COLOR_SUCCESS}[Success] SELinux配置已禁用${COLOR_RESET}"
  setenforce 0 &>/dev/null
  echo -e "${COLOR_SUCCESS}[Success] SELinux已临时禁用${COLOR_RESET}"
  return 0
}

function check_firewall {
  systemctl disable --now firewalld &>/dev/null
  echo -e "${COLOR_SUCCESS}[Success] 防火墙已关闭并禁用${COLOR_RESET}"
  return 0
}

# 检查端口是否被占用
check_ports() {
  local occupied=()
  echo -e "${COLOR_INFO}正在检查端口占用情况...${COLOR_RESET}"
  init_ports_based_on_web

  for port in "${PORTS[@]}"; do
    if ss -tuln | grep -q ":${port} "; then
      occupied+=("$port")
      echo -e "${COLOR_WARNING}[Warning] 端口 $port 已被占用${COLOR_RESET}"
    else
      echo -e "${COLOR_INFO}[Info] 端口 $port 可用${COLOR_RESET}"
    fi
  done

  if [ ${#occupied[@]} -gt 0 ]; then
    echo -e "${COLOR_ERROR}[Error]错误：以下端口已被占用: ${occupied[*]}${COLOR_RESET}"
    echo -e "${COLOR_ERROR}[Error]请先释放这些端口再运行脚本${COLOR_RESET}"
    return 1
  fi
  echo -e "${COLOR_SUCCESS}[Success]检查端口占用情况成功，端口未占用${COLOR_RESET}"
  return 0
}

# 配置防火墙
setup_firewall() {

  echo -e "${COLOR_INFO}[Info]配置防火墙...${COLOR_RESET}"

  if ! systemctl is-active --quiet firewalld; then
    echo -e "${COLOR_SUCCESS}[Success]防火墙未运行${COLOR_RESET}"
    return 0
  fi
  echo -e "${COLOR_INFO}[Info]防火墙已运行，开放端口${COLOR_RESET}"
  for port in "${PORTS[@]}"; do
    echo -e "${COLOR_INFO}[Info]开放端口 $port/tcp...${COLOR_RESET}"
    firewall-cmd --permanent --add-port=${port}/tcp || {
      echo -e "${COLOR_ERROR}[Error]开放端口 $port 失败！${COLOR_RESET}"
      return 1
    }
  done

  echo -e "${COLOR_INFO}[Info]重新加载防火墙规则...${COLOR_RESET}"
  firewall-cmd --reload || {
    echo -e "${COLOR_ERROR}[Error]防火墙规则重载失败！${COLOR_RESET}"
    return 1
  }
  echo -e "${COLOR_SUCCESS}[Success]重新加载防火墙规则成功${COLOR_RESET}"
  return 0
}
# 读取安装模式的方法
read_install_mode() {
  # 检查文件是否存在
  if [ ! -f "$INSTALL_MODE_FILE" ]; then
    echo "web_install=n" >"$INSTALL_MODE_FILE"
    echo "rag_install=n" >>"$INSTALL_MODE_FILE"
  fi

  # 从文件读取配置（格式：key=value）
  local web_install=$(grep "web_install=" "$INSTALL_MODE_FILE" | cut -d'=' -f2)
  local rag_install=$(grep "rag_install=" "$INSTALL_MODE_FILE" | cut -d'=' -f2)

  # 验证读取结果
  if [ -z "$web_install" ] || [ -z "$rag_install" ]; then
    echo -e "${COLOR_ERROR}[Error] 安装模式文件格式错误${COLOR_RESET}"
    return 1
  fi
  # 将结果存入全局变量（供其他函数使用）
  WEB_INSTALL=$web_install
  RAG_INSTALL=$rag_install
  return 0
}
# 示例：根据安装模式执行对应操作（可根据实际需求扩展）
install_components() {
  # 读取安装模式
  read_install_mode || return 1
  echo -e "${COLOR_INFO}[Info] 检查软件包是否可用${COLOR_RESET}"
  if [ "$WEB_INSTALL" = "y" ]; then
    check_web_pkg
  fi

  if [ "$RAG_INSTALL" = "y" ]; then
    # 此处添加RAG安装命令，示例：
    check_rag_pkg
  fi

  check_framework_pkg
  echo -e "--------------------------------"

  if $all_available; then
    echo -e "${COLOR_SUCCESS}[Success] 所有软件包都可用${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] 部分软件包不可用${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 提示：可以尝试以下命令更新仓库缓存：${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] sudo dnf clean all && sudo dnf makecache${COLOR_RESET}"
    return 1
  fi
}

function main {
  check_user || return 1
  check_os_version || return 1
  check_hostname || return 1

  # 网络检查与模式判断
  install_components || return 1

  check_dns || return 1
  check_ram || return 1
  check_disk_space "/" 70

  if [ $? -eq 1 ]; then
    echo -e "${COLOR_WARNING}[Warning] 需要清理磁盘空间！${COLOR_RESET}"
  else
    echo -e "${COLOR_SUCCESS}[Success] 磁盘空间正常${COLOR_RESET}"
  fi

  check_selinux || return 1
  check_ports || return 1
  setup_firewall || return 1
  check_url_accessibility || return 1

  # 最终部署提示
  echo -e "\n${COLOR_SUCCESS}#####################################"
  echo -e "#   环境检查完成，准备在线部署     #"
  echo -e "#####################################${COLOR_RESET}"
  return 0
}

main
