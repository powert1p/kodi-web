# Concept result — Фокус-станция

## Frozen direction

Выбрано направление **C — «Фокус-станция»**.

Причины:

- оба независимых judge после acceptance delta дали `wow=true`, `critical_flags=0` и
  среднее 9.04/9.05;
- концепт лучше остальных отделяет самостоятельную работу, explicit guided и recovery;
- визуальный язык новый относительно прежней строгой tape-системы и не опирается на mascot;
- evidence-контур показывает только серверные факты: место в маршруте, текущий режим и
  подтверждённое mastery.

## Production translation rules

- Крупный display type использовать только на route/result/lesson transition; condition,
  diagnostic question, feedback и form labels всегда визуально старше декора.
- Orange — action/evidence accent, не page fill.
- Один экран — одна задача и одно доминирующее действие.
- Guided открывается только по явному «Не знаю, как решать» / «Помоги начать», остаётся
  той же задачей и никогда не засчитывается в mastery.
- После guided только новая independent transfer task с одним фото может дать evidence.
- Unreadable, uncertain, wrong-photo, provider/offline — отдельные recoverable states;
  они не записываются как математическая ошибка и не теряют выбранное фото/ввод.
- Для production нужны result, transfer/mastery, resume, processing/uncertain/offline,
  full responsive render, real Gemini и public smoke; concept PASS не является production READY.
