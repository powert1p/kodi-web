import { fetchLearningPath } from './api'

/**
 * Новый ученик начинает с первого авторитетного server-side урока.
 * Регистрация уже завершена, поэтому любой сбой здесь не должен отменять аккаунт:
 * корневой экран повторно загрузит путь и покажет своё recoverable состояние.
 */
/** Возвращает авторитетный текущий учебный шаг после любой auth-операции. */
export async function currentLearningDestination(): Promise<string> {
  try {
    const { lesson } = await fetchLearningPath()
    const lessonId = lesson?.primary_action.lesson_id.trim()
    return lessonId ? `/lesson/${encodeURIComponent(lessonId)}` : '/'
  } catch {
    return '/'
  }
}
