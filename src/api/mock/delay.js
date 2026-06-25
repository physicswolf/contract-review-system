// 模拟网络延迟，返回数据的深拷贝，避免 mock 源数据被页面直接修改。
export function delay(data, ms = 360) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(JSON.parse(JSON.stringify(data))), ms)
  })
}

let _seq = 1000
export function nextId(prefix = '') {
  _seq += 1
  return `${prefix}${_seq}`
}
