export function parseServerDate(value) {
  if (!value) return null
  const hasZone = /Z$|[+-]\d{2}:\d{2}$/.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

export function timeAgo(value) {
  const date = parseServerDate(value)
  if (!date || Number.isNaN(date.getTime())) return ''
  const diff = Date.now() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < day * 7) return `${Math.floor(diff / day)} 天前`
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

export function formatDate(value) {
  const date = parseServerDate(value)
  if (!date) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function excerpt(text, len = 96) {
  const plain = String(text || '').replace(/\s+/g, ' ').trim()
  return plain.length > len ? `${plain.slice(0, len)}…` : plain
}

export function weekdayLabel(date) {
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

export function greeting(hour = new Date().getHours()) {
  if (hour < 6) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 13) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}
