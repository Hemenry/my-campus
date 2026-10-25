import http from './http'

export const authApi = {
  login: (data) => http.post('/auth/login', data),
  register: (data) => http.post('/auth/register', data),
  me: () => http.get('/auth/me'),
  updateMe: (data) => http.patch('/auth/me', data)
}

export const postApi = {
  list: (params) => http.get('/posts', { params }),
  detail: (id) => http.get(`/posts/${id}`),
  create: (data) => http.post('/posts', data),
  remove: (id) => http.delete(`/posts/${id}`),
  like: (id) => http.post(`/posts/${id}/like`),
  collect: (id) => http.post(`/posts/${id}/collect`),
  createAnswer: (id, data) => http.post(`/posts/${id}/answers`, data),
  likeAnswer: (id) => http.post(`/answers/${id}/like`),
  adoptAnswer: (id) => http.post(`/answers/${id}/adopt`)
}

export const commentApi = {
  list: (targetType, targetId) => http.get('/comments', { params: { targetType, targetId } }),
  create: (data) => http.post('/comments', data),
  remove: (id) => http.delete(`/comments/${id}`)
}

export const englishApi = {
  wordbooks: () => http.get('/wordbooks'),
  book: (id) => http.get(`/wordbooks/${id}`),
  createBook: (data) => http.post('/wordbooks', data),
  // 解析一本 PDF 远比普通请求慢，单独放宽超时；后端 gunicorn 60s 是硬上限
  parsePdf: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/wordbooks/parse-pdf', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 45000
    })
  },
  updateBook: (id, data) => http.patch(`/wordbooks/${id}`, data),
  removeBook: (id) => http.delete(`/wordbooks/${id}`),
  queue: (id, size = 20) => http.get(`/wordbooks/${id}/review`, { params: { size } }),
  submitReview: (id, data) => http.post(`/wordbooks/${id}/review`, data),
  checkins: (params) => http.get('/checkins', { params }),
  checkin: (data) => http.post('/checkins', data),
  plans: () => http.get('/plans'),
  createPlan: (data) => http.post('/plans', data),
  updatePlan: (id, data) => http.patch(`/plans/${id}`, data)
}

export const mistakeApi = {
  list: (params) => http.get('/mistakes', { params }),
  create: (data) => http.post('/mistakes', data),
  update: (id, data) => http.patch(`/mistakes/${id}`, data),
  remove: (id) => http.delete(`/mistakes/${id}`)
}

export const noticeApi = {
  list: (params) => http.get('/notifications', { params }),
  read: (ids) => http.post('/notifications/read', { ids })
}

export const uploadApi = {
  file: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/uploads', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  }
}

export const statsApi = {
  summary: () => http.get('/stats/summary'),
  myPosts: () => http.get('/me/posts'),
  myCollections: () => http.get('/me/collections'),
  user: (id) => http.get(`/users/${id}`)
}
