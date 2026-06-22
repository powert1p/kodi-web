# kodi-web Deploy — self-hosted VPS (план revival, по образцу CDP)

> Статус: **план** (на 2026-06-22 ещё на Railway / не задеплоен). Финализируется на фазе 3, после чего этот файл = факт.

## Цель
- Уйти с Railway на **свой VPS** (тот же сервер, что CDP: ssh-хост `aiplus`, **sudo НЕТ** — nginx/SSL правит только root).
- Docker Compose: сервис `app` (образ kodi-web: Flutter-статика + FastAPI same-origin) + свой `postgres` (отдельный volume, bind-mount).
- Наружу — host nginx vhost (нужен root) → `proxy_pass` на localhost-порт контейнера. Прямой публичный порт ЗАКРЫТ.

## Порты (ПРОВЕРИТЬ свободность на хосте ПЕРЕД up)
- Заняты: системный PG `5432`, CDP postgres `127.0.0.1:5434`, CDP api `127.0.0.1:8200`.
- Брать свежие: api `127.0.0.1:8300`, postgres `127.0.0.1:5435` (или первые свободные — `ss -ltn` на хосте).

## Pre-deploy чеклист (из аудита — без этого ломается)
1. `backend/fonts/DejaVuSerif.ttf` в git (иначе Docker build падает — P0 BUILD-1).
2. `JWT_SECRET` — выделенный случайный 32+ байт в env VPS (не пустой, не BOT_TOKEN — P0 SEC-1).
3. `CORS_ORIGINS` = домен VPS (убрать мёртвый Railway-URL — P0 SEC-2).
4. exam/start `IN :seen` пофикшен (P0 API-1).
5. uvicorn **single-worker** + `proxy_headers=True` + `forwarded_allow_ips=<nginx-ip>` (ARCH-1/OPS-1).
6. Стартовать со **свежей БД** — `create_all` строит полную схему (обойти migration-gap MIG-1). Старые Railway-данные НЕ переносим.
7. `.dockerignore` есть (не тянуть build-артефакты в контекст).

## Путь деплоя (после финализации)
- rsync изменённых файлов в `~/kodi-web/` на сервере → `ssh aiplus 'cd ~/kodi-web && docker compose build app && docker compose up -d'` → health-check → лог.
- НЕ railway up, НЕ git push (авто-деплоя нет).

## Cutover-порядок (vault: paas-to-self-hosted-cutover-order)
- Личный проект, данные тестовые → миграция данных НЕ нужна (старт со свежей БД). Если когда-то понадобится: дамп→restore→smoke→стоп источника→секреты→DNS последним.

## Health
- Нужен `/health` эндпоинт (проверить наличие; если нет — добавить, P-инфра). После деплоя: `curl https://<domain>/health` → 200.

## Known issues (заполнить по факту фазы 3)
- nginx vhost/SSL требует root (Умид) — внешняя зависимость; до vhost доступ через SSH-туннель.
