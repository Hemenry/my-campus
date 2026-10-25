import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/', redirect: '/plaza' },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/plaza',
    name: 'plaza',
    component: () => import('@/views/PlazaView.vue'),
    meta: { title: '广场', tab: 'plaza' }
  },
  {
    path: '/detail/:id',
    name: 'detail',
    component: () => import('@/views/PostDetailView.vue'),
    meta: { title: '详情', flush: true }
  },
  {
    path: '/publish/:type?',
    name: 'publish',
    component: () => import('@/views/PublishView.vue'),
    meta: { title: '发布', requiresAuth: true }
  },
  {
    path: '/english',
    name: 'english',
    component: () => import('@/views/EnglishView.vue'),
    meta: { title: '英语', tab: 'english', requiresAuth: true }
  },
  {
    path: '/review/:bookId',
    name: 'review',
    component: () => import('@/views/ReviewView.vue'),
    meta: { title: '复习', flush: true, requiresAuth: true }
  },
  {
    path: '/message',
    name: 'message',
    component: () => import('@/views/MessagesView.vue'),
    meta: { title: '消息', tab: 'message', requiresAuth: true }
  },
  {
    path: '/mine',
    name: 'mine',
    component: () => import('@/views/MineView.vue'),
    meta: { title: '我的', tab: 'mine', requiresAuth: true }
  },
  { path: '/post/:id', redirect: (to) => `/detail/${to.params.id}` },
  { path: '/messages', redirect: '/message' },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (!userStore.user) await userStore.fetchMe()
  // 先设标题，再做鉴权跳转，否则 401 重定向分支会漏掉 document.title
  document.title = to.meta.title ? `${to.meta.title} · GeekCampus` : 'GeekCampus'
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
