import http from '../api/http'
import { USE_MOCK } from './config'
import { delay } from '../api/mock/delay'
import { profile } from '../api/mock/db'

export async function login({ account, password }) {
  if (USE_MOCK) {
    await delay(null, 500)
    return { token: 'mock-token-' + Date.now(), user: { ...profile, account } }
  }
  const { data } = await http.post('/auth/login', { account, password })
  return data.data
}

export async function getProfile() {
  if (USE_MOCK) return delay(profile)
  const { data } = await http.get('/auth/profile')
  return data
}

export async function updateProfile(payload) {
  if (USE_MOCK) return delay({ ...profile, ...payload })
  const { data } = await http.put('/auth/profile', payload)
  return data
}
