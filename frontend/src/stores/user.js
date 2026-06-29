import { reactive } from 'vue'
import { getStoredItem, removeStoredItem, setStoredItem } from '../utils/browser'

// 轻量全局用户状态（不引入 Pinia）
export const userStore = reactive({
  token: getStoredItem('token'),
  profile: null,

  setLogin(token, profile) {
    this.token = token
    this.profile = profile
    setStoredItem('token', token)
  },
  setProfile(profile) {
    this.profile = profile
  },
  logout() {
    this.token = ''
    this.profile = null
    removeStoredItem('token')
  },
  get isLoggedIn() {
    return !!this.token
  },
})
