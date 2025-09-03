#!/bin/bash
# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色
INSTALL_MODE_FILE="/etc/euler_Intelligence_install_mode"
# 全局变量
declare -a installed_pkgs=()
install_success=true
missing_pkgs=()
LOCAL_REPO_DIR="/var/cache/rpms"
LOCAL_REPO_FILE="/etc/yum.repos.d/local.repo"
# 初始化本地仓库
init_local_repo() {
  [ "$(id -u)" -ne 0 ] && {
    echo "需要root权限"
    return 1
  }

  # 检查仓库目录和repo文件是否存在
  if [ ! -d "$LOCAL_REPO_DIR" ] 2>/dev/null; then
    return 0
  fi

  # 配置本地仓库
  cat >"$LOCAL_REPO_FILE" <<EOF
[local-rpms]
name=Local RPM Repository
baseurl=file://$LOCAL_REPO_DIR
enabled=1
gpgcheck=0
priority=1  # 本地仓库优先
metadata_expire=never
EOF

  # 重建元数据（如果已有rpm文件）
  if ls "$LOCAL_REPO_DIR"/*.rpm &>/dev/null; then
    if ! command -v createrepo &>/dev/null; then
      dnf install -y createrepo
    fi
    createrepo --update "$LOCAL_REPO_DIR"
  fi

  dnf clean all
  dnf makecache

}
# 安装MinIO
install_minio() {
  echo -e "${COLOR_INFO}[Info] 开始安装MinIO...${COLOR_RESET}"
  local minio_dir="/opt/minio"
  if ! mkdir -p "$minio_dir"; then
    echo -e "${COLOR_ERROR}[Error] 创建目录失败: $minio_dir${COLOR_RESET}"
    return 1
  fi
  ! is_x86_architecture || {
  local minio_url="https://dl.min.io/server/minio/release/linux-amd64/archive/minio-20250524170830.0.0-1.x86_64.rpm"
  local minio_src="../5-resource/rpm/minio-20250524170830.0.0-1.x86_64.rpm"
  local minio_file="/opt/minio/minio-20250524170830.0.0-1.x86_64.rpm"

  if [ -f "$minio_src" ]; then
    cp -r "$minio_src" "$minio_file"
    sleep 1
  fi
  if [ ! -f "$minio_file" ]; then
    echo -e "${COLOR_INFO}[Info] 正在下载MinIO软件包...${COLOR_RESET}"
    if ! wget "$minio_url" --no-check-certificate -O "$minio_file"; then
      echo -e "${COLOR_ERROR}[Error] MinIO下载失败${COLOR_RESET}"
      return 1
    fi
  fi

  dnf install -y $minio_file || {
    echo -e "${COLOR_ERROR}[Error] MinIO安装失败${COLOR_RESET}"
    return 1
  }
  echo -e "${COLOR_SUCCESS}[Success] MinIO安装成功...${COLOR_RESET}"
  return 0
  }
  echo -e "${COLOR_INFO}[Info] 下载MinIO二进制文件（aarch64）...${COLOR_RESET}"
  local minio_url="https://dl.min.io/server/minio/release/linux-arm64/minio"
  local temp_dir=$minio_dir
  local minio_path="../5-resource/rpm/minio"

  # 检查文件是否已存在
  if [ -f "$minio_path" ]; then
    cp -r $minio_path $temp_dir
    echo -e "${COLOR_INFO}[Info] MinIO二进制文件已存在，跳过下载${COLOR_RESET}"
  else
    if ! wget -q --show-progress "$minio_url" -O "$temp_dir/minio" --no-check-certificate; then
      echo -e "${COLOR_ERROR}[Error] 下载MinIO失败，请检查网络连接${COLOR_RESET}"
      rm -rf "$temp_dir"
      return 1
    fi
  fi
}
# 智能安装函数
smart_install() {
  local pkg=$1
  local retry=3
  local LOCAL_REPO_DIR="/var/cache/rpms"
  local use_local=false

  # 检查本地仓库目录是否存在
  if [ -d "$LOCAL_REPO_DIR" ]; then
    use_local=true
  fi

  echo -e "${COLOR_INFO}[Info] 正在安装 $pkg ...${COLOR_RESET}"

  while [ $retry -gt 0 ]; do
    # 本地安装模式（仅在本地仓库可用时尝试）
    if [[ "$use_local" == true ]]; then
      # 检查本地是否存在包（支持模糊匹配）
      local local_pkg=$(find "$LOCAL_REPO_DIR" -name "${pkg}-*.rpm" | head -1)

      if [[ -n "$local_pkg" ]]; then
        if dnf --disablerepo='*' --enablerepo=local-rpms install -y "$pkg"; then
          installed_pkgs+=("$pkg")
          return 0
        fi
      fi
    fi

    # 在线安装模式（本地仓库不可用或本地安装失败）
    if dnf install -y "$pkg"; then
      installed_pkgs+=("$pkg")
      return 0
    fi

    ((retry--))
    sleep 1
  done

  echo "${COLOR_ERROR}[Error] 错误: $pkg 安装失败！${COLOR_RESET}"
  missing_pkgs+=("$pkg")
  install_success=false

  return 1
}
#&>/dev/null
install_and_verify() {
  # 接收传入的包列表参数
  local pkgs=("$@")
  # 检查并安装每个包
  for pkg in "${pkgs[@]}"; do
    smart_install $pkg
    sleep 1
  done
  # 检查安装结果
  if $install_success; then
    echo -e "${COLOR_SUCCESS}[Success] dnf 包安装完成！${COLOR_RESET}"
  else
    echo -e "${COLOR_ERROR}[Error] 以下包安装失败: ${missing_pkgs[*]}${COLOR_RESET}"
    return 1
  fi
}
# 安装pgvector服务
install_pgvector() {
  local pgvector_dir="/opt/pgvector"
  local zhparser_url="https://bgithub.xyz/pgvector/pgvector.git"
  local pgvector_installed_marker="/usr/share/pgsql/extension/vector.control" # pgvector安装后的标志文件
  echo -e "${COLOR_INFO}[Info] 开始安装pgvector...${COLOR_RESET}"
  if [ -f "$pgvector_installed_marker" ]; then
    echo -e "${COLOR_INFO}[Info] pgvector已安装，跳过安装过程${COLOR_RESET}"
    return 0
  fi
  # 1. 临时禁用SSL验证
  echo -e "${COLOR_INFO} 临时禁用Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify false

  # 2. 克隆仓库
  echo -e "${COLOR_INFO} 正在克隆zhparser仓库...${COLOR_RESET}"
  if [ -d "$pgvector_dir" ]; then
    echo -e "${COLOR_INFO} 目标目录已存在，尝试更新代码...${COLOR_RESET}"
    cd "$pgvector_dir" || {
      echo -e "${COLOR_ERROR}[Error] 无法进入目录: $pgvector_dir${COLOR_RESET}"
      return 1
    }
    git pull origin master || {
      echo -e "${COLOR_ERROR}[Error] 代码更新失败${COLOR_RESET}"
      return 1
    }
  else
    git clone --branch v0.8.0 "$zhparser_url" "$pgvector_dir" || {
      echo -e "${COLOR_ERROR}[Error] 克隆仓库失败${COLOR_RESET}"
      return 1
    }
    cd "$pgvector_dir" || {
      echo -e "${COLOR_ERROR}[Error] 无法进入目录: $pgvector_dir${COLOR_RESET}"
      return 1
    }
  fi

  # 3. 恢复SSL验证
  echo -e "${COLOR_INFO} 恢复Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify true

  # 4. 进入解压目录编译安装
  echo -e "${COLOR_INFO} 正在编译安装pgvector...${COLOR_RESET}"
  cd "$pgvector_dir" || {
    echo -e "${COLOR_ERROR}[Error] 无法进入目录: $pgvector_dir${COLOR_RESET}"
    return 1
  }

  if ! make >/dev/null; then
    echo -e "${COLOR_ERROR}[Error] make编译失败${COLOR_RESET}"
    return 1
  fi
  if ! make install >/dev/null; then
    echo -e "${COLOR_ERROR}[Error] make install安装失败${COLOR_RESET}"
    return 1
  fi
  echo -e "${COLOR_SUCCESS}[Success] pgvector安装成功${COLOR_RESET}"
  return 0
}
# 安装scws服务
install_scws() {
  local scws_url="http://www.xunsearch.com/scws/down/scws-1.2.3.tar.bz2"
  local scws_tar="/opt/scws-1.2.3.tar.bz2"
  local scws_dir="/opt/scws"
  local scws_installed_marker="/usr/local/lib/libscws.la" # SCWS安装后的标志性文件

  echo -e "${COLOR_INFO}[Info] 开始安装SCWS分词库...${COLOR_RESET}"
  # 1. 检查是否已安装
  if [ -f "$scws_installed_marker" ]; then
    echo -e "${COLOR_INFO}[Info] SCWS已安装，跳过安装过程${COLOR_RESET}"
    return 0
  fi
  # 2. 下载SCWS安装包
  echo -e "${COLOR_INFO} 正在下载SCWS...${COLOR_RESET}"
  if ! wget "$scws_url" --no-check-certificate -O "$scws_tar"; then
    echo -e "${COLOR_ERROR}[Error] SCWS下载失败${COLOR_RESET}"
    return 1
  fi

  # 3. 创建目标目录
  if ! mkdir -p "$scws_dir"; then
    echo -e "${COLOR_ERROR}[Error] 创建目录失败: $scws_dir${COLOR_RESET}"
    return 1
  fi

  # 4. 解压安装包
  echo -e "${COLOR_INFO} 正在解压SCWS...${COLOR_RESET}"
  if ! tar -xjf "$scws_tar" -C "$scws_dir" --strip-components=1; then
    echo -e "${COLOR_ERROR}[Error] 解压SCWS失败${COLOR_RESET}"
    return 1
  fi

  # 5. 编译安装
  echo -e "${COLOR_INFO} 正在编译安装SCWS...${COLOR_RESET}"
  cd "$scws_dir" || {
    echo -e "${COLOR_ERROR}[Error] 无法进入目录: $scws_dir${COLOR_RESET}"
    return 1
  }

  if ! ./configure >/dev/null; then
    echo -e "${COLOR_ERROR}[Error] configure配置失败${COLOR_RESET}"
    return 1
  fi

  if ! make >/dev/null; then
    echo -e "${COLOR_ERROR}[Error] make编译失败${COLOR_RESET}"
    return 1
  fi

  if ! make install >/dev/null; then
    echo -e "${COLOR_ERROR}[Error] make install安装失败${COLOR_RESET}"
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] SCWS安装成功${COLOR_RESET}"
  return 0
}
# 安装zhparser服务
install_zhparser() {
  # 目标目录
  local zhparser_dir="/opt/zhparser"
  local zhparser_url="https://bgithub.xyz/amutu/zhparser.git"
  local zhparser_installed_marker="/usr/share/pgsql/extension/zhparser.control" # zhparser安装后的标志文件
  echo -e "${COLOR_INFO}[Info] 开始安装zhparser...${COLOR_RESET}"
  # 检查是否已安装
  if [ -f "$zhparser_installed_marker" ]; then
    echo -e "${COLOR_INFO}[INFO] zhparser已安装，跳过安装过程${COLOR_RESET}"
    return 0
  fi
  # 1. 临时禁用SSL验证
  echo -e "${COLOR_INFO} 临时禁用Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify false

  # 2. 克隆仓库
  echo -e "${COLOR_INFO} 正在克隆zhparser仓库...${COLOR_RESET}"
  if [ -d "$zhparser_dir" ]; then
    echo -e "${COLOR_INFO}[Info] 目标目录已存在，尝试更新代码...${COLOR_RESET}"
    cd "$zhparser_dir" || {
      echo -e "${COLOR_ERROR}[Error] 无法进入目录: $zhparser_dir${COLOR_RESET}"
      return 1
    }
    git pull origin master || {
      echo -e "${COLOR_ERROR}[Error] 代码更新失败${COLOR_RESET}"
      return 1
    }
  else
    git clone "$zhparser_url" "$zhparser_dir" || {
      echo -e "${COLOR_ERROR}[Error] 克隆仓库失败${COLOR_RESET}"
      return 1
    }
    cd "$zhparser_dir" || {
      echo -e "${COLOR_ERROR}[Error] 无法进入目录: $zhparser_dir${COLOR_RESET}"
      return 1
    }
  fi

  # 3. 恢复SSL验证
  echo -e "${COLOR_INFO} 恢复Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify true

  # 4. 编译安装
  echo -e "${COLOR_INFO} 正在编译安装zhparser...${COLOR_RESET}"
  if ! make; then
    echo -e "${COLOR_ERROR}[Error] 编译失败${COLOR_RESET}"
    return 1
  fi

  if ! make install; then
    echo -e "${COLOR_ERROR}[Error] 安装失败${COLOR_RESET}"
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] zhparser安装成功${COLOR_RESET}"
  return 0
}
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

# 安装配置mongodb
install_mongodb() {
  local mongodb_server_url="https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/x86_64/RPMS/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_mongosh_url="https://downloads.mongodb.com/compass/mongodb-mongosh-2.5.2.x86_64.rpm"
  local mongodb_server_arm_url="https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/aarch64/RPMS/mongodb-org-server-7.0.21-1.el9.aarch64.rpm"
  local mongodb_mongosh_arm_url="https://downloads.mongodb.com/compass/mongodb-mongosh-2.5.2.aarch64.rpm"

  is_x86_architecture || {
    mongodb_server_url=$mongodb_server_arm_url
    mongodb_mongosh_url=$mongodb_mongosh_arm_url
  }
  local mongodb_dir="/opt/mongodb"
  local mongodb_server="/opt/mongodb/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_server_src="../5-resource/rpm/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_mongosh="/opt/mongodb/mongodb-mongosh-2.5.2.x86_64.rpm"
  local mongodb_mongosh_src="../5-resource/rpm/mongodb-mongosh-2.5.2.x86_64.rpm"
  echo -e "${COLOR_INFO}[Info] 开始安装MongoDB...${COLOR_RESET}"
  if rpm -q mongod &>/dev/null; then
    echo -e "${COLOR_WARNING}[Warning] MongoDB 已安装，当前版本: $(rpm -q mongod)${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 跳过MongoDB安装${COLOR_RESET}"
    return 0
  fi
  echo -e "${COLOR_INFO}[Info] 安装MongoDB软件包...${COLOR_RESET}"

  if ! mkdir -p "$mongodb_dir"; then
    echo -e "${COLOR_ERROR}[Error] 创建目录失败: $mongodb_dir${COLOR_RESET}"
    return 1
  fi
  if [ -f "$mongodb_server_src" ]; then
    cp -r "$mongodb_server_src" "$mongodb_server"
    sleep 1
  fi
  if [ -f "$mongodb_mongosh_src" ]; then
    cp -r "$mongodb_mongosh_src" "$mongodb_mongosh"
    sleep 1
  fi
  if [ ! -f "$mongodb_server" ]; then
    echo -e "${COLOR_INFO}[Info] 正在下载MongoDB server软件包...${COLOR_RESET}"
    if ! wget "$mongodb_server_url" --no-check-certificate -O "$mongodb_server"; then
      echo -e "${COLOR_ERROR}[Error] MongoDB下载失败${COLOR_RESET}"
      return 1
    fi
  fi
  if [ ! -f "$mongodb_mongosh" ]; then
    echo -e "${COLOR_INFO}[Info] 正在下载MongoDB mongosh软件包...${COLOR_RESET}"
    if ! wget "$mongodb_mongosh_url" --no-check-certificate -O "$mongodb_mongosh"; then
      echo -e "${COLOR_ERROR}[Error] MongoDB下载失败${COLOR_RESET}"
      return 1
    fi
  fi
  dnf install -y $mongodb_server || {
    echo -e "${COLOR_ERROR}[Error] MongoDB server安装失败${COLOR_RESET}"
    return 1
  }
  dnf install -y $mongodb_mongosh || {
    echo -e "${COLOR_ERROR}[Error] MongoDB sh安装失败${COLOR_RESET}"
    return 1
  }
  # 3. 配置MongoDB环境
  echo -e "${COLOR_INFO}[Info] 配置 MongoDB 副本集环境...${COLOR_RESET}"
  # 定义 MongoDB 配置文件路径
  mongo_config_file="/etc/mongod.conf"
  # 检查 MongoDB 配置文件是否存在
  if [ ! -f "$mongo_config_file" ]; then
    echo -e "${COLOR_ERROR}[Error] MongoDB 配置文件 $mongo_config_file 不存在${COLOR_RESET}"
    return 1
  fi
  # 检查是否已经配置了副本集
  if grep -q "replication:" "$mongo_config_file" && grep -q "replSetName:" "$mongo_config_file"; then
    echo -e "${COLOR_WARNING}[Warning] MongoDB 副本集已经配置，跳过...${COLOR_RESET}"
    return 0
  fi
  # 使用 sed 添加配置
  if ! sed -i '/^#replication:/a replication:\n  replSetName: "rs0"' "$mongo_config_file"; then
    echo -e "${COLOR_ERROR}[Error] 无法添加副本集配置${COLOR_RESET}"
    return 1
  fi
  # 5. 启动服务
  echo -e "${COLOR_INFO}[Info] 启动MongoDB服务...${COLOR_RESET}"
  systemctl enable --now mongod || {
    echo -e "${COLOR_ERROR}[Error] MongoDB服务启动失败${COLOR_RESET}"
    return 1
  }

  # 6. 检查服务状态
  echo -e "${COLOR_INFO}[Info] 检查MongoDB服务状态...${COLOR_RESET}"
  if ! systemctl is-active --quiet mongod; then
    echo -e "${COLOR_ERROR}[Error] MongoDB服务未正常运行${COLOR_RESET}"
    return 1
  fi
  # 等待 MongoDB 服务完全启动
  echo -e "${COLOR_INFO}[Info] 等待 MongoDB 服务启动..."
  sleep 5

  # 初始化副本集和创建用户
  echo -e "${COLOR_INFO}[Info] 正在初始化副本集和创建用户..."
  # 初始化副本集（单节点）
  mongosh --eval 'rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27017"}]})' || {
    echo -e "${COLOR_ERROR}[Error] 初始化副本集失败 ${COLOR_RESET}"
    return 1
  }
  # 创建管理员用户
  mongosh admin --eval '
    db.createUser({
      user: "euler_copilot",
      pwd: "YqzzpxJtF5tMAMCrHWw6",
      roles: [
        { role: "readWrite", db: "admin" }
      ]
    })' || {
    echo -e "${COLOR_ERROR}[Error] 创建管理员用户失败 ${COLOR_RESET}"
    return 1
  }
  echo -e "${COLOR_SUCCESS}[Success] MongoDB安装配置完成${COLOR_RESET}"
  return 0
}

check_pip_rag() {
  # 定义需要检查的包和版本
  declare -A REQUIRED_PACKAGES=(
    ["sqlalchemy"]="2.0.23"
    ["paddlepaddle"]="3.0.0"
    ["paddleocr"]="2.9.1"
    ["tiktoken"]=""
  )

  local need_install=0
  local install_list=()

  echo -e "${COLOR_INFO}[Info] 检查Python依赖包...${COLOR_RESET}"

  # 检查每个包是否需要安装
  for pkg in "${!REQUIRED_PACKAGES[@]}"; do
    local required_ver="${REQUIRED_PACKAGES[$pkg]}"
    local installed_ver=$(pip show "$pkg" 2>/dev/null | grep '^Version:' | awk '{print $2}')

    if [[ -z "$installed_ver" ]]; then
      echo -e "${COLOR_WARNING}[Warning] 未安装包: $pkg${COLOR_RESET}"
      need_install=1
      if [[ -n "$required_ver" ]]; then
        install_list+=("${pkg}==${required_ver}")
      else
        install_list+=("$pkg")
      fi
    elif [[ -n "$required_ver" && "$installed_ver" != "$required_ver" ]]; then
      echo -e "${COLOR_WARNING}[Warning] 包版本不匹配: $pkg (已安装: $installed_ver, 需要: $required_ver)${COLOR_RESET}"
      need_install=1
      install_list+=("${pkg}==${required_ver}")
    else
      echo -e "${COLOR_SUCCESS}[OK] 已安装: $pkg${COLOR_RESET}"
    fi
  done

  # 如果需要安装，则执行安装命令
  if [[ "$need_install" -eq 1 ]]; then
    echo -e "${COLOR_INFO}[Info] 开始安装Python依赖...${COLOR_RESET}"
    pip install --retries 10 --timeout 120 "${install_list[@]}" -i https://repo.huaweicloud.com/repository/pypi/simple || {
      echo -e "${COLOR_ERROR}[Error] Python依赖安装失败！${COLOR_RESET}"
      return 1
    }
    echo -e "${COLOR_SUCCESS}[Success] Python依赖安装完成！${COLOR_RESET}"
  else
    echo -e "${COLOR_SUCCESS}[Success] Python依赖已满足要求，跳过安装${COLOR_RESET}"
  fi

  return 0
}
check_pip() {
  # 定义需要检查的包和版本
  declare -A REQUIRED_PACKAGES=(
    ["pymongo"]=""
    ["requests"]=""
    ["pydantic"]=""
    ["aiohttp"]=""
  )

  local need_install=0
  local install_list=()

  echo -e "${COLOR_INFO}[Info] 检查Python依赖包...${COLOR_RESET}"

  # 检查每个包是否需要安装
  for pkg in "${!REQUIRED_PACKAGES[@]}"; do
    local required_ver="${REQUIRED_PACKAGES[$pkg]}"
    local installed_ver=$(pip show "$pkg" 2>/dev/null | grep '^Version:' | awk '{print $2}')

    if [[ -z "$installed_ver" ]]; then
      echo -e "${COLOR_WARNING}[Warning] 未安装包: $pkg${COLOR_RESET}"
      need_install=1
      if [[ -n "$required_ver" ]]; then
        install_list+=("${pkg}==${required_ver}")
      else
        install_list+=("$pkg")
      fi
    elif [[ -n "$required_ver" && "$installed_ver" != "$required_ver" ]]; then
      echo -e "${COLOR_WARNING}[Warning] 包版本不匹配: $pkg (已安装: $installed_ver, 需要: $required_ver)${COLOR_RESET}"
      need_install=1
      install_list+=("${pkg}==${required_ver}")
    else
      echo -e "${COLOR_SUCCESS}[OK] 已安装: $pkg${COLOR_RESET}"
    fi
  done

  # 如果需要安装，则执行安装命令
  if [[ "$need_install" -eq 1 ]]; then
    echo -e "${COLOR_INFO}[Info] 开始安装Python依赖...${COLOR_RESET}"
    pip install --retries 10 --timeout 120 "${install_list[@]}" -i https://repo.huaweicloud.com/repository/pypi/simple || {
      echo -e "${COLOR_ERROR}[Error] Python依赖安装失败！${COLOR_RESET}"
      return 1
    }
    echo -e "${COLOR_SUCCESS}[Success] Python依赖安装完成！${COLOR_RESET}"
  else
    echo -e "${COLOR_SUCCESS}[Success] Python依赖已满足要求，跳过安装${COLOR_RESET}"
  fi

  return 0
}
install_framework() {
  echo -e "\n${COLOR_INFO}[Info] 开始安装框架服务...${COLOR_RESET}"
  local pkgs=(
    "euler-copilot-framework"
    "git"
    "make"
    "gcc"
    "gcc-c++"
    "tar"
    "python3-pip"
  )
  if ! install_and_verify "${pkgs[@]}"; then
    echo -e "${COLOR_ERROR}[Error] dnf安装验证未通过！${COLOR_RESET}"
    return 1
  fi
  cd "$SCRIPT_DIR" || return 1
  cd "$SCRIPT_DIR" || return 1
  install_mongodb || return 1
  check_pip || return 1
}
install_rag() {
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
  if ! install_and_verify "${pkgs[@]}"; then
    echo -e "${COLOR_ERROR}[Error] dnf安装验证未通过！${COLOR_RESET}"
    return 1
  fi
  cd "$SCRIPT_DIR" || return 1
  install_scws || return 1
  cd "$SCRIPT_DIR" || return 1
  install_pgvector || return 1
  cd "$SCRIPT_DIR" || return 1
  install_zhparser || return 1
  cd "$SCRIPT_DIR" || return 1
  install_minio || return 1
  cd "$SCRIPT_DIR" || return 1
  check_pip_rag || return 1
}
install_web() {
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
  if ! install_and_verify "${pkgs[@]}"; then
    echo -e "${COLOR_ERROR}[Error] dnf安装验证未通过！${COLOR_RESET}"
    return 1
  fi
}
# 读取安装模式的方法
read_install_mode() {
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

  # 输出读取结果（也可根据需要返回变量）
  echo -e "${COLOR_INFO}[Info] 读取安装模式:"
  echo -e "  安装Web界面: ${web_install}"
  echo -e "  安装RAG组件: ${rag_install}${COLOR_RESET}"

  # 将结果存入全局变量（供其他函数使用）
  WEB_INSTALL=$web_install
  RAG_INSTALL=$rag_install
  return 0
}
# 示例：根据安装模式执行对应操作（可根据实际需求扩展）
install_components() {
  # 读取安装模式
  read_install_mode || return 1

  # 安装Web界面（如果用户选择）
  if [ "$WEB_INSTALL" = "y" ]; then
    echo -e "\n${COLOR_INFO}[Info] 开始安装Web管理界面...${COLOR_RESET}"
    # 此处添加Web安装命令，示例：
    install_web || return 1
  fi

  # 安装RAG组件（如果用户选择）
  if [ "$RAG_INSTALL" = "y" ]; then
    echo -e "\n${COLOR_INFO}[Info] 开始安装RAG检索增强组件...${COLOR_RESET}"
    # 此处添加RAG安装命令，示例：
    install_rag || return 1
  fi
}

# 主执行函数
main() {
  echo -e "${COLOR_INFO}[Info] === 开始服务安装===${COLOR_RESET}"
  # 获取脚本所在的绝对路径
  declare SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  # 切换到脚本所在目录
  cd "$SCRIPT_DIR" || return 1
  #查看当前脚本执行的模式

  systemctl stop dnf-makecache.timer
  # 执行安装验证
  init_local_repo
  #分支执行TODO
  install_framework || return 1
  install_components || return 1
  echo -e "${COLOR_SUCCESS}[Success] 安装 openEuler Intelligence 完成！${COLOR_RESET}"
  return 0
}

main
