<template>
  <AppTopbar title="个人设置">
    <template #actions>
      <el-button @click="router.push({ name: 'review' })">返回合同审核</el-button>
    </template>
  </AppTopbar>

  <div class="page">
    <div class="page-head">
      <h1>个人设置</h1>
      <p>管理个人资料、账号信息与安全设置</p>
    </div>

    <el-card shadow="never" v-loading="loading" style="max-width: 820px">
      <div class="profile-head">
        <span class="avatar">{{ avatar }}</span>
        <div class="ph-info">
          <h2>{{ form.name }}</h2>
          <el-tag type="success" effect="light">{{ form.role }}</el-tag>
        </div>
        <el-button @click="changeAvatar">更换头像</el-button>
      </div>

      <div class="grid2">
        <div class="field"><label>姓名</label><el-input v-model="form.name" /></div>
        <div class="field"><label>登录账号</label><el-input v-model="form.account" disabled /></div>
        <div class="field"><label>所属企业</label><el-input v-model="form.company" /></div>
        <div class="field"><label>角色</label><el-input v-model="form.role" disabled /></div>
        <div class="field"><label>手机号</label><el-input v-model="form.phone" /></div>
        <div class="field"><label>邮箱</label><el-input v-model="form.email" /></div>
      </div>

      <div class="security">
        <div class="sec-title">账号安全</div>
        <div class="sec-row">
          <div>
            <b>登录密码</b>
            <small>建议定期修改密码，保护账号安全</small>
          </div>
          <div class="sec-actions">
            <el-button @click="changePwd">修改密码</el-button>
            <el-button text type="danger" @click="logout">退出登录</el-button>
          </div>
        </div>
      </div>

      <div class="actions">
        <el-button @click="reload">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppTopbar from '../components/AppTopbar.vue'
import { getProfile, updateProfile } from '../services/auth.service'
import { userStore } from '../stores/user'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const form = reactive({ name: '', account: '', company: '', phone: '', email: '', role: '' })

const avatar = computed(() => (form.name || 'U').slice(0, 2).toUpperCase())

onMounted(reload)
async function reload() {
  loading.value = true
  try {
    Object.assign(form, await getProfile())
  } finally {
    loading.value = false
  }
}
async function save() {
  saving.value = true
  try {
    const updated = await updateProfile(form)
    userStore.setProfile(updated)
    ElMessage.success('保存成功')
  } finally {
    saving.value = false
  }
}
function changeAvatar() {
  ElMessage.info('更换头像功能将在后端就绪后开放')
}
function changePwd() {
  ElMessage.info('修改密码功能将在后端就绪后开放')
}
function logout() {
  userStore.logout()
  router.replace({ name: 'login' })
}
</script>

<style scoped>
.page {
  flex: 1;
  padding: 24px 28px;
  overflow: auto;
}
.page-head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.page-head p {
  margin: 8px 0 16px;
  color: var(--muted);
}
.profile-head {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  margin-bottom: 22px;
  border-bottom: 0.667px solid var(--line);
}
.ph-info {
  flex: 1;
}
.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 800;
  color: #dbe6fa;
  background: #263e66;
}
.ph-info h2 {
  margin: 0 0 8px;
  font-size: 20px;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.field label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #526077;
}
.security {
  margin-top: 8px;
  border: 0.667px solid var(--line);
  border-radius: 12px;
  padding: 18px;
}
.sec-title {
  font-weight: 700;
  margin-bottom: 12px;
}
.sec-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sec-row b {
  display: block;
  font-size: 14px;
}
.sec-row small {
  color: var(--muted);
  font-size: 12.5px;
}
.sec-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 22px;
}
</style>
