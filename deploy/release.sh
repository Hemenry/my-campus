#!/usr/bin/env bash
# GeekCampus 发版：备份数据库 → 执行迁移 → 重启服务 → 健康检查
# 用法：sudo bash /srv/geekcampus/deploy/release.sh
# 前端是静态文件，上传到 web/dist 后即生效，不需要重启；本脚本不处理前端。

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/geekcampus}"
APP_USER="${APP_USER:-geekcampus}"
APP_PORT="${APP_PORT:-5001}"
DB_NAME="${DB_NAME:-geekcampus}"
SERVICE="${SERVICE:-geekcampus}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/geekcampus}"
KEEP="${KEEP:-7}"

SERVER_DIR="$APP_DIR/server"
VENV="$SERVER_DIR/.venv"

log()  { printf '\033[32m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m %s\n' "$*" >&2; exit 1; }

trap 'die "第 $LINENO 行出错，已中止（数据库备份在 $BACKUP_DIR）"' ERR

[[ $(id -u) -eq 0 ]] || die "请用 root 运行：sudo bash deploy/release.sh"
[[ -d "$SERVER_DIR" ]] || die "找不到 $SERVER_DIR"

STAMP=$(date '+%Y%m%d-%H%M%S')

# ---------------------------------------------------------------- 1. 备份
log "备份数据库"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
DUMP="$BACKUP_DIR/$DB_NAME-$STAMP.sql.gz"
mysqldump --protocol=socket -uroot \
  --single-transaction --quick --default-character-set=utf8mb4 \
  "$DB_NAME" | gzip > "$DUMP"
echo "    $DUMP ($(du -h "$DUMP" | cut -f1))"

# 只保留最近 N 份
ls -1t "$BACKUP_DIR"/"$DB_NAME"-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "    当前保留 $(ls -1 "$BACKUP_DIR"/"$DB_NAME"-*.sql.gz 2>/dev/null | wc -l) 份"

# ---------------------------------------------------------------- 2. 依赖
log "同步 Python 依赖"
sudo -u "$APP_USER" "$VENV/bin/pip" install -q -r "$SERVER_DIR/requirements.txt"

# ---------------------------------------------------------------- 3. 迁移
log "执行数据库迁移"
cd "$SERVER_DIR"
BEFORE=$(sudo -u "$APP_USER" "$VENV/bin/flask" --app wsgi db current 2>/dev/null | tail -1 || echo "unknown")
sudo -u "$APP_USER" "$VENV/bin/flask" --app wsgi db upgrade
AFTER=$(sudo -u "$APP_USER" "$VENV/bin/flask" --app wsgi db current 2>/dev/null | tail -1 || echo "unknown")
echo "    迁移版本: $BEFORE → $AFTER"

# ---------------------------------------------------------------- 4. 重启
log "重启服务"
systemctl restart "$SERVICE"

# ---------------------------------------------------------------- 5. 健康检查
log "健康检查"
OK=0
for i in $(seq 1 10); do
  sleep 1
  if BODY=$(curl -fsS --max-time 3 "http://127.0.0.1:$APP_PORT/api/health" 2>/dev/null); then
    OK=1
    echo "    $BODY"
    break
  fi
done

if [[ $OK -ne 1 ]]; then
  printf '\033[31m健康检查失败\033[0m\n'
  echo "最近日志："
  journalctl -u "$SERVICE" -n 40 --no-pager || true
  echo
  echo "回滚思路："
  echo "  1) 代码回退到上一个提交/版本"
  echo "  2) 如需回退表结构：sudo -u $APP_USER $VENV/bin/flask --app wsgi db downgrade -1（不带 revision 会报错，-1 表示回退一步，也可指定具体版本号）"
  echo "  3) 极端情况用备份恢复：zcat $DUMP | sudo mysql $DB_NAME"
  exit 1
fi

log "发版完成（$STAMP）"
echo "    日志：journalctl -u $SERVICE -f"
