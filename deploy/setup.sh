#!/usr/bin/env bash
# GeekCampus 服务器初始化：装依赖、建库、建 venv、生成 .env、跑迁移
# 用法：sudo bash deploy/setup.sh
# 可重复执行（幂等）：已存在的用户/库/venv 不会重建，只会补齐

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/geekcampus}"
APP_USER="${APP_USER:-geekcampus}"
DB_NAME="${DB_NAME:-geekcampus}"
DB_USER="${DB_USER:-geekcampus}"
APP_PORT="${APP_PORT:-5001}"

SERVER_DIR="$APP_DIR/server"
ENV_FILE="$SERVER_DIR/.env"
VENV="$SERVER_DIR/.venv"

log()  { printf '\033[32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m %s\n' "$*" >&2; exit 1; }

trap 'die "第 $LINENO 行出错，已中止"' ERR

[[ $(id -u) -eq 0 ]] || die "请用 root 运行：sudo bash deploy/setup.sh"
[[ -d "$SERVER_DIR" ]] || die "找不到 $SERVER_DIR，先把代码放到 $APP_DIR"

log "环境检查"
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || warn "当前系统是 ${ID:-unknown}，脚本按 Ubuntu 24.04 写的，请自行确认包名"
echo "    系统: ${PRETTY_NAME:-unknown}"
echo "    内存: $(free -h | awk '/^Mem:/{print $2}')"
echo "    磁盘: $(df -h "$APP_DIR" | awk 'NR==2{print $4" 可用"}')"

# ---------------------------------------------------------------- 1. 系统包
log "安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  nginx mysql-server python3-venv python3-dev build-essential \
  git curl ca-certificates >/dev/null
echo "    nginx $(nginx -v 2>&1 | grep -o '[0-9.]*') / $(python3 --version) / $(mysql --version | grep -o 'Ver [0-9.]*')"

# ---------------------------------------------------------------- 2. 系统用户
if id "$APP_USER" &>/dev/null; then
  log "系统用户 $APP_USER 已存在"
else
  log "创建系统用户 $APP_USER"
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
fi

# ---------------------------------------------------------------- 3. MySQL
log "配置 MySQL"

# 2G 机器的内存调参：buffer pool 压到 256M，关掉 performance_schema
TUNING=/etc/mysql/mysql.conf.d/zz-geekcampus.cnf
if [[ ! -f $TUNING ]]; then
  cat > "$TUNING" <<'EOF'
[mysqld]
# GeekCampus · 2G 机器调参
innodb_buffer_pool_size      = 256M
innodb_log_buffer_size       = 16M
performance_schema           = OFF
max_connections              = 50
table_open_cache             = 400
tmp_table_size               = 32M
max_heap_table_size          = 32M
character-set-server         = utf8mb4
collation-server             = utf8mb4_unicode_ci
bind-address                 = 127.0.0.1
EOF
  systemctl restart mysql
  echo "    已写入 $TUNING"
else
  echo "    $TUNING 已存在，跳过"
fi

DB_PASS=""
if [[ -f $ENV_FILE ]]; then
  DB_PASS=$(grep -E '^MYSQL_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || true)
fi
if [[ -z $DB_PASS ]]; then
  DB_PASS=$(openssl rand -hex 16)
  echo "    已生成数据库密码"
fi

mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL
echo "    数据库 $DB_NAME / 账号 $DB_USER@localhost 就绪"

# ---------------------------------------------------------------- 4. .env
if [[ -f $ENV_FILE ]]; then
  log ".env 已存在，保留原有密钥（如需重置请先备份再删）"
else
  log "生成 .env"
  cat > "$ENV_FILE" <<EOF
# 由 deploy/setup.sh 生成于 $(date '+%Y-%m-%d %H:%M:%S')
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASS
MYSQL_DATABASE=$DB_NAME

SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_EXPIRES_DAYS=7

# 同源部署不需要 CORS；留空 = 禁止所有跨域（最严）。跨站部署时填 https://你的域名
# 注意：必须是纯 https:// 域名，不要带路径或结尾斜杠
CORS_ORIGINS=

FLASK_RUN_HOST=127.0.0.1
FLASK_RUN_PORT=$APP_PORT
EOF
fi
chown "$APP_USER":"$APP_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

# ---------------------------------------------------------------- 5. 目录权限
# 必须排在 venv 之前：上传时目录属主是登录用户（常为 root），晚一步 chown 的话，
# geekcampus 在 root 属主的 server/ 里没有写权限，venv 会直接 Permission denied
log "整理目录权限"
mkdir -p "$SERVER_DIR/uploads"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
# 755：nginx 的 www-data 要能穿越 /srv/geekcampus 才能读到 web/dist，750 会直接 403
chmod 755 "$APP_DIR"
[[ -d "$APP_DIR/web" ]] && chmod -R a+rX "$APP_DIR/web"

# ---------------------------------------------------------------- 6. venv
if [[ ! -x "$VENV/bin/python" ]]; then
  log "创建虚拟环境"
  sudo -u "$APP_USER" python3 -m venv "$VENV"
else
  log "虚拟环境已存在"
fi

log "安装 Python 依赖"
sudo -u "$APP_USER" "$VENV/bin/pip" install -q -U pip wheel
sudo -u "$APP_USER" "$VENV/bin/pip" install -q -r "$SERVER_DIR/requirements.txt"
# 生产服务器：requirements.txt 里没有 gunicorn，这里单独装
sudo -u "$APP_USER" "$VENV/bin/pip" install -q "gunicorn>=22,<23"
echo "    $(sudo -u "$APP_USER" "$VENV/bin/pip" list 2>/dev/null | grep -iE '^(flask|gunicorn|sqlalchemy) ' | tr '\n' ' ')"

# ---------------------------------------------------------------- 7. 迁移
log "执行数据库迁移"
cd "$SERVER_DIR"
sudo -u "$APP_USER" "$VENV/bin/flask" --app wsgi db upgrade

log "健康检查"
set +e
sudo -u "$APP_USER" "$VENV/bin/python" - <<'PY'
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    print("    数据库连接:", db.session.execute(db.text("SELECT 1")).scalar())
    print("    表数量:", len(db.metadata.tables))
PY
set -e

cat <<EOF

$(printf '\033[32m部署完成\033[0m')

下一步：
  1) 上传前端产物到 $APP_DIR/web/dist/
  2) sudo cp deploy/gunicorn.service /etc/systemd/system/geekcampus.service
     sudo systemctl daemon-reload && sudo systemctl enable --now geekcampus
  3) sudo cp deploy/nginx.conf /etc/nginx/sites-available/geekcampus
     sudo ln -sf /etc/nginx/sites-available/geekcampus /etc/nginx/sites-enabled/geekcampus
     sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx

记得在云控制台安全组只放行 22 / 80 / 443。
EOF
