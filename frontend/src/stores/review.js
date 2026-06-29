import { reactive } from 'vue'

// 审核向导跨步骤数据
export const reviewStore = reactive({
  contractId: '',
  fileId: '',
  fileName: '',
  detectedType: '',
  matchConfidence: 0,
  role: '甲方', // 立场：甲方 / 乙方
  selectedPoints: [], // 选中的审核点 id

  reset() {
    this.contractId = ''
    this.fileId = ''
    this.fileName = ''
    this.detectedType = ''
    this.matchConfidence = 0
    this.role = '甲方'
    this.selectedPoints = []
  },
})
