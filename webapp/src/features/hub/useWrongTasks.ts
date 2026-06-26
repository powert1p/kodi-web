import { useQuery } from '@tanstack/react-query'
import type { WrongTask } from '../../lib/types'
import { MOCK_WRONG_TASKS } from './mock'

// В DEV отдаём мок (с искусственной задержкой, чтобы был виден skeleton).
// В PROD — реальный эндпоинт; форма ответа = WrongTask[].
async function fetchWrongTasks(): Promise<WrongTask[]> {
  if (import.meta.env.DEV) {
    await new Promise((r) => setTimeout(r, 700))
    return MOCK_WRONG_TASKS
  }

  const res = await fetch('/api/srez/wrong-tasks', {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Не удалось загрузить срез (${res.status})`)
  }
  return (await res.json()) as WrongTask[]
}

export function useWrongTasks() {
  return useQuery({
    queryKey: ['wrong-tasks'],
    queryFn: fetchWrongTasks,
    staleTime: 60_000,
  })
}
