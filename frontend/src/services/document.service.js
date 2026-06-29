import http from '../api/http'
import { USE_MOCK } from './config'
import { delay } from '../api/mock/delay'
import { cloneData } from '../utils/browser'

const mockStructure = {
  node_id: 'root',
  parent_id: null,
  title: 'ROOT',
  kind: 'root',
  children: [
    {
      node_id: 'node_1',
      parent_id: 'root',
      label: '第一章',
      title: '合同主体',
      kind: 'chapter',
      page_no: 1,
      source_ref: '#/texts/1',
      content: [{ source_ref: '#/texts/2', text: '甲方：华城数字建设有限公司\n乙方：云启科技有限公司' }],
      warnings: [],
      children: [],
    },
  ],
}

export async function getDocument(fileId) {
  if (USE_MOCK) {
    return delay({
      document: {
        file_id: fileId,
        schema_name: 'MockContractDocument',
        origin: { filename: '智慧园区软件采购合同.docx' },
        has_structure: true,
        chapter_count: 1,
        warning_count: 0,
      },
    })
  }
  const { data } = await http.get(`/documents/${fileId}`)
  return data
}

export async function getDocumentStructure(fileId) {
  if (USE_MOCK) {
    return delay({
      meta: { schema_name: 'MockContractDocument', file_id: fileId },
      structure: cloneData(mockStructure),
    })
  }
  const { data } = await http.get(`/documents/${fileId}/structure`)
  return data
}

export async function saveDocumentStructure(fileId, structure) {
  if (USE_MOCK) return delay({ message: '结构已保存' })
  const { data } = await http.put(`/documents/${fileId}/structure`, { structure })
  return data
}
