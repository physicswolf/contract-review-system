// 前后端对接总开关。
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// 真实后端基础路径（USE_MOCK=false 时生效），由 Vite proxy 转发。
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
