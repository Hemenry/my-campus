#!/usr/bin/env bash
# GeekCampus 一键上线：setup.sh（环境/库/venv/迁移）→ systemd → nginx → 健康检查
# 用法：sudo bash deploy/bootstrap.sh
#      sudo SEED=1 bash deploy/bootstrap.sh    # 顺便灌演示数据
# 幂等：重复跑只会重启服务、重载 nginx

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/geekcampus}"
APP_USER="${APP_USER:-geekcampus}"
APP_PORT="${APP_PORT:-5001}"
SEED="${SEED:-0}"
SERVER_DIR="$APP_DIR/server"

log()  { printf '\033[32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m %s\n' "$*" >&2; exit 1; }
trap 'die "第 $LINENO 行出错，已中止（上面的报错就是原因）"' ERR

[[ $(id -u) -eq 0 ]] || die "请用 root 运行：sudo bash deploy/bootstrap.sh"
[[ -d "$SERVER_DIR" ]] || die "找不到 $SERVER_DIR，先把代码放上去"

# ---------------------------------------------------------------- 1. 基础环境
log "阶段 1/4：环境初始化（装包/建库/venv/迁移）"
bash "$APP_DIR/deploy/setup.sh"

# ---------------------------------------------------------------- 2. systemd
log "阶段 2/4：安装 Gunicorn 服务"
install -m 644 "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/geekcampus.service
systemctl daemon-reload
systemctl enable geekcampus >/dev/null 2>&1 || true
systemctl restart geekcampus
sleep 2
systemctl is-active --quiet geekcampus || {
  journalctl -u geekcampus -n 40 --no-pager || true
  die "geekcampus 服务没起来"
}
echo "    geekcampus.service: $(systemctl is-active geekcampus)"

# ---------------------------------------------------------------- 3. nginx
log "阶段 3/4：配置 Nginx"
[[ -f "$APP_DIR/web/dist/index.html" ]] || warn "web/dist/index.html 不存在，首页会 404"

install -m 644 "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/geekcampus
ln -sf /etc/nginx/sites-available/geekcampus /etc/nginx/sites-enabled/geekcampus
rm -f /etc/nginx/sites-enabled/default
# 站点根目录要能被 www-data 穿越
chmod 755 "$APP_DIR"
[[ -d "$APP_DIR/web" ]] && chmod -R a+rX "$APP_DIR/web"

nginx -t
systemctl reload nginx
echo "    nginx: $(systemctl is-active nginx)"

# ---------------------------------------------------------------- 4. 演示数据
if [[ "$SEED" == "1" ]]; then
  log "阶段 4/4：灌演示数据"
  cd "$SERVER_DIR"
  sudo -u "$APP_USER" "$SERVER_DIR/.venv/bin/python" seed.py
  warn "演示账号密码是 123456，真正对外前请改掉"
else
  log "阶段 4/4：跳过演示数据（需要时：sudo SEED=1 bash deploy/bootstrap.sh）"
fi

# ---------------------------------------------------------------- 5. 自检
log "健康检查"
set +e
API=$(curl -s --max-time 5 "http://127.0.0.1:$APP_PORT/api/health")
echo "    /api/health -> ${API:0:160}"
PAGE=$(curl -s -o /dev/null -w '%{http_code} %{content_type}' --max-time 5 "http://127.0.0.1/")
echo "    /           -> $PAGE"
POSTS=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1/api/posts?page=1&size=1")
echo "    /api/posts  -> $POSTS"
set -e

if [[ "$API" == *'"status":"healthy"'* && "$PAGE" == 200* && "$POSTS" == "200" ]]; then
  PUBIP=$(curl -s --max-time 3 https://api.ipify.org || echo "<公网IP>")
  cat <<EOF

$(printf '\033[32m上线成功\033[0m')  →  http://$PUBIP

日志：journalctl -u geekcampus -f
发版：上传新代码后 sudo bash $APP_DIR/deploy/release.sh
EOF
else
  warn "有检查项没过，看上面的输出和：journalctl -u geekcampus -n 50 --no-pager"
  exit 1
fi
