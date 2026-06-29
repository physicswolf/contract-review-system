import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { dimensionDetail, selectableDimensions } from '../api/mock/db'

export async function listDimensionDetail() {
  if (USE_MOCK) return delay({ items: dimensionDetail, total: dimensionDetail.length })
  const { data } = await http.get('/dimensions')
  return data
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
  const { data } = await http[payload.id ? 'put' : 'post'](
    payload.id ? `/dimensions/${payload.id}` : '/dimensions',
    payload,
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
  if (USE_MOCK) return delay(selectableDimensions)
  const { data } = await http.get('/dimensions/selectable')
  return data
}

export async function saveRelations(payload) {
  if (USE_MOCK) return delay({ ok: true })
  const { data } = await http.post('/dimensions/relations', payload)
  return data
}
