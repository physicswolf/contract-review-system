import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { dimensionDetail } from '../api/mock/db'

function adapt(d) {
  return {
    id: d.id,
    name: d.name,
    desc: d.description,
    description: d.description,
    sortOrder: d.sortOrder ?? d.sort_order ?? 0,
    enabled: d.enabled,
    status: d.enabled ? '已启用' : '已停用',
    updatedAt: d.updatedAt ? d.updatedAt.slice(0, 10) : '',
  }
}

export async function listDimensionDetail() {
  if (USE_MOCK) return delay({ items: dimensionDetail, total: dimensionDetail.length })
  const { data } = await http.get('/dimensions')
  const items = (data.data || []).map(adapt)
  return { items, total: items.length }
}

export async function saveDimension(payload) {
  if (USE_MOCK) {
    if (payload.id) {
      const t = dimensionDetail.find((d) => d.id === payload.id)
      if (t) Object.assign(t, payload)
      return delay(t)
    }
    const row = { id: nextId('d'), status: '已启用', updatedAt: '刚刚', ...payload }
    dimensionDetail.unshift(row)
    return delay(row)
  }
  // 启停
  if (payload.id && Object.keys(payload).join(',') === 'id,status') {
    const { data } = await http.put(`/dimensions/${payload.id}`, {
      enabled: payload.status === '已启用' ? 1 : 0,
    })
    return data
  }
  const body = {
    name: payload.name,
    description: payload.desc || payload.description,
    sortOrder: payload.sortOrder,
    enabled: payload.enabled ?? (payload.status === '已停用' ? 0 : 1),
  }
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/dimensions/${payload.id}` : '/dimensions',
    body,
  )
  return data
}

export async function deleteDimension(id) {
  if (USE_MOCK) {
    const i = dimensionDetail.findIndex((d) => d.id === id)
    if (i > -1) dimensionDetail.splice(i, 1)
    return delay({ ok: true })
  }
  const { data } = await http.delete(`/dimensions/${id}`)
  return data
}

export async function listSelectableDimensions() {
  if (USE_MOCK) return delay(dimensionDetail.filter((d) => d.status === '已启用'))
  const { data } = await http.get('/dimensions', { params: { enabled: 1 } })
  return (data.data || []).map(adapt)
}
