// Движок авторинга reasoning-лесенок: автор -> критик -> (<=1 правка) на задачу.
// Промпты простые, на принципах: лесенка = логические шаги самого решения, ничего лишнего.
// Читаемые копии — engine/author-prompt.md / engine/critic-prompt.md (держать в синхроне!).
// args = { tasks: TaskRecord[] }
// TaskRecord = { node_id, topic, statement_ru, answer, primary_micro_skill, steps:[{n,instruction_ru,micro_skill,expected_value}], wrong_answer?, misconception? }
export const meta = {
  name: 'ladder-authoring-engine',
  description: 'Author reasoning-ladders from grounded tasks: author -> critic -> revise',
  phases: [
    { title: 'Author', detail: 'one author agent per task (grounded on steps[])' },
    { title: 'Critic', detail: 'rubric critic per ladder' },
    { title: 'Revise', detail: 'one revision pass if critic says revise' },
  ],
}

const AUTHOR = [
  'Ты собираешь «лесенку понимания»: ребёнок (10–17 лет, НИШ, RU/KZ) завалил задачу из среза, и ты ведёшь его к решению маленькими шагами — не выдаёшь ответ, а даёшь дойти самому.',
  '',
  '# Что тебе дают',
  'Условие, верный ответ, проверенное пошаговое решение steps[] (числа бери отсюда) и где/как ответил ребёнок неверно (если данных нет — назови сам типичную ошибку этого навыка).',
  '',
  '# Как строить',
  'Лесенка = логические шаги ЭТОГО решения. Структуру бери из steps[], не выдумывай. На том ОДНОМ шаге, где ребёнок свернул не туда -> choose (2–3 коротких варианта, ловушка = его реальная ошибка, не выдуманная). Остальные шаги -> compute (ребёнок вводит число или дробь). Арифметику и «почему» держи в reveal — он показывается только при затыке. По-русски, тепло, без назидания. Математику в инструкциях/вариантах — в $...$ (KaTeX), дроби в answer — ASCII (например 3/8).',
  '',
  '# Definition of Done — лесенка готова, только если КАЖДЫЙ пункт «да». Прогони все 7 перед выдачей; не выполнено — переделай.',
  '1. Один смысловой ход = одна ступень. Ступень — это новая мысль решения, а не отдельное арифметическое действие. «Цена выросла на 20%» — одна ступень, не «найди 20%» + «прибавь». Тест: две соседние ступени — это «посчитай кусок» и «подставь его» одного действия -> слей в одну.',
  '2. Каждая ступень нужна. Убери ступень — следующая перестаёт решаться (или это финальный ответ). Тест: можно выкинуть, а ответ всё равно собирается -> выкинь.',
  '3. Один вопрос на ступень. Ровно одно искомое. Никаких «и» — два действия или две величины в одной ступени -> разбей или убери лишнее.',
  '4. Вопрос не содержит свой ответ. В формулировке нет ни искомого числа, ни готового выражения, ни подсказки верной стороны. Запрещено в тексте вопроса: «(½ от ¾)», «1/6−1/15», «180·(100+995)/2» — это уносим в reveal. Считает/выбирает ребёнок, не вопрос.',
  '5. Нет ступеней-пересказов и «теории ошибки». Ступень что-то вычисляет/решает, а не повторяет уже сделанный вывод и не читает лекцию «почему ты ошибся». Объяснение — только в reveal.',
  '6. Этапы последовательны и однородны. По порядку, каждый опирается на предыдущий, без скачков. Одинаковое действие (например, перевод слов в выражения) делай в одном месте — не «одно сейчас, остальное даром потом». Тест: появилось готовое выражение, которого ребёнок раньше не выводил -> это утечка.',
  '7. Лесенка доводит до ответа. Последняя ступень даёт финальный ответ задачи.',
  '',
  '# Выход',
  'Верни ТОЛЬКО JSON: { "rungs": [ { "type":"compute|choose", "prompt_ru":"...", "options_ru":["...","..."] (только для choose, 2–3 коротких варианта), "answer":"...", "reveal_ru":"..." (коротко, 1–2 строки; арифметика и «почему» — здесь), "_kc":"<один микро-навык>", "_targets":"<что именно решает эта ступень>" } ] }',
  'Думай в уме — поле reasoning не выводи. Лишних полей не добавляй.',
].join('\n')

const CRITIC = [
  'Ты — строгий ревьюер «лесенок понимания». Тебе дают условие задачи, проверенное пошаговое решение steps[], ошибку ребёнка и ЛЕСЕНКУ автора (rungs[]). Проверь её против Definition of Done. Ты не переписываешь сам — называешь ступень, нарушение и конкретную правку.',
  '',
  '# Сначала — план (1–2 строки)',
  'Какова логика решения (из steps[]) и где ребёнок свернул.',
  '',
  '# Definition of Done — лесенка готова, только если КАЖДЫЙ пункт «да». Проверь все 7.',
  '1. Один смысловой ход = одна ступень. Ступень — новая мысль решения, не отдельное арифметическое действие. «Цена выросла на 20%» — одна ступень, не «найди 20%» + «прибавь». Нарушение: две соседние ступени — «посчитай кусок» и «подставь его» одного действия -> слить.',
  '2. Каждая ступень нужна. Убери ступень — следующая перестаёт решаться (или это финальный ответ). Можно выкинуть, а ответ всё равно собирается -> ступень лишняя.',
  '3. Один вопрос на ступень. Ровно одно искомое. Есть «и» / два действия / две величины -> нарушение, разбить.',
  '4. Вопрос не содержит свой ответ. В формулировке нет искомого числа, готового выражения, подсказки верной стороны. «(½ от ¾)», «1/6−1/15», «180·(100+995)/2» в тексте вопроса -> нарушение, унести в reveal. Тест: понявший и непонявший ответили бы по-разному?',
  '5. Нет ступеней-пересказов и «теории ошибки». Ступень вычисляет/решает, а не повторяет вывод и не объясняет «почему ошибся». Иначе -> нарушение, выкинуть (объяснение в reveal).',
  '6. Этапы последовательны и однородны. По порядку, каждый опирается на предыдущий, без скачков. Одинаковое действие разбросано «одно сейчас, остальное даром потом», или появилось выражение, которого ребёнок не выводил -> нарушение (утечка/непоследовательность).',
  '7. Лесенка доводит до ответа. Последняя ступень даёт финальный ответ задачи.',
  '',
  '# Вердикт',
  'Для каждого нарушения выпиши {rung_index, issue, fix}. Верни JSON: { "plan":"...", "findings":[{rung_index, issue, fix}], "verdict":"accept|revise", "needs_human":bool, "confidence":"high|medium|low" }',
  'verdict="revise" при нарушении любого пункта. needs_human=true, если числа лесенки расходятся со steps[]. findings пуст -> accept. Каждая находка конкретна: какая ступень, какой пункт DoD нарушен, как починить. Без общих «в целом норм».',
].join('\n')

const LADDER_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    rungs: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          type: { type: 'string', enum: ['compute', 'choose'] },
          prompt_ru: { type: 'string' },
          options_ru: { type: 'array', items: { type: 'string' } },
          answer: { type: 'string' },
          reveal_ru: { type: 'string' },
          _kc: { type: 'string' },
          _targets: { type: 'string' },
        },
        required: ['type', 'prompt_ru', 'answer', 'reveal_ru', '_kc', '_targets'],
      },
    },
  },
  required: ['rungs'],
}

const CRITIC_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    plan: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          rung_index: { type: 'number' }, issue: { type: 'string' }, fix: { type: 'string' },
        },
        required: ['rung_index', 'issue', 'fix'],
      },
    },
    verdict: { type: 'string', enum: ['accept', 'revise'] },
    needs_human: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['plan', 'findings', 'verdict', 'needs_human', 'confidence'],
}

const _a = typeof args === 'string' ? JSON.parse(args) : (args || {})
const tasks = _a.tasks || []
log(`engine: получено задач = ${tasks.length}`)

const taskBlock = (t) =>
  '=== ЗАДАЧА (grounding) ===\n' +
  JSON.stringify(
    {
      node_id: t.node_id, topic: t.topic, statement_ru: t.statement_ru,
      answer: t.answer, primary_micro_skill: t.primary_micro_skill, steps: t.steps,
      wrong_answer: t.wrong_answer ?? '(нет данных — назови самую частую ошибку навыка сам)',
      misconception: t.misconception ?? '(определи сам)',
    },
    null, 1,
  )

const results = await pipeline(
  tasks,
  (t) =>
    agent(AUTHOR + '\n\n' + taskBlock(t), {
      label: `author:${t.node_id}`, phase: 'Author', schema: LADDER_SCHEMA, effort: 'medium',
    }),
  (ladder, t) =>
    // критик — best-effort: если он умер (StructuredOutput retry cap и т.п.),
    // author-лесенку НЕ теряем, помечаем critic:null (нужен ручной взгляд).
    agent(CRITIC + '\n\n' + taskBlock(t) + '\n\n=== ЛЕСЕНКА ОТ АВТОРА ===\n' + JSON.stringify(ladder, null, 1), {
      label: `critic:${t.node_id}`, phase: 'Critic', schema: CRITIC_SCHEMA,
    }).catch(() => null).then((critic) => ({ ladder, critic })),
  (cr, t) => {
    if (!cr || !cr.critic || cr.critic.verdict === 'accept') {
      return { node_id: t.node_id, ladder: cr?.ladder ?? null, critic: cr?.critic ?? null, revised: false }
    }
    return agent(
      AUTHOR + '\n\n' + taskBlock(t) +
        '\n\n=== ТВОЯ ПРЕДЫДУЩАЯ ЛЕСЕНКА ===\n' + JSON.stringify(cr.ladder, null, 1) +
        '\n\n=== ЗАМЕЧАНИЯ КРИТИКА (исправь ТОЧЕЧНО) ===\n' + JSON.stringify(cr.critic.findings, null, 1),
      { label: `revise:${t.node_id}`, phase: 'Revise', schema: LADDER_SCHEMA, effort: 'medium' },
    ).then((l2) => ({ node_id: t.node_id, ladder: l2, critic: cr.critic, revised: true }))
  },
)

return { count: results.filter(Boolean).length, results }
