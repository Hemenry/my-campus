<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { toastText } from '@/utils/toast'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const screenEl = ref(null)

const steps = [
  { h: '记录', d: '把没弄懂的那道题、那本词书，先收进来' },
  { h: '求助', d: '在广场换回同学的思路，还能被采纳' },
  { h: '沉淀', d: '有用的存进个人空间，不再靠翻聊天记录' },
  { h: '复习', d: '用打卡把「看过的」变成「记住了」' }
]

const tabs = [
  { k: 'plaza', l: '广场', i: 'i-plaza', path: '/plaza' },
  { k: 'english', l: '英语', i: 'i-book', path: '/english' },
  { k: 'message', l: '消息', i: 'i-msg', path: '/message' },
  { k: 'mine', l: '我的', i: 'i-user', path: '/mine' }
]

const STEP_OF = {
  plaza: 1,
  detail: 1,
  message: 1,
  publish: 0,
  mine: 2,
  english: 3,
  review: 3,
  login: 1
}

const activeTab = computed(() => route.meta.tab || null)
const stepIndex = computed(() => STEP_OF[route.name] ?? 1)
const flush = computed(() => Boolean(route.meta.flush))

watch(
  () => route.fullPath,
  () => {
    if (screenEl.value) screenEl.value.scrollTop = 0
  }
)

onMounted(async () => {
  if (!userStore.user) await userStore.fetchMe()
  if (userStore.isLoggedIn) appStore.refreshUnread()
})
</script>

<template>
  <aside class="rail">
    <div class="rail__mark">
      <div class="rail__logo">G</div>
      <div class="rail__name">GeekCampus</div>
    </div>
    <div class="rail__thesis">错题、词书和资料，<br /><em>第一次收在同一个入口。</em></div>
    <div class="rail__loop">
      <div
        v-for="(item, index) in steps"
        :key="item.h"
        class="rail__step"
        :class="{ 'is-on': stepIndex === index }"
      >
        <div class="rail__dot"></div>
        <div class="rail__h">{{ item.h }}</div>
        <div class="rail__d">{{ item.d }}</div>
      </div>
    </div>
  </aside>

  <div class="app">
    <main ref="screenEl" class="screen" :class="{ 'screen--flush': flush }">
      <router-view />
    </main>

    <nav v-if="activeTab" class="tabbar">
      <a
        v-for="tab in tabs"
        :key="tab.k"
        class="tabbar__i"
        :class="{ 'is-on': activeTab === tab.k }"
        :href="`#${tab.path}`"
        :aria-label="tab.l"
        @click.prevent="router.push(tab.path)"
      >
        <Icon :name="tab.i" />
        <span v-if="tab.k === 'message' && appStore.unreadCount > 0" class="tabbar__dot"></span>
        <span class="tabbar__l">{{ tab.l }}</span>
      </a>
    </nav>

    <div class="toast" :class="{ 'is-on': toastText }">{{ toastText }}</div>
  </div>
</template>
