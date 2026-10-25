<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/toast'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const mode = ref('login')
const submitting = ref(false)
const form = reactive({ username: '', password: '', nickname: '' })

async function submit() {
  if (!form.username.trim()) return toast('请输入用户名')
  if (form.password.length < 6) return toast('密码至少 6 位')

  submitting.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login({ username: form.username.trim(), password: form.password })
      toast(`欢迎回来，${userStore.user.nickname}`)
    } else {
      await userStore.register({
        username: form.username.trim(),
        password: form.password,
        nickname: form.nickname.trim() || form.username.trim()
      })
      toast('注册成功，先发一条求助试试')
    }
    router.replace(route.query.redirect || '/plaza')
  } catch (err) {
    toast(err.message)
  } finally {
    submitting.value = false
  }
}

function useDemo() {
  mode.value = 'login'
  form.username = 'linyizhou'
  form.password = '123456'
}
</script>

<template>
  <header class="navbar">
    <button class="iconbtn" aria-label="返回" @click="router.push('/plaza')">
      <Icon name="i-back" />
    </button>
    <div class="navbar__t">{{ mode === 'login' ? '登录' : '注册' }}</div>
  </header>

  <div class="pad">
    <div class="hello login-hero">
      <h1 class="hello__h">错题、词书和资料，<br />第一次收在<em style="font-style: normal; color: var(--brand-700)">同一个入口</em>。</h1>
      <p class="hello__sub">登录后开始记录：广场里的回答、错题本和背单词进度都会跟着你。</p>
    </div>

    <div class="field" style="margin-top: 18px">
      <div class="field__l">
        <span class="field__t">用户名</span>
        <span class="field__n">3~32 位字母数字</span>
      </div>
      <input v-model="form.username" class="input" placeholder="linyizhou" autocomplete="username" />
    </div>

    <div v-if="mode === 'register'" class="field">
      <div class="field__l"><span class="field__t">昵称</span><span class="field__n">同学怎么称呼你</span></div>
      <input v-model="form.nickname" class="input" maxlength="12" />
    </div>

    <div class="field">
      <div class="field__l"><span class="field__t">密码</span><span class="field__n">至少 6 位</span></div>
      <input
        v-model="form.password"
        class="input"
        type="password"
        autocomplete="current-password"
        @keyup.enter="submit"
      />
    </div>

    <button class="btn btn--primary btn--block" style="margin-top: 16px" :disabled="submitting" @click="submit">
      {{ mode === 'login' ? '登录' : '注册并进入' }}
    </button>

    <div class="login-switch">
      {{ mode === 'login' ? '还没有账号？' : '已经有账号了？' }}
      <button @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === 'login' ? '去注册' : '去登录' }}
      </button>
    </div>

    <div class="login-demo">
      演示账号 linyizhou / 123456 · <button style="color: var(--brand-700)" @click="useDemo">一键填入</button>
    </div>
  </div>
</template>
