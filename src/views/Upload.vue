<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>上传合同</span>
        <el-tag v-if="health" :type="health.llm_configured ? 'success' : 'warning'">
          {{ health.llm_configured ? '通义 API 已配置' : '通义 API 未配置' }}
        </el-tag>
      </div>
    </template>

    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      accept=".pdf,.docx"
      :on-change="handleFileChange"
      :disabled="uploading"
    >
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 PDF、Word（.docx），最大 20MB</div>
      </template>
    </el-upload>

    <div v-if="selectedFile" class="file-info">
      <el-text>已选择：{{ selectedFile.name }}（{{ formatSize(selectedFile.size) }}）</el-text>
      <el-button type="primary" :loading="uploading" @click="submitUpload">开始分析</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="mt-16"
    />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { checkHealth, uploadDocument } from '../api/document'

const router = useRouter()
const selectedFile = ref(null)
const uploading = ref(false)
const error = ref('')
const health = ref(null)

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function handleFileChange(file) {
  error.value = ''
  selectedFile.value = file.raw
}

async function submitUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = ''
  try {
    const result = await uploadDocument(selectedFile.value)
    ElMessage.success('上传成功，正在分析')
    router.push(`/tasks/${result.id}`)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  try {
    health.value = await checkHealth()
  } catch {
    health.value = { llm_configured: false }
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.upload-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 8px;
}
.file-info {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.mt-16 {
  margin-top: 16px;
}
</style>
