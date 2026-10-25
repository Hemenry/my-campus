<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { postApi, uploadApi } from '@/api'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const router = useRouter()

const TYPE = {
  ask: { label: '求助' },
  mistake: { label: '错题' },
  material: { label: '资料' },
  paper: { label: '试卷' }
}

const SUBJECTS = ['高等数学', '线性代数', '概率论', '大学物理', '数据结构', '计算机网络', '操作系统', '英语', '其他']
const TAG_OPTIONS = ['求讲解', '求思路', '已掌握', '期末复习', '真题', '概念', '面试']

const type = computed(() => (TYPE[route.params.type] ? route.params.type : 'ask'))
const meta = computed(() => TYPE[type.value])
const isMist = computed(() => type.value === 'mistake')
const isFile = computed(() => ['material', 'paper'].includes(type.value))

const form = reactive({
  title: '',
  body: '',
  subject: '',
  tags: [],
  visibility: 'public',
  reason: '',
  correct: '',
  images: []
})
const submitting = ref(false)

const titlePlaceholder = computed(() => {
  if (type.value === 'ask') return '一句话说清卡在哪'
  if (isMist.value) return '这道错题考什么'
  if (isFile.value) return '资料名称'
  return '标题'
})

const bodyPlaceholder = computed(() => {
  if (type.value === 'ask') return '已经试过什么、卡在第几步，写清楚更容易被答上'
  if (isMist.value) return '当时是怎么想错的，写下来才有用'
  return '这份资料包含什么、怎么用最方便'
})

function pickSubject(name) {
  form.subject = form.subject === name ? '' : name
}

function pickTag(name) {
  const index = form.tags.indexOf(name)
  if (index > -1) {
    form.tags.splice(index, 1)
    return
  }
  if (form.tags.length >= 3) {
    toast('最多选 3 个标签')
    return
  }
  form.tags.push(name)
}

async function addImages(event) {
  const files = Array.from(event.target.files || []).slice(0, 4 - form.images.length)
  event.target.value = ''
  for (const file of files) {
    try {
      const res = await uploadApi.file(file)
      form.images.push(res.url)
    } catch (err) {
      toast(err.message)
    }
  }
}

function removeImage(index) {
  form.images.splice(index, 1)
}

async function submit() {
  if (!form.title.trim()) return toast('先写个标题')
  submitting.value = true
  try {
    let content = form.body.trim()
    if (isMist.value) {
      if (form.reason.trim()) content += `${content ? '\n\n' : ''}【错因】${form.reason.trim()}`
      if (form.correct.trim()) content += `\n\n【解法】${form.correct.trim()}`
    }
    const created = await postApi.create({
      type: type.value,
      title: form.title.trim(),
      content,
      subject: form.subject,
      topics: form.tags,
      images: form.images,
      visibility: form.visibility
    })
    toast('发布成功')
    router.replace(`/detail/${created.id}`)
  } catch (err) {
    toast(err.message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <header class="navbar">
    <button class="iconbtn" aria-label="返回" @click="router.back()">
      <Icon name="i-back" />
    </button>
    <div class="navbar__t">{{ isFile ? `上传${meta.label}` : '发布' }}</div>
    <button class="navbar__a" @click="submit">发布</button>
  </header>

  <div class="pad">
    <div class="field">
      <div class="field__l">
        <span class="field__t">标题</span>
        <span class="field__n">{{ form.title.length }}/40</span>
      </div>
      <input v-model="form.title" class="input" maxlength="40" :placeholder="titlePlaceholder" />
    </div>

    <div class="field">
      <div class="field__l">
        <span class="field__t">{{ isFile ? '说明' : '正文' }}</span>
        <span class="field__n">{{ form.body.length }}/1000</span>
      </div>
      <textarea v-model="form.body" class="textarea" maxlength="1000" :placeholder="bodyPlaceholder"></textarea>
    </div>

    <div class="field">
      <div class="field__l"><span class="field__t">学科</span></div>
      <div class="tagpick">
        <button
          v-for="subject in SUBJECTS"
          :key="subject"
          type="button"
          class="tagpick__i"
          :class="{ 'is-on': form.subject === subject }"
          @click="pickSubject(subject)"
        >
          {{ subject }}
        </button>
      </div>
    </div>

    <template v-if="isMist">
      <div class="field">
        <div class="field__l"><span class="field__t">我的错因</span></div>
        <input v-model="form.reason" class="input" placeholder="例如：展开时漏掉常数项" />
      </div>
      <div class="field">
        <div class="field__l"><span class="field__t">正确答案 / 思路</span></div>
        <textarea
          v-model="form.correct"
          class="textarea"
          style="min-height: 88px"
          placeholder="写清楚正确解法，方便复习"
        ></textarea>
      </div>
    </template>

    <div class="field">
      <div class="field__l">
        <span class="field__t">配图</span>
        <span class="field__n">最多 4 张</span>
      </div>
      <div class="imggrid">
        <div v-for="(src, index) in form.images" :key="src" class="imggrid__i">
          <img :src="src" :alt="`配图 ${index + 1}`" />
          <button class="imggrid__x" @click="removeImage(index)">
            <Icon name="i-close" cls="ico--xs" />
          </button>
        </div>
        <label v-if="form.images.length < 4" class="imggrid__add">
          <Icon name="i-camera" cls="ico--sm" />
          <span>加图片</span>
          <input type="file" accept="image/*" multiple hidden @change="addImages" />
        </label>
      </div>
    </div>

    <div class="field">
      <div class="field__l">
        <span class="field__t">标签</span>
        <span class="field__n">选填，最多 3 个</span>
      </div>
      <div class="tagpick">
        <button
          v-for="tag in TAG_OPTIONS"
          :key="tag"
          type="button"
          class="tagpick__i"
          :class="{ 'is-on': form.tags.includes(tag) }"
          @click="pickTag(tag)"
        >
          {{ tag }}
        </button>
      </div>
    </div>

    <div class="field">
      <div class="field__l"><span class="field__t">可见性</span></div>
      <div class="tagpick">
        <button
          type="button"
          class="tagpick__i"
          :class="{ 'is-on': form.visibility === 'public' }"
          @click="form.visibility = 'public'"
        >
          公开到广场
        </button>
        <button
          type="button"
          class="tagpick__i"
          :class="{ 'is-on': form.visibility === 'private' }"
          @click="form.visibility = 'private'"
        >
          仅自己可见
        </button>
      </div>
    </div>

    <div style="height: 92px"></div>
  </div>

  <div class="sticky-cta">
    <button class="btn btn--primary btn--block" :disabled="submitting" @click="submit">发布</button>
  </div>
</template>
