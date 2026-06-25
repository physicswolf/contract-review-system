import http from '../api/http'
import { USE_MOCK } from './config'
import { delay, nextId } from '../api/mock/delay'
import { contracts, buildAuditResult } from '../api/mock/db'

export async function listContracts(params = {}) {
  if (USE_MOCK) {
    let rows = [...contracts]
    if (params.name) rows = rows.filter((c) => c.name.includes(params.name))
    if (params.partyA) rows = rows.filter((c) => c.partyA.includes(params.partyA))
    if (params.partyB) rows = rows.filter((c) => c.partyB.includes(params.partyB))
    return delay({ items: rows, total: rows.length })
  }
  const { data } = await http.get('/contracts', { params })
  return data
}

export async function deleteContract(id) {
  if (USE_MOCK) {
    const idx = contracts.findIndex((c) => c.id === id)
    if (idx > -1) contracts.splice(idx, 1)
    return delay({ ok: true })
  }
  const { data } = await http.delete(`/contracts/${id}`)
  return data
}

// 上传合同（向导 Step1）。返回新建合同 id + 已识别的合同类型（用于回填）。
export async function uploadContract(file) {
  if (USE_MOCK) {
    await delay(null, 600)
    return {
      id: nextId('c'),
      name: file?.name || '智慧园区软件采购合同.docx',
      detectedType: '采购合同',
      matchConfidence: 96,
    }
  }
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post('/contracts/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// 发起审核（向导 Step2 提交：立场 + 审核点）
export async function startAudit(contractId, payload) {
  if (USE_MOCK) {
    await delay(null, 500)
    return { id: contractId, status: 'done' }
  }
  const { data } = await http.post(`/contracts/${contractId}/audit`, payload)
  return data
}

export async function getAuditResult(contractId) {
  if (USE_MOCK) return delay(buildAuditResult(contractId))
  const { data } = await http.get(`/contracts/${contractId}/result`)
  return data
}
