import { defineStore } from 'pinia'
import { ref } from 'vue'
import { noticeApi, statsApi } from '@/api'

export const useAppStore = defineStore('app', () => {
  const unreadCount = ref(0)
  const summary = ref(null)

  async function refreshUnread() {
    try {
      const data = await noticeApi.list({ type: 'all' })
      unreadCount.value = data.unreadCount
      return data
    } catch (err) {
      unreadCount.value = 0
      return { list: [], unreadCount: 0 }
    }
  }

  async function refreshSummary() {
    summary.value = await statsApi.summary()
    unreadCount.value = summary.value.unreadCount
    return summary.value
  }

  function reset() {
    unreadCount.value = 0
    summary.value = null
  }

  return { unreadCount, summary, refreshUnread, refreshSummary, reset }
})
