<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { englishApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import Ring from '@/components/Ring.vue'

const router = useRouter()
const appStore = useAppStore()

const GOAL = 20
const loading = ref(true)
const books = ref([])
const checkinDays = ref([])
const summary = ref({ todayReview: 0, dueWords: 0, streakDays: 0, totalCheckinDays: 0 })
const sheetOpen = ref(false)
const saving = ref(false)
const form = reactive({ name: '', text: '' })
const fileInput = ref(null)
const parsing = ref(false)
const parsed = ref([])
const parsedMeta = ref({ pages: 0, total: 0, truncated: false })

const done = computed(() => summary.value.todayReview || 0)
const capped = computed(() => Math.min(GOAL, done.value))
const due = computed(() => summary.value.dueWords || 0)
const streak = computed(() => summary.value.streakDays || 0)
const checked = computed(() => done.value > 0)
const streakTicks = computed(() => Math.min(7, streak.value))

const calendar = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const firstWeekday = new Date(year, month, 1).getDay()
  const totalDays = new Date(year, month + 1, 0).getDate()
  const set = {}
  checkinDays.value.forEach((d) => {
    set[d.date] = d.wordCount
  })

  const cells = []
  for (let i = 0; i < firstWeekday; i += 1) cells.push({ placeholder: true })
  for (let day = 1; day <= totalDays; day += 1) {
    const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    cells.push({
      day,
      on: Boolean(set[key]),
      today: day === now.getDate(),
      count: set[key] || 0
    })
  }
  const monthCount = Object.keys(set).filter((key) =>
    key.startsWith(`${year}-${String(month + 1).padStart(2, '0')}`)
  ).length
  return { month: month + 1, cells, monthCount }
})

async function load() {
  loading.value = true
  try {
    const now = new Date()
    const [bookList, checkins] = await Promise.all([
      englishApi.wordbooks(),
      englishApi.checkins({ year: now.getFullYear(), month: now.getMonth() + 1 })
    ])
    books.value = bookList
    checkinDays.value = checkins.days || []
    const data = await appStore.refreshSummary()
    summary.value = {
      todayReview: data.todayReview,
      dueWords: data.dueWords,
      streakDays: data.streakDays,
      totalCheckinDays: data.totalCheckinDays
    }
  } finally {
    loading.value = false
  }
}

function pickPdf() {
  fileInput.value?.click()
}

async function onPickPdf(event) {
  const file = event.target.files?.[0]
  // 先清空，这样连续选同一个文件也能再次触发 change
  event.target.value = ''
  if (!file) return
  if (!/\.pdf$/i.test(file.name)) return toast('请选择 PDF 文件')
  parsing.value = true
  try {
    const result = await englishApi.parsePdf(file)
    parsed.value = result.words || []
    parsedMeta.value = {
      pages: result.parsedPages || 0,
      total: result.pageCount || 0,
      truncated: Boolean(result.truncated)
    }
    if (!form.name.trim()) form.name = file.name.replace(/\.pdf$/i, '').slice(0, 20)
    toast(`识别到 ${parsed.value.length} 个词`)
  } catch (err) {
    toast(err.message)
  } finally {
    parsing.value = false
  }
}

function removeWord(index) {
  parsed.value.splice(index, 1)
}

function clearParsed() {
  parsed.value = []
  parsedMeta.value = { pages: 0, total: 0, truncated: false }
}

async function createBook() {
  if (!form.name.trim()) return toast('给词书起个名字')
  const useParsed = parsed.value.length > 0
  if (!useParsed && !form.text.trim()) return toast('至少粘贴一个单词，或上传 PDF 词库')
  saving.value = true
  try {
    const data = { name: form.name.trim(), source: useParsed ? 'pdf' : 'manual' }
    // 词条是结构化数组，走这条才能保留音标；粘贴的文本才走 text
    if (useParsed) data.words = parsed.value
    else data.text = form.text
    await englishApi.createBook(data)
    toast('词书已创建')
    sheetOpen.value = false
    form.name = ''
    form.text = ''
    clearParsed()
    await load()
  } catch (err) {
    toast(err.message)
  } finally {
    saving.value = false
  }
}

function openBook(book) {
  router.push(`/review/${book.id}`)
}

onMounted(load)
</script>

<template>
  <header class="topbar">
    <div class="topbar__row">
      <div class="brand__name" style="font-size: 19px; letter-spacing: -0.4px">英语</div>
      <div class="topbar__acts">
        <button class="iconbtn" aria-label="导入" @click="sheetOpen = true">
          <Icon name="i-upload" />
        </button>
      </div>
    </div>
  </header>

  <div class="pad">
    <div class="goal">
      <div class="goal__ring"><Ring :done="capped" :total="GOAL" :size="88" /></div>
      <div class="goal__body">
        <div class="goal__k">{{ done >= GOAL ? '今日已完成' : `今日已复习 ${done} / ${GOAL}` }}</div>
        <div class="goal__h">
          <template v-if="due > 0">还有 <b>{{ due }}</b> 个词到期</template>
          <template v-else>今天没有到期的词</template>
        </div>
        <div class="goal__streak">
          <span class="streak">
            <i v-for="n in 7" :key="n" :class="{ on: n <= streakTicks }"></i>
          </span>
          <span class="goal__st">连续 {{ streak }} 天 · 累计 {{ summary.totalCheckinDays }} 次打卡</span>
        </div>
      </div>
    </div>

    <button v-if="due > 0" class="btn btn--primary btn--block" style="margin-top: 10px" @click="router.push('/review/all')">
      开始复习 {{ Math.min(due, Math.max(GOAL - done, 1)) }} 个词
    </button>
    <div v-else class="donebar">
      <Icon name="i-check" cls="ico--sm" />
      <span>{{ checked ? '今天已打卡 · 明天再来' : '没有到期的词，去导入一本新词书' }}</span>
    </div>

    <div class="sec">
      <h2 class="sec__h">我的词书</h2>
      <button class="sec__more" @click="sheetOpen = true">导入新词书</button>
    </div>

    <div class="books">
      <div v-for="book in books" :key="book.id" class="book" @click="openBook(book)">
        <div class="book__cover" :class="{ 'book--b': book.source === 'recommend' }">
          <span>{{ book.name.slice(0, 2) }}</span>
        </div>
        <div class="book__body">
          <div class="book__t">{{ book.name }}</div>
          <div class="book__s">
            {{ book.totalCount }} 词 · 已掌握 {{ book.masteredCount }} · 今日到期 {{ book.dueCount }}
          </div>
          <div class="bar">
            <div class="bar__in" :style="{ width: `${book.progress}%` }"></div>
          </div>
        </div>
        <span class="act"><Icon name="i-chevron" cls="ico--sm" /></span>
      </div>

      <div v-if="!loading && !books.length" class="empty">
        <Icon name="i-book" />
        <div class="empty__t">还没有词书</div>
        <div class="empty__s">从一本 PDF 词书开始，或者直接粘贴单词表</div>
        <button class="btn btn--primary btn--sm empty__a" @click="sheetOpen = true">导入词书</button>
      </div>
    </div>

    <div class="sec">
      <h2 class="sec__h">打卡日历</h2>
      <span class="sec__more">连续 {{ streak }} 天</span>
    </div>

    <div class="cal">
      <div class="cal__head">
        <div class="cal__m">{{ calendar.month }} 月</div>
        <div class="cal__sum">本月打卡 {{ calendar.monthCount }} 天 · 累计 {{ summary.totalCheckinDays }} 天</div>
      </div>
      <div class="cal__wk">
        <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
      </div>
      <div class="cal__grid">
        <div v-for="(cell, index) in calendar.cells" :key="index" class="cal__d" :class="{ on: cell.on, 'is-now': cell.today, mute: cell.placeholder }">
          <span>{{ cell.placeholder ? '' : cell.day }}</span>
        </div>
      </div>
    </div>

    <div style="height: 8px"></div>
  </div>

  <div class="sheet-root" :class="{ 'is-open': sheetOpen }">
    <div v-if="sheetOpen" class="scrim" @click="sheetOpen = false"></div>
    <div v-if="sheetOpen" class="sheet" role="dialog">
      <div class="sheet__grab"></div>
      <div class="sheet__t">新建词书</div>
      <div class="sheet__s">上传 PDF 词库自动识别（文字版、3 MB 以内），或者粘贴单词表</div>
      <div class="field">
        <input v-model="form.name" class="input" maxlength="20" placeholder="词书名称" />
      </div>

      <div class="field">
        <input
          ref="fileInput"
          type="file"
          accept="application/pdf,.pdf"
          hidden
          @change="onPickPdf"
        />
        <button class="btn btn--ghost btn--block" :disabled="parsing" @click="pickPdf">
          <Icon v-if="!parsing" name="i-upload" cls="ico--sm" />
          <span>{{ parsing ? '正在解析 PDF…' : '从 PDF 词库导入' }}</span>
        </button>
      </div>

      <div v-if="parsed.length" class="pdfbox">
        <div class="pdfbox__h">
          <span class="pdfbox__t">识别到 {{ parsed.length }} 个词</span>
          <button class="pdfbox__clr" @click="clearParsed">清除</button>
        </div>
        <div v-if="parsedMeta.total" class="pdfbox__m">
          解析 {{ parsedMeta.pages }} / {{ parsedMeta.total }} 页<template v-if="parsedMeta.truncated">，超出部分未处理</template>
        </div>
        <div class="pdfbox__list">
          <div v-for="(item, index) in parsed" :key="`${item.word}-${index}`" class="pdfrow">
            <div class="pdfrow__b">
              <div class="pdfrow__w">
                {{ item.word }}
                <span v-if="item.phonetic" class="pdfrow__p">/{{ item.phonetic }}/</span>
              </div>
              <div class="pdfrow__m">{{ item.meaning }}</div>
            </div>
            <button class="pdfrow__x" @click="removeWord(index)">移除</button>
          </div>
        </div>
      </div>

      <template v-if="!parsed.length">
        <div class="ordiv"><span>或者粘贴单词表</span></div>
        <div class="field">
          <textarea
            v-model="form.text"
            class="textarea"
            style="min-height: 130px"
            placeholder="ambiguous | adj. 模糊不清的&#10;coherent | adj. 连贯的"
          ></textarea>
        </div>
      </template>

      <button
        class="btn btn--primary btn--block"
        style="margin-top: 14px"
        :disabled="saving || parsing"
        @click="createBook"
      >
        创建并开始
      </button>
    </div>
  </div>
</template>
