const memoryStore = new Map()

export function getStoredItem(key, fallback = '') {
  try {
    return window.localStorage.getItem(key) || memoryStore.get(key) || fallback
  } catch {
    return memoryStore.get(key) || fallback
  }
}

export function setStoredItem(key, value) {
  memoryStore.set(key, value)
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* Storage can be unavailable in strict browser privacy modes. */
  }
}

export function removeStoredItem(key) {
  memoryStore.delete(key)
  try {
    window.localStorage.removeItem(key)
  } catch {
    /* Storage can be unavailable in strict browser privacy modes. */
  }
}

export function cloneData(value) {
  if (typeof structuredClone === 'function') return structuredClone(value)
  return JSON.parse(JSON.stringify(value))
}
