# Dogfood Report: AiPlus learning journey

| Field | Value |
|-------|-------|
| **Date** | 2026-07-15 |
| **App URL** | http://127.0.0.1:8399/app/ |
| **Session** | kodi-r5-mobile |
| **Scope** | Новый путь: регистрация → выбор темы → объяснение → guided practice → самостоятельная задача → перенос → результат; mobile 375×844 и desktop 1280×900 |

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| **Total** | **0** |

## Issues

### INVALIDATED-001: Новый ученик не может начать урок в загрязнённой QA DB

| Field | Value |
|-------|-------|
| **Severity** | invalidated — не дефект продукта |
| **Category** | functional |
| **URL** | http://127.0.0.1:8399/app/learn/mixtures-1 |
| **Repro Video** | videos/issue-001-start-lesson-503.webm |

**Description**

После успешной регистрации кнопка «Начать урок» возвращала `503`. Root cause: full pytest по ошибке был параллельно направлен в ту же локальную PostgreSQL DB и заменил canonical problem rows тестовыми данными. После запуска release image, который повторно выполнил недеструктивный canonical sync, тот же аккаунт восстановил урок и открыл шаг 1. На VPS тесты не запускаются против app DB. На продуктовый issue не засчитывается; evidence сохранён как контроль test-isolation.

**Repro Steps**

1. Войти под новым учеником.
   ![Login](screenshots/issue-001-step-1.png)
2. На странице пути нажать «Продолжить».
   ![Path](screenshots/issue-001-step-2.png)
3. **Observe:** вместо объяснения появляется невосстанавливаемый error state.
   ![Result](screenshots/issue-001-result.png)
