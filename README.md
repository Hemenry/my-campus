# GeekCampus 校园学习互助

把「记录 → 求助 → 沉淀 → 复习」串成一条闭环的校园学习工具。仓库里现在有一套 Web 客户端和一套后端：

| 目录 | 内容 | 技术栈 |
|---|---|---|
| `server/` | 后端 API + 数据库 | Flask 3 + SQLAlchemy 2 + Alembic + PyMySQL + MySQL 8 |
| `web/` | Web 客户端（手机壳布局，桌面端带左侧闭环导航） | Vue 3 + Vite + Vue Router + Pinia + Axios |
| `docs/` | 设计规范、接口清单与实施计划 | — |

`web/` 完整复刻了早期 H5 原型的布局与视觉：直接沿用原型的设计规范（`web/src/styles/app.css`，主色 `#1F8A6B` / 深色 `#0E5C46`），页面结构、字号与栅格与原 H5 一致 —— 430px 手机壳、底部四 tab、桌面端左侧「记录 → 求助 → 沉淀 → 复习」闭环栏。原来的零依赖 H5 演示版本已移除。

## 快速启动

### 1. 数据库

需要一个可用的 MySQL 8 实例，先建库：

```sql
CREATE DATABASE geekcampus DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 后端

```bash
cd server
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
copy .env.example .env                             # 填入本机 MySQL 账号密码
.venv\Scripts\flask --app wsgi db upgrade           # 建表
.venv\Scripts\python seed.py                        # 写入演示数据
.venv\Scripts\python wsgi.py                        # http://127.0.0.1:5000
```

演示账号：`linyizhou / 123456`（其余演示账号密码相同）。`python seed.py --force` 会清空重灌。

### 3. 前端

```bash
cd web
npm install
npm run dev        # http://127.0.0.1:5173
```

Vite 已把 `/api` 与 `/uploads` 代理到 `127.0.0.1:5000`，前后端分别启动即可。生产构建：`npm run build`。

### 4. 测试

```bash
node --test                 # 前端纯函数测试（tests/*.test.mjs，仓库根目录执行）
cd server && python -m unittest discover -s tests -v   # 后端 API 回归（SQLite 内存库，不需要 MySQL）
```

## 功能范围

- **广场**：五个分类（推荐 / 求助 / 错题 / 资料 / 试卷）、关键词与排序（最新 / 最热 / 待回答）、分页加载、点赞与收藏（幂等切换）、详情页回答与采纳、评论。
- **英语**：词书列表与进度、创建词书（`单词 | 释义` 批量粘贴）、复习队列（按到期时间取词）、翻卡复习、提交后自动计算掌握状态与下次复习时间、打卡日历与连续天数、学习计划进度。
- **消息**：按回答 / 评论 / 采纳 / 系统分类，未读计数与全部已读，点击跳转对应帖子。
- **我的**：数据概览、我的发布 / 收藏 / 错题本，错题掌握状态三档切换，资料编辑。

## 数据库表

共 17 张表，与 `docs/superpowers/specs/2026-10-20-geekcampus-design.md` 第 6 节一一对应：

`users`、`posts`、`answers`、`answer_likes`、`comments`、`tags`、`post_tags`、`post_likes`、`collections`、`materials`、`mistakes`、`wordbooks`、`word_entries`、`review_records`、`checkins`、`notifications`、`plans`

关键约束：`checkins(user_id, date)` 唯一 → 一天一条不叠加；`collections(user_id, target_type, target_id)` 唯一 → 收藏幂等；`post_likes` / `answer_likes` 唯一 → 点赞幂等；采纳答案时同帖其余回答自动置否。

## 接口约定

- 统一前缀 `/api`，响应体 `{ "code": 0, "message": "ok", "data": ... }`；出错时 `code` 为 HTTP 或业务码，`message` 可直接展示。
- 鉴权用 JWT，请求头 `Authorization: Bearer <token>`，token 存 `localStorage`，401 时前端自动清理并跳登录。
- 分页参数 `page` / `pageSize`，返回 `{ list, total, page, pageSize, hasMore }`。

完整接口清单见 [`docs/api.md`](docs/api.md)。

## 已知边界

- 上传文件落本地 `server/uploads/`，生产环境需替换为对象存储。
- 复习算法是「认识 → 1/2/7 天递进，不认识 → 6 小时后重来」的简化 SRS，未引入完整 SM-2 参数。
- 消息推送为站内拉取，没有 WebSocket 或订阅消息。
