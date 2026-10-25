import axios from 'axios'
import { toast } from '@/utils/toast'

const TOKEN_KEY = 'geekcampus_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY) || '',
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({
  baseURL: '/api',
  timeout: 12000
})

http.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response.data?.data,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message || (error.code === 'ECONNABORTED' ? '请求超时，请重试' : '网络异常，请检查后端服务是否启动')

    if (status === 401) {
      tokenStore.clear()
      if (!location.hash.startsWith('#/login')) {
        location.hash = '#/login'
      }
    }
    if (!error.config?.silent) {
      toast(message)
    }
    return Promise.reject(new Error(message))
  }
)

export default http
