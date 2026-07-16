# Frozen acceptance rubric

## Critical binary gates

Все пункты обязательны:

- `GET /` и `GET /app` не отдают Flutter HTML и приводят к `/app/`.
- `/app/` и все React deep links отдают PWA; отсутствующий asset остаётся 404.
- новый номер можно зарегистрировать через реальный UI без заранее созданных данных;
- после submit регистрации первый математический activity виден без дополнительного клика;
- от submit регистрации до первого activity нет dashboard, диагностики, review, фото или чата;
- ребёнка не просят объявлять себя родителем; фото-согласие не входит в детскую регистрацию;
- lesson id берётся из авторитетного `/api/learning/path/current`, а не зашит в auth UI;
- failure получения пути не отменяет созданный аккаунт и даёт восстановимый экран;
- reload и повторный login сразу возвращают в тот же серверный lesson state и не создают дубликат session;
- на 375×844 и 1280×900: unexpected console/page/request errors = 0, horizontal overflow = 0;
- primary touch target ≥44 px, keyboard focus видим, loading/error states доступны;
- полный frontend/backend gate зелёный, production image собран из проверенного tree;
- публичный synthetic CJM после деплоя проходит регистрацию → урок → meaningful action → reload.

## Quality axes (0–10)

| Ось | Что значит 10 |
|---|---|
| time-to-learning | Математика появляется сразу после регистрации |
| decision clarity | На каждом экране одна очевидная следующая операция |
| continuity | Reload/relogin восстанавливает тот же серверный контекст |
| error recovery | Ошибка сети не теряет аккаунт и объясняет восстановление |
| child readability | Условие, действие и feedback читаются без UI-шума |
| mobile ergonomics | 375 px работает одной рукой без overflow и мелких targets |
| trust | Нет ложных обещаний, скрытых ответов и browser-only прогресса |
| production cohesion | Один публичный продукт, без legacy split-brain |

READY: каждый critical gate PASS, каждая ось ≥8.0, среднее ≥8.5, все обязательные reviewers
дают `READY`. Два acceptance-провала подряд требуют replan, не третью косметическую итерацию.
