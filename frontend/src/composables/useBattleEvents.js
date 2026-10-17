import { onUnmounted, reactive } from 'vue'

const priority = { accepted: 1, leader: 2, first: 3, final: 4 }
const duration = { accepted: 1100, leader: 2400, first: 2600, final: 3000 }

export function useBattleEvents(onShow = () => {}) {
  const event = reactive({ visible: false, title: '', subtitle: '', kind: 'round', stamp: 0 })
  const pending = [], seen = new Map()
  let timer, batchTimer, sequence = 0
  function schedule(delay = 240) {
    if (event.visible || batchTimer || !pending.length) return
    batchTimer = setTimeout(() => {
      batchTimer = undefined
      pending.sort((a, b) => b.priority - a.priority || a.order - b.order)
      const next = pending.shift()
      if (!next) return
      Object.assign(event, { positionText: '', deltaText: '', streakText: '', points: null }, next,
        { visible: true, stamp: ++sequence })
      onShow(event)
      timer = setTimeout(dismiss, duration[next.kind] || 2600)
    }, delay)
  }
  function push(payload) {
    const group = payload.group || `event:${++sequence}`
    const rank = priority[payload.kind] || 0
    // A late acceptance cannot replay or replace a final result. Close events
    // for the same match collapse during the short initial batching window.
    if (seen.has(group) && seen.get(group) >= rank) return
    seen.set(group, rank)
    if (seen.size > 200) seen.delete(seen.keys().next().value)
    const previous = pending.findIndex(item => item.group === group)
    if (previous !== -1) pending.splice(previous, 1)
    pending.push({ ...payload, group, priority: rank, order: ++sequence })
    if (pending.length > 8) {
      pending.sort((a, b) => b.priority - a.priority || a.order - b.order)
      pending.pop()
    }
    schedule()
  }
  function dismiss() {
    clearTimeout(timer)
    event.visible = false
    schedule(180)
  }
  function reset() {
    clearTimeout(timer)
    clearTimeout(batchTimer)
    batchTimer = undefined
    pending.length = 0
    seen.clear()
    event.visible = false
  }
  onUnmounted(reset)
  return { event, push, dismiss, reset }
}
