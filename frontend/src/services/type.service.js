import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { contractTypes } from '../api/mock/db'

export async function listTypes(params = {}) {
  if (USE_MOCK) {
    let rows = [...contractTypes]
    if (params.keyword) rows = rows.filter((t) => t.name.includes(params.keyword))
    return delay({ items: rows, total: rows.length })
  }
  const { data } = await http.get('/contract-types', { params })
  return data
}

export async function getType(id) {
  if (USE_MOCK) return delay(contractTypes.find((t) => t.id === id) || null)
  const { data } = await http.get(`/contract-types/${id}`)
  return data
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
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/contract-types/${payload.id}` : '/contract-types',
    payload,
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
