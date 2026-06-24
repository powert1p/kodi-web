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
  'Ты собираешь «лесенку понимания»: ребёнок (10–17 лет, НИШ, RU/KZ) завалил задачу из среза, и ты ведёшь его к решению маленькими шагами — но не выдаёшь ответ, а даёшь дойти самому.',
  '',
  '# Что тебе дают',
  'Условие, верный ответ, проверенное пошаговое решение steps[] (числа бери отсюда) и что/где ответил ребёнок неверно (если данных нет — назови сам типичную ошибку этого навыка).',
  '',
  '# Главный принцип: лесенка = шаги ЭТОГО решения',
  'Структуру не придумывай — она уже есть в steps[]. Каждая ступень — один настоящий шаг решения, чей результат нужен следующему шагу (или это финальный ответ). Соседние шаги, которые для ребёнка одна мысль, объедини в одну ступень. Ничего, чего нет в решении, не добавляй.',
  '',
  'Проверка КАЖДОЙ ступени: мысленно убери её — следующая ступень всё ещё вычисляется? Если да (её результат никому дальше не нужен и это не ответ) — это пересказ вывода или «теория ошибки», такой ступени в лесенке не место. Нужные вычисления (например «осталось 3/4», то есть 1 минус 1/4) не давай готовыми — это и есть ступень.',
  '',
  '# Как ребёнок отвечает на ступени',
  '- Обычный шаг -> compute: ребёнок сам вводит значение (число или дробь).',
  '- Тот ОДИН шаг, где этот ребёнок свернул не туда -> choose: 2–3 коротких варианта, и ловушка = его реальный неверный ход (то, что он и правда подумал/ответил), не выдуманный. На остальных шагах choose не нужен.',
  '',
  '# Два запрета',
  '- Не называй в вопросе то значение, которое спрашиваешь, и никогда не выдавай финальный ответ. Арифметику и «почему» держи в reveal — он показывается только при затыке.',
  '- Не объясняй заблуждение отдельной ступенью. Оно живёт как ловушка-вариант на нужном шаге и как строка в его reveal — не как самостоятельный вопрос.',
  '',
  'Длина — по решению: короткое решение -> короткая лесенка (хоть 2 ступени). По-русски, тепло, без назидания. Математику в инструкциях и вариантах оформляй в $...$ (KaTeX), дроби в answer — ASCII (например 3/8).',
  '',
  '# Выход',
  'Верни ТОЛЬКО JSON: { "rungs": [ { "type":"compute|choose", "prompt_ru":"...", "options_ru":["...","..."] (только для choose, 2–3 коротких варианта), "answer":"...", "reveal_ru":"..." (коротко, 1–2 строки; арифметика и «почему» — здесь), "_kc":"<один микро-навык>", "_targets":"<что именно решает эта ступень>" } ] }',
  'Думай в уме — поле reasoning не выводи. Лишних полей не добавляй.',
].join('\n')

const CRITIC = [
  'Ты — ревьюер «лесенок понимания». Тебе дают условие задачи, проверенное пошаговое решение steps[], ошибку ребёнка и ЛЕСЕНКУ автора (rungs[]). Твой главный вопрос один: логично ли разложена задача? Ты не переписываешь сам — называешь ступень, в чём проблема и как починить.',
  '',
  '# Принципы логичности (по ним судишь — это не галочки-чеклист)',
  '1. Каждая ступень необходима. Её результат нужен следующей ступени или это финальный ответ. Ступень-пересказ вывода, ступень-«теория ошибки», разогрев, повтор — лишние. Тест: убери ступень — следующая всё ещё вычисляется? Если да — ступень лишняя, в revise.',
  '2. Этапы идут логикой решения. Подряд, без скачков и без пропущенных шагов; ребёнок может пройти их по порядку и сам дойти до ответа. Нужный шаг отдан готовым в условии вместо отдельной ступени — тоже нарушение.',
  '3. Вопрос не выдаёт свой ответ. Не называет искомое значение и не предобосновывает верную сторону; «почему» и число — в reveal. Тест: понявший и непонявший ответили бы по-разному?',
  '4. Слом оформлен как выбор с реальной ловушкой. На шаге, где ребёнок ошибся, — choose, и неверный вариант = его настоящая ошибка (не выдуманная, не абсурдная).',
  '',
  '# Вердикт',
  'Верни JSON: { "plan":"<1–2 строки: какова логика решения и где ребёнок свернул>", "findings":[{rung_index, issue, fix}], "verdict":"accept|revise", "needs_human":bool, "confidence":"high|medium|low" }',
  'verdict="revise" при нарушении любого принципа. needs_human=true, если числа лесенки расходятся со steps[]. findings пуст -> accept. Каждая находка конкретна: какая ступень, в чём нелогичность, как починить. Без общих «в целом норм».',
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
