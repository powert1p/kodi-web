# Research notes — webapp v11

## Product research

Источник истины — `docs/VISION.md`, реальные React flows и behavior inventory. Продуктовая единица — не «урок», а короткое восстановление конкретного ошибочного шага с последующей проверкой переноса.

## Asset research

Из пользовательской Google Drive-папки проверены 47 PNG-иллюстраций. Для run отобраны прозрачные оригиналы, покрывающие роли coach, learner, studying и celebration. Это бренд-белки; прежний costume fox исключён.

## UX research retained

- touch targets не меньше 44×44 px;
- минимум 8 px между соседними touch targets;
- понятные loading/error/recovery states;
- error рядом с полем и через `aria-live`/`role=alert`;
- input не очищается после network failure;
- visible keyboard focus;
- `touch-action` для интерактивных controls;
- motion объясняет переход состояния, а не украшает каждый mount.

## Research recommendations deliberately rejected

Автоматический UI-style search предложил Claymorphism, app-store layout, blue/orange palette и Calistoga/Inter. Это противоречит запросу, возрасту аудитории, Cyrillic/Kazakh требованиям и clean-slate запретам. Рекомендация записана как anti-reference; из исследования сохранены только проверяемые UX/accessibility правила.

## Typography gate

Используются только локальные font files с проверяемой Cyrillic поддержкой. Body и controls должны оставаться Onest/Golos-class readable; display-шрифт допускается только короткими фразами и не может делать интерфейс официальным или «постерным» вместо учебного.

## Inference

Для этого продукта «дорого» означает не тёмный luxury и не пустой editorial canvas. Это точный rhythm, уверенная типографика, качественная micro-interaction, мягкая материальность, дисциплина цвета и ощущение, что каждая деталь поддерживает решение задачи.

