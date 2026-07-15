// Хук профиля текущего студента (/auth/me) — источник photo_consent
// для consent-UI (hub-карточка «Спросим родителя», drill 403).
import { useQuery } from '@tanstack/react-query'
import { fetchMe } from '../../lib/auth'
import { useLearningIdentity } from '../../lib/api'

/** Ключ react-query для профиля — используется и для инвалидации после postConsent. */
export const ME_QUERY_KEY = ['me'] as const

export function useMe() {
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: [...ME_QUERY_KEY, identity],
    queryFn: fetchMe,
    staleTime: 60_000,
  })
}
