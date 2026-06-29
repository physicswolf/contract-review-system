import { reactive } from 'vue'

// 轻量全局用户状态（不引入 Pinia）
export const userStore = reactive({
  token: localStorage.getItem('token') || '',
  profile: null,

  setLogin(token, profile) {
    this.token = token
    this.profile = profile
    localStorage.setItem('token', token)
  },
  setProfile(profile) {
    this.profile = profile
  },
  logout() {
    this.token = ''
    this.profile = null
    localStorage.removeItem('token')
  },
  get isLoggedIn() {
    return !!this.token
  },
})
