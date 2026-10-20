const test = require('node:test');
const assert = require('node:assert');
const {
  formatRelativeTime,
  formatCount,
  truncate
} = require('../miniprogram/utils/format');

test('formatRelativeTime 一分钟内为刚刚', () => {
  assert.strictEqual(formatRelativeTime(1000, 1000 + 59 * 1000), '刚刚');
});

test('formatRelativeTime 分钟级', () => {
  assert.strictEqual(formatRelativeTime(0, 12 * 60 * 1000), '12 分钟前');
});

test('formatRelativeTime 小时级', () => {
  assert.strictEqual(formatRelativeTime(0, 3 * 3600 * 1000), '3 小时前');
});

test('formatRelativeTime 昨天', () => {
  const now = new Date('2026-10-20T12:00:00').getTime();
  const ts = new Date('2026-10-19T09:00:00').getTime();
  assert.strictEqual(formatRelativeTime(ts, now), '昨天');
});

test('formatRelativeTime 超过 7 天回落到日期', () => {
  const now = new Date('2026-10-20T12:00:00').getTime();
  const ts = new Date('2026-10-01T12:00:00').getTime();
  assert.strictEqual(formatRelativeTime(ts, now), '10-01');
});

test('formatRelativeTime 未来时间不返回负数', () => {
  assert.strictEqual(formatRelativeTime(10000, 5000), '刚刚');
});

test('formatCount 千位与万位', () => {
  assert.strictEqual(formatCount(0), '0');
  assert.strictEqual(formatCount(999), '999');
  assert.strictEqual(formatCount(1200), '1.2k');
  assert.strictEqual(formatCount(12000), '1.2w');
});

test('formatCount 整数千位不带多余小数', () => {
  assert.strictEqual(formatCount(2000), '2k');
});

test('truncate 不超长时原样返回', () => {
  assert.strictEqual(truncate('高数极限', 10), '高数极限');
});

test('truncate 超长时截断并补省略号', () => {
  assert.strictEqual(truncate('一二三四五六七八九十', 5), '一二三四五…');
});

test('truncate 空值返回空串', () => {
  assert.strictEqual(truncate(null, 5), '');
  assert.strictEqual(truncate(undefined, 5), '');
});
