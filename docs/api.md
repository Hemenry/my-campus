# GeekCampus API 清单

统一前缀 `/api`，响应体固定为 `{ code, message, data }`；需要登录的接口带 `Authorization: Bearer <token>`。
表中「🔒」表示需要登录。

## 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册，body：`username` `password` `nickname?`，返回 token + user |
| POST | `/auth/login` | 登录，body：`username` `password` |
| GET | `/auth/me` | 🔒 当前用户 |
| PATCH | `/auth/me` | 🔒 修改昵称 / 头像 / 学校 / 院系 / 年级 / 简介 |

## 广场

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/posts` | 列表，query：`category`(推荐/求助/错题/资料/试卷)、`sort`(latest/hot/unanswered)、`keyword`、`subject`、`page`、`pageSize` |
| GET | `/posts/:id` | 详情，含 `answers`、`comments`、`isLiked`、`isCollected`、`isOwner`，同时累加浏览量 |
| POST | `/posts` | 🔒 发布，body：`type` `title` `content` `images[]` `subject` `topics[]` `visibility` |
| DELETE | `/posts/:id` | 🔒 下架自己的内容（软删除 `status=offline`，同时清理收藏关系） |
| POST | `/posts/:id/like` | 🔒 点赞开关，返回 `{ liked, likeCount }` |
| POST | `/posts/:id/collect` | 🔒 收藏开关，返回 `{ collected, collectCount }` |
| POST | `/posts/:id/answers` | 🔒 回答（不能回答自己的帖子），给作者产生通知 |
| POST | `/answers/:id/like` | 🔒 回答点赞开关 |
| POST | `/answers/:id/adopt` | 🔒 采纳（仅提问者，且整帖只能采纳一条；被采纳者 `adopted_count +1`） |

## 评论

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/comments?targetType=post&targetId=1` | 评论列表 |
| POST | `/comments` | 🔒 发表评论，`targetType` 为 `post`/`answer`，支持 `parentId` |
| DELETE | `/comments/:id` | 🔒 删除自己的评论 |

## 英语

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/wordbooks` | 🔒 我的词书，含 `dueCount` |
| POST | `/wordbooks` | 🔒 创建词书，`text` 支持 `单词 | 释义` 逐行粘贴 |
| GET | `/wordbooks/:id` | 🔒 词书详情（含 `entries`） |
| PATCH | `/wordbooks/:id` | 🔒 改名称 / 描述 |
| DELETE | `/wordbooks/:id` | 🔒 删除词书（级联词条） |
| GET | `/wordbooks/:id/review?size=20` | 🔒 复习队列：优先到期词，不足时补未掌握词 |
| POST | `/wordbooks/:id/review` | 🔒 提交复习，body：`results:[{entryId, known}]` `durationSeconds`；返回本词书进度、打卡、连续天数 |
| GET | `/checkins?year=&month=` | 🔒 当月打卡日历 |
| POST | `/checkins` | 🔒 手动打卡（复习提交时也会自动打卡） |
| GET | `/plans` / POST `/plans` / PATCH `/plans/:id` | 🔒 学习计划 |

## 错题本

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/mistakes?mastery=&keyword=&page=` | 🔒 错题分页 |
| POST | `/mistakes` | 🔒 录入，`prompt` `reason` `answer` `knowledgePoint` `mastery` |
| PATCH | `/mistakes/:id` | 🔒 修改内容或掌握状态（0 未掌握 / 1 复习中 / 2 已掌握） |
| DELETE | `/mistakes/:id` | 🔒 删除 |

## 消息

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/notifications?type=all|answer|comment|adopt|system&unread=1` | 🔒 通知列表 + 未读数 |
| POST | `/notifications/read` | 🔒 标记已读，body：`ids: []`，不传则全部已读 |

## 个人与统计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/users/:id` | 公开主页与计数 |
| GET | `/stats/summary` | 🔒 我的概览：发布 / 回答 / 采纳 / 错题 / 收藏 / 待复习 / 本周复习 / 连续打卡 / 未读 |
| GET | `/me/posts` | 🔒 我的发布 |
| GET | `/me/collections` | 🔒 我的收藏（自动过滤已下架内容） |

## 文件

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/uploads` | 🔒 multipart `file`，返回 `{ url: "/uploads/xxx.png" }`，限制 png/jpg/jpeg/gif/webp/pdf，单文件 8MB |
| GET | `/uploads/:filename` | 静态访问已上传文件 |

## 复习算法

提交复习时逐词处理：

- 认识：`new → learning`，下次 +1 天；`learning` 且复习次数 ≥2 → `mastered`，下次 +7 天；否则 +2 天。
- 不认识：置为 `learning`，下次 +6 小时。
- 每次提交写一条 `review_records`，并按 `(user_id, date)` 累加当天打卡词数；连续天数按日期倒序回溯计算，同步写回 `users.streak_days`。
