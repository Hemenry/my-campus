<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { postApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import Ring from '@/components/Ring.vue'
import { timeAgo } from '@/utils/format'

const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const tabs = ['推荐', '求助', '错题', '资料', '试卷']
const activeTab = ref('推荐')
const keyword = ref('')
const posts = ref([])
const loading = ref(false)
const sheetOpen = ref(false)

const TYPE = {
  ask: { label: '求助', cls: 'ask' },
  mistake: { label: '错题', cls: 'mist' },
  material: { label: '资料', cls: 'mat' },
  paper: { label: '试卷', cls: 'paper' }
}

const publishTypes = [
  { k: 'ask', t: '题目求助', d: '不会的题发出去，等人讲思路', ic: 'i-msg', bg: '--ask-bg', fg: '--ask' },
  { k: 'mistake', t: '错题', d: '记下错因，可只存个人空间', ic: 'i-mist', bg: '--mist-bg', fg: '--mist' },
  { k: 'material', t: '资料', d: '笔记、讲义、复习提纲', ic: 'i-file', bg: '--mat-bg', fg: '--mat' },
  { k: 'paper', t: '试卷', d: '真题、模拟卷、期中期末', ic: 'i-plan', bg: '--paper-bg', fg: '--paper' }
]

const me = computed(() => userStore.user)
const summary = computed(() => appStore.summary)
const goal = 20
const done = computed(() => Math.min(goal, summary.value?.todayReview || 0))
const due = computed(() => summary.value?.dueWords || 0)
const streak = computed(() => summary.value?.streakDays || 0)
const checked = computed(() => summary.value?.checkedInToday || false)

const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour < 5) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1}月${d.getDate()}日 ${week}`
})

async function load() {
  loading.value = true
  try {
    const data = await postApi.list({
      category: activeTab.value,
      keyword: keyword.value,
      page: 1,
      pageSize: 30
    })
    posts.value = data.list
  } finally {
    loading.value = false
  }
}

function switchTab(tab) {
  activeTab.value = tab
  load()
}

function openPublish() {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: '/publish/ask' } })
    return
  }
  sheetOpen.value = true
}

function pickType(type) {
  sheetOpen.value = false
  router.push(`/publish/${type}`)
}

async function toggleLike(post) {
  if (!userStore.isLoggedIn) {
    toast('登录后才能点赞')
    return
  }
  const res = await postApi.like(post.id)
  post.isLiked = res.liked
  post.likeCount = res.likeCount
}

async function toggleCollect(post) {
  if (!userStore.isLoggedIn) {
    toast('登录后才能收藏')
    return
  }
  const res = await postApi.collect(post.id)
  post.isCollected = res.collected
  post.collectCount = res.collectCount
  toast(res.collected ? '已收藏，可在「我的」里找到' : '已取消收藏')
}

onMounted(async () => {
  await load()
  if (userStore.isLoggedIn) appStore.refreshSummary()
})
</script>

<template>
  <header class="topbar">
    <div class="topbar__row">
      <div class="brand">
        <div class="brand__logo">G</div>
        <div>
          <span class="brand__name">GeekCampus</span>
          <span class="brand__school">
            {{ me?.school || '未登录' }}
            <Icon name="i-chevron" cls="ico--xs" />
          </span>
        </div>
      </div>
      <div class="topbar__acts">
        <button class="iconbtn" aria-label="发布" @click="openPublish">
          <Icon name="i-plus" />
        </button>
        <button class="iconbtn" aria-label="通知" @click="router.push('/message')">
          <Icon name="i-bell" />
          <span v-if="appStore.unreadCount" class="bell__dot"></span>
        </button>
      </div>
    </div>
  </header>

  <div class="pad">
    <div class="hello">
      <h1 class="hello__h">{{ greetingText }}，{{ me?.nickname || '同学' }}</h1>
      <p class="hello__sub">{{ todayText }} · 把没弄懂的题分出来，和同学一起学会它。</p>
    </div>

    <div class="search">
      <Icon name="i-search" />
      <input
        v-model="keyword"
        placeholder="搜问题、资料、错题或单词本"
        @keyup.enter="load"
      />
    </div>

    <div class="quick">
      <button class="quick__item" @click="router.push('/publish/ask')">
        <span class="quick__icon" style="background: var(--ask-bg); color: var(--ask)">
          <Icon name="i-msg" cls="ico--sm" />
        </span>
        <span class="quick__label">发起求助</span>
      </button>
      <button class="quick__item" @click="router.push('/publish/mistake')">
        <span class="quick__icon" style="background: var(--mist-bg); color: var(--mist)">
          <Icon name="i-mist" cls="ico--sm" />
        </span>
        <span class="quick__label">上传错题</span>
      </button>
      <button class="quick__item" @click="router.push('/english')">
        <span class="quick__icon" style="background: var(--mat-bg); color: var(--mat)">
          <Icon name="i-book" cls="ico--sm" />
        </span>
        <span class="quick__label">背单词</span>
      </button>
      <button class="quick__item" @click="router.push('/publish/material')">
        <span class="quick__icon" style="background: var(--paper-bg); color: var(--paper)">
          <Icon name="i-file" cls="ico--sm" />
        </span>
        <span class="quick__label">传资料</span>
      </button>
    </div>

    <div v-if="!me" class="today">
      <div class="today__body">
        <div class="today__kicker"><Icon name="i-spark" cls="ico--xs" /> 今日学习 · 英语</div>
        <div class="today__title">登录后开始你今天的复习</div>
        <span class="today__sub">错题、词书和资料都收在同一个入口</span>
        <button class="today__cta" @click="router.push({ name: 'login', query: { redirect: '/plaza' } })">
          登录 / 注册<Icon name="i-chevron" cls="ico--xs" />
        </button>
      </div>
      <div class="today__ring"><Ring :done="0" :total="goal" :size="76" /></div>
    </div>

    <div v-else-if="checked && done >= goal" class="today today--done">
      <div class="today__body">
        <div class="today__kicker"><Icon name="i-spark" cls="ico--xs" /> 今日学习 · 英语</div>
        <div class="today__title">今天已经复习完 {{ done }} 个词</div>
        <span class="today__sub">连续打卡 {{ streak }} 天 · 明天还有 {{ due }} 个词</span>
        <button class="today__cta" @click="router.push('/english')">
          看看打卡记录<Icon name="i-chevron" cls="ico--xs" />
        </button>
      </div>
      <div class="today__ring"><Ring :done="done" :total="goal" :size="76" /></div>
    </div>

    <div v-else class="today">
      <div class="today__body">
        <div class="today__kicker"><Icon name="i-spark" cls="ico--xs" /> 今日学习 · 英语</div>
        <div class="today__title">
          <template v-if="due > 0">还有 <b>{{ due }}</b> 个词待复习</template>
          <template v-else>今天的词都清空了</template>
        </div>
        <span class="today__sub">
          {{ streak > 0 ? `已连续打卡 ${streak} 天` : '今天开始第一次打卡' }} · 今日已完成 {{ done }}/{{ goal }}
        </span>
        <button class="today__cta" @click="router.push(due > 0 ? '/english' : '/english')">
          {{ due > 0 ? '开始复习' : '去英语页' }}<Icon name="i-chevron" cls="ico--xs" />
        </button>
      </div>
      <div class="today__ring"><Ring :done="done" :total="goal" :size="76" /></div>
    </div>

    <div class="sec">
      <h2 class="sec__h">学习广场</h2>
      <span class="sec__more">{{ posts.length }} 条</span>
    </div>

    <div class="segs">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="seg"
        :class="{ 'is-on': activeTab === tab }"
        @click="switchTab(tab)"
      >
        {{ tab }}
      </button>
    </div>

    <div class="feed">
      <article
        v-for="post in posts"
        :key="post.id"
        class="card"
        :class="{ 'card--mist': post.type === 'mistake' }"
        @click="router.push(`/detail/${post.id}`)"
      >
        <div class="card__head">
          <div class="avatar" :class="{ 'avatar--me': me && post.author?.id === me.id }">
            {{ (post.author?.nickname || '?').charAt(0) }}
          </div>
          <div class="card__by">
            <div class="card__name">
              {{ post.author?.nickname }}
              <i v-if="me && post.author?.id === me.id">· 我发布的</i>
            </div>
            <span class="card__meta">{{ post.author?.dept }} · {{ timeAgo(post.createdAt) }}</span>
          </div>
          <div class="tag" :class="`tag--${(TYPE[post.type] || TYPE.ask).cls}`">
            {{ (TYPE[post.type] || TYPE.ask).label }}
          </div>
        </div>

        <div class="card__title">{{ post.title }}</div>
        <div v-if="post.content" class="card__text">{{ post.content }}</div>

        <div v-if="post.images && post.images.length" class="media" style="height: auto; padding: 0; background: none">
          <img :src="post.images[0]" alt="题目图片" style="width: 100%; border-radius: 10px; display: block; max-height: 220px; object-fit: cover" />
        </div>

        <div v-if="post.topics && post.topics.length" class="chips">
          <span
            v-for="topic in post.topics"
            :key="topic"
            class="chip"
            :class="{ 'chip--done': topic === '已掌握' }"
          >
            {{ topic }}
          </span>
        </div>

        <div class="card__foot">
          <span class="act">
            <Icon name="i-comment" cls="ico--sm" />
            <span class="act__n">{{ post.answerCount || 0 }}</span>
          </span>
          <button
            class="act act--like"
            :class="{ 'is-on': post.isLiked }"
            @click.stop="toggleLike(post)"
          >
            <Icon name="i-heart" cls="ico--sm" />
            <span class="act__n">{{ post.likeCount }}</span>
          </button>
          <span class="spacer"></span>
          <button
            class="act act--save"
            :class="{ 'is-on': post.isCollected }"
            aria-label="收藏"
            @click.stop="toggleCollect(post)"
          >
            <Icon name="i-save" cls="ico--sm" />
          </button>
        </div>
      </article>

      <div v-if="!loading && !posts.length" class="empty">
        <Icon name="i-file" />
        <div class="empty__t">{{ activeTab === '推荐' ? '还没有内容' : '这个分类还没有内容' }}</div>
        <div class="empty__s">换个分类看看，或者由你发第一条</div>
        <button class="btn btn--primary btn--sm empty__a" @click="router.push('/publish/ask')">
          发一条求助
        </button>
      </div>
    </div>
  </div>

  <div class="sheet-root" :class="{ 'is-open': sheetOpen }">
    <div v-if="sheetOpen" class="scrim" @click="sheetOpen = false"></div>
    <div v-if="sheetOpen" class="sheet" role="dialog">
      <div class="sheet__grab"></div>
      <div class="sheet__t">发点什么</div>
      <div class="sheet__s">选一种类型，后面是同一套编辑页</div>
      <div class="types">
        <button v-for="item in publishTypes" :key="item.k" class="type" @click="pickType(item.k)">
          <span class="type__ic" :style="{ background: `var(${item.bg})`, color: `var(${item.fg})` }">
            <Icon :name="item.ic" cls="ico--sm" />
          </span>
          <span class="type__t">{{ item.t }}</span>
          <span class="type__d">{{ item.d }}</span>
        </button>
      </div>
      <button class="sheet__cancel" @click="sheetOpen = false">取消</button>
    </div>
  </div>
</template>
