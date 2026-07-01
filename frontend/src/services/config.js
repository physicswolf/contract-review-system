export const USE_MOCK = false
const _base = location.hostname === 'localhost' ? 'http://localhost:5002' : 'http://180.76.53.236:5002'
export const API_BASE = import.meta.env.VITE_API_BASE || `${_base}/api/v1/config`
