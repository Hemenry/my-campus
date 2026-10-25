// 迁移自原 miniprogram/utils/format 测试（miniprogram/ 已删除）。
// 等价断言落到 web/src/utils/format.js —— 前端当前唯一保留的纯函数工具模块。
// 运行：node --test（仓库根目录自动发现）
//      或 node --test "tests/**"
// 注意：`node --test tests/` 会把目录参数当模块加载而报错，别用这种写法。
import { test } from 'node:test';
import assert from 'node:assert';
import {
  parseServerDate,
  timeAgo,
  formatDate,
  excerpt,
  weekdayLabel,
  greeting
} from '../web/src/utils/format.js';

test('parseServerDate 无时区信息的字符串按 UTC 解析', () => {
  const date = parseServerDate('2026-10-21T08:00:00');
  assert.strictEqual(date.toISOString(), '2026-10-21T08:00:00.000Z');
});

test('parseServerDate 带时区后缀时原样解析', () => {
  const date = parseServerDate('2026-10-21T08:00:00+08:00');
  assert.strictEqual(date.toISOString(), '2026-10-21T00:00:00.000Z');
});

test('parseServerDate 空值返回 null', () => {
  assert.strictEqual(parseServerDate(''), null);
  assert.strictEqual(parseServerDate(null), null);
});

test('timeAgo 一分钟内为刚刚', () => {
  assert.strictEqual(timeAgo(new Date().toISOString()), '刚刚');
});

test('timeAgo 分钟级', () => {
  const value = new Date(Date.now() - 12 * 60 * 1000).toISOString();
  assert.strictEqual(timeAgo(value), '12 分钟前');
});

test('timeAgo 小时级', () => {
  const value = new Date(Date.now() - 3 * 3600 * 1000).toISOString();
  assert.strictEqual(timeAgo(value), '3 小时前');
});

test('timeAgo 天级', () => {
  const value = new Date(Date.now() - 2 * 24 * 3600 * 1000).toISOString();
  assert.strictEqual(timeAgo(value), '2 天前');
});

test('timeAgo 非法输入返回空串', () => {
  assert.strictEqual(timeAgo('not-a-date'), '');
});

test('excerpt 超长文本截断并加省略号', () => {
  const text = 'a'.repeat(120);
  const out = excerpt(text, 96);
  assert.strictEqual(out, `${'a'.repeat(96)}…`);
});

test('excerpt 不足长度原文返回并压缩空白', () => {
  assert.strictEqual(excerpt('  hello   world  '), 'hello world');
});

test('formatDate 输出月日时分', () => {
  const out = formatDate('2026-10-21T08:05:00');
  assert.ok(out.includes('10'));
  assert.ok(out.includes('21'));
});

test('weekdayLabel 星期映射', () => {
  assert.strictEqual(weekdayLabel(new Date('2026-10-21T00:00:00')), '周三');
});

test('greeting 按小时分段', () => {
  assert.strictEqual(greeting(5), '夜深了');
  assert.strictEqual(greeting(8), '早上好');
  assert.strictEqual(greeting(12), '中午好');
  assert.strictEqual(greeting(15), '下午好');
  assert.strictEqual(greeting(20), '晚上好');
});
