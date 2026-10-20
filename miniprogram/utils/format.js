/**
 * 纯函数格式化工具。不依赖任何 wx API，因此可在 Node 下直接测试。
 */

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

function pad2(n) {
  return n < 10 ? '0' + n : String(n);
}

/**
 * 相对时间：刚刚 / N 分钟前 / N 小时前 / 昨天 / N 天前 / MM-DD
 * @param {number} ts 目标时间戳
 * @param {number} [now] 当前时间戳，测试可注入
 */
function formatRelativeTime(ts, now) {
  if (ts === null || ts === undefined) return '';
  const current = now === undefined ? Date.now() : now;
  const diff = current - ts;

  // 未来时间或 1 分钟内，统一视为刚刚，避免出现负数
  if (diff < MINUTE) return '刚刚';
  if (diff < HOUR) return Math.floor(diff / MINUTE) + ' 分钟前';
  if (diff < DAY) return Math.floor(diff / HOUR) + ' 小时前';

  const target = new Date(ts);
  const today = new Date(current);
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOfDay(today) - startOfDay(target)) / DAY);

  if (dayDiff === 1) return '昨天';
  if (dayDiff > 1 && dayDiff < 7) return dayDiff + ' 天前';
  return pad2(target.getMonth() + 1) + '-' + pad2(target.getDate());
}

/**
 * 计数缩写：999 / 1.2k / 1.2w
 */
function formatCount(n) {
  const num = Number(n) || 0;
  if (num < 1000) return String(num);
  const strip = (v) => String(Number(v.toFixed(1)));
  if (num < 10000) return strip(num / 1000) + 'k';
  return strip(num / 10000) + 'w';
}

/**
 * 按字符数截断，超长补省略号
 */
function truncate(text, max) {
  if (text === null || text === undefined) return '';
  const str = String(text);
  if (str.length <= max) return str;
  return str.slice(0, max) + '…';
}

module.exports = {
  formatRelativeTime,
  formatCount,
  truncate
};
