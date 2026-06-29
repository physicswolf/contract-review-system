import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { points, dimensions } from '../api/mock/db'

// 后端 → 前端字段适配
function adaptPoint(p) {
  return {
    id: p.id,
    name: p.name,
    desc: p.description,
    dimension: p.dimName,
    dimId: p.dimId,
    riskPoints: Array.isArray(p.riskPoints) ? p.riskPoints.length : (p.riskPoints ?? 0),
    status: p.enabled ? '已启用' : '已停用',
    updatedAt: p.updatedAt ? p.updatedAt.slice(0, 10) : '',
    instruction: p.instruction,
    risks: p.riskPoints,
    examples: p.examples,
    defaultResult: p.defaultResult,
  }
}

export async function listPoints(params = {}) {
  if (USE_MOCK) {
    let rows = [...points]
    if (params.keyword) rows = rows.filter((p) => p.name.includes(params.keyword))
    return delay({ items: rows, total: rows.length })
  }
  const { data } = await http.get('/audit-points', {
    params: { keyword: params.keyword, dimId: params.dimId, enabled: params.enabled },
  })
  const items = (data.data || []).map(adaptPoint)
  return { items, total: items.length }
}

export async function getPoint(id) {
  if (USE_MOCK) return delay(points.find((p) => p.id === id) || null)
  const { data } = await http.get(`/audit-points/${id}`)
  return adaptPoint(data.data)
}

export async function savePoint(payload) {
  if (USE_MOCK) {
    if (payload.id) {
      const t = points.find((p) => p.id === payload.id)
      if (t) Object.assign(t, payload)
      return delay(t)
    }
    const row = { id: nextId('p'), status: '已启用', riskPoints: 0, updatedAt: '刚刚', ...payload }
    points.unshift(row)
    return delay(row)
  }
  // 启停走专用接口
  if (payload.id && Object.keys(payload).join(',') === 'id,status') {
    const { data } = await http.patch(`/audit-points/${payload.id}/enabled`, {
      enabled: payload.status === '已启用' ? 1 : 0,
    })
    return data
  }
  const body = {
    dimId: payload.dimId,
    name: payload.name,
    description: payload.desc,
    instruction: payload.instruction || payload.note,
    riskPoints: payload.risks,   // [{name,highStd,lowStd,noneStd}]
    examples: payload.examples,  // [{original,level,analysis,suggestion}]
    defaultResult: payload.defaultResult, // {level,analysis,suggestion}
    enabled: payload.enabled ?? (payload.status === '已停用' ? 0 : 1),
  }
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/audit-points/${payload.id}` : '/audit-points',
    body,
  )
  return data
}

export async function deletePoint(id) {
  if (USE_MOCK) {
    const i = points.findIndex((p) => p.id === id)
    if (i > -1) points.splice(i, 1)
    return delay({ ok: true })
  }
  const { data } = await http.delete(`/audit-points/${id}`)
  return data
}

export async function listDimensions() {
  if (USE_MOCK) return delay(dimensions)
  const { data } = await http.get('/dimensions', { params: { enabled: 1 } })
  return (data.data || []).map((d) => ({ id: d.id, name: d.name }))
}
