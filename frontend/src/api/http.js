import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE } from '../services/config'

const http = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
})

// 请求拦截：注入 token
http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// 响应拦截：统一错误提示 + 401 跳登录
http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    const msg = error?.response?.data?.msg || error?.response?.data?.detail || error?.message || '请求失败'
    if (status === 401) {
      localStorage.removeItem('token')
      if (location.pathname !== '/login') location.href = '/login'
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

export default http
