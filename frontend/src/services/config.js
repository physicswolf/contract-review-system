// 前后端对接总开关。
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const _base = location.hostname === 'localhost' ? 'http://localhost:8000' : ''

// 真实后端基础路径（USE_MOCK=false 时生效），可由 VITE_API_BASE 覆盖。
export const API_BASE = import.meta.env.VITE_API_BASE || `${_base}/api`

export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
