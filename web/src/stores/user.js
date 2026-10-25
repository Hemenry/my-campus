import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import { tokenStore } from '@/api/http'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const loading = ref(false)
  const isLoggedIn = computed(() => Boolean(user.value))

  function applyAuth(payload) {
    tokenStore.set(payload.token)
    user.value = payload.user
  }

  async function login(form) {
    loading.value = true
    try {
      applyAuth(await authApi.login(form))
    } finally {
      loading.value = false
    }
  }

  async function register(form) {
    loading.value = true
    try {
      applyAuth(await authApi.register(form))
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!tokenStore.get()) return null
    try {
      user.value = await authApi.me()
    } catch (err) {
      user.value = null
    }
    return user.value
  }

  async function updateProfile(form) {
    user.value = await authApi.updateMe(form)
    return user.value
  }

  function logout() {
    tokenStore.clear()
    user.value = null
  }

  return { user, loading, isLoggedIn, login, register, fetchMe, updateProfile, logout }
})
