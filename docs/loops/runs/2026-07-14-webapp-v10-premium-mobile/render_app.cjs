/* Production visual/state harness for AiPlus v10 Living Equality. */

const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('playwright')

const BASE = process.env.KODI_RENDER_BASE || 'http://127.0.0.1:5173'
const ROOT = __dirname
const OUT = path.join(ROOT, 'renders', process.env.KODI_RENDER_ROUND || 'round-1')
const executablePath = path.join(
  process.env.HOME,
  'Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
)
let activeBrowser = null

const TASK = {
  id: 'wt-pc-01',
  problem_id: 4821,
  node_id: 'PC02',
  topic_label: 'Проценты',
  statement: 'Цена товара $1200$ ₸ выросла на $15\\%$, а затем снизилась на $10\\%$. Найдите итоговую цену.',
  answer: '1242',
  primary_micro_skill: 'percent_of_change',
  primary_micro_skill_label: 'Изменение на процент',
  decomp_idx: 0,
  state: 'revisit',
  wrong_answer: '1230',
  mastery: 0.31,
  theory_ru: '**Метод** — каждый процент считается от актуальной величины. Второе изменение применяй к результату первого.\n\n**Пример** — $200 \\cdot 1{,}1 = 220$, затем $220 \\cdot 0{,}9 = 198$.\n\n**Ловушка** — считать оба процента от начальной цены.',
  steps: [
    { n: 1, instruction_ru: 'Сколько тенге составляет рост на $15\\%$ от $1200$?', micro_skill: 'percent_of_number', micro_skill_label: 'Процент от числа', expected_value: '180', kind: 'compute', reveal: '$1200 \\cdot 0{,}15 = 180$ ₸.' },
    { n: 2, instruction_ru: 'Какой стала цена после роста?', micro_skill: 'add_percent', micro_skill_label: 'Прибавить процент', expected_value: '1380', kind: 'compute', reveal: '$1200 + 180 = 1380$ ₸.' },
    { n: 3, instruction_ru: 'Снижение на $10\\%$ считаем от новой цены $1380$ или от старой $1200$?', micro_skill: 'percent_base', micro_skill_label: 'База процента', expected_value: 'новая', kind: 'choose', reveal: 'От новой цены $1380$.' },
  ],
}

const SECOND_TASK = {
  ...TASK,
  id: 'wt-fr-02',
  problem_id: 5093,
  node_id: 'FR04',
  topic_label: 'Дроби',
  statement: 'Вычислите $\\dfrac{3}{4} + \\dfrac{5}{6} - \\dfrac{2}{3}$.',
  answer: '11/12',
  wrong_answer: '13/12',
  state: 'almost',
  steps: [],
  theory_ru: null,
}

const LONG_TASK = {
  ...TASK,
  id: 'wt-long-01',
  statement: 'Для школьного проекта сравнили выражения $\\dfrac{17x^4-31x^3+29x^2-11x+7}{(x-1)(x+2)(x^2+3x+5)}$ и $\\dfrac{5x^3+9x^2-4x+12}{x^2-4}$, затем прибавили $18\\%$ от промежуточного результата и вычли $7{,}5\\%$ от новой величины. Найдите итоговое значение при $x=3$.',
  wrong_answer: '123456789012345',
  steps: [{
    n: 1,
    instruction_ru: 'Сначала вычисли значение длинного выражения $\\dfrac{17x^4-31x^3+29x^2-11x+7}{(x-1)(x+2)(x^2+3x+5)} + \\dfrac{5x^3+9x^2-4x+12}{x^2-4}$ при $x=3$ и запиши ответ без округления.',
    micro_skill: 'long_expression',
    micro_skill_label: 'Длинное выражение',
    expected_value: '123456789012345',
    kind: 'compute',
    reveal: null,
  }],
}

const SREZ = [
  { problem_id: 9001, node_title: 'Цифры числа и разряды', statement: 'Найдите двузначное число, если оно равно удвоенному произведению своих цифр.', answer_type: 'number', position: 1, total: 2 },
  { problem_id: 9002, node_title: 'Проценты', statement: 'Какое число составляет $40\\%$ от $250$?', answer_type: 'number', position: 2, total: 2 },
]

const PROFILE = {
  id: 1, first_name: 'Аян', last_name: null, username: null, full_name: 'Аян', lang: 'ru', grade: 7,
  registered: true, diagnostic_complete: true, has_paused_diagnostic: false, photo_consent: null,
}

const VERIFICATION = {
  problem_id: 4899,
  node_id: 'PC02',
  topic_label: 'Проценты',
  statement: 'Цена $800$ ₸ выросла на $25\\%$, затем снизилась на $20\\%$. Найдите итоговую цену.',
  micro_skill: 'percent_of_change',
  micro_skill_label: 'Изменение на процент',
  xp: 30,
}

function json(route, body, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

function api(mode = 'normal') {
  return async (route) => {
    const url = route.request().url()
    if (mode === 'loading' && /wrong-tasks|srez\/start|analytics|verification\/start/.test(url)) return
    if (mode === 'login-loading' && url.includes('/api/auth/phone/check')) return
    if (url.includes('/api/auth/me')) return json(route, PROFILE)
    if (url.includes('/api/auth/phone/check')) {
      if (mode === 'login-error') return json(route, { detail: 'Связь прервалась. Попробуй ещё раз.' }, 503)
      return json(route, { exists: mode === 'login-existing' })
    }
    if (url.includes('/api/auth/phone/login') || url.includes('/api/auth/phone/register')) return json(route, { access_token: 'visual-test' })
    if (url.includes('/trainer/wrong-tasks')) {
      if (mode === 'hub-error') return json(route, { detail: 'temporary' }, 503)
      const tasks = mode === 'hub-empty' || mode === 'hub-new' || mode === 'closure-not-found'
        ? []
        : mode === 'long'
          ? [LONG_TASK]
          : [TASK, SECOND_TASK]
      return json(route, { tasks, has_activity: mode !== 'hub-new' })
    }
    if (url.includes('/trainer/problem-topics')) {
      return json(route, { topics: [{ topic_id: 'PC', strand: 'Числа', name_ru: 'Проценты', error_count: 7, top_micro_skills: [], nodes_mastery_avg: 0.34, closure_progress: 0.25 }] })
    }
    if (url.includes('/trainer/analytics')) {
      if (mode === 'analytics-error') return json(route, { detail: 'temporary' }, 503)
      const items = mode === 'analytics-empty' ? [] : [
        { micro_skill: 'percent_base', label_ru: 'База процента', error_count: 7, last_cause_text: 'снижение посчитано от старой цены', node_id: 'PC02' },
        { micro_skill: 'common_denominator', label_ru: 'Общий знаменатель', error_count: 5, last_cause_text: null, node_id: 'FR04' },
        { micro_skill: 'distribute_terms', label_ru: 'Раскрытие скобок', error_count: 3, last_cause_text: null, node_id: 'LE01' },
      ]
      return json(route, { my_top: items })
    }
    if (url.includes('/trainer/srez/start')) {
      if (mode === 'srez-error') return json(route, { detail: 'temporary' }, 503)
      return json(route, { tasks: mode === 'srez-empty' ? [] : SREZ })
    }
    if (url.includes('/trainer/srez/answer')) return json(route, { is_correct: false })
    if (url.includes('/trainer/verification/start')) {
      if (mode === 'closure-start-network') return json(route, { detail: 'temporary' }, 503)
      return json(route, VERIFICATION)
    }
    if (url.includes('/trainer/verification/answer')) {
      if (mode === 'closure-network') return json(route, { detail: 'temporary' }, 503)
      return json(route, { correct: mode === 'closure-success' })
    }
    if (url.includes('/trainer/step-submit')) {
      if (mode === 'photo-consent') return json(route, { detail: 'consent' }, 403)
      if (mode === 'photo-network') return json(route, { detail: 'vision unavailable' }, 503)
      const verdict = mode === 'photo-unsure' ? 'unsure' : mode === 'photo-mismatch' ? 'mismatch' : 'match'
      return json(route, { verdict, hint: verdict === 'mismatch' ? 'Проверь, от какой цены считаешь процент.' : null, confidence: verdict === 'unsure' ? 0.42 : 0.93, step_n: 1 })
    }
    if (url.includes('/trainer/tutor/chat')) return json(route, { session_id: 1, reply: 'С какой величины начинается этот шаг?', history: [] })
    return json(route, {})
  }
}

function diagnostics(page) {
  const errors = []
  const failed = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error}`))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`) })
  page.on('requestfailed', (request) => failed.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText}`))
  return { errors, failed }
}

async function inspect(page) {
  return page.evaluate(async () => {
    await document.fonts.ready
    const root = document.documentElement
    const body = document.body
    const visible = (element) => {
      const style = getComputedStyle(element)
      const rect = element.getBoundingClientRect()
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
    }
    const controls = [...document.querySelectorAll('button,a,input,textarea,select,summary')]
      .filter((element) => visible(element) && !element.classList.contains('sr-only') && element.getAttribute('type') !== 'file')
    const smallTargets = controls.map((element) => {
      const rect = element.getBoundingClientRect()
      return { tag: element.tagName, label: element.getAttribute('aria-label') || element.textContent?.trim().slice(0, 60), width: Math.round(rect.width), height: Math.round(rect.height) }
    }).filter((item) => item.width < 44 || item.height < 44)
    const inputs = [...document.querySelectorAll('input:not([type=file]),textarea,select')].filter(visible)
    const images = [...document.querySelectorAll('img')].filter(visible)
    const localMath = [...document.querySelectorAll('.math-viewport,.math-scroll,.number-viewport')]
    const literataRequired = [...document.querySelectorAll('.font-editorial')].some(visible)
    return {
      viewport: { width: innerWidth, height: innerHeight },
      scrollHeight: root.scrollHeight,
      overflowX: Math.max(root.scrollWidth, body.scrollWidth) > root.clientWidth + 1,
      bodyScrollWidth: body.scrollWidth,
      clientWidth: root.clientWidth,
      fonts: {
        status: document.fonts.status,
        onest: document.fonts.check('600 20px "Onest"', 'Разбор решения Ң'),
        literata: document.fonts.check('600 32px "Literata"', 'Проценты Ң'),
        literataRequired,
      },
      imagesLoaded: images.every((image) => image.complete && image.naturalWidth > 0),
      smallTargets,
      minInputFont: inputs.length ? Math.min(...inputs.map((element) => Number.parseFloat(getComputedStyle(element).fontSize))) : null,
      h1Count: document.querySelectorAll('h1').length,
      mainLandmarks: [...document.querySelectorAll('main,[role="main"]')].filter(visible).length,
      bracketCount: document.querySelectorAll('.bracket-slot').length,
      localMathScrollers: localMath.filter((element) => element.scrollWidth > element.clientWidth + 1).length,
      reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    }
  })
}

async function keyboard(page) {
  await page.mouse.click(2, 2)
  const sequence = []
  for (let index = 0; index < 4; index += 1) {
    await page.keyboard.press('Tab')
    const state = await page.evaluate(() => {
      const element = document.activeElement
      const style = element ? getComputedStyle(element) : null
      return {
        tag: element?.tagName || null,
        label: element?.getAttribute('aria-label')
          || [...(element?.labels || [])].map((label) => label.textContent?.trim()).filter(Boolean).join(' ')
          || element?.textContent?.trim().slice(0, 60)
          || null,
        outline: style?.outlineStyle || null,
        width: style?.outlineWidth || null,
        shadow: style?.boxShadow || null,
      }
    })
    if (state.tag === 'BODY') break
    sequence.push(state)
  }
  return sequence
}

async function openScenario(browser, spec) {
  const context = await browser.newContext({
    viewport: spec.viewport,
    deviceScaleFactor: 1,
    colorScheme: 'light',
    reducedMotion: spec.reduced ? 'reduce' : 'no-preference',
  })
  await context.route('**/api/**', api(spec.mode))
  if (spec.auth !== false) await context.addInitScript(() => localStorage.setItem('kodi.jwt', 'visual-test'))
  const page = await context.newPage()
  const events = diagnostics(page)
  await page.goto(`${BASE}/app${spec.path}`, { waitUntil: spec.mode === 'loading' ? 'domcontentloaded' : 'networkidle' })
  await page.waitForTimeout(spec.mode === 'loading' ? 550 : 320)
  if (spec.interact) await spec.interact(page)
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(650)
  if (spec.capture) {
    await page.locator(spec.capture).first().evaluate((element) => element.scrollIntoView({ block: 'start', inline: 'nearest' }))
  } else {
    await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'auto' }))
  }
  await page.waitForTimeout(80)
  const details = await inspect(page)
  await page.screenshot({ path: path.join(OUT, `${spec.viewport.width}-${spec.name}.png`), fullPage: false })
  const focus = await keyboard(page)
  await context.close()
  const errors = spec.allowHttpError
    ? events.errors.filter((item) => !item.includes('Failed to load resource: the server responded with a status of'))
    : events.errors
  return { details, focus, errors, requestFailures: events.failed.filter((item) => !item.includes('ERR_ABORTED')) }
}

const fillWrongOnce = async (page) => {
  await page.getByLabel('Введите ответ').fill('999')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByText('Намёк').waitFor()
}

const fillReveal = async (page) => {
  await fillWrongOnce(page)
  await page.getByLabel('Введите ответ').fill('999')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByLabel('Введите ответ').fill('20')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByLabel('Введите ответ').fill('999')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByLabel('Введите ответ').fill('999')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByText('Разобрать этот шаг').waitFor()
}

const finishDrill = async (page) => {
  await page.getByLabel('Введите ответ').fill('180')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByText('Какой стала цена после роста?').waitFor()
  await page.getByLabel('Введите ответ').fill('1380')
  await page.getByRole('button', { name: 'Проверить шаг' }).click()
  await page.getByRole('button', { name: 'новая цена' }).click()
  await page.getByText('Цепочка собрана').waitFor()
}

const submitSrezOnce = async (page) => {
  await page.getByLabel('Введите ответ').fill('10')
  await page.getByRole('button', { name: 'Проверить' }).click()
  await page.getByText('Оставим в плане').waitFor()
}

const submitPhone = async (page) => {
  await page.getByLabel('Номер телефона').fill('+7 700 000 00 00')
  await page.getByRole('button', { name: 'Продолжить' }).click()
}

const photo = async (page) => {
  await page.getByRole('tab', { name: 'По тетради' }).click()
  const tinyPng = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  await page.locator('input[type=file]').setInputFiles({ name: 'step.png', mimeType: 'image/png', buffer: tinyPng })
  await page.waitForTimeout(900)
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true })
  const browser = await chromium.launch({ headless: true, executablePath })
  activeBrowser = browser
  const report = {}
  const base = [
    { name: 'hub', path: '/', mode: 'normal' },
    { name: 'drill', path: '/drill/wt-pc-01', mode: 'normal' },
    { name: 'closure', path: '/closure/wt-pc-01', mode: 'normal' },
    { name: 'srez', path: '/srez', mode: 'normal' },
    { name: 'analytics', path: '/analytics', mode: 'normal' },
    { name: 'login', path: '/login', mode: 'normal', auth: false },
  ]
  for (const viewport of [{ width: 375, height: 844 }, { width: 1280, height: 900 }]) {
    for (const spec of base) {
      const full = { ...spec, viewport }
      report[`${viewport.width}-${spec.name}`] = await openScenario(browser, full)
    }
  }

  const mobile = { width: 375, height: 844 }
  const states = [
    { name: 'hub-loading', path: '/', mode: 'loading' },
    { name: 'hub-error', path: '/', mode: 'hub-error', allowHttpError: true },
    { name: 'hub-empty', path: '/', mode: 'hub-empty' },
    { name: 'hub-new', path: '/', mode: 'hub-new' },
    { name: 'drill-wrong', path: '/drill/wt-pc-01', mode: 'normal', capture: '[aria-current="step"]', interact: fillWrongOnce },
    { name: 'drill-reveal', path: '/drill/wt-pc-01', mode: 'normal', capture: '[aria-current="step"]', interact: fillReveal },
    { name: 'drill-finished', path: '/drill/wt-pc-01', mode: 'normal', capture: '.equation-commit', interact: finishDrill },
    { name: 'photo-unsure', path: '/drill/wt-pc-01', mode: 'photo-unsure', capture: 'aside', interact: photo },
    { name: 'photo-mismatch', path: '/drill/wt-pc-01', mode: 'photo-mismatch', capture: 'aside', interact: photo },
    { name: 'photo-network', path: '/drill/wt-pc-01', mode: 'photo-network', allowHttpError: true, capture: 'aside', interact: photo },
    { name: 'photo-consent', path: '/drill/wt-pc-01', mode: 'photo-consent', allowHttpError: true, capture: 'aside', interact: photo },
    { name: 'closure-wrong', path: '/closure/wt-pc-01', mode: 'normal', capture: '[aria-label="Проверочная задача"] .ink-stage', interact: async (page) => { await page.getByLabel('Введите ответ контрольной').fill('700'); await page.getByRole('button', { name: 'Проверить решение' }).click(); await page.getByText('Пока не сошлось').waitFor() } },
    { name: 'closure-network', path: '/closure/wt-pc-01', mode: 'closure-network', allowHttpError: true, capture: '[aria-label="Проверочная задача"] .ink-stage', interact: async (page) => { await page.getByLabel('Введите ответ контрольной').fill('800'); await page.getByRole('button', { name: 'Проверить решение' }).click(); await page.getByText('Ответ сохранён в поле').waitFor() } },
    { name: 'closure-start-network', path: '/closure/wt-pc-01', mode: 'closure-start-network', allowHttpError: true, capture: '[aria-label="Проверочная задача"]', interact: async (page) => { await page.getByRole('heading', { name: 'Не удалось подготовить проверку' }).waitFor(); await page.getByRole('button', { name: 'Попробовать ещё раз' }).waitFor() } },
    { name: 'closure-success', path: '/closure/wt-pc-01', mode: 'closure-success', interact: async (page) => { await page.getByLabel('Введите ответ контрольной').fill('800'); await page.getByRole('button', { name: 'Проверить решение' }).click(); await page.getByText('Получилось самостоятельно.').waitFor() } },
    { name: 'closure-not-found', path: '/closure/missing', mode: 'closure-not-found' },
    { name: 'srez-empty', path: '/srez', mode: 'srez-empty' },
    { name: 'srez-error', path: '/srez', mode: 'srez-error', allowHttpError: true },
    { name: 'srez-feedback', path: '/srez', mode: 'normal', capture: '[aria-live="polite"]', interact: submitSrezOnce },
    { name: 'srez-final', path: '/srez', mode: 'normal', interact: async (page) => { for (let index = 0; index < 2; index += 1) { await page.getByLabel('Введите ответ').fill('10'); await page.getByRole('button', { name: 'Проверить' }).click(); await page.getByRole('button', { name: 'Следующий вопрос' }).click(); if (index === 0) await page.getByText('Какое число составляет').waitFor() } await page.getByText('План стал точнее.').waitFor() } },
    { name: 'analytics-empty', path: '/analytics', mode: 'analytics-empty' },
    { name: 'analytics-error', path: '/analytics', mode: 'analytics-error', allowHttpError: true },
    { name: 'analytics-loading', path: '/analytics', mode: 'loading' },
    { name: '404', path: '/missing', mode: 'normal' },
    { name: 'login-register-grade', path: '/login', mode: 'normal', auth: false, interact: async (page) => { await page.getByLabel('Номер телефона').fill('+7 700 000 00 00'); await page.getByRole('button', { name: 'Продолжить' }).click(); await page.getByLabel('Имя').fill('Аян'); await page.getByRole('button', { name: 'Далее' }).click(); await page.getByText('В какой класс идёшь?').waitFor() } },
    { name: 'login-loading', path: '/login', mode: 'login-loading', auth: false, interact: submitPhone },
    { name: 'login-error', path: '/login', mode: 'login-error', auth: false, allowHttpError: true, interact: async (page) => { await submitPhone(page); await page.getByText('Связь прервалась. Попробуй ещё раз.').waitFor() } },
    { name: 'reduced-motion', path: '/drill/wt-pc-01', mode: 'normal', reduced: true },
  ]
  for (const spec of states) report[`375-${spec.name}`] = await openScenario(browser, { ...spec, viewport: mobile })

  for (const viewport of [{ width: 320, height: 844 }, { width: 375, height: 844 }, { width: 1280, height: 900 }]) {
    report[`${viewport.width}-long-math`] = await openScenario(browser, { name: 'long-math', path: '/drill/wt-long-01', mode: 'long', viewport })
  }

  await browser.close()
  activeBrowser = null
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2))

  const failures = []
  for (const [name, value] of Object.entries(report)) {
    if (value.errors.length) failures.push(`${name}: ${value.errors.join('; ')}`)
    if (value.requestFailures.length && !name.includes('loading')) failures.push(`${name}: request ${value.requestFailures.join('; ')}`)
    if (value.details.overflowX) failures.push(`${name}: page overflow-x`)
    if (value.details.fonts.status !== 'loaded' || !value.details.fonts.onest || (value.details.fonts.literataRequired && !value.details.fonts.literata)) failures.push(`${name}: fonts`)
    if (value.details.smallTargets.length) failures.push(`${name}: small targets ${JSON.stringify(value.details.smallTargets)}`)
    if (value.details.mainLandmarks !== 1) failures.push(`${name}: expected 1 main landmark, got ${value.details.mainLandmarks}`)
    if (value.details.minInputFont !== null && value.details.minInputFont < 16) failures.push(`${name}: input font ${value.details.minInputFont}`)
    if (!value.details.imagesLoaded) failures.push(`${name}: visible image not loaded`)
    if (value.focus.some((item) => (item.outline === 'none' || item.width === '0px') && (!item.shadow || item.shadow === 'none'))) failures.push(`${name}: invisible keyboard focus`)
  }
  if (failures.length) throw new Error(`render gate failed:\n- ${failures.join('\n- ')}`)
  process.stdout.write(`render gate passed: ${Object.keys(report).length} scenarios, output=${OUT}\n`)
}

main().catch(async (error) => {
  if (activeBrowser) await activeBrowser.close()
  process.stderr.write(`${error.stack || error}\n`)
  process.exitCode = 1
})
