import { useState, type CSSProperties } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Mascot } from '../../components/Mascot'
import { ApButton } from '../../components/ApButton'
import { ApCard } from '../../components/ApCard'
import { postConsent } from '../../lib/api'
import { ME_QUERY_KEY } from '../auth/useMe'

/** Ключ sessionStorage — «Позже» скрывает карточку до конца сессии (переживает переход по разделам). */
export const CONSENT_DISMISS_KEY = 'kodi.consent.dismissed'

/** true — пользователь уже нажал «Позже» в этой сессии. */
export function isConsentDismissed(): boolean {
  try {
    return sessionStorage.getItem(CONSENT_DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

interface ConsentCardProps {
  /** Задержка stagger-reveal в мс (позиция в общей ленте hub). Игнорируется, если задан onDismiss (drill). */
  delay?: number
  /** Вызывается ПОСЛЕ успешного сохранения согласия — например, вернуть фото-поток к повтору (drill). */
  onGranted?: () => void
  /**
   * «Позже» в кастомном режиме (drill-403): передай свой обработчик — сессионный dismiss НЕ трогаем
   * (это не тот же отказ, что на хабе, — карточка должна вернуться при следующей попытке фото).
   * Не задан — карточка сама скрывается на сессию (сценарий hub).
   */
  onDismiss?: () => void
}

// Мягкое напоминание про согласие на фото (DESIGN_SYSTEM §0/§5): тёплый амбер —
// «не сошлось», НЕ тревога и НЕ красный. Единственный primary-CTA карточки — «Разрешаю».
// Переиспользуется в двух местах: хаб (photo_consent == null, самостоятельный dismiss)
// и drill при 403 от /trainer/diagnose (сервер требует согласие, dismiss = продолжить без фото).
export function ConsentCard({ delay = 0, onGranted, onDismiss }: ConsentCardProps) {
  const queryClient = useQueryClient()
  // В hub-режиме (onDismiss не задан) карточка сама себя скрывает по сессионному флагу —
  // нужно и при первом маунте (пришли на хаб заново), и мгновенно по клику «Позже».
  const [hiddenLocally, setHiddenLocally] = useState(() => !onDismiss && isConsentDismissed())

  const grant = useMutation({
    mutationFn: () => postConsent(true),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
      onGranted?.()
    },
  })

  function handleDismiss() {
    if (onDismiss) {
      onDismiss()
      return
    }
    try {
      sessionStorage.setItem(CONSENT_DISMISS_KEY, '1')
    } catch {
      // sessionStorage недоступен (приватный режим) — карточка вернётся при перезагрузке, не критично
    }
    setHiddenLocally(true)
  }

  if (hiddenLocally) return null

  return (
    <ApCard
      as="section"
      tone="attn-soft"
      padding="m"
      className="reveal flex flex-col gap-4"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="flex items-start gap-3">
        <Mascot mood="thinking" size="m" className="shrink-0" />
        <div className="flex flex-col gap-1 pt-0.5">
          <h3 className="text-h3 text-ink">Спросим родителя</h3>
          <p className="text-body text-text">
            Чтобы разбирать ошибки по фото, нужно согласие родителя на использование снимков.
          </p>
        </div>
      </div>

      {grant.isError && (
        <p className="text-caption1 text-attn">Не сохранилось — попробуй ещё раз.</p>
      )}

      <div className="flex items-center gap-3">
        <ApButton
          variant="primary"
          size="m"
          className="flex-1"
          loading={grant.isPending}
          disabled={grant.isPending}
          onClick={() => grant.mutate()}
        >
          Разрешаю
        </ApButton>
        <ApButton
          variant="ghost"
          size="m"
          disabled={grant.isPending}
          onClick={handleDismiss}
        >
          Позже
        </ApButton>
      </div>
    </ApCard>
  )
}
