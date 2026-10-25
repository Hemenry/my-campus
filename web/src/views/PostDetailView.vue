<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { commentApi, postApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'
import { timeAgo } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const post = ref(null)
const loading = ref(true)
const error = ref('')
const commentText = ref('')
const answerOpen = ref(false)
const answerText = ref('')
const submitting = ref(false)

const TYPE = {
  ask: { label: '求助', cls: 'ask' },
  mistake: { label: '错题', cls: 'mist' },
  material: { label: '资料', cls: 'mat' },
  paper: { label: '试卷', cls: 'paper' }
}

const meta = computed(() => TYPE[post.value?.type] || TYPE.ask)
const me = computed(() => userStore.user)
const isMine = computed(() => Boolean(me.value && post.value?.author?.id === me.value.id))
const isFile = computed(() => ['material', 'paper'].includes(post.value?.type))
const paragraphs = computed(() =>
  String(post.value?.content || '')
    .split(/\n{2,}/)
    .filter(Boolean)
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    post.value = await postApi.detail(route.params.id)
  } catch (err) {
    post.value = null
    error.value = err.message || '这条内容已被删除'
  } finally {
    loading.value = false
  }
}

function requireLogin() {
  if (userStore.isLoggedIn) return true
  toast('登录后才能互动')
  router.push({ name: 'login', query: { redirect: route.fullPath } })
  return false
}

async function toggleLike() {
  if (!requireLogin()) return
  const res = await postApi.like(post.value.id)
  post.value.isLiked = res.liked
  post.value.likeCount = res.likeCount
}

async function toggleCollect() {
  if (!requireLogin()) return
  const res = await postApi.collect(post.value.id)
  post.value.isCollected = res.collected
  post.value.collectCount = res.collectCount
  toast(res.collected ? '已收藏，可在「我的」里找到' : '已取消收藏')
}

async function adopt(answer) {
  try {
    await postApi.adoptAnswer(answer.id)
    toast('已采纳，对方会收到通知')
    await load()
  } catch (err) {
    toast(err.message)
  }
}

function openAnswer() {
  if (!requireLogin()) return
  answerOpen.value = true
}

async function submitAnswer() {
  const value = answerText.value.trim()
  if (value.length < 5) {
    toast('再多写一点，至少 5 个字')
    return
  }
  submitting.value = true
  try {
    await postApi.createAnswer(post.value.id, { content: value })
    answerText.value = ''
    answerOpen.value = false
    toast('回答已发布')
    await load()
  } finally {
    submitting.value = false
  }
}

async function submitComment() {
  if (!requireLogin()) return
  const value = commentText.value.trim()
  if (!value) {
    toast('写点什么再发')
    return
  }
  await commentApi.create({ targetType: 'post', targetId: post.value.id, content: value })
  commentText.value = ''
  toast('评论已发布')
  await load()
}

async function removePost() {
  if (!window.confirm('删除这条内容？草稿、回答和评论都会一起删除，无法恢复。')) return
  await postApi.remove(post.value.id)
  toast('已删除')
  router.push('/plaza')
}

onMounted(load)
</script>

<template>
  <header class="navbar">
    <button class="iconbtn" aria-label="返回" @click="router.back()">
      <Icon name="i-back" />
    </button>
    <div class="navbar__t">{{ post ? `${meta.label}详情` : '内容详情' }}</div>
  </header>

  <div v-if="loading" class="pad" style="padding-top: 18px">
    <div class="skel" style="height: 18px; width: 40%"></div>
    <div class="skel" style="height: 24px; width: 82%; margin-top: 14px"></div>
    <div class="skel" style="height: 14px; width: 100%; margin-top: 16px"></div>
    <div class="skel" style="height: 14px; width: 92%; margin-top: 8px"></div>
  </div>

  <div v-else-if="error" class="pad">
    <div class="empty">
      <Icon name="i-file" />
      <div class="empty__t">这条内容已被删除</div>
      <div class="empty__s">{{ error }}</div>
      <button class="btn btn--ghost btn--sm empty__a" @click="router.push('/plaza')">回广场看看</button>
    </div>
  </div>

  <template v-else-if="post">
    <div class="detail">
      <div class="detail__head">
        <div class="avatar avatar--lg" :class="{ 'avatar--me': isMine }">
          {{ (post.author?.nickname || '?').charAt(0) }}
        </div>
        <div class="card__by">
          <div class="card__name">
            {{ post.author?.nickname }} <i>· {{ post.author?.dept }}</i>
          </div>
          <span class="card__meta">{{ timeAgo(post.createdAt) }} · {{ post.subject }}</span>
        </div>
        <div class="tag" :class="`tag--${meta.cls}`">{{ meta.label }}</div>
      </div>

      <h1 class="detail__title">{{ post.title }}</h1>
      <div class="detail__body">
        <p v-for="(para, index) in paragraphs" :key="index">
          <span style="white-space: pre-line">{{ para }}</span>
        </p>
      </div>

      <div v-if="post.images && post.images.length" style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px">
        <img
          v-for="src in post.images"
          :key="src"
          :src="src"
          alt="题目图片"
          style="width: 100%; border-radius: 12px; display: block"
        />
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

      <template v-if="!isFile">
        <div class="sec">
          <h2 class="sec__h">{{ post.answers.length }} 条回答</h2>
          <span class="sec__more">{{ post.likeCount }} 人点赞</span>
        </div>

        <div class="feed">
          <article
            v-for="answer in post.answers"
            :key="answer.id"
            class="answer"
            :class="{ 'answer--best': answer.isAdopted }"
          >
            <span v-if="answer.isAdopted" class="best">
              <Icon name="i-check" cls="ico--xs" /> 已采纳
            </span>
            <div class="card__head" style="margin-bottom: 9px">
              <div class="avatar" :class="{ 'avatar--me': me && answer.author?.id === me.id }">
                {{ (answer.author?.nickname || '?').charAt(0) }}
              </div>
              <div class="card__by">
                <div class="card__name">
                  {{ answer.author?.nickname }} <i>· {{ answer.author?.dept }}</i>
                </div>
                <span class="card__meta">{{ timeAgo(answer.createdAt) }}</span>
              </div>
              <button
                v-if="isMine && post.status !== 'adopted'"
                class="btn btn--soft btn--sm"
                @click="adopt(answer)"
              >
                采纳
              </button>
            </div>
            <div class="answer__t">
              <p v-for="(para, index) in String(answer.content).split(/\n{2,}/).filter(Boolean)" :key="index">
                <span style="white-space: pre-line">{{ para }}</span>
              </p>
            </div>
          </article>

          <div v-if="!post.answers.length" class="empty">
            <Icon name="i-comment" />
            <div class="empty__t">还没有回答</div>
            <div class="empty__s">讲清思路比给答案更有用，被采纳后会显示在顶部</div>
          </div>
        </div>
      </template>

      <div class="sec">
        <h2 class="sec__h">评论 {{ post.comments.length }}</h2>
      </div>
      <div
        class="chatbox"
        style="background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 4px 14px"
      >
        <div v-for="comment in post.comments" :key="comment.id" class="cmt">
          <div class="avatar avatar--lg">
            {{ (comment.author?.nickname || '?').charAt(0) }}
          </div>
          <div class="cmt__b">
            <div class="cmt__n">{{ comment.author?.nickname }}</div>
            <div class="cmt__t">{{ comment.content }}</div>
            <div class="cmt__m">{{ timeAgo(comment.createdAt) }}</div>
          </div>
        </div>
        <div v-if="!post.comments.length" class="inline-hint">还没有评论，说点什么</div>

        <div class="composer">
          <textarea
            v-model="commentText"
            class="textarea"
            rows="1"
            placeholder="写下你的评论…"
            @keydown.enter.exact.prevent="submitComment"
          ></textarea>
          <button class="btn btn--primary btn--sm" style="height: 40px; padding: 0 14px" @click="submitComment">
            发送
          </button>
        </div>
      </div>
    </div>

    <div class="actionbar">
      <template v-if="isFile">
        <button class="btn btn--primary" style="flex: 1" @click="toast('这份资料只有元信息，没有可下载的附件')">
          这份资料没有附件
        </button>
      </template>
      <template v-else>
        <button class="actionbar__in" @click="openAnswer">写下你的思路…</button>
      </template>
      <button
        class="act act--save"
        :class="{ 'is-on': post.isCollected }"
        style="width: 38px; height: 38px; border-radius: 11px; background: var(--bg); justify-content: center"
        aria-label="收藏"
        @click="toggleCollect"
      >
        <Icon name="i-save" cls="ico--sm" />
      </button>
      <button
        v-if="isMine"
        class="act"
        style="width: 38px; height: 38px; border-radius: 11px; background: var(--bg); justify-content: center"
        aria-label="删除"
        @click="removePost"
      >
        <Icon name="i-mist" cls="ico--sm" />
      </button>
    </div>

    <div class="sheet-root" :class="{ 'is-open': answerOpen }">
      <div v-if="answerOpen" class="scrim" @click="answerOpen = false"></div>
      <div v-if="answerOpen" class="sheet" role="dialog">
        <div class="sheet__grab"></div>
        <div class="sheet__t">写回答</div>
        <div class="sheet__s">讲清思路比只给答案更有用</div>
        <div class="field">
          <textarea
            v-model="answerText"
            class="textarea"
            style="min-height: 140px"
            placeholder="你是怎么想到的？关键那一步在哪里？"
          ></textarea>
        </div>
        <button
          class="btn btn--primary btn--block"
          style="margin-top: 14px"
          :disabled="submitting"
          @click="submitAnswer"
        >
          发布回答
        </button>
      </div>
    </div>
  </template>
</template>
