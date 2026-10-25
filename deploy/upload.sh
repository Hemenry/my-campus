#!/usr/bin/env bash
# GeekCampus · 本地 → 服务器 上传脚本
#
# 把 server/（后端源码）、deploy/（部署脚本）、web/dist（本地构建好的前端产物）
# 打包送到服务器并解压到 /srv/geekcampus。
#
# 用法（在仓库根目录或任意位置执行）：
#   bash deploy/upload.sh --host 1.2.3.4 --user root
#   bash deploy/upload.sh --host 1.2.3.4 --user root --domain example.com
#   bash deploy/upload.sh --host 1.2.3.4 --user ubuntu --port 2222 --key ~/.ssh/mykey
#
# 环境变量等价写法：DEPLOY_HOST / DEPLOY_USER / DEPLOY_PORT / DEPLOY_KEY / DEPLOY_DOMAIN
#
# 注意：
#   - 不会上传本地 .env、.venv、node_modules、uploads，服务器上的这些一律保留/自行生成
#   - 前端产物必须在本地构建好（npm run build），服务器 2G 内存跑 vite build 会 OOM

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOST="${DEPLOY_HOST:-}"
PORT="${DEPLOY_PORT:-22}"
REMOTE_USER="${DEPLOY_USER:-root}"
KEY_FILE="${DEPLOY_KEY:-$HOME/.ssh/geekcampus_deploy}"
DOMAIN="${DEPLOY_DOMAIN:-}"
REMOTE_DIR="/srv/geekcampus"
# 跑服务的系统用户。chown 必须落到它身上，绝不能是登录用户：
# 以 root 上传时若 chown 成 root，.env(600) 就变成 root 专属，gunicorn 读不到直接崩
APP_USER="${APP_USER:-geekcampus}"

log()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m  ✓\033[0m %s\n' "$*"; }
warn() { printf '\033[33m  !!\033[0m %s\n' "$*"; }
die()  { printf '\033[31m  xx\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  grep -E '^#  ' "$0" | sed 's/^#  //' | sed 's/^# //'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)     HOST="$2"; shift 2 ;;
    --port)     PORT="$2"; shift 2 ;;
    --user)     REMOTE_USER="$2"; shift 2 ;;
    --key)      KEY_FILE="$2"; shift 2 ;;
    --domain)   DOMAIN="$2"; shift 2 ;;
    --remote-dir) REMOTE_DIR="$2"; shift 2 ;;
    -h|--help)  usage ;;
    *)          die "未知参数：$1（用 --help 看用法）" ;;
  esac
done

[[ -n "$HOST" ]] || die "缺少 --host（服务器 IP 或主机名）"
[[ -f web/dist/index.html ]] || die "web/dist/index.html 不存在，先在本地跑：cd web && npm run build"

# ---------------------------------------------------------------- 1. 域名
if [[ -n "$DOMAIN" ]]; then
  log "写入域名到 nginx.conf"
  if grep -qE '^\s*server_name _;' deploy/nginx.conf; then
    # 保留原有缩进；有 www 子域名需求时它也被 certbot 一起覆盖
    sed -i -E "s|^([[:space:]]*)server_name _;|\1server_name ${DOMAIN} www.${DOMAIN};|" deploy/nginx.conf
    ok "server_name → ${DOMAIN} www.${DOMAIN}"
  else
    warn "nginx.conf 里没找到 'server_name _;'，跳过（可能已改过）"
  fi
fi

# ---------------------------------------------------------------- 2. 打包
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="/tmp/geekcampus-${STAMP}.tar.gz"

log "打包（排除 .venv / node_modules / .env / uploads / 缓存）"
tar czf "$ARCHIVE" \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='server/.venv' \
  --exclude='server/.env' \
  --exclude='server/uploads' \
  --exclude='web/node_modules' \
  --exclude='web/dist_old' \
  server deploy web/dist
ok "$(du -h "$ARCHIVE" | cut -f1) → $ARCHIVE"

# ---------------------------------------------------------------- 3. 传输
[[ -f "$KEY_FILE" ]] || die "私钥 $KEY_FILE 不存在。用 --key 指定，或先建立免密登录"

COMMON_OPTS=(
  -i "$KEY_FILE"
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=10
  -o BatchMode=yes
)
# 坑：ssh 用小写 -p 指定端口，scp 必须大写 -P（小写 -p 在 scp 里是"保留文件属性"，
#     写错会报 stat local "22": No such file）
SSH_OPTS=( "${COMMON_OPTS[@]}" -p "$PORT" )
SCP_OPTS=( "${COMMON_OPTS[@]}" -P "$PORT" )
# 已经是 root 就不必再套 sudo
[[ "$REMOTE_USER" == "root" ]] && SUDO="" || SUDO="sudo"

log "上传到 ${REMOTE_USER}@${HOST}:${PORT}"
scp "${SCP_OPTS[@]}" "$ARCHIVE" "${REMOTE_USER}@${HOST}:/tmp/" || die "上传失败，检查 IP/端口/私钥是否正确"
ok "已到达服务器 /tmp/$(basename "$ARCHIVE")"

# ---------------------------------------------------------------- 4. 解压
log "远端解压到 ${REMOTE_DIR}"
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${HOST}" \
  "${SUDO} mkdir -p ${REMOTE_DIR}/server/uploads ${REMOTE_DIR}/web/dist && \
   ${SUDO} tar xzf /tmp/$(basename "$ARCHIVE") -C ${REMOTE_DIR} && \
   rm -f /tmp/$(basename "$ARCHIVE") && \
   { ${SUDO} chown -R ${APP_USER}:${APP_USER} ${REMOTE_DIR} 2>/dev/null || ${SUDO} chown -R ${REMOTE_USER}:${REMOTE_USER} ${REMOTE_DIR}; } && \
   ${SUDO} chmod 755 ${REMOTE_DIR} && \
   { if [ -f ${REMOTE_DIR}/server/.env ]; then ${SUDO} chown ${APP_USER}:${APP_USER} ${REMOTE_DIR}/server/.env 2>/dev/null; ${SUDO} chmod 600 ${REMOTE_DIR}/server/.env; fi; } && \
   echo '--- .env 属主 ---' && ls -l ${REMOTE_DIR}/server/.env && \
   ls -d ${REMOTE_DIR}/{server,deploy,web/dist} && \
   ls ${REMOTE_DIR}/web/dist" \
  || die "解压失败"
ok "代码已就位"

cat <<EOF

下一步（在服务器上执行）：
  1) 首次部署（装环境/建库/起服务/配 nginx）：
     sudo bash ${REMOTE_DIR}/deploy/bootstrap.sh
  2) 需要演示数据时：
     sudo SEED=1 bash ${REMOTE_DIR}/deploy/bootstrap.sh
  3) 上 HTTPS（域名已解析到本机后）：
     sudo certbot --nginx -d ${DOMAIN:-你的域名} -d www.${DOMAIN:-你的域名}
EOF
