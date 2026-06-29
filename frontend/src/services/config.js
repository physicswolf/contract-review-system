// 前后端对接总开关。后端 API 就绪后改为 false（或用环境变量控制）。
export const USE_MOCK = true

// 真实后端基础路径（USE_MOCK=false 时生效），由 Vite proxy 转发。
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
