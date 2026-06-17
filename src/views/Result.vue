<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/tasks')" content="分析结果" class="mb-16" />

    <el-card v-if="task">
      <template #header>
        <div class="card-header">
          <div>
            <div class="filename">{{ task.filename }}</div>
            <el-tag :type="statusType(task.status)" class="mt-8">{{ statusLabel(task.status) }}</el-tag>
          </div>
          <el-button
            v-if="task.status === 'completed' || task.status === 'failed'"
            @click="handleReanalyze"
            :loading="reanalyzing"
          >
            重新分析
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="task.status === 'failed'"
        :title="task.error_message || '处理失败'"
        type="error"
        show-icon
        :closable="false"
        class="mb-16"
      />

      <el-alert
        v-if="isProcessing"
        title="正在解析或分析中，页面将自动刷新..."
        type="info"
        show-icon
        :closable="false"
        class="mb-16"
      />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="结构化摘要" name="summary">
          <template v-if="task.analysis_result">
            <el-descriptions :column="1" border>
              <el-descriptions-item
                v-for="field in summaryFields"
                :key="field.key"
                :label="field.label"
              >
                <template v-if="Array.isArray(task.analysis_result[field.key])">
                  <ul v-if="task.analysis_result[field.key].length" class="list">
                    <li v-for="(item, idx) in task.analysis_result[field.key]" :key="idx">{{ item }}</li>
                  </ul>
                  <span v-else>-</span>
                </template>
                <span v-else>{{ task.analysis_result[field.key] || '-' }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="暂无分析结果" />
        </el-tab-pane>

        <el-tab-pane name="chapters">
          <template #label>
            章节结构
            <el-badge
              v-if="task.chapters && task.chapters.length"
              :value="task.chapters.length"
              type="primary"
              class="tab-badge"
            />
          </template>
          <template v-if="task.chapters && task.chapters.length">
            <el-collapse>
              <el-collapse-item
                v-for="(ch, idx) in task.chapters"
                :key="idx"
                :name="idx"
              >
                <template #title>
                  <span class="chapter-title" :style="{ paddingLeft: (ch.level || 0) * 16 + 'px' }">
                    <el-tag size="small" :type="levelTagType(ch.level)" class="chapter-level">
                      {{ ch.level === 0 ? '前言' : 'H' + ch.level }}
                    </el-tag>
                    {{ ch.title }}
                  </span>
                </template>
                <pre class="chapter-content">{{ ch.content }}</pre>
              </el-collapse-item>
            </el-collapse>
          </template>
          <el-empty v-else description="未识别到章节结构" />
        </el-tab-pane>

        <el-tab-pane label="解析原文" name="text">
          <el-input
            v-if="task.parsed_text"
            type="textarea"
            :rows="20"
            :model-value="task.parsed_text"
            readonly
          />
          <el-empty v-else description="暂无解析文本" />
        </el-tab-pane>

        <el-tab-pane label="元信息" name="meta">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="任务 ID">{{ task.id }}</el-descriptions-item>
            <el-descriptions-item label="文件类型">{{ task.file_type }}</el-descriptions-item>
            <el-descriptions-item label="页数">{{ task.page_count ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(task.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatTime(task.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDocument, reanalyzeDocument } from '../api/document'

const route = useRoute()
const task = ref(null)
const loading = ref(false)
const reanalyzing = ref(false)
const activeTab = ref('summary')
let timer = null

const summaryFields = [
  { key: '合同名称', label: '合同名称' },
  { key: '甲方', label: '甲方' },
  { key: '乙方', label: '乙方' },
  { key: '合同金额', label: '合同金额' },
  { key: '履行期限', label: '履行期限' },
  { key: '付款方式', label: '付款方式' },
  { key: '违约责任', label: '违约责任' },
  { key: '争议解决', label: '争议解决' },
  { key: '风险点', label: '风险点' },
  { key: '关键条款摘要', label: '关键条款摘要' },
  { key: '免责声明', label: '免责声明' },
]

const STATUS_MAP = {
  pending: { label: '待处理', type: 'info' },
  parsing: { label: '解析中', type: 'warning' },
  parsed: { label: '已解析', type: 'warning' },
  analyzing: { label: '分析中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

const isProcessing = computed(() =>
  ['pending', 'parsing', 'parsed', 'analyzing'].includes(task.value?.status)
)

function statusLabel(status) {
  return STATUS_MAP[status]?.label || status
}

function statusType(status) {
  return STATUS_MAP[status]?.type || 'info'
}

function levelTagType(level) {
  return ['info', 'primary', 'success', 'warning', 'danger'][level] || 'info'
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

async function loadTask() {
  loading.value = true
  try {
    task.value = await getDocument(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleReanalyze() {
  reanalyzing.value = true
  try {
    await reanalyzeDocument(route.params.id)
    ElMessage.success('已重新提交分析')
    await loadTask()
    startPolling()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    reanalyzing.value = false
  }
}

function startPolling() {
  stopPolling()
  timer = setInterval(async () => {
    if (!isProcessing.value) {
      stopPolling()
      return
    }
    try {
      task.value = await getDocument(route.params.id)
      if (!isProcessing.value) stopPolling()
    } catch {
      // ignore polling errors
    }
  }, 3000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(async () => {
  await loadTask()
  if (isProcessing.value) startPolling()
})

onUnmounted(stopPolling)
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.mt-8 {
  margin-top: 8px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.filename {
  font-size: 16px;
  font-weight: 600;
}
.list {
  margin: 0;
  padding-left: 18px;
}
.tab-badge {
  margin-left: 6px;
}
.chapter-title {
  display: inline-flex;
  align-items: center;
  font-size: 14px;
}
.chapter-level {
  margin-right: 8px;
}
.chapter-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  color: #606266;
  background: #f8f9fb;
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
}
</style>
