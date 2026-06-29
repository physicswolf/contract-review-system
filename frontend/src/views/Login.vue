<template>
  <div class="auth">
    <div class="auth-card">
      <div class="auth-brand">
        <div class="brand">
          <span class="logo">AI</span>
          <span>AI智契</span>
        </div>
        <h1>智能审合同<br />风险早知道</h1>
        <p>用 AI 识别合同风险，让审查更准确、更高效。</p>
      </div>

      <div class="auth-form">
        <h2>欢迎使用 AI智契</h2>
        <p class="sub">登录后进入合同审核工作台</p>

        <el-form :model="form" @submit.prevent="onSubmit">
          <div class="field">
            <label>账号</label>
            <el-input v-model="form.account" placeholder="请输入账号" />
          </div>
          <div class="field">
            <label>密码</label>
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
            />
          </div>
          <button class="login-btn" :disabled="loading" @click="onSubmit">
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../services/auth.service'
import { userStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ account: 'demo@company.com', password: '12345678' })

async function onSubmit() {
  if (!form.account || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const { token, user } = await login(form)
    userStore.setLogin(token, user)
    ElMessage.success('登录成功')
    router.replace(route.query.redirect || { name: 'review' })
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(139px 139px at 259px 162px, rgba(23, 55, 101, 1) 0%, rgba(12, 28, 51, 0.5) 17%, rgba(0, 0, 0, 0) 34%),
    linear-gradient(148deg, #07101f 0%, #101f39 100%);
  padding: 24px;
}
.auth-card {
  width: 900px;
  max-width: 100%;
  height: 540px;
  display: grid;
  grid-template-columns: 471.79px 1fr;
  border: 0.667px solid #2b4168;
  border-radius: 26px;
  overflow: hidden;
  box-shadow: 0 36px 100px rgba(0, 0, 0, 0.53);
}
.auth-brand {
  padding: 58px;
  color: #fff;
  background: linear-gradient(141deg, #16305b 6%, #09162c 94%);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  font-weight: 700;
  font-size: 16px;
}
.logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #586ff5, #25c9bb);
  box-shadow: 0 10px 12px rgba(89, 111, 245, 0.27);
}
.auth-brand h1 {
  margin: 54px 0 18px;
  font-size: 42px;
  font-weight: 700;
  line-height: 50.4px;
}
.auth-brand p {
  color: #a7b5cc;
  font-size: 16px;
  line-height: 28.8px;
  margin: 0;
}
.auth-form {
  padding: 62px 54px;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.auth-form h2 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #1c273b;
}
.auth-form .sub {
  margin: 0 0 32px;
  color: #758199;
  font-size: 16px;
}
.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #526077;
}
.field :deep(.el-input__wrapper) {
  height: 44px;
  border-radius: 10px;
  box-shadow: 0 0 0 0.667px #dbe3ef inset;
}
.field :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--blue) inset;
}
.login-btn {
  width: 100%;
  margin-top: 16px;
  height: 48px;
  border: 0;
  border-radius: 10px;
  font-size: 16px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(90deg, #586ff5 0%, #7561ff 100%);
  transition: opacity 0.15s;
}
.login-btn:hover {
  opacity: 0.92;
}
.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
@media (max-width: 720px) {
  .auth-card {
    grid-template-columns: 1fr;
    height: auto;
  }
  .auth-brand {
    display: none;
  }
}
</style>
