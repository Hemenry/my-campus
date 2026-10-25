<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { englishApi, mistakeApi, statsApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import { timeAgo } from '@/utils/format'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const summary = ref(null)
const posts = ref([])
const collections = ref([])
const mistakes = ref([])
const checkins = ref([])
const plans = ref([])
const tab = ref('posts')

const editOpen = ref(false)
const mistakeOpen = ref(false)
const saving = ref(false)
const profileForm = reactive({ nickname: '', school: '', dept: '', grade: '', bio: '' })
const mistakeForm = reactive({ prompt: '', knowledgePoint: '', reason: '', answer: '', mastery: 0 })

const me = computed(() => summary.value?.user || userStore.user)
const activePlan = computed(() => plans.value[0] || null)

const weekBars = computed(() => {
  const counts = {}
  checkins.value.forEach((item) => {
    counts[item.date] = item.wordCount
  })
  const days = []
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    days.push({ label: '日一二三四五六'.charAt(d.getDay()), count: counts[key] || 0 })
  }
  const max = Math.max(1, ...days.map((x) => x.count))
  return { days, max, total: days.reduce((sum, x) => sum + x.count, 0) }
})

async function load() {
  loading.value = true
  try {
    const now = new Date()
    const [summaryData, postList, collectionList, mistakeData, checkinData, planList] = await Promise.all([
      statsApi.summary(),
      statsApi.myPosts(),
      statsApi.myCollections(),
      mistakeApi.list({ pageSize: 50 }),
      englishApi.checkins({ year: now.getFullYear(), month: now.getMonth() + 1 }),
      englishApi.plans()
    ])
    summary.value = summaryData
    posts.value = postList
    collections.value = collectionList
    mistakes.value = mistakeData.list
    checkins.value = checkinData.days || []
    plans.value = planList
  } finally {
    loading.value = false
  }
}

function openEdit() {
  Object.assign(profileForm, {
    nickname: me.value?.nickname || '',
    school: me.value?.school || '',
    dept: me.value?.dept || '',
    grade: me.value?.grade || '',
    bio: me.value?.bio || ''
  })
  editOpen.value = true
}

async function saveProfile() {
  if (!profileForm.nickname.trim()) return toast('昵称不能为空')
  saving.value = true
  try {
    await userStore.updateProfile(profileForm)
    toast('资料已更新')
    editOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function createMistake() {
  if (!mistakeForm.prompt.trim()) return toast('至少写下题干')
  saving.value = true
  try {
    await mistakeApi.create(mistakeForm)
    toast('已加入错题本')
    mistakeOpen.value = false
    Object.assign(mistakeForm, { prompt: '', knowledgePoint: '', reason: '', answer: '', mastery: 0 })
    await load()
  } finally {
    saving.value = false
  }
}

async function cycleMastery(item) {
  const updated = await mistakeApi.update(item.id, { mastery: (item.mastery + 1) % 3 })
  Object.assign(item, updated)
}

async function removeMistake(item) {
  if (!window.confirm('删除这道错题？')) return
  await mistakeApi.remove(item.id)
  mistakes.value = mistakes.value.filter((row) => row.id !== item.id)
}

function logout() {
  userStore.logout()
  toast('已退出登录')
  router.push('/plaza')
}

onMounted(load)
</script>

<template>
  <header class="topbar">
    <div class="topbar__row">
      <div class="brand__name" style="font-size: 19px; letter-spacing: -0.4px">我的</div>
      <button class="iconbtn" aria-label="退出" @click="logout"><Icon name="i-logout" /></button>
    </div>
  </header>

  <div class="profile">
    <div class="profile__row">
      <div class="profile__ava">{{ (me?.nickname || 'G').charAt(0) }}</div>
      <div style="flex: 1; min-width: 0">
        <div class="profile__n">{{ me?.nickname }}</div>
        <div class="profile__s">
          {{ me?.school || '未填写学校' }} · {{ me?.dept || '未填写院系' }} · {{ me?.grade || '未填写年级' }}
        </div>
      </div>
      <button class="profile__edit" @click="openEdit">编辑</button>
    </div>

    <div class="nums">
      <div class="nums__c">
        <div class="nums__n">{{ summary?.postCount || 0 }}</div>
        <div class="nums__k">发布</div>
      </div>
      <div class="nums__c">
        <div class="nums__n">{{ summary?.adoptedCount || 0 }}</div>
        <div class="nums__k">被采纳</div>
      </div>
      <div class="nums__c">
        <div class="nums__n">{{ summary?.streakDays || 0 }}</div>
        <div class="nums__k">打卡天数</div>
      </div>
    </div>

    <div class="grid4">
      <button class="grid4__i" @click="tab = 'mistakes'">
        <span class="grid4__ic" style="background: var(--mist-bg); color: var(--mist)">
          <Icon name="i-mist" cls="ico--sm" />
        </span>
        <span class="grid4__l">我的错题</span>
      </button>
      <button class="grid4__i" @click="router.push('/english')">
        <span class="grid4__ic" style="background: var(--ask-bg); color: var(--ask)">
          <Icon name="i-plan" cls="ico--sm" />
        </span>
        <span class="grid4__l">学习计划</span>
      </button>
      <button class="grid4__i" @click="tab = 'collections'">
        <span class="grid4__ic" style="background: var(--paper-bg); color: var(--paper)">
          <Icon name="i-save" cls="ico--sm" />
        </span>
        <span class="grid4__l">我的收藏</span>
      </button>
      <button class="grid4__i" @click="tab = 'posts'">
        <span class="grid4__ic" style="background: var(--mat-bg); color: var(--mat)">
          <Icon name="i-file" cls="ico--sm" />
        </span>
        <span class="grid4__l">我发布的</span>
      </button>
    </div>

    <div class="plan">
      <div class="plan__top">
        <div class="plan__t">{{ activePlan ? activePlan.name : '还没有学习计划' }}</div>
        <span class="chip" :class="activePlan ? 'chip--todo' : 'chip--todo'">
          {{ activePlan ? `${activePlan.percent}%` : '去英语页创建' }}
        </span>
      </div>
      <div class="plan__meta">
        <template v-if="activePlan">
          目标 {{ activePlan.targetValue }} {{ activePlan.targetType === 'words' ? '词' : '题' }} ·
          {{ activePlan.period === 'daily' ? '每天' : '每周' }} · 截止 {{ activePlan.deadline || '未设置' }}
        </template>
        <template v-else>给「每天背多少词」设一个截止日，进度会自动算</template>
      </div>
      <div v-if="activePlan" class="bar">
        <div class="bar__in" :style="{ width: `${activePlan.percent}%` }"></div>
      </div>
    </div>

    <div class="chart">
      <div class="chart__h">
        <div class="chart__t">最近 7 天</div>
        <div class="chart__s">复习 {{ weekBars.total }} 词</div>
      </div>
      <div v-if="weekBars.total" class="bars">
        <div v-for="(item, index) in weekBars.days" :key="index" class="bars__b">
          <div
            class="bars__v"
            :class="{ hi: item.count === weekBars.max && item.count > 0 }"
            :style="{ height: `${Math.max(6, Math.round((item.count / weekBars.max) * 100))}%` }"
          ></div>
          <div class="bars__l">{{ item.label }}</div>
        </div>
      </div>
      <div v-else class="inline-hint" style="margin-top: 12px">
        这周还没有复习记录，去英语页背几个词就有的看了
      </div>
    </div>

    <div class="list">
      <div class="list__i" @click="tab = 'posts'">
        <span class="list__ic" style="background: var(--bg); color: var(--text-2)">
          <Icon name="i-msg" cls="ico--sm" />
        </span>
        <span class="list__l">我的发布</span>
        <span class="list__v">{{ posts.length }}</span>
        <Icon name="i-chevron" cls="ico--xs" />
      </div>
      <div class="list__i" @click="tab = 'collections'">
        <span class="list__ic" style="background: var(--bg); color: var(--text-2)">
          <Icon name="i-save" cls="ico--sm" />
        </span>
        <span class="list__l">我的收藏</span>
        <span class="list__v">{{ collections.length }}</span>
        <Icon name="i-chevron" cls="ico--xs" />
      </div>
      <div class="list__i" @click="tab = 'mistakes'">
        <span class="list__ic" style="background: var(--bg); color: var(--text-2)">
          <Icon name="i-mist" cls="ico--sm" />
        </span>
        <span class="list__l">我的错题</span>
        <span class="list__v">{{ mistakes.length }}</span>
        <Icon name="i-chevron" cls="ico--xs" />
      </div>
    </div>
  </div>

  <div class="pad">
    <div class="segs" style="margin-top: 18px">
      <button class="seg" :class="{ 'is-on': tab === 'posts' }" @click="tab = 'posts'">我的发布</button>
      <button class="seg" :class="{ 'is-on': tab === 'collections' }" @click="tab = 'collections'">我的收藏</button>
      <button class="seg" :class="{ 'is-on': tab === 'mistakes' }" @click="tab = 'mistakes'">错题本</button>
    </div>

    <div v-if="tab === 'posts'" class="feed">
      <article v-for="post in posts" :key="post.id" class="card" @click="router.push(`/detail/${post.id}`)">
        <div class="card__head">
          <div class="avatar avatar--me">{{ (post.author?.nickname || '?').charAt(0) }}</div>
          <div class="card__by">
            <div class="card__name">{{ post.author?.nickname }} <i>· 我发布的</i></div>
            <span class="card__meta">{{ post.author?.dept }} · {{ timeAgo(post.createdAt) }}</span>
          </div>
          <div class="tag" :class="post.type === 'mistake' ? 'tag--mist' : post.type === 'material' ? 'tag--mat' : post.type === 'paper' ? 'tag--paper' : 'tag--ask'">
            {{ post.typeLabel }}
          </div>
        </div>
        <div class="card__title">{{ post.title }}</div>
        <div v-if="post.content" class="card__text">{{ post.content }}</div>
        <div class="card__foot">
          <span class="act"><Icon name="i-comment" cls="ico--sm" /><span class="act__n">{{ post.answerCount }}</span></span>
          <span class="act"><Icon name="i-heart" cls="ico--sm" /><span class="act__n">{{ post.likeCount }}</span></span>
          <span class="spacer"></span>
          <span class="act"><Icon name="i-save" cls="ico--sm" /><span class="act__n">{{ post.collectCount }}</span></span>
        </div>
      </article>

      <div v-if="!posts.length" class="empty">
        <Icon name="i-file" />
        <div class="empty__t">还没有发布内容</div>
        <div class="empty__s">第一条求助，往往就是闭环的起点</div>
        <button class="btn btn--primary btn--sm empty__a" @click="router.push('/publish/ask')">去发布</button>
      </div>
    </div>

    <div v-else-if="tab === 'collections'" class="feed">
      <article v-for="post in collections" :key="post.id" class="card" @click="router.push(`/detail/${post.id}`)">
        <div class="card__head">
          <div class="avatar">{{ (post.author?.nickname || '?').charAt(0) }}</div>
          <div class="card__by">
            <div class="card__name">{{ post.author?.nickname }}</div>
            <span class="card__meta">{{ post.author?.dept }} · {{ timeAgo(post.createdAt) }}</span>
          </div>
          <div class="tag tag--ask">{{ post.typeLabel }}</div>
        </div>
        <div class="card__title">{{ post.title }}</div>
        <div v-if="post.content" class="card__text">{{ post.content }}</div>
      </article>

      <div v-if="!collections.length" class="empty">
        <Icon name="i-save" />
        <div class="empty__t">收藏夹是空的</div>
        <div class="empty__s">在详情页点收藏，内容会沉淀到这里</div>
      </div>
    </div>

    <div v-else class="feed">
      <article v-for="item in mistakes" :key="item.id" class="card">
        <div class="card__head">
          <div class="tag tag--mist">{{ item.knowledgePoint || '未分类' }}</div>
          <span class="spacer"></span>
          <span class="card__meta">{{ item.masteryLabel }}</span>
        </div>
        <div class="card__title">{{ item.prompt }}</div>
        <div v-if="item.reason" class="reason">
          <span class="reason__k">错因</span>
          <span class="reason__v">{{ item.reason }}</span>
        </div>
        <div v-if="item.answer" class="reason">
          <span class="reason__k">解法</span>
          <span class="reason__v">{{ item.answer }}</span>
        </div>
        <div class="card__foot">
          <button class="textbtn" @click="cycleMastery(item)">切换掌握状态</button>
          <span class="spacer"></span>
          <button class="textbtn" style="color: var(--mist)" @click="removeMistake(item)">删除</button>
        </div>
      </article>

      <button class="btn btn--ghost btn--block" @click="mistakeOpen = true">录入一道错题</button>

      <div v-if="!mistakes.length" class="empty">
        <Icon name="i-mist" />
        <div class="empty__t">错题本是空的</div>
        <div class="empty__s">把没弄懂的那道题先收进来</div>
      </div>
    </div>

    <div style="height: 24px"></div>
  </div>

  <div class="sheet-root" :class="{ 'is-open': editOpen }">
    <div v-if="editOpen" class="scrim" @click="editOpen = false"></div>
    <div v-if="editOpen" class="sheet" role="dialog">
      <div class="sheet__grab"></div>
      <div class="sheet__t">编辑资料</div>
      <div class="field">
        <div class="field__l"><span class="field__t">昵称</span><span class="field__n">最多 12 字</span></div>
        <input v-model="profileForm.nickname" class="input" maxlength="12" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">学校</span></div>
        <input v-model="profileForm.school" class="input" maxlength="16" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">院系</span></div>
        <input v-model="profileForm.dept" class="input" maxlength="16" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">年级</span></div>
        <input v-model="profileForm.grade" class="input" maxlength="12" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">简介</span><span class="field__n">选填</span></div>
        <textarea v-model="profileForm.bio" class="textarea" maxlength="80" style="min-height: 88px"></textarea>
      </div>
      <button class="btn btn--primary btn--block" style="margin-top: 14px" :disabled="saving" @click="saveProfile">
        保存
      </button>
    </div>
  </div>

  <div class="sheet-root" :class="{ 'is-open': mistakeOpen }">
    <div v-if="mistakeOpen" class="scrim" @click="mistakeOpen = false"></div>
    <div v-if="mistakeOpen" class="sheet" role="dialog">
      <div class="sheet__grab"></div>
      <div class="sheet__t">录入错题</div>
      <div class="field">
        <div class="field__l"><span class="field__t">题干</span></div>
        <textarea v-model="mistakeForm.prompt" class="textarea" style="min-height: 80px" placeholder="题目描述或结论"></textarea>
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">知识点</span></div>
        <input v-model="mistakeForm.knowledgePoint" class="input" placeholder="线性代数 / 概率论 …" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">我的错因</span></div>
        <input v-model="mistakeForm.reason" class="input" placeholder="当时卡在哪一步" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">正确解法</span></div>
        <textarea v-model="mistakeForm.answer" class="textarea" style="min-height: 72px"></textarea>
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">掌握状态</span></div>
        <div class="tagpick">
          <button class="tagpick__i" :class="{ 'is-on': mistakeForm.mastery === 0 }" @click="mistakeForm.mastery = 0">未掌握</button>
          <button class="tagpick__i" :class="{ 'is-on': mistakeForm.mastery === 1 }" @click="mistakeForm.mastery = 1">复习中</button>
          <button class="tagpick__i" :class="{ 'is-on': mistakeForm.mastery === 2 }" @click="mistakeForm.mastery = 2">已掌握</button>
        </div>
      </div>
      <button class="btn btn--primary btn--block" style="margin-top: 14px" :disabled="saving" @click="createMistake">
        保存
      </button>
    </div>
  </div>
</template>
