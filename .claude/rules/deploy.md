# kodi-web Deploy — self-hosted VPS (по образцу CDP)

> Статус: **задеплоен** (2026-06-22) на сервер AiPlus (тот же, что CDP). Контейнеры `kodi-app`/`kodi-postgres` живы, `/health` → 200.

## Факт (что есть сейчас)
- Сервер: ssh-хост `aiplus` (user `eset`), compose-дир `~/kodi-web`, Docker 26.1.3, **sudo НЕТ**.
- Контейнеры: `kodi-app` (127.0.0.1:8300→8000), `kodi-postgres` (127.0.0.1:5435→5432, bind-mount `~/kodi-web/pgdata`). Свежая БД, seed 118 нод/2525 задач.
- **Публичный вход (с 2026-07-20) — cloudflared quick-туннель**: контейнер `kodi-tunnel` (orphan вне compose, `tunnel --url http://app:8000`, restart unless-stopped, фикс-IP `172.30.57.4` в сети `kodi-web_kodi-internal` 172.30.57.0/24). ⚠️ **URL меняется при КАЖДОМ рестарте туннеля** — актуальный брать `docker logs kodi-tunnel | grep -o 'https://.*trycloudflare.com' | tail -1`. Стабильный домен (named tunnel или nginx vhost от root/Умида) — бэклог.
- ⚠️ **Перед recreate контейнеров сверяй env ЖИВОГО контейнера** (`docker inspect kodi-app --format '{{.Config.Env}}'`) с тем, что даст новый compose: сервер-специфика живёт в `~/kodi-web/.env` (`FORWARDED_ALLOW_IPS=<gateway>,<tunnel-ip>`, `OWNER_STUDENT_ID`), НЕ в форке compose (кейс 2026-07-21: git-archive затёр серверный compose со старой сетью 172.28.0.0/16 → recreate упал; значения восстановлены из env живого контейнера, compose переведён на `${FORWARDED_ALLOW_IPS:-…}`). Туннель после пересборки сети: `docker network connect --ip 172.30.57.4 … kodi-tunnel && docker restart kodi-tunnel`.
- **Image-parity деплой (основной путь с 2026-07-21):** кандидата НЕ пересобирать на сервере — `docker save <tag> | gzip | ssh aiplus 'gunzip | docker load'` (~3 мин); Image ID может смениться (containerd-стор мака ↔ classic сервера пересериализует манифест) — паритет сверять по `RootFS.Layers`. Активация: `docker tag kodi-web:online kodi-web:rollback-before-<slug>` → `docker tag <tag> kodi-web-app:latest && docker tag <tag> kodi-web:online` → `docker compose up -d --no-build` → `/ready` (все checks true).
- Деплой апдейта: СНАЧАЛА `ssh aiplus 'cd ~/kodi-web && rm -rf webapp backend'` (архив/tar поверх НЕ удаляет файлы, удалённые из git — стейловый .ts сломал tsc-сборку 2026-07-10), затем `git archive HEAD | ssh aiplus 'cd ~/kodi-web && tar -x'` → `docker compose build app && docker compose up -d` → health → лог. ⚠️ Exit-код build не глотать пайпом в `tail` (лог в файл, потом tail). ⚠️ Builder-кэш на сервере периодически вычищен → build перекачивает базовые слои ~1.7GB на ~1.3MB/s (кейс 2026-07-14: ~25 мин) — закладывай время и держи build в фоновой задаче, не в интерактивном ssh. pgdata/error_photos/backups/.env — top-level, чистка webapp/backend их не задевает. Секреты — в `~/kodi-web/.env` на сервере (НЕ в git).

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
