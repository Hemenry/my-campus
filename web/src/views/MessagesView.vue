<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { noticeApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import { timeAgo } from '@/utils/format'

const router = useRouter()
const appStore = useAppStore()

const tabs = ['全部', '回答', '评论', '采纳', '系统']
const MAP = { 回答: 'answer', 评论: 'comment', 采纳: 'adopt', 系统: 'system' }

const activeTab = ref('全部')
const list = ref([])
const unread = ref(0)
const loading = ref(true)

const filtered = computed(() =>
  activeTab.value === '全部' ? list.value : list.value.filter((item) => item.type === MAP[activeTab.value])
)

async function load() {
  loading.value = true
  try {
    const data = await noticeApi.list({ type: 'all' })
    list.value = data.list
    unread.value = data.unreadCount
    appStore.unreadCount = data.unreadCount
  } finally {
    loading.value = false
  }
}

async function markAll() {
  const ids = list.value.filter((item) => !item.isRead).map((item) => item.id)
  if (!ids.length) return
  await noticeApi.read(ids)
  toast('已全部标为已读')
  await load()
}

async function open(notice) {
  if (!notice.isRead) {
    await noticeApi.read([notice.id])
    notice.isRead = true
    unread.value = Math.max(0, unread.value - 1)
    appStore.unreadCount = unread.value
  }
  if (notice.targetType === 'post' && notice.targetId) {
    router.push(`/detail/${notice.targetId}`)
  }
}

onMounted(load)
</script>

<template>
  <header class="topbar">
    <div class="topbar__row">
      <div class="brand__name" style="font-size: 19px; letter-spacing: -0.4px">
        消息
        <span v-if="unread" class="countbadge">{{ unread }}</span>
      </div>
      <button class="textbtn" @click="markAll">全部已读</button>
    </div>
  </header>

  <div class="pad">
    <div class="segs" style="margin-top: 2px">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="seg"
        :class="{ 'is-on': activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </div>
  </div>

  <div style="margin-top: 6px">
    <div v-for="notice in filtered" :key="notice.id" class="msg" @click="open(notice)">
      <div class="msg__ava">
        <div
          v-if="notice.type === 'system'"
          class="msg__thumb"
          style="background: var(--brand-100); color: var(--brand-700)"
        >
          <Icon name="i-trend" cls="ico--sm" />
        </div>
        <div v-else class="avatar avatar--lg">{{ (notice.actor?.nickname || '!').charAt(0) }}</div>
        <span v-if="!notice.isRead" class="msg__un"></span>
      </div>
      <div class="msg__body">
        <div class="msg__t">
          <b v-if="notice.actor">{{ notice.actor.nickname }}</b>
          {{ notice.summary }}
          <span v-if="notice.type === 'adopt'" class="msg__badge"><Icon name="i-check" cls="ico--xs" /></span>
        </div>
        <span class="msg__time">{{ timeAgo(notice.createdAt) }}</span>
      </div>
    </div>

    <div v-if="!loading && !filtered.length" class="empty">
      <Icon name="i-bell" />
      <div class="empty__t">这里还很安静</div>
      <div class="empty__s">有人回答、评论或采纳时会出现在这里</div>
    </div>
  </div>
</template>
