// Мок-данные среза. Форма повторяет backend-модель декомпозиции:
// тема → микро-навык → задача-в-шагах. На реальном API заменяется фетчем.
// Все 7 лесенок авторил движок cabinet/engine (автор→критик→правка),
// grounding — реальные задачи из банка НИШ (problems_v10 + full_decomposition_v1).

export const catalog: Record<string, string> = {
  frac_concept: "понятие дроби",
  addsub_frac: "сложение/вычитание дробей",
  mul_frac: "умножение дробей",
  div_frac: "деление дробей",
  common_denom: "общий знаменатель",
  reduce_frac: "сокращение дроби",
  order_of_ops: "порядок действий",
  frac_of_number: "дробь от числа",
  // Текстовые задачи (движение)
  distance_speed_time: "расстояние = скорость × время",
  int_add_sub: "сложение/вычитание целых",
  average_speed: "средняя скорость",
  closing_speed: "скорость сближения",
  time_from_distance_speed: "время по расстоянию и скорости",
  meeting_with_head_start: "встречное движение с форой",
  // Проценты
  percent_change: "проценты подряд",
  percent_increase: "повышение на %",
  percent_base_identification: "база процента",
  // Доли пути
  frac_of_remaining: "доля от остатка",
  // Отношения
  ratio_parts: "отношение в частях",
  // Совместная работа
  work_rate: "производительность",
  time_from_rate: "время по производительности",
  // Отношение и проценты
  percent_change_from_ratio: "проценты из отношения",
  percent_base_choice: "выбор базы %",
  frac_to_percent: "дробь → проценты",
  // Новые задачи из НИШ (движение по реке / возраст / прогрессия)
  stream_speed: "скорость течения",
  solve_linear: "линейное уравнение",
  arithmetic_series_sum: "сумма ряда",
};

// Состояние освоения задачи (светофор)
export type Mastery = "revisit" | "almost" | "got";

// Вариант ответа для ступени-выбора (kind "choose")
export interface StepOption {
  id: string;
  label: string;
}

export interface Step {
  n: number;
  instruction: string; // текст с инлайн-KaTeX ($...$)
  microSkill: string; // ключ из catalog
  expected: string; // эталон: для "compute" — ответ; для "choose" — id верного варианта
  // Расширение для текстовых задач (всё опционально — дробные задачи работают как раньше):
  kind?: "compute" | "choose"; // по умолчанию "compute"
  options?: StepOption[]; // варианты для kind "choose"
  reveal?: string; // явная расписанная арифметика — показывается ТОЛЬКО как глубокая подсказка после ошибки
}

export interface WrongTask {
  id: string;
  nodeId: string;
  topicLabel: string;
  statement: string; // условие задачи с KaTeX
  answer: string; // финальный ответ
  primaryMicroSkill: string;
  steps: Step[];
  state: Mastery;
  wrongAnswer: string; // что ученик ответил изначально (скрыто по умолчанию)
}

// Пул «более лёгких ступеней» — вставляются при двойной ошибке на ступени.
// Ключ — microSkill. Подбираем по микро-навыку проваленной ступени.
export interface EasierRung {
  instruction: string;
  microSkill: string;
  expected: string;
}

export const easierPool: Record<string, EasierRung> = {
  mul_frac: {
    instruction: "Зайдём проще. Перемножь: $\\frac{2}{5}\\cdot\\frac{1}{2}$.",
    microSkill: "mul_frac",
    expected: "1/5",
  },
  addsub_frac: {
    instruction: "Зайдём проще. Сложи: $\\frac{1}{5}+\\frac{2}{5}$.",
    microSkill: "addsub_frac",
    expected: "3/5",
  },
  frac_concept: {
    instruction:
      "Зайдём проще. Запиши «1 из 4» дробью — числитель сверху, знаменатель снизу.",
    microSkill: "frac_concept",
    expected: "1/4",
  },
  common_denom: {
    instruction: "Зайдём проще. Приведи $\\frac{1}{2}$ к знаменателю $4$.",
    microSkill: "common_denom",
    expected: "2/4",
  },
  reduce_frac: {
    instruction: "Зайдём проще. Сократи $\\frac{2}{4}$ — раздели верх и низ на $2$.",
    microSkill: "reduce_frac",
    expected: "1/2",
  },
  frac_of_number: {
    instruction: "Зайдём проще. Сколько $\\frac{1}{2}$ от $10$?",
    microSkill: "frac_of_number",
    expected: "5",
  },
  // Текстовые задачи (движение)
  distance_speed_time: {
    instruction:
      "Зайдём проще. Расстояние $=$ скорость $\\times$ время. Скорость $4$ км/ч, время $3$ ч: $4\\cdot3=\\;?$",
    microSkill: "distance_speed_time",
    expected: "12",
  },
  int_add_sub: {
    instruction: "Зайдём проще. Сложи два участка: $10+12=\\;?$",
    microSkill: "int_add_sub",
    expected: "22",
  },
  average_speed: {
    instruction:
      "Зайдём проще. Весь путь $22$ км за $5$ ч. Средняя скорость $=22:5=\\;?$",
    microSkill: "average_speed",
    expected: "4.4",
  },
  closing_speed: {
    instruction:
      "Зайдём проще. Идут навстречу $5$ км/ч и $3$ км/ч. Скорость сближения $=5+3=\\;?$",
    microSkill: "closing_speed",
    expected: "8",
  },
  time_from_distance_speed: {
    instruction:
      "Зайдём проще. Время $=$ расстояние $:$ скорость. $120:8=\\;?$",
    microSkill: "time_from_distance_speed",
    expected: "15",
  },
  meeting_with_head_start: {
    instruction:
      "Зайдём проще. Сначала скорость сближения двух поездов: $60+80=\\;?$",
    microSkill: "meeting_with_head_start",
    expected: "140",
  },
  // Проценты
  percent_change: {
    instruction:
      "Цена $100$ тенге сначала выросла на $10\\%$, а потом упала на $10\\%$. Сколько стало в итоге?",
    microSkill: "percent_change",
    expected: "99",
  },
  percent_increase: {
    instruction: "Повысь число $200$ на $20\\%$. Сколько получится?",
    microSkill: "percent_increase",
    expected: "240",
  },
  // Доли пути
  frac_of_remaining: {
    instruction:
      "Зайдём проще. Осталось $\\frac{1}{2}$ пути. Прошли половину остатка — какую часть всего пути это? ($\\frac{1}{2}\\cdot\\frac{1}{2}$)",
    microSkill: "frac_of_remaining",
    expected: "1/4",
  },
  // Отношения
  ratio_parts: {
    instruction:
      "Два числа относятся как $1 : 3$. Запиши их через одну часть $k$ и найди их сумму в частях: сколько всего частей $k$?",
    microSkill: "ratio_parts",
    expected: "4",
  },
  // Совместная работа
  work_rate: {
    instruction:
      "Тренировка скилла. Рабочий выполняет всю работу за $4$ часа. Какую долю всей работы (приняв её за $1$) он делает за $\\textbf{один час}$?",
    microSkill: "work_rate",
    expected: "1/4",
  },
  time_from_rate: {
    instruction:
      "Тренировка скилла. Рабочий за один час делает $\\dfrac{1}{8}$ всей работы. За сколько $\\textbf{часов}$ он выполнит всю работу целиком?",
    microSkill: "time_from_rate",
    expected: "8",
  },
  // Отношение и проценты
  percent_change_from_ratio: {
    instruction:
      "Мальчиков $6$ долей, девочек $5$ долей. На какую часть от девочек мальчиков больше? Запиши дробью: $\\frac{?}{5}$.",
    microSkill: "percent_change_from_ratio",
    expected: "1/5",
  },
  percent_base_choice: {
    instruction:
      "Яблок $10$, груш $4$. Вопрос «на сколько яблок больше, ЧЕМ груш». С каким числом сравниваем разницу $-$ с числом яблок или груш? Напиши это число.",
    microSkill: "percent_base_choice",
    expected: "4",
  },
  // Скорость течения (g): течение = половина разности скоростей
  stream_speed_half_diff: {
    instruction:
      "Тренировка скилла. В разрыве скоростей спрятаны два одинаковых течения, вместе $10$ км/ч. Сколько одно течение? ($10\\div2$)",
    microSkill: "stream_speed_half_diff",
    expected: "5",
  },
  // Возраст (h): «в N раз» — это деление/умножение, а не ±
  phrase_to_operation: {
    instruction:
      "Зайдём проще. «В $3$ раза меньше, чем $12$» — это $12-3$ или $12\\div3$? Посчитай правильный вариант.",
    microSkill: "phrase_to_operation",
    expected: "4",
  },
  // Возраст (h): решить простое линейное уравнение
  solve_linear: {
    instruction: "Зайдём проще. Реши уравнение $2x = 10$. Чему равен $x$?",
    microSkill: "solve_linear",
    expected: "5",
  },
  // Прогрессия (DV01): сами числа против промежутков между ними
  fencepost_gaps_vs_items: {
    instruction:
      "Зайдём проще. Столбы стоят на отметках $0, 5, 10, 15$. Между ними $3$ промежутка. А сколько самих столбов?",
    microSkill: "fencepost_gaps_vs_items",
    expected: "4",
  },
  // Прогрессия (DV01): сколько кратных в коротком ряду
  count_multiples_in_range: {
    instruction:
      "Зайдём проще. Числа, кратные $5$, от $10$ до $30$: $10, 15, 20, 25, 30$. Сколько их? ($(30-10)\\div5+1$)",
    microSkill: "count_multiples_in_range",
    expected: "5",
  },
  // Прогрессия (DV01): формула суммы ряда на маленьких числах
  arithmetic_series_sum: {
    instruction:
      "Тренировка скилла. Ряд из $4$ чисел, первое $2$, последнее $8$. Сумма $=4\\times(2+8)\\div2$. Сколько?",
    microSkill: "arithmetic_series_sum",
    expected: "20",
  },
};

// Финальная задача-проверка для закрытия (другие числа, тот же узел, без подсказок).
export interface Verification {
  nodeId: string;
  statement: string;
  expected: string;
}

export const verifications: Record<string, Verification> = {
  FR01: {
    nodeId: "FR01",
    statement: "Проверим понимание. Вычисли: $\\frac{1}{4}+\\frac{1}{2}=\\;?$",
    expected: "3/4",
  },
  FR03: {
    nodeId: "FR03",
    statement: "Проверим понимание. Запиши «5 от 8» дробью.",
    expected: "5/8",
  },
  FR05: {
    nodeId: "FR05",
    statement: "Проверим понимание. Сократи дробь: $\\frac{6}{9}=\\;?$",
    expected: "2/3",
  },
  // Доли пути (см. задачу c)
  WP01: {
    nodeId: "WP01",
    statement:
      "Путник в первый день прошёл треть всего пути, во второй — половину оставшегося, а в третий — оставшиеся $20$ км. Какова длина всего пути?",
    expected: "60",
  },
  WP02: {
    nodeId: "WP02",
    statement:
      "Проверим понимание. Навстречу из пунктов на расстоянии $90$ км вышли пешеходы $4$ и $5$ км/ч. Через сколько часов встретятся?",
    expected: "10",
  },
  // Проценты (цепочка изменений) — задача a
  PC02: {
    nodeId: "PC02",
    statement:
      "Куртка стоила $40\\,000$ тенге. Цена сначала повысилась на $25\\%$, затем понизилась на $20\\%$. Какова цена после понижения?",
    expected: "40000",
  },
  // Возраст и линейное уравнение — задача h (новая EQ04)
  EQ04: {
    nodeId: "EQ04",
    statement:
      "Брат на $2$ года старше Тимура, а отец в $4$ раза старше Тимура. Если сумма возрастов всех троих (вместе с Тимуром) равна $38$, сколько лет Тимуру?",
    expected: "6",
  },
  // Совместная работа — задача e
  WP05: {
    nodeId: "WP05",
    statement:
      "Двое рабочих вместе выполняют работу за $4$ часа. Один из них в одиночку справляется за $12$ часов. За сколько часов выполнит работу второй рабочий?",
    expected: "6",
  },
  // Отношение и проценты — задача f
  PC04: {
    nodeId: "PC04",
    statement:
      "В классе число девочек относится к числу мальчиков как $9 : 6$. На сколько процентов девочек больше, чем мальчиков?",
    expected: "50",
  },
  // Скорость течения — задача g (новая WP03)
  WP03: {
    nodeId: "WP03",
    statement:
      "Лодка прошла $60$ км по течению за $2$ ч, а против течения — за $3$ ч. Найди скорость течения реки.",
    expected: "5",
  },
  // Сумма арифметической прогрессии — задача i (новая DV01)
  DV01: {
    nodeId: "DV01",
    statement: "Найди сумму всех двузначных чисел, кратных $4$.",
    expected: "1188",
  },
};

export const wrongTasks: WrongTask[] = [
  // Все лесенки авторил движок cabinet/engine (автор → критик → правка),
  // промпты простые на принципах: лесенка = логические шаги самого решения.
  {
    id: "a",
    nodeId: "PC02",
    topicLabel: "проценты",
    statement:
      "Фотоаппарат стоил $25\\,000$ тенге. Цена сначала повысилась на $20\\%$, затем понизилась на $20\\%$. Какова цена после понижения?",
    answer: "24000",
    primaryMicroSkill: "percent_change",
    wrongAnswer: "25000",
    state: "almost",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "percent_increase",
        instruction:
          "Сначала цена выросла на $20\\%$. Сколько тенге составляют эти $20\\%$ от $25\\,000$?",
        expected: "5000",
        reveal: "$20\\%$ от $25\\,000$ — это $0{,}2 \\cdot 25\\,000 = 5000$ тенге.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "percent_increase",
        instruction: "Прибавим эту надбавку к старой цене. Какой стала цена после повышения?",
        expected: "30000",
        reveal:
          "$25\\,000 + 5000 = 30\\,000$ тенге — это новая цена, с неё и пойдём дальше.",
      },
      {
        n: 3,
        kind: "choose",
        microSkill: "percent_change",
        instruction: "Теперь цену понижают на $20\\%$. От какой суммы берём эти $20\\%$?",
        options: [
          { id: "o0", label: "От текущих $30\\,000$" },
          { id: "o1", label: "От исходных $25\\,000$" },
        ],
        expected: "o0",
        reveal:
          "Понижение всегда считается от той цены, что есть сейчас — от $30\\,000$. Если взять от $25\\,000$, то $+20\\%$ и $-20\\%$ как будто сократятся, но это не так: проценты берутся от разных сумм.",
      },
      {
        n: 4,
        kind: "compute",
        microSkill: "percent_increase",
        instruction: "Сколько тенге составляют $20\\%$ от $30\\,000$?",
        expected: "6000",
        reveal: "$0{,}2 \\cdot 30\\,000 = 6000$ тенге — на столько подешевеет.",
      },
      {
        n: 5,
        kind: "compute",
        microSkill: "percent_change",
        instruction: "Вычти снижение из текущей цены. Какова цена после понижения?",
        expected: "24000",
        reveal:
          "$30\\,000 - 6000 = 24\\,000$ тенге. Это меньше исходных $25\\,000$ — значит, $+20\\%$ и $-20\\%$ всё-таки не компенсировались.",
      },
    ],
  },
  {
    id: "c",
    nodeId: "WP01",
    topicLabel: "доли пути",
    statement:
      "Турист в первый день прошёл четверть всего пути, во второй — половину оставшегося, а в третий — оставшиеся $36$ км. Какова длина всего пути?",
    answer: "96",
    primaryMicroSkill: "frac_of_remaining",
    wrongAnswer: "72",
    state: "revisit",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "frac_of_remaining",
        instruction:
          "В первый день турист прошёл четверть пути. Какая часть всего пути осталась после первого дня? Запиши дробью.",
        expected: "3/4",
        reveal:
          "Весь путь — это $1$. Отняли четверть: $1 - \\frac{1}{4} = \\frac{3}{4}$. Осталось три четверти.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "frac_of_remaining",
        instruction:
          "Во второй день турист прошёл половину остатка ($\\frac{1}{2}$ от $\\frac{3}{4}$). Значит, на третий день остались ровно те же $36$ км. Какой частью ВСЕГО пути являются эти $36$ км?",
        options: [
          { id: "o0", label: "$\\frac{1}{2}$ всего пути" },
          { id: "o1", label: "$\\frac{3}{4}$ всего пути" },
          { id: "o2", label: "$\\frac{3}{8}$ всего пути" },
        ],
        expected: "o2",
        reveal:
          "Половину остатка $\\frac{3}{4}$ прошёл, половина осталась: $\\frac{1}{2}\\cdot\\frac{3}{4}=\\frac{3}{8}$. $36$ км — это не половина пути и не весь остаток $\\frac{3}{4}$, а именно $\\frac{3}{8}$.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "div_frac",
        instruction:
          "Итак, $\\frac{3}{8}$ всего пути — это $36$ км. Чему равна длина всего пути в км?",
        expected: "96",
        reveal:
          "Делим на дробь: $36 \\div \\frac{3}{8} = 36\\cdot\\frac{8}{3} = 96$ км.",
      },
    ],
  },
  {
    id: "e",
    nodeId: "WP05",
    topicLabel: "совместная работа",
    statement:
      "Двое рабочих вместе выполняют работу за $6$ часов. Один из них в одиночку справляется за $15$ часов. За сколько часов выполнит работу второй рабочий?",
    answer: "10",
    primaryMicroSkill: "work_rate",
    wrongAnswer: "9",
    state: "almost",
    steps: [
      {
        n: 1,
        kind: "choose",
        microSkill: "work_rate",
        instruction:
          "Вместе двое справляются за $6$ ч, первый сам — за $15$ ч. Как найти, сколько работы делает второй за час?",
        options: [
          { id: "o0", label: "$15-6=9$ — вычесть часы" },
          { id: "o1", label: "$\\frac{1}{6}-\\frac{1}{15}$ — вычесть доли работы за час" },
        ],
        expected: "o1",
        reveal:
          "Часы вычитать нельзя: $15-6=9$ значило бы, что двое медленнее одного — абсурд. Работаем с долями работы в час: вместе $\\frac{1}{6}$, первый $\\frac{1}{15}$.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "work_rate",
        instruction:
          "Доля второго рабочего за час $= \\frac{1}{6}-\\frac{1}{15}$. Чему она равна?",
        expected: "1/10",
        reveal:
          "$\\frac{1}{6}-\\frac{1}{15}=\\frac{5}{30}-\\frac{2}{30}=\\frac{3}{30}=\\frac{1}{10}$ в час.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "time_from_rate",
        instruction:
          "Второй рабочий делает $\\frac{1}{10}$ работы в час. За сколько часов он выполнит всю работу?",
        expected: "10",
        reveal:
          "Если за час делается $\\frac{1}{10}$, то на всю работу нужно $1\\div\\frac{1}{10}=10$ часов.",
      },
    ],
  },
  {
    id: "f",
    nodeId: "PC04",
    topicLabel: "отношение и проценты",
    statement:
      "В классе число мальчиков относится к числу девочек как $8 : 5$. На сколько процентов мальчиков больше, чем девочек?",
    answer: "60",
    primaryMicroSkill: "percent_base_choice",
    wrongAnswer: "37.5",
    state: "almost",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "ratio_parts",
        instruction:
          "Мальчиков $8$ частей, девочек $5$. На сколько частей мальчиков больше? Введи число частей разницы.",
        expected: "3",
        reveal: "$8 - 5 = 3$ части — вот на столько мальчиков больше.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "percent_base_choice",
        instruction:
          "Спрашивают: «на сколько процентов больше, ЧЕМ девочек». От какого числа частей считаем — с чем сравниваем?",
        options: [
          { id: "o0", label: "от девочек — $5$ частей" },
          { id: "o1", label: "от мальчиков — $8$ частей" },
        ],
        expected: "o0",
        reveal:
          "«Больше ЧЕМ девочек» → сравниваем с девочками, база $= 5$. Делить на $8$ — частая ловушка: тогда выйдет $\\frac{3}{8}$, но $8$ это не то, с чем сравнивают.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "frac_to_percent",
        instruction:
          "Теперь $3$ части от $5$ переведи в проценты: $\\frac{3}{5} \\cdot 100 = ?$",
        expected: "60",
        reveal:
          "$\\frac{3}{5} \\cdot 100 = 60$. Значит мальчиков на $60\\%$ больше, чем девочек.",
      },
    ],
  },
  {
    id: "g",
    nodeId: "WP03",
    topicLabel: "движение по реке",
    statement:
      "Теплоход прошёл расстояние между двумя причалами в $80$ км по течению реки за $3$ ч $20$ мин, а против течения — за $5$ ч. Найди скорость течения реки.",
    answer: "4",
    primaryMicroSkill: "stream_speed",
    wrongAnswer: "8",
    state: "almost",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "time_from_distance_speed",
        instruction:
          "По течению теплоход прошёл $80$ км за $3$ ч $20$ мин. Сначала переведём время в часы — сколько часов это, дробью? (подсказка: $20$ мин $= \\frac{1}{3}$ ч)",
        expected: "10/3",
        reveal:
          "$3$ ч $20$ мин $= 3 + \\frac{1}{3} = \\frac{10}{3}$ ч. С минутами в формуле $s=v\\cdot t$ работать нельзя — только в часах.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "distance_speed_time",
        instruction:
          "Теперь найди скорость по течению: $80$ км за $\\frac{10}{3}$ ч. Сколько км/ч?",
        expected: "24",
        reveal:
          "$80 \\div \\frac{10}{3} = 80 \\cdot \\frac{3}{10} = 24$ км/ч. Деление на дробь — умножение на перевёрнутую.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "distance_speed_time",
        instruction:
          "Против течения теплоход прошёл те же $80$ км за $5$ ч. Какая скорость против течения, км/ч?",
        expected: "16",
        reveal: "$80 \\div 5 = 16$ км/ч. Против течения медленнее — река тянет назад.",
      },
      {
        n: 4,
        kind: "choose",
        microSkill: "stream_speed_half_diff",
        instruction:
          "По течению — $24$ км/ч, против — $16$ км/ч. Чему равна сама скорость течения?",
        options: [
          { id: "o0", label: "$8$ км/ч" },
          { id: "o1", label: "$4$ км/ч" },
          { id: "o2", label: "$40$ км/ч" },
        ],
        expected: "o1",
        reveal:
          "Течение разгоняет на $+v_т$ и тормозит на $-v_т$, поэтому разность $24-16=8$ вмещает ДВА течения. Одно: $8 \\div 2 = 4$ км/ч.",
      },
    ],
  },
  {
    id: "h",
    nodeId: "EQ04",
    topicLabel: "возраст и уравнение",
    statement:
      "Брат на $3$ года старше Адилета, младший брат на $3$ года младше, сестрёнка в $3$ раза младше, а отец в $3$ раза старше Адилета. Сумма всех возрастов равна $133$. Сколько лет Адилету?",
    answer: "21",
    primaryMicroSkill: "solve_linear",
    wrongAnswer: "24",
    state: "revisit",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "phrase_to_operation",
        instruction:
          "Возьмём возраст Адилета за $x$. Сестрёнка $\\textbf{в 3 раза младше}$ — запиши её возраст через $x$.",
        expected: "x/3",
        reveal:
          "«В 3 раза младше» — это деление: $x/3$. Не путай с «на 3» — там было бы $-3$.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "include_self_in_sum",
        instruction:
          "Теперь сложим все возрасты и приравняем к $133$. Кого складываем — только четверых родственников или ещё кого-то?",
        options: [
          { id: "o0", label: "Только четверых родственников" },
          { id: "o1", label: "Четверых и ещё кого-то" },
        ],
        expected: "o1",
        reveal:
          "В сумму входит и сам Адилет — это $x$. Если его забыть, получится на один $x$ меньше и ответ выйдет больше (как раз $24$). Правильно: $x+(x+3)+(x-3)+\\frac{x}{3}+3x=133$.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "solve_linear",
        instruction:
          "Собери всё слева: целые $x+(x+3)+(x-3)+3x$ дают $6x$ (тройки сокращаются), плюс $\\frac{x}{3}$. Сколько третей $x$ получится в сумме? Запиши коэффициент перед $x$ дробью.",
        expected: "19/3",
        reveal:
          "$6x=\\frac{18x}{3}$, добавляем $\\frac{x}{3}$ → $\\frac{19x}{3}$. То есть $\\frac{19x}{3}=133$.",
      },
      {
        n: 4,
        kind: "compute",
        microSkill: "solve_linear",
        instruction: "Осталось $\\frac{19x}{3}=133$. Найди $x$.",
        expected: "21",
        reveal:
          "Умножаем обе части на $3$: $19x=399$. Делим на $19$: $x=21$. Проверка: $21+24+18+7+63=133$.",
      },
    ],
  },
  {
    id: "i",
    nodeId: "DV01",
    topicLabel: "сумма прогрессии",
    statement: "Найди сумму всех трёхзначных чисел, кратных $5$.",
    answer: "98550",
    primaryMicroSkill: "arithmetic_series_sum",
    wrongAnswer: "98002",
    state: "revisit",
    steps: [
      {
        n: 1,
        kind: "compute",
        microSkill: "count_multiples_in_range",
        instruction:
          "Сначала найдём края. Самое маленькое трёхзначное число, кратное $5$ — это $100$. А какое самое большое трёхзначное число делится на $5$ без остатка? Введи его.",
        expected: "995",
        reveal:
          "Самое большое трёхзначное — $999$, но оно не делится на $5$. Ближайшее снизу, кратное $5$, — это $995$. Значит, идём от $100$ до $995$ с шагом $5$.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "fencepost_gaps_vs_items",
        instruction:
          "Теперь сосчитаем, сколько всего таких чисел от $100$ до $995$ с шагом $5$. Сколько их?",
        options: [
          { id: "o0", label: "$179$" },
          { id: "o1", label: "$180$" },
        ],
        expected: "o1",
        reveal:
          "$(995-100)/5 = 179$ — это число ПРОМЕЖУТКОВ между числами, а самих чисел на одно больше: $179+1=180$. Классическая ловушка «забор и столбы»: столбов всегда на один больше, чем пролётов.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "arithmetic_series_sum",
        instruction:
          "Осталось сложить. У ряда есть удобная формула: количество умножить на полусумму первого и последнего. Подставь свои числа: $180 \\cdot (100+995)/2$. Что получится?",
        expected: "98550",
        reveal:
          "$(100+995)/2 = 1095/2 = 547{,}5$, и $180 \\cdot 547{,}5 = 98\\,550$. Или короче: $180 \\cdot 1095 / 2 = 197\\,100/2 = 98\\,550$.",
      },
    ],
  },
];

// Шапка среза
export const srez = {
  id: "srez-2026-06-20",
  title: "Математика · интенсив · НИШ",
  date: "20 июня",
  total: 40,
  correct: 33,
  // проценты · доли · работа · отношения · движение · возраст · прогрессия;
  // ошибок в работе = длина списка
  errors: wrongTasks.length,
};

// Профиль-метрики (мок) — дни разбора и пожизненный счётчик
export const learner = {
  streakDays: 3,
  lifetimeMastered: 47,
};
