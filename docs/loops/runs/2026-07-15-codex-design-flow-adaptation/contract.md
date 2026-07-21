# Contract — перенос нового design/loop flow в Codex

## Цель

Переадаптировать восстановленный 2026-07-15 Claude-flow в исполнимый Codex-flow для
`kodi-web`: Codex остаётся implementer'ом и владельцем интеграции, а полноценный цикл
улучшает генератор дизайна, а не бесконечно полирует первый артефакт.

## Источники истины

- намерение владельца в текущей задаче;
- `~/Documents/design-lab/FLOW.md` и сегодняшний `FLOW-CHANGELOG.md`;
- `~/.claude/workflow.md` и `~/.claude/skills/benchmark-loop/SKILL.md` как evidence исходного
  поведения, но не как runtime dependency;
- локальные `AGENTS.md`, `docs/VISION.md` и `docs/loops/rubric-design.md`.

## Scope

- глобальный Codex skill `~/.agents/skills/benchmark-loop/`;
- routing в `~/.agents/skills/codex-brainstorming/SKILL.md` и `~/.codex/AGENTS.md`;
- generator inputs `~/.agents/skills/frontend-design/SKILL.md` и `~/.codex/rubrics/design.md`;
- проектный профиль `docs/loops/DESIGN-FLOW.md`;
- минимальные ссылки и инварианты в `webapp/AGENTS.md`, `docs/loops/rubric-design.md` и
  `docs/loops/FLOW-CHANGELOG.md`.

## Non-goals

- новый визуальный редизайн `webapp/` в этом run'е;
- изменение текущего `webapp/DESIGN_SYSTEM.md` или frozen evidence прошлых run'ов;
- запуск внешнего `codex`, Claude/Opus workers или зависимость от Claude-only hooks;
- деплой, публикация или изменение production data.

## Роли

- maker/integrator: текущий корневой Codex;
- judges: минимум два независимых native Codex reviewers, не участвовавших в maker-правках;
- механические проверки и итоговый синтез: корневой Codex.

## Frozen gate

- rubric: `RUBRIC.md`;
- frozen SHA-256: `RUBRIC.sha256` после первого сохранения;
- READY: все бинарные пункты rubric зелёные, `git diff --check` зелёный и оба независимых
  reviewer'а не находят блокирующей дельты;
- `NOT_RUN` и `BLOCKED` не считаются PASS.

## Stop policy

READY допустим только после frozen gate. Бюджет или plateau до READY фиксируются как
`NOT_READY`, а не как «готово». Изменение rubric после SHA создаёт новый run.
