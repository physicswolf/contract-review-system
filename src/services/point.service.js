import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { points, dimensions } from '../api/mock/db'

export async function listPoints(params = {}) {
  if (USE_MOCK) {
    let rows = [...points]
    if (params.keyword) rows = rows.filter((p) => p.name.includes(params.keyword))
    return delay({ items: rows, total: rows.length })
  }
  const { data } = await http.get('/points', { params })
  return data
}

export async function getPoint(id) {
  if (USE_MOCK) return delay(points.find((p) => p.id === id) || null)
  const { data } = await http.get(`/points/${id}`)
  return data
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
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/points/${payload.id}` : '/points',
    payload,
  )
  return data
}

export async function deletePoint(id) {
  if (USE_MOCK) {
    const i = points.findIndex((p) => p.id === id)
    if (i > -1) points.splice(i, 1)
    return delay({ ok: true })
  }
  const { data } = await http.delete(`/points/${id}`)
  return data
}

export async function listDimensions() {
  if (USE_MOCK) return delay(dimensions)
  const { data } = await http.get('/dimensions')
  return data
}
