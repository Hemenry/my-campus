# GeekCampus 上线状态与运维手册

## 当前状态（2026-10-24）

| 项 | 值 |
|---|---|
| 站点地址 | http://<服务器公网IP> |
| 服务器 | 阿里云 ECS · 华南 1（深圳）· <服务器公网IP> |
| 规格 | 2 vCPU / 2 GiB（ecs.e-c1m1.large）· 40 GiB 盘 · 3 Mbps |
| 系统 | Ubuntu 24.04.5 LTS |
| 组件 | nginx 1.24.0 · Gunicorn 22.0.0（2 worker × 4 线程）· MySQL 8.0.46 |
| 代码目录 | /srv/geekcampus（后端 server/ · 前端 web/dist · 脚本 deploy/） |
| 域名 | 未配置，nginx 目前 `server_name _` |
| HTTPS | 未签，等域名 |

**验证结果**：首页 200 · 静态资源 200 · `/api/health` 返回 `healthy` · `/api/posts` 200 · 数据库 17 张表。

**内存实测**：mysqld 181 MB + gunicorn 72 MB × 2 + 阿里云 agent 约 150 MB，可用 983 MB，另配 2 GiB swap。

---

## 日常运维

```bash
# 服务状态
systemctl status geekcampus nginx mysql --no-pager

# 实时日志（API 与报错都在这里）
journalctl -u geekcampus -f

# Nginx 访问 / 错误日志
tail -f /var/log/nginx/geekcampus.access.log
tail -f /var/log/nginx/geekcampus.error.log

# 健康自检
curl -s http://127.0.0.1/api/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
```

配置与密钥在 `/srv/geekcampus/server/.env`（600，属主 geekcampus），**不要提交到仓库**。

---

## 发版流程

前端必须在本地构建（服务器 2G 内存跑 vite build 会 OOM）。

```bash
# 本地
cd web && npm run build
cd .. && bash deploy/upload.sh --host <服务器公网IP> --user root

# 服务器：备份库 → 跑迁移 → 重启服务
bash /srv/geekcampus/deploy/release.sh
```

前端是静态文件，上传完立即生效，不需要重启服务。

---

## 上域名 + HTTPS

域名需先在阿里云解析（A 记录 `@` 与 `www` → <服务器公网IP>，TTL 600 秒），然后：

```bash
# 写入域名并重载
sed -i -E 's|^\s*server_name _;|    server_name 你的域名 www.你的域名;|' /srv/geekcampus/deploy/nginx.conf
cp /srv/geekcampus/deploy/nginx.conf /etc/nginx/sites-available/geekcampus
nginx -t && systemctl reload nginx

# 签证书
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名 -d www.你的域名

# 必做：确认自动续期可用
certbot renew --dry-run
systemctl list-timers | grep certbot
```

HTTP-01 验证在国内偶发超时，失败时改用 DNS-01（阿里云 DNS 用 `certbot-dns-aliyun` 插件）。

---

## 回滚方案

**回滚代码**（前端 + 后端，不含数据库）：

```bash
# 1) 停服务
systemctl stop geekcampus

# 2) 从备份包恢复（上传脚本每次会在 /tmp 留一份 geekcampus-<时间戳>.tar.gz）
cd / && tar xzf /tmp/geekcampus-<时间戳>.tar.gz -C /srv/geekcampus

# 3) 重启
systemctl start geekcampus && systemctl status geekcampus --no-pager
```

**回滚数据库**：`release.sh` 每次发版会先备份，备份在 `/srv/geekcampus/server/backups/`（或脚本输出路径）。

```bash
# 确认备份位置
ls -lt /srv/geekcampus/server/backups/ | head

# 恢复（会覆盖现有数据，先确认）
mysql -ugeekcampus -p geekcampus < /path/to/backup.sql
```

**最坏情况兜底**：阿里云控制台 → 实例 → 快照回滚，或用 Workbench 登录（走 HTTPS，不受 SSH 端口与安全组影响）。

---

## 上线后的安全检查

| 项 | 状态 | 说明 |
|---|---|---|
| `CORS_ORIGINS` | ✅ 空值 | 禁止所有跨域，同源部署不需要 |
| `SECRET_KEY` / `JWT_SECRET_KEY` | ✅ 随机 32 字节 | 缺失时生产环境直接拒绝启动 |
| MySQL 端口 | ✅ 仅监听 127.0.0.1 | 安全组未放行 3306 |
| Gunicorn 端口 | ✅ 仅监听 127.0.0.1 | 安全组未放行 5001 |
| 登录限流 | ✅ | nginx 10 次/分 + 应用内滑动窗口 |
| SSH 端口 22 | ⚠️ 对全网开放 | 建议在安全组改成只放行你自己的出口 IP |
| 演示账号 | ✅ 未灌 | 若灌了必须改掉 `123456` |
| 数据库备份 | ⚠️ 仅发版时备份 | 建议加个每日 crontab |
