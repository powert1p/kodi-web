// Телеметрия UX (Блок 1.0): fire-and-forget POST /api/trainer/events.
// НИКОГДА не блокирует UX и не бросает — все ошибки глотаются.

const STORAGE_KEY = 'kodi.jwt'

/** Отправляет одно событие. Ошибки глотаются (fire-and-forget). */
export async function track(eventType: string, payload?: Record<string, unknown>): Promise<void> {
  try {
    let token: string | null = null
    try {
      token = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
    } catch { /* localStorage недоступен */ }
    if (!token) return
    await fetch('/api/trainer/events', {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ events: [{ event_type: eventType, payload: payload ?? null }] }),
    })
  } catch {
    // fire-and-forget: телеметрия не должна ронять UX
  }
}
