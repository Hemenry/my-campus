<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { englishApi } from '@/api'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import Ring from '@/components/Ring.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const book = ref(null)
const entries = ref([])
const index = ref(0)
const flipped = ref(false)
const results = ref([])
const startedAt = ref(Date.now())
const summary = ref(null)
const submitting = ref(false)

const current = computed(() => entries.value[index.value] || null)
const progress = computed(() =>
  entries.value.length ? Math.round((index.value / entries.value.length) * 100) : 0
)
const rate = computed(() => {
  if (!summary.value || !summary.value.reviewed) return 0
  return Math.round((summary.value.known / summary.value.reviewed) * 100)
})
const seconds = computed(() => summary.value?.duration || 0)

async function resolveBookId() {
  const param = route.params.bookId
  if (param && param !== 'all') return param
  const books = await englishApi.wordbooks()
  const target = books.find((item) => item.dueCount > 0) || books[0]
  return target ? target.id : null
}

async function load() {
  loading.value = true
  try {
    const bookId = await resolveBookId()
    if (!bookId) {
      toast('还没有词书，先去导入一本')
      router.replace('/english')
      return
    }
    const data = await englishApi.queue(bookId, 20)
    book.value = data.book
    entries.value = data.entries
    startedAt.value = Date.now()
    if (!data.entries.length) {
      toast('这本词书已经全部掌握了')
      router.replace('/english')
    }
  } finally {
    loading.value = false
  }
}

function flip() {
  if (!current.value) return
  flipped.value = !flipped.value
}

function grade(kind) {
  if (!flipped.value) {
    toast('先翻面看看释义')
    return
  }
  results.value.push({ entryId: current.value.id, known: kind !== 'again' })
  flipped.value = false
  if (index.value + 1 >= entries.value.length) {
    finish()
  } else {
    index.value += 1
  }
}

async function finish() {
  if (!book.value) return
  submitting.value = true
  try {
    const duration = Math.round((Date.now() - startedAt.value) / 1000)
    const data = await englishApi.submitReview(book.value.id, {
      results: results.value,
      durationSeconds: duration
    })
    summary.value = { ...data, duration, known: results.value.filter((item) => item.known).length }
  } finally {
    submitting.value = false
  }
}

function exit() {
  if (summary.value || index.value === 0) {
    router.push('/english')
    return
  }
  if (window.confirm(`已经评过的 ${index.value} 个词会按间隔排好，确定退出？`)) {
    router.push('/english')
  }
}

function speak() {
  if (!current.value || !window.speechSynthesis) {
    toast('这个浏览器不支持发音')
    return
  }
  const utter = new SpeechSynthesisUtterance(current.value.word)
  utter.lang = 'en-US'
  utter.rate = 0.9
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utter)
}

function onKey(event) {
  if (summary.value || !current.value) return
  if (event.code === 'Space') {
    event.preventDefault()
    flip()
  } else if (flipped.value && event.key === '1') {
    grade('again')
  } else if (flipped.value && event.key === '3') {
    grade('know')
  }
}

onMounted(async () => {
  await load()
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div v-if="summary" class="result">
    <header class="navbar" style="flex: none">
      <button class="iconbtn" aria-label="关闭" @click="router.push('/english')">
        <Icon name="i-close" />
      </button>
      <div class="navbar__t">复习结果</div>
    </header>
    <div class="result__main">
      <div class="result__hero">
        <div class="result__k">本节复习完成</div>
        <div class="result__big">{{ rate }}<i>%</i></div>
        <div class="result__sub">掌握率 · {{ summary.reviewed }} 个词里 {{ summary.known }} 个直接想起来了</div>
      </div>
      <div class="stats">
        <div class="stats__row"><span class="stats__k">本节词数</span><span class="stats__v">{{ summary.reviewed }}</span></div>
        <div class="stats__row">
          <span class="stats__k">用时</span>
          <span class="stats__v">{{ seconds > 60 ? `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒` : `${seconds} 秒` }}</span>
        </div>
        <div class="stats__row"><span class="stats__k">今日累计</span><span class="stats__v">{{ summary.checkin.wordCount }} 词</span></div>
        <div class="stats__row"><span class="stats__k">连续打卡</span><span class="stats__v"><em>{{ summary.streakDays }}</em> 天</span></div>
      </div>
      <div class="cheer">
        <div class="cheer__badge"><Icon name="i-check" cls="ico--sm" /></div>
        <div>
          <div class="cheer__t">打卡已记录，这是第 {{ summary.streakDays }} 天</div>
          <div class="cheer__s">{{ summary.book.name }} 已掌握 {{ summary.book.masteredCount }} / {{ summary.book.totalCount }}</div>
        </div>
      </div>
    </div>
    <div class="result__acts">
      <button class="btn btn--ghost" style="flex: 1" @click="router.push('/english')">返回英语</button>
      <button class="btn btn--primary" style="flex: 1.4" @click="router.push('/plaza')">去广场看看</button>
    </div>
  </div>

  <div v-else-if="loading" class="pad" style="padding-top: 40px">
    <div class="skel" style="height: 320px; border-radius: 22px"></div>
  </div>

  <div v-else-if="current" class="review">
    <div class="review__bar">
      <button class="iconbtn" style="width: 34px; height: 34px; margin-left: -6px" aria-label="退出" @click="exit">
        <Icon name="i-close" />
      </button>
      <div class="review__prog"><i :style="{ width: `${progress}%` }"></i></div>
      <div class="review__cnt">{{ index + 1 }} / {{ entries.length }}</div>
    </div>

    <div class="review__stage">
      <div
        class="wordcard"
        :class="{ 'is-flip': flipped }"
        role="button"
        tabindex="0"
        aria-label="翻转卡片"
        @click="flip"
      >
        <div class="wordcard__in">
          <div class="face">
            <div class="wc__word">{{ current.word }}</div>
            <div class="wc__ph">
              <span>{{ current.phonetic }}</span>
              <button class="wc__spk" aria-label="发音" @click.stop="speak">
                <Icon name="i-spk" cls="ico--sm" />
              </button>
            </div>
            <div class="wc__hint"><Icon name="i-spark" cls="ico--xs" /> 点击卡片查看释义</div>
          </div>
          <div class="face face--back">
            <div class="wc__def">{{ current.meaning }}</div>
            <div v-if="current.example" class="wc__eg">
              <p>{{ current.example }}</p>
            </div>
            <div class="wc__tag">
              <span class="chip">{{ book?.name }}</span>
              <span class="chip">{{ current.status === 'new' ? '新词' : `第 ${current.reviewCount + 1} 次` }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="rates" :class="{ 'is-locked': !flipped }">
      <button class="rate rate--no" @click="grade('again')">不认识<span>10 分钟后再来</span></button>
      <button class="rate rate--mid" @click="grade('fuzzy')">模糊<span>明天再过一遍</span></button>
      <button class="rate rate--yes" @click="grade('know')">认识<span>按间隔往后排</span></button>
    </div>

    <div class="review__tip">
      {{ flipped ? '凭第一反应选，间隔会自动排' : '翻面之后才能评级，避免误触' }}
    </div>
  </div>
</template>
