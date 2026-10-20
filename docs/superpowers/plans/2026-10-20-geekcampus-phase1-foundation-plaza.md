# GeekCampus 第一阶段实现计划：基础设施 + 广场模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可运行的小程序骨架，完成设计 token 落地、统一请求层与状态层、8 个公共组件，以及可交互的广场首页（T1-01）与其四态。

**Architecture:** 微信小程序原生四 tab 工程。样式统一从 `styles/tokens.wxss` 取 CSS 变量，页面不写裸色值；所有网络请求走 `utils/request.js` 单点封装；跨页状态走 `utils/store.js` 的轻量订阅式 store（不引入 npm 依赖，接口与 mobx 等价，后续可替换）；纯逻辑模块用 Node 内置 `node --test` 覆盖。

**Tech Stack:** 微信小程序原生（WXML / WXSS / JS）、Node 22 内置测试运行器（零依赖）、CSS 变量。

**Spec:** `docs/superpowers/specs/2026-10-20-geekcampus-design.md`

## Global Constraints

- 主色只用 `--brand-600: #1F8A6B`；主色在单屏出现不超过 3 处，且必须对应主操作或选中态。
- 页面左右安全边距固定 16px（32rpx）；1px = 2rpx 换算。
- 页面与组件禁止出现裸色值、裸字号，一律引用 `styles/tokens.wxss` 的变量。
- 页面禁止直接调用 `wx.request`，只能经 `utils/request.js`。
- 跨页共享状态只走 `store/`，禁止 `getApp().globalData`。
- 所有列表必须实现「加载中 / 成功 / 空 / 失败」四态，不允许白屏。
- 可点区域不小于 44×44（88rpx）。
- `--text-3` 只用于占位与禁用，不承载信息。
- 颜色不作为唯一信息载体（状态必须带文字）。

## Review Focus

- **空列表**：广场五个分类都为空时，必须显示对应文案与一个明确动作，而不是空白容器。
- **长文本**：标题超 2 行、摘要超 2 行、回答超 3 行时，必须截断并给「展开」，卡片高度不能撑破列表。
- **弱网与失败**：任一请求失败时列表区显示行内重试，不弹全局错误、不白屏。
- **重复点击**：点赞 / 收藏 / 发布按钮必须防重，连续点击不能产生多条记录。
- **无图与图片加载失败**：内容卡无图时不出现空白占位；图片加载失败显示灰底占位块。

---

### Task 1: 工程骨架与设计 token

**Files:**
- Create: `miniprogram/project.config.json`
- Create: `miniprogram/app.js`
- Create: `miniprogram/app.json`
- Create: `miniprogram/app.wxss`
- Create: `miniprogram/sitemap.json`
- Create: `miniprogram/styles/tokens.wxss`
- Create: `miniprogram/pages/english/index.*`、`miniprogram/pages/message/index.*`、`miniprogram/pages/mine/index.*`（占位页，保证四 tab 可启动）

**Interfaces:**
- Produces: 全局 CSS 变量（`--brand-600`、`--bg`、`--surface`、`--text-1/2/3`、`--border`、`--radius-*`、`--shadow-card`、`--space-*`、字号变量 `--fs-*`）

- [ ] **Step 1:** 建立 `app.json`，注册 4 个 tab（广场 / 英语 / 消息 / 我的），tabBar 选中色 `#1F8A6B`、未选中 `#9AA6A1`。
- [ ] **Step 2:** 写 `styles/tokens.wxss`，按 Spec 第 5 章逐条落成 CSS 变量，挂在 `page{}` 上。
- [ ] **Step 3:** `app.wxss` 引入 tokens 并写全局基线（page 底色 `--bg`、字体栈、`box-sizing: border-box`）。
- [ ] **Step 4:** 启动验证：开发者工具打开工程，四个 tab 可切换且不报错。
- [ ] **Step 5:** Commit。

### Task 2: 工具层（请求 / 存储 / 格式化）

**Files:**
- Create: `miniprogram/utils/format.js`
- Create: `miniprogram/utils/storage.js`
- Create: `miniprogram/utils/request.js`
- Test: `tests/format.test.js`、`tests/request.test.js`

**Interfaces:**
- Produces:
  - `formatRelativeTime(ts: number, now?: number): string` → 「刚刚」「12 分钟前」「3 小时前」「昨天」「10-18」
  - `formatCount(n: number): string` → `999` / `1.2k` / `1.2w`
  - `truncate(text: string, max: number): string`
  - `storage.get(key, fallback)` / `storage.set(key, value)` / `storage.remove(key)`
  - `request({ url, method, data, needAuth }): Promise<any>`，失败抛 `{ code, message }`

- [ ] **Step 1: 写失败测试** —— `tests/format.test.js` 覆盖边界：

```js
const test = require('node:test');
const assert = require('node:assert');
const { formatRelativeTime, formatCount, truncate } = require('../miniprogram/utils/format');

test('formatRelativeTime 一分钟内为刚刚', () => {
  assert.strictEqual(formatRelativeTime(1000, 1000 + 59 * 1000), '刚刚');
});
test('formatRelativeTime 分钟级', () => {
  assert.strictEqual(formatRelativeTime(0, 12 * 60 * 1000), '12 分钟前');
});
test('formatRelativeTime 超过 7 天回落到日期', () => {
  const now = new Date('2026-10-20T12:00:00').getTime();
  const ts = new Date('2026-10-01T12:00:00').getTime();
  assert.strictEqual(formatRelativeTime(ts, now), '10-01');
});
test('formatCount 千位与万位', () => {
  assert.strictEqual(formatCount(999), '999');
  assert.strictEqual(formatCount(1200), '1.2k');
  assert.strictEqual(formatCount(12000), '1.2w');
});
test('truncate 不超长时原样返回', () => {
  assert.strictEqual(truncate('高数极限', 10), '高数极限');
});
test('truncate 超长时补省略号且长度为 max', () => {
  assert.strictEqual(truncate('一二三四五六七八九十', 5), '一二三四五…');
});
```

- [ ] **Step 2: 跑测试确认失败** —— `node --test tests/format.test.js`，预期 `Cannot find module`。
- [ ] **Step 3: 实现 format.js**（纯函数，无 wx API 依赖，保证可在 Node 下测试）。
- [ ] **Step 4: 跑测试确认通过**。
- [ ] **Step 5: 写请求层失败测试** —— 用注入的 `transport` 替身覆盖三种情况：业务码非 0 抛错、401 触发一次续期重放、超时抛 `{code:'TIMEOUT'}`。
- [ ] **Step 6: 实现 request.js**（8s 超时、登录态注入、错误归一、401 重放一次、并发同 key 合并）。
- [ ] **Step 7: 跑全部测试** —— `node --test tests/`。
- [ ] **Step 8: Commit。**

### Task 3: 状态层

**Files:**
- Create: `miniprogram/utils/store.js`
- Create: `miniprogram/store/user.js`
- Create: `miniprogram/store/plaza.js`
- Test: `tests/store.test.js`

**Interfaces:**
- Produces:
  - `createStore(initialState)` → `{ getState(), setState(patch), subscribe(fn) => unsubscribe, bind(page)`，其中 `bind(page)` 自动把 state 合进 `page.data` 并在变更时 `setData`，`unsubscribe` 在 `onUnload` 调用
  - `userStore`：`{ profile, isLogin }`，`login()`、`logout()`、`restore()`
  - `plazaStore`：`{ feed, category, loading, error, hasMore, page }`，`loadFeed({ reset })`、`setCategory(c)`、`toggleLike(id)`、`toggleCollect(id)`

- [ ] **Step 1: 写失败测试** —— 覆盖：`setState` 只通知变化的键、`subscribe` 返回的 unsub 生效、`toggleLike` 幂等（同一 id 连点两次回到初始）、`setCategory` 切换后 `page` 归 1。
- [ ] **Step 2: 跑测试确认失败**。
- [ ] **Step 3: 实现 store.js**（核心是浅比较 + 通知，`bind` 依赖 wx.setData，实现时对它做存在性守卫以便 Node 下测试）。
- [ ] **Step 4: 实现 user/plaza store**。
- [ ] **Step 5: 跑测试确认通过**。
- [ ] **Step 6: Commit。**

### Task 4: 基础组件

**Files:**
- Create: `miniprogram/components/nav-bar/*`
- Create: `miniprogram/components/search-bar/*`
- Create: `miniprogram/components/quick-grid/*`
- Create: `miniprogram/components/segment-tabs/*`
- Create: `miniprogram/components/empty-state/*`
- Create: `miniprogram/components/skeleton-card/*`

**Interfaces:**
- `nav-bar`: props `brandName`、`school`、`unread`；event `tap-notify`、`tap-school`
- `search-bar`: props `placeholder`、`value`、`readonly`；event `confirm`、`tap`
- `quick-grid`: props `items: [{key,label,icon,color}]`；event `select` → `{ key }`
- `segment-tabs`: props `items: string[]`、`active: number`；event `change` → `{ index }`
- `empty-state`: props `title`、`desc`、`actionText`；event `action`
- `skeleton-card`: props `rows`（默认 3）

- [ ] **Step 1:** 逐个实现 6 个组件，样式全部引用 token 变量。
- [ ] **Step 2:** 每个组件在 `pages/plaza` 挂一次做视觉自检（用开发者工具或预览快照）。
- [ ] **Step 3:** 检查 44×44 最小点击区与 `--text-3` 使用合规。
- [ ] **Step 4:** Commit。

### Task 5: 广场首页 T1-01

**Files:**
- Create: `miniprogram/pages/plaza/index.js|json|wxml|wxss`
- Create: `miniprogram/components/today-card/*`
- Create: `miniprogram/components/post-card/*`
- Create: `miniprogram/mock/plaza.js`

**Interfaces:**
- Consumes: `plazaStore`、`userStore`、`formatRelativeTime`、`formatCount`
- `today-card`: props `pending`、`streak`、`finished`；event `start`
- `post-card`: props `post`；events `tap`、`like`、`collect`

- [ ] **Step 1:** 用 mock 数据实现首屏结构：品牌栏 → 问候语 → 搜索框 → 四宫格 → 今日学习卡 → 区块标题 → 分类 tab → 内容流。
- [ ] **Step 2:** 接入 `plazaStore`，实现下拉刷新、上拉加载、分类切换、点赞收藏本地乐观更新 + 防重。
- [ ] **Step 3:** 实现四态：骨架屏（首次）、空态（分类无内容）、失败（行内重试）、成功。
- [ ] **Step 4:** 长文本截断：标题 2 行、摘要 2 行、多图角标「共 N 张」。
- [ ] **Step 5:** 未登录点赞/收藏拉起授权提示，不跳页。
- [ ] **Step 6:** 视觉自检：主色出现次数、卡片间距 12px、标题重字重、对比度。
- [ ] **Step 7:** Commit。

### Task 6: 浏览器预览快照（视觉验收用）

**Files:**
- Create: `preview/plaza.html`

**说明:** 微信开发者工具不在本环境内，本任务用同一套 token 变量生成广场首页的静态 HTML 快照（手机外框 375×812），供快速视觉验收与后续比对；它不是第二套实现，仅作预览，改样式时同步改这份即可。

- [ ] **Step 1:** 生成快照，逐项比对 Spec 5.7 的今日学习卡细则与内容卡细则。
- [ ] **Step 2:** 修正偏差（字号、圆角、底色、图标底块）。
- [ ] **Step 3:** Commit。

---

## 后续阶段（不在本计划内）

- 第二阶段：广场二级页（内容详情、写回答、发布三类、资料预览）。
- 第三阶段：英语模块（PDF 导入、识别校对、背诵卡、结果页、日历）。
- 第四阶段：消息与我的（12 页 + 2 页）。
- 第五阶段：全局页（登录、搜索、他人主页、状态页）与真机联调。
