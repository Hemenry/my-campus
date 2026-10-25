# GeekCampus 部署手册（Ubuntu 24.04 + Nginx + Gunicorn + MySQL 8）

面向：一台 2C2G 的 Ubuntu 24.04 ECS，部署 `server/`（Flask API）+ `web/dist`（Vue 静态站）。

> 这些脚本按 Ubuntu 24.04 写，做过 `bash -n` 语法检查，但**没有在真实 Linux 上跑过**。
> 首次部署请照「检查点」逐条确认，别一路盲目往下敲。

---

## 0. 架构

```
浏览器
  │
  ▼
Nginx :80/:443   ──  /            → /srv/geekcampus/web/dist （静态，history 回退 index.html）
  │                 /api/、/uploads/ → 反代 127.0.0.1:5001
  ▼
Gunicorn（2 worker）→ Flask 应用（systemd 守护，用户 geekcampus）
  ▼
MySQL 8（本机 3306，仅监听 127.0.0.1）
```

安全组只开 **22 / 80 / 443**。3306、5001 一律不对外。

---

## 1. 上传代码

在服务器上：

```bash
sudo mkdir -p /srv/geekcampus && sudo chown $USER:$USER /srv/geekcampus
# 方式一：git
git clone <你的仓库> /srv/geekcampus
# 方式二：本地 scp / rsync（推荐，见第 3 步）
```

## 2. 服务器初始化（只跑一次）

```bash
sudo bash deploy/setup.sh
```

它会做：装 nginx / mysql-server / python3-venv / git → 建 `geekcampus` 系统用户 →
建数据库与专用账号（随机密码）→ 建 venv 装依赖 → 生成 `.env`（随机 SECRET_KEY / JWT_SECRET_KEY）
→ 写 MySQL 内存调参 → 跑 Alembic 迁移。

跑之前先看一眼脚本里的这几个变量，按需改：

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_DIR` | `/srv/geekcampus` | 代码目录 |
| `APP_USER` | `geekcampus` | 跑应用的系统用户 |
| `DB_NAME` | `geekcampus` | 数据库名 |
| `DB_USER` | `geekcampus` | 数据库账号（不是 root） |
| `APP_PORT` | `5001` | Gunicorn 监听（避开 5000，防止与别的服务撞） |

**检查点**

```bash
sudo -u geekcampus /srv/geekcampus/server/.venv/bin/pip list | grep -i flask
sudo mysql -e "SHOW DATABASES LIKE 'geekcampus';"
sudo -u geekcampus cat /srv/geekcampus/server/.env | head -5
```

`.env` 应该是 600 权限、属主 `geekcampus`。

## 3. 前端构建（在本地 Windows 上做，不要在服务器上 build）

2G 内存跑 `vite build` 很容易 OOM，本地构建再上传最省事：

```bash
# 本地
cd web
npm ci
npm run build            # 产出 web/dist

# 上传（Windows 用 scp，或 rsync）
scp -r web/dist/* root@<服务器IP>:/srv/geekcampus/web/dist/
```

`web/src/api/http.js` 里 `baseURL: '/api'` 是相对路径，所以不需要配域名，Nginx 反代即可。

**检查点**：`ls /srv/geekcampus/web/dist/index.html` 存在。

## 4. 跑起来

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/geekcampus.service
sudo systemctl daemon-reload
sudo systemctl enable --now geekcampus
sudo systemctl status geekcampus --no-pager

sudo cp deploy/nginx.conf /etc/nginx/sites-available/geekcampus
sudo ln -sf /etc/nginx/sites-available/geekcampus /etc/nginx/sites-enabled/geekcampus
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

**检查点**

```bash
curl -s http://127.0.0.1:5001/api/health      # {"code":0,...,"status":"healthy","database":"geekcampus"}
curl -sI http://127.0.0.1/ | head -3          # 200，text/html
curl -s http://127.0.0.1/api/posts?page=1 | head -c 200
```

三个都通，再用浏览器打开 `http://<公网IP>`。

## 5. 演示数据（可选）

```bash
cd /srv/geekcampus/server
sudo -u geekcampus .venv/bin/python seed.py            # 首次灌演示数据
# sudo -u geekcampus .venv/bin/python seed.py --force  # 清空重灌，慎用
```

演示账号：`linyizhou / 123456`。**上线前要么改密码，要么别灌演示数据。**

## 6. 以后发版

```bash
# 本地
cd web && npm run build
scp -r web/dist/* root@<IP>:/srv/geekcampus/web/dist/

# 服务器
sudo bash /srv/geekcampus/deploy/release.sh
```

`release.sh` 做三件事：备份数据库 → `flask db upgrade` → 重启服务。前端是静态文件，上传完即生效，不用重启。

## 7. 上域名 + HTTPS（可选）

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

国内服务器绑域名走 80/443 需要先备案；只用 IP 访问不需要。

---

## 已知待加固（部署前建议处理）

| 项 | 现状 | 建议 |
|---|---|---|
| CORS | 已改为读 `CORS_ORIGINS` 环境变量 | 同源部署不用配；`setup.sh` 会写成空值（禁所有跨域），跨站部署时改成 `https://你的域名` |
| 默认密钥 | `config.py` 有 `geekcampus-dev-secret` 兜底 | 已处理：非 debug 模式下缺 `SECRET_KEY`/`JWT_SECRET_KEY` 直接启动失败，`.env` 由 `setup.sh` 生成随机值 |
| 演示账号密码 | `123456` | 上线前改掉或删掉演示账号 |
| 上传目录 | `server/uploads` 由 Flask 直出 | 量大后可交给 Nginx `alias`，省一次反代 |
| 日志 | 走 journald | `journalctl -u geekcampus -f` 查；长期可加 logrotate |

## 常见问题

**502 Bad Gateway** — Gunicorn 没起来。`sudo journalctl -u geekcampus -n 50 --no-pager` 看报错，九成是 `.env` 里数据库密码不对或迁移没跑。

**`nginx -t` 报 `duplicate default server`** — `sites-enabled/default` 没删。

**页面能开但接口 404** — Nginx 的 `location /api/` 少了结尾斜杠，或 `proxy_pass` 写成了带 URI 的形式导致路径被截断。本仓库的配置是原样透传，不要改。

**上传图片报 413** — 后端限 8MB，Nginx 的 `client_max_body_size` 已设 10m；如果调大了后端限制，记得同步改这里。

**内存吃紧** — `free -h` 看 available，`systemctl status` 看 gunicorn 内存。2 个 worker 是刻意压低的，别随手改 4 个。
