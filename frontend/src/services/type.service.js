import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { contractTypes } from '../api/mock/db'

function adaptType(t) {
  return {
    id: t.id,
    code: t.code,
    name: t.name,
    stance: t.stance,
    desc: t.description,
    description: t.description,
    keywords: t.keywords,
    enabled: t.enabled,
    status: t.enabled ? '已启用' : '已停用',
    relatedPoints: t.linkedPointCount ?? t.linkedAuditPoints?.length ?? 0,
    linkedAuditPoints: t.linkedAuditPoints,
    updatedAt: t.updatedAt ? t.updatedAt.slice(0, 10) : '',
  }
}

export async function listTypes(params = {}) {
  if (USE_MOCK) {
    let rows = [...contractTypes]
    if (params.keyword) rows = rows.filter((t) => t.name.includes(params.keyword))
    return delay({ items: rows, total: rows.length })
  }
  const { data } = await http.get('/contract-types', { params })
  const items = (data.data || []).map(adaptType)
  return { items, total: items.length }
}

export async function getType(id) {
  if (USE_MOCK) return delay(contractTypes.find((t) => t.id === id) || null)
  const { data } = await http.get(`/contract-types/${id}`)
  return adaptType(data.data)
}

export async function saveType(payload) {
  if (USE_MOCK) {
    if (payload.id) {
      const t = contractTypes.find((x) => x.id === payload.id)
      if (t) Object.assign(t, payload)
      return delay(t)
    }
    const row = { id: nextId('t'), status: '已启用', relatedPoints: 0, updatedAt: '刚刚', ...payload }
    contractTypes.unshift(row)
    return delay(row)
  }
  // 启停
  if (payload.id && Object.keys(payload).join(',') === 'id,status') {
    const { data } = await http.put(`/contract-types/${payload.id}`, {
      enabled: payload.status === '已启用' ? 1 : 0,
    })
    return data
  }
  const body = {
    code: payload.code,
    name: payload.name,
    stance: payload.stance,
    description: payload.desc || payload.description,
    keywords: payload.keywords,
    enabled: payload.enabled ?? (payload.status === '已停用' ? 0 : 1),
  }
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/contract-types/${payload.id}` : '/contract-types',
    body,
  )
  return data
}

export async function deleteType(id) {
  if (USE_MOCK) {
    const i = contractTypes.findIndex((t) => t.id === id)
    if (i > -1) contractTypes.splice(i, 1)
    return delay({ ok: true })
  }
  const { data } = await http.delete(`/contract-types/${id}`)
  return data
}

export async function saveAuditPoints(typeId, auditPointIds) {
  if (USE_MOCK) return delay({ ok: true })
  const { data } = await http.put(`/contract-types/${typeId}/audit-points`, { auditPointIds })
  return data
}
