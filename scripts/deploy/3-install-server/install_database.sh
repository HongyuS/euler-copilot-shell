#!/bin/bash
# 颜色定义
COLOR_INFO='\033[34m'    # 蓝色信息
COLOR_SUCCESS='\033[32m' # 绿色成功
COLOR_ERROR='\033[31m'   # 红色错误
COLOR_WARNING='\033[33m' # 黄色警告
COLOR_RESET='\033[0m'    # 重置颜色

## 配置参数
#MYSQL_ROOT_PASSWORD="n6F2tJvvY9Khv16CoybL"  # 设置您的MySQL root密码
#AUTHHUB_USER_PASSWORD="n6F2tJvvY9Khv16CoybL"
#MINIO_ROOT_PASSWORD="ZVzc6xJr3B7HsEUibVBh"
#MONGODB_PASSWORD="YqzzpxJtF5tMAMCrHWw6"
#PGSQL_PASSWORD="6QoJxWoBTL5C6syXhR6k"
# 生成随机密码函数
generate_random_password() {
  # 生成24位随机密码（包含大小写字母、数字和特殊字符）
  local password=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)
  echo $password
}

# 配置参数（自动生成随机密码）
MYSQL_ROOT_PASSWORD=$(generate_random_password)
AUTHHUB_USER_PASSWORD=$(generate_random_password)
MINIO_ROOT_PASSWORD=$(generate_random_password)
PGSQL_PASSWORD=$(generate_random_password)

SQL_FILE="/opt/aops/database/authhub.sql"
tika_jar_src="../5-resource/tika-server-standard-3.2.0.jar"
tika_service_src="../5-resource/tika.service"
tika_jar_dest="/opt/tika/tika-server-standard-3.2.0.jar"
tika_service_dest="/etc/systemd/system/tika.service"
tika_dir="/opt/tika"
config_toml_file="../5-resource/config.toml"
env_file="../5-resource/env"
mysql_temp="../5-resource/mysql_temp"
update_password() {
  # 使用sed命令更新配置文件
  sed -i "s/secret_key = .*/secret_key = '$MINIO_ROOT_PASSWORD'/" $config_toml_file
  sed -i "s/DATABASE_PASSWORD = .*/DATABASE_PASSWORD = $PGSQL_PASSWORD/" $env_file
  sed -i "s/MINIO_SECRET_KEY = .*/MINIO_SECRET_KEY = $MINIO_ROOT_PASSWORD/" $env_file
  if [ -f "$mysql_temp" ]; then
    rm -rf $mysql_temp
  fi
  touch $mysql_temp
  echo $AUTHHUB_USER_PASSWORD >>$mysql_temp
  return 0
}

# 启用并启动服务（改进版）
enable_services() {
  echo -e "${COLOR_INFO}[Info] === 配置系统服务 ===${COLOR_RESET}"
  local services=("redis" "mysqld")

  for service in "${services[@]}"; do
    echo -e "${COLOR_INFO}[Info] 正在处理 $service 服务...${COLOR_RESET}"

    # 检查服务是否存在
    if ! systemctl list-unit-files | grep -q "^$service.service"; then
      echo -e "${COLOR_ERROR}[Error] 服务 $service 不存在${COLOR_RESET}"
      continue
    fi

    # 2. 检查服务是否已运行
    if systemctl is-active "$service" >/dev/null 2>&1; then
      echo -e "${COLOR_SUCCESS}[Success] 服务已在运行中${COLOR_RESET}"
      continue
    fi

    # 3. 启动服务
    echo -e "${COLOR_INFO}[Info] 正在启动 $service ...${COLOR_RESET}"
    if systemctl enable --now "$service" >/dev/null 2>&1; then
      echo -e "${COLOR_SUCCESS}[Success] 启动成功${COLOR_RESET}"

      # 可选：验证服务是否真正启动
      sleep 1
      if ! systemctl is-active "$service" >/dev/null 2>&1; then
        echo -e "${COLOR_ERROR}[Error] 服务启动后未保持运行状态${COLOR_RESET}"
      fi
    else
      echo -e "${COLOR_ERROR}[Error] 启动失败${COLOR_RESET}"
      echo -e "${COLOR_INFO}[Info] 请手动检查：systemctl status $service${COLOR_RESET}"
    fi
  done
}
import_sql_file() {
  local DB_NAME="oauth2" # 替换为你的数据库名
  local DB_USER="root"   # 数据库用户名

  # 检查SQL文件是否存在
  if [ ! -f "$SQL_FILE" ]; then
    echo -e "${COLOR_WARNING}[Warning] 警告：未找到 $SQL_FILE 文件，跳过数据库导入${COLOR_RESET}"
    return 1
  fi

  echo -e "${COLOR_INFO}[Info] 正在准备导入数据库($SQL_FILE)...${COLOR_RESET}"

  # 检查数据库是否已存在
  if mysql -u "$DB_USER" -e "USE $DB_NAME" 2>/dev/null; then
    echo -e "${COLOR_INFO}[Info] 检测到已存在数据库 $DB_NAME，将执行重建...${COLOR_RESET}"

    # 删除现有数据库
    if ! mysql -u "$DB_USER" -e "DROP DATABASE $DB_NAME" 2>/dev/null; then
      echo -e "${COLOR_ERROR}[Error] 错误：无法删除现有数据库 $DB_NAME${COLOR_RESET}"
      return 1
    fi
    echo -e "${COLOR_SUCCESS}[Success] 成功删除旧数据库${COLOR_RESET}"
  fi

  # 导入SQL文件
  echo -e "${COLOR_INFO}正在导入SQL文件...${COLOR_RESET}"
  if mysql -u "$DB_USER" <"$SQL_FILE"; then
    echo -e "${COLOR_SUCCESS}[Success] 数据库导入成功${COLOR_RESET}"

    # 验证导入结果
    if mysql -u "$DB_USER" -e "USE $DB_NAME; SHOW TABLES" 2>/dev/null | grep -q .; then
      echo -e "${COLOR_SUCCESS}[Success] 数据库验证通过${COLOR_RESET}"
      return 0
    else
      echo -e "${COLOR_WARNING}[Warning] 警告：数据库导入后未检测到数据表${COLOR_RESET}"
      return 1
    fi
  else
    echo -e "${COLOR_ERROR}[Error] 数据库导入失败${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 可能原因："
    echo -e "[Info] 1. SQL文件格式错误"
    echo -e "[Info] 2. 数据库权限不足"
    echo -e "[Info] 3. SQL文件包含错误语句${COLOR_RESET}"
    return 1
  fi
}
# 配置MySQL
configure_mysql() {
  echo -e "${COLOR_INFO}[Info] === 配置MySQL数据库 ===${COLOR_RESET}"

  # 安全初始化MySQL（如果未初始化）
  if ! mysql -u root -e "SELECT 1" >/dev/null 2>&1; then
    echo -e "${COLOR_INFO}[Info] 正在初始化MySQL安全配置...${COLOR_RESET}"
    mysql_secure_installation <<EOF
y
${MYSQL_ROOT_PASSWORD}
${MYSQL_ROOT_PASSWORD}
y
y
y
y
EOF
  fi

  # 创建authhub用户
  echo -e "${COLOR_INFO}[Info] 正在创建authhub用户... ${COLOR_RESET}"
  if mysql -u root -e "CREATE USER IF NOT EXISTS 'authhub'@'localhost' IDENTIFIED BY '${AUTHHUB_USER_PASSWORD}'" >/dev/null 2>&1; then
    echo -e "${COLOR_SUCCESS}[Success] 成功${COLOR_RESET}"
  else
    echo -e "${COLOR_ERROR}[Error] 失败${COLOR_RESET}"
    echo -e "${COLOR_ERROR}[Error] 错误：无法创建MySQL用户${COLOR_RESET}"
    return 1
  fi

  import_sql_file || return 1

  # 设置权限
  echo -e "${COLOR_INFO}[Info] 正在设置数据库权限... ${COLOR_RESET}"
  if mysql -u root -e "GRANT ALL PRIVILEGES ON oauth2.* TO 'authhub'@'localhost' WITH GRANT OPTION" >/dev/null 2>&1; then
    echo -e "${COLOR_SUCCESS}[Success] 成功${COLOR_RESET}"
    return 0
  else
    echo -e "${COLOR_ERROR}[Error] 失败${COLOR_RESET}"
    echo -e "${COLOR_ERROR}[Error] 错误：权限设置失败，请检查oauth2数据库是否存在${COLOR_RESET}"
    return 1
  fi
}

# 验证安装
verify_installation() {
  echo -e "${COLOR_INFO}[Info] === 验证安装结果 ===${COLOR_RESET}"

  # 验证服务状态
  echo -e "${COLOR_INFO}[Info] 服务状态：${COLOR_RESET}"
  systemctl status redis --no-pager | grep -E "Active:|Loaded:"
  systemctl status mysqld --no-pager | grep -E "Active:|Loaded:"

  # 验证数据库连接
  echo -e "${COLOR_INFO}[Info] 验证authhub用户连接... ${COLOR_RESET}"
  if mysql -u authhub -p"${AUTHHUB_USER_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
    echo -e "${COLOR_SUCCESS}[Success] 成功${COLOR_RESET}"
  else
    echo -e "${COLOR_ERROR}[Error] 失败${COLOR_RESET}"
  fi
  return 0
  #    echo -e "${COLOR_INFO}[Info] === 重要信息 ===${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] authhub用户密码: ${AUTHHUB_USER_PASSWORD}${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 请妥善保管以上密码！${COLOR_RESET}"
}
#配置nginx
configure_nginx() {
  local nginx_conf="/etc/nginx/conf.d/authhub.nginx.conf"
  local backup_conf="/etc/nginx/conf.d/authhub.nginx.conf.bak"
  local temp_conf="/tmp/authhub.nginx.conf.tmp"

  echo -e "${COLOR_INFO}[Info] 开始配置Nginx...${COLOR_RESET}"

  # 1. 检查原配置文件是否存在
  if [ ! -f "$nginx_conf" ]; then
    echo -e "${COLOR_ERROR}[Error] Nginx配置文件不存在: $nginx_conf${COLOR_RESET}"
    return 1
  fi

  # 2. 创建备份
  if ! cp -f "$nginx_conf" "$backup_conf"; then
    echo -e "${COLOR_ERROR}[Error] 创建配置文件备份失败${COLOR_RESET}"
    return 1
  fi
  echo -e "${COLOR_INFO}[Info] 已创建配置文件备份: $backup_conf${COLOR_RESET}"

  # 3. 执行替换操作
  if ! sed 's|proxy_pass http://oauth2server;|proxy_pass http://127.0.0.1:11120;|g' "$nginx_conf" >"$temp_conf"; then
    echo -e "${COLOR_ERROR}[Error] 配置文件替换失败${COLOR_RESET}"
    return 1
  fi

  # 4. 应用新配置
  if ! mv -f "$temp_conf" "$nginx_conf"; then
    echo -e "${COLOR_ERROR}[Error] 应用新配置文件失败${COLOR_RESET}"
    return 1
  fi
  # 5. 验证新配置文件语法
  if ! nginx -t &>/dev/null; then
    echo -e "${COLOR_ERROR}[Error] 新配置文件语法检查失败${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 正在恢复原始配置...${COLOR_RESET}"
    cp -f "$backup_conf" "$nginx_conf"
    return 1
  fi

  if ! systemctl enable --now nginx; then
    echo -e "${COLOR_ERROR}[Error] Nginx启动失败${COLOR_RESET}"
  fi
  # 6. 重载Nginx配置
  if ! systemctl reload nginx; then
    echo -e "${COLOR_ERROR}[Error] Nginx配置重载失败${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 正在恢复原始配置...${COLOR_RESET}"
    cp -f "$backup_conf" "$nginx_conf"
    systemctl reload nginx
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] Nginx配置更新成功！${COLOR_RESET}"
  return 0
}
# 安装并配置Tika服务
install_tika() {

  echo -e "${COLOR_INFO}[Info] 开始安装Tika服务...${COLOR_RESET}"

  # 1. 检查源文件是否存在
  if [ ! -f "$tika_jar_src" ]; then
    echo -e "${COLOR_ERROR}[Error] Tika JAR文件不存在: $tika_jar_src${COLOR_RESET}"
    return 1
  fi

  if [ ! -f "$tika_service_src" ]; then
    echo -e "${COLOR_ERROR}[Error] Tika服务文件不存在: $tika_service_src${COLOR_RESET}"
    return 1
  fi

  # 2. 复制JAR文件并设置权限
  if [ ! -d "$tika_dir" ]; then
    echo -e "${COLOR_INFO}[Info] 创建目录: $tika_dir${COLOR_RESET}"
    if ! mkdir -p "$tika_dir"; then
      echo -e "${COLOR_ERROR}[Error] 无法创建目录: $tika_dir${COLOR_RESET}"
      return 1
    fi
  fi
  if ! cp -v "$tika_jar_src" "$tika_jar_dest"; then
    echo -e "${COLOR_ERROR}[Error] 复制Tika JAR文件失败${COLOR_RESET}"
    return 1
  fi

  if ! chmod 755 "$tika_jar_dest"; then
    echo -e "${COLOR_WARNING}[Warning] 设置Tika JAR文件权限失败${COLOR_RESET}"
  fi

  # 3. 复制服务文件并设置权限
  if ! cp -v "$tika_service_src" "$tika_service_dest"; then
    echo -e "${COLOR_ERROR}[Error] 复制Tika服务文件失败${COLOR_RESET}"
    return 1
  fi

  if ! chmod 644 "$tika_service_dest"; then
    echo -e "${COLOR_WARNING}[Warning] 设置Tika服务文件权限失败${COLOR_RESET}"
  fi

  # 4. 重载systemd
  if ! systemctl daemon-reload; then
    echo -e "${COLOR_ERROR}[Error] systemd重载失败${COLOR_RESET}"
    return 1
  fi

  # 5. 启用并启动服务
  if ! systemctl enable --now tika; then
    echo -e "${COLOR_ERROR}[Error] Tika服务启动失败${COLOR_RESET}"

    # 检查服务状态获取更多信息
    local service_status=$(systemctl status tika --no-pager 2>&1)
    echo -e "${COLOR_INFO}[Debug] 服务状态信息:\n$service_status${COLOR_RESET}"

    journalctl -u tika --no-pager -n 20 | grep -i error
    return 1
  fi

  # 6. 验证服务运行状态
  sleep 2 # 等待服务启动
  if ! systemctl is-active --quiet tika; then
    echo -e "${COLOR_ERROR}[Error] Tika服务未正常运行${COLOR_RESET}"
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] Tika服务安装配置完成！${COLOR_RESET}"

  # 显示安装信息
  #    echo -e "${COLOR_INFO}[Info] Tika JAR位置: $tika_jar_dest${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 服务文件位置: $tika_service_dest${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 使用命令: systemctl status tika 查看服务状态${COLOR_RESET}"
  return 0
}
# 安装并配置pgvector服务
install_pgvector() {
  local pgvector_dir="/opt/pgvector"
  local zhparser_url="https://github.com/pgvector/pgvector.git"
  local pgvector_installed_marker="/usr/share/pgsql/extension/vector.control" # pgvector安装后的标志文件
  echo -e "${COLOR_INFO}[Info] 开始安装pgvector...${COLOR_RESET}"
  if [ -f "$pgvector_installed_marker" ]; then
    echo -e "${COLOR_INFO}[Info] pgvector已安装，跳过安装过程${COLOR_RESET}"
    return 0
  fi
  # 1. 临时禁用SSL验证
  echo -e "${COLOR_INFO}[Info] 临时禁用Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify false

  # 2. 克隆仓库
  echo -e "${COLOR_INFO}[Info] 正在克隆zhparser仓库...${COLOR_RESET}"
  if [ -d "$pgvector_dir" ]; then
    echo -e "${COLOR_INFO}[Info] 目标目录已存在，尝试更新代码...${COLOR_RESET}"
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
  echo -e "${COLOR_INFO}[Info] 恢复Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify true

  # 4. 进入解压目录编译安装
  echo -e "${COLOR_INFO}[Info] 正在编译安装pgvector...${COLOR_RESET}"
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
# 安装并配置scws服务
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
  echo -e "${COLOR_INFO}[Info] 正在下载SCWS...${COLOR_RESET}"
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
  echo -e "${COLOR_INFO}[Info] 正在解压SCWS...${COLOR_RESET}"
  if ! tar -xjf "$scws_tar" -C "$scws_dir" --strip-components=1; then
    echo -e "${COLOR_ERROR}[Error] 解压SCWS失败${COLOR_RESET}"
    return 1
  fi

  # 5. 编译安装
  echo -e "${COLOR_INFO}[Info] 正在编译安装SCWS...${COLOR_RESET}"
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
# 安装并配置zhparser服务
install_zhparser() {
  # 目标目录
  local zhparser_dir="/opt/zhparser"
  local zhparser_url="https://github.com/amutu/zhparser.git"
  local zhparser_installed_marker="/usr/share/pgsql/extension/zhparser.control" # zhparser安装后的标志文件
  echo -e "${COLOR_INFO}[Info] 开始安装zhparser...${COLOR_RESET}"
  # 检查是否已安装
  if [ -f "$zhparser_installed_marker" ]; then
    echo -e "${COLOR_INFO}[INFO] zhparser已安装，跳过安装过程${COLOR_RESET}"
    return 0
  fi
  # 1. 临时禁用SSL验证
  echo -e "${COLOR_INFO}[Info] 临时禁用Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify false

  # 2. 克隆仓库
  echo -e "${COLOR_INFO}[Info] 正在克隆zhparser仓库...${COLOR_RESET}"
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
  echo -e "${COLOR_INFO}[Info] 恢复Git SSL验证...${COLOR_RESET}"
  git config --global http.sslVerify true

  # 4. 编译安装
  echo -e "${COLOR_INFO}[Info] 正在编译安装zhparser...${COLOR_RESET}"
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
# PostgreSQL配置函数
configure_postgresql() {
  echo -e "${COLOR_INFO}[Info] 开始配置PostgreSQL...${COLOR_RESET}"

  local pg_data_dir="/var/lib/pgsql/data"
  local pg_service="postgresql"

  # 1. 检查并处理PostgreSQL服务状态
  echo -e "${COLOR_INFO}[Info] 检查PostgreSQL服务状态...${COLOR_RESET}"

  if systemctl is-active --quiet "$pg_service"; then
    echo -e "${COLOR_WARNING}[Warning] PostgreSQL服务正在运行，正在停止服务...${COLOR_RESET}"
    systemctl stop "$pg_service" || {
      echo -e "${COLOR_ERROR}[Error] 无法停止PostgreSQL服务${COLOR_RESET}"
      return 1
    }
  fi

  # 2. 检查并处理数据目录
  echo -e "${COLOR_INFO}[Info] 检查PostgreSQL数据目录...${COLOR_RESET}"

  if [ -d "$pg_data_dir" ] && [ "$(ls -A $pg_data_dir)" ]; then
    echo -e "${COLOR_WARNING}[Warning] 数据目录不为空: $pg_data_dir${COLOR_RESET}"

    # 检查是否已经是有效的PostgreSQL数据目录
    if [ -f "$pg_data_dir/PG_VERSION" ]; then
      echo -e "${COLOR_INFO}[Info] 检测到已有PostgreSQL数据，准备重新初始化${COLOR_RESET}"
      #            read -p "确定要重新初始化数据库吗？所有现有数据将被删除！(y/n) " choice
      #            if [[ ! "$choice" =~ ^[Yy]$ ]]; then
      #                echo -e "${COLOR_INFO}[Info] 用户取消操作${COLOR_RESET}"
      #                return 1
      #            fi

      echo -e "${COLOR_INFO}[Info] 删除现有数据目录...${COLOR_RESET}"
      rm -rf "$pg_data_dir" || {
        echo -e "${COLOR_ERROR}[Error] 无法删除数据目录${COLOR_RESET}"
        return 1
      }
    else
      echo -e "${COLOR_WARNING}[Warning] 目录不是有效的PostgreSQL数据目录${COLOR_RESET}"
      read -p "是否要清空目录？(y/n) " choice
      if [[ "$choice" =~ ^[Yy]$ ]]; then
        echo -e "${COLOR_INFO}[Info] 清空数据目录...${COLOR_RESET}"
        rm -rf "${pg_data_dir}"/*
      else
        echo -e "${COLOR_INFO}[Info] 跳过目录处理${COLOR_RESET}"
      fi
    fi

    # 确保目录权限正确
    chown postgres:postgres "$pg_data_dir"
    chmod 700 "$pg_data_dir"
  fi

  # 3. 初始化数据库
  echo -e "${COLOR_INFO}[Info] 初始化PostgreSQL数据库...${COLOR_RESET}"
  /usr/bin/postgresql-setup --initdb || {
    echo -e "${COLOR_ERROR}[Error] 数据库初始化失败"
    echo -e "请检查日志文件: /var/lib/pgsql/initdb_postgresql.log${COLOR_RESET}"
    return 1
  }

  # 2. 启动服务
  echo -e "${COLOR_INFO}[Info] 启动PostgreSQL服务...${COLOR_RESET}"
  systemctl enable --now postgresql || {
    echo -e "${COLOR_ERROR}[Error] 服务启动失败${COLOR_RESET}"
    return 1
  }

  # 3. 设置postgres用户密码
  echo -e "${COLOR_INFO}[Info] 设置PostgreSQL密码...${COLOR_RESET}"
  sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$PGSQL_PASSWORD';" || {
    echo -e "${COLOR_ERROR}[Error] 密码设置失败${COLOR_RESET}"
    return 1
  }

  # 4. 启用扩展
  echo -e "${COLOR_INFO}[Info] 启用PostgreSQL扩展...${COLOR_RESET}"
  sudo -u postgres psql -c "CREATE EXTENSION  zhparser;" || {
    echo -e "${COLOR_ERROR}[Error] 无法启用zhparser扩展${COLOR_RESET}"
    return 1
  }

  sudo -u postgres psql -c "CREATE EXTENSION  vector;" || {
    echo -e "${COLOR_ERROR}[Error] 无法启用vector扩展${COLOR_RESET}"
    return 1
  }

  sudo -u postgres psql -c "CREATE TEXT SEARCH CONFIGURATION  zhparser (PARSER = zhparser);" || {
    echo -e "${COLOR_ERROR}[Error] 无法创建全文搜索配置${COLOR_RESET}"
    return 1
  }

  sudo -u postgres psql -c "ALTER TEXT SEARCH CONFIGURATION zhparser ADD MAPPING FOR n,v,a,i,e,l WITH simple;" || {
    echo -e "${COLOR_ERROR}[Error] 无法添加映射${COLOR_RESET}"
    return 1
  }

  # 5. 查找并修改pg_hba.conf
  echo -e "${COLOR_INFO}[Info] 配置认证方式...${COLOR_RESET}"
  local pg_hba_conf=$(find / -name pg_hba.conf 2>/dev/null | head -n 1)

  if [ -z "$pg_hba_conf" ]; then
    echo -e "${COLOR_ERROR}[Error] 找不到pg_hba.conf文件${COLOR_RESET}"
    return 1
  fi

  # 备份原始文件
  cp "$pg_hba_conf" "${pg_hba_conf}.bak"

  # 修改认证方式
  sed -i -E 's/(local\s+all\s+all\s+)peer/\1md5/' "$pg_hba_conf"
  sed -i -E 's/(host\s+all\s+all\s+127\.0\.0\.1\/32\s+)ident/\1md5/' "$pg_hba_conf"
  sed -i -E 's/(host\s+all\s+all\s+::1\/128\s+)ident/\1md5/' "$pg_hba_conf"
  # 2. 启动服务
  echo -e "${COLOR_INFO}[Info] 重启PostgreSQL服务...${COLOR_RESET}"
  systemctl daemon-reload
  systemctl restart postgresql || {
    echo -e "${COLOR_ERROR}[Error] 服务重启失败${COLOR_RESET}"
    return 1
  }
  echo -e "${COLOR_SUCCESS}[Success] PostgreSQL配置完成${COLOR_RESET}"
  return 0
}
# 安装配置MinIO
install_minio() {
  local minio_url="https://dl.min.io/server/minio/release/linux-amd64/archive/minio-20250524170830.0.0-1.x86_64.rpm"
  local minio_src="../5-resource/rpm/minio-20250524170830.0.0-1.x86_64.rpm"
  local minio_dir="/opt/minio"
  local minio_file="/opt/minio/minio-20250524170830.0.0-1.x86_64.rpm"
  echo -e "${COLOR_INFO}[Info] 开始安装配置MinIO...${COLOR_RESET}"
  # 1. 检查MinIO是否已安装
  if rpm -q minio &>/dev/null; then
    echo -e "${COLOR_WARNING}[Warning] MinIO 已安装，当前版本: $(rpm -q minio)${COLOR_RESET}"
    echo -e "${COLOR_INFO}[Info] 跳过MinIO安装${COLOR_RESET}"
    return 0
  fi
  # 2. 安装MinIO
  echo -e "${COLOR_INFO}[Info] 安装MinIO软件包...${COLOR_RESET}"

  if ! mkdir -p "$minio_dir"; then
    echo -e "${COLOR_ERROR}[Error] 创建目录失败: $minio_dir${COLOR_RESET}"
    return 1
  fi
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

  # 3. 配置MinIO环境
  echo -e "${COLOR_INFO}[Info] 配置MinIO环境...${COLOR_RESET}"
  cat >/etc/default/minio <<EOF
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
MINIO_VOLUMES=/var/lib/minio
EOF

  # 4. 创建用户和目录
  echo -e "${COLOR_INFO}[Info] 创建MinIO用户和目录...${COLOR_RESET}"
  if ! id minio-user &>/dev/null; then
    groupadd minio-user
    useradd -g minio-user --shell=/sbin/nologin -r minio-user
  fi

  mkdir -p /var/lib/minio
  chown -R minio-user:minio-user /var/lib/minio

  # 5. 启动服务
  echo -e "${COLOR_INFO}[Info] 启动MinIO服务...${COLOR_RESET}"
  systemctl enable --now minio || {
    echo -e "${COLOR_ERROR}[Error] MinIO服务启动失败${COLOR_RESET}"
    return 1
  }

  # 6. 检查服务状态
  echo -e "${COLOR_INFO}[Info] 检查MinIO服务状态...${COLOR_RESET}"
  if ! systemctl is-active --quiet minio; then
    echo -e "${COLOR_ERROR}[Error] MinIO服务未正常运行${COLOR_RESET}"
    return 1
  fi

  echo -e "${COLOR_SUCCESS}[Success] MinIO安装配置完成${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 访问地址: http://<服务器IP>:9000${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 用户名: minioadmin${COLOR_RESET}"
  #    echo -e "${COLOR_INFO}[Info] 密码: ZVzc6xJr3B7HsEUibVBh${COLOR_RESET}"
  return 0
}

# 安装配置mongodb
install_mongodb() {
  local mongodb_server_url="https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/x86_64/RPMS/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_mongosh_url="https://downloads.mongodb.com/compass/mongodb-mongosh-2.5.2.x86_64.rpm"
  local mongodb_dir="/opt/mongodb"
  local mongodb_server="/opt/mongodb/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_server_src="../5-resource/rpm/mongodb-org-server-7.0.21-1.el9.x86_64.rpm"
  local mongodb_mongosh="/opt/mongodb/mongodb-mongosh-2.5.2.x86_64.rpm"
  local mongodb_mongosh_src="../5-resource/rpm/mongodb-mongosh-2.5.2.x86_64.rpm"
  echo -e "${COLOR_INFO}[Info] 开始安装配置MongoDB...${COLOR_RESET}"
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
    echo -e "${COLOR_INFO}[Info] 正在下载MongoDB软件包...${COLOR_RESET}"
    if ! wget "$mongodb_server_url" --no-check-certificate -O "$mongodb_server"; then
      echo -e "${COLOR_ERROR}[Error] MongoDB下载失败${COLOR_RESET}"
      return 1
    fi
  fi
  if [ ! -f "$mongodb_mongosh" ]; then
    echo -e "${COLOR_INFO}[Info] 正在下载MongoDB软件包...${COLOR_RESET}"
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

  echo "MongoDB 配置完成"
  echo -e "${COLOR_SUCCESS}[Success] MongoDB安装配置完成${COLOR_RESET}"
  return 0
}
# 主函数
main() {
  # 获取脚本所在的绝对路径
  SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  # 切换到脚本所在目录
  cd "$SCRIPT_DIR" || exit 1
  update_password
  enable_services || return 1
  configure_mysql || return 1
  verify_installation || return 1
  configure_nginx || return 1
  install_tika || return 1
  install_pgvector || return 1
  install_scws || return 1
  install_zhparser || return 1
  cd "$SCRIPT_DIR" || exit 1
  install_minio || return 1
  cd "$SCRIPT_DIR" || exit 1
  install_mongodb || return 1
  # 执行配置函数
  if configure_postgresql; then
    echo -e "${COLOR_SUCCESS}[Success] postgresql配置已完成${COLOR_RESET}"
  else
    echo -e "${COLOR_ERROR}[Error] postgresql配置过程中出现错误${COLOR_RESET}"
    exit 1
  fi
  cd "$SCRIPT_DIR" || exit 1
  ./install_authhub_config.sh || return 1
}

main "$@"
