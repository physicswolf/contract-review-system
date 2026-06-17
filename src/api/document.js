import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listDocuments(params = {}) {
  const { data } = await api.get('/documents', { params })
  return data
}

export async function getDocument(id) {
  const { data } = await api.get(`/documents/${id}`)
  return data
}

export async function reanalyzeDocument(id) {
  const { data } = await api.post(`/documents/${id}/reanalyze`)
  return data
}

export async function deleteDocument(id) {
  const { data } = await api.delete(`/documents/${id}`)
  return data
}

export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}
