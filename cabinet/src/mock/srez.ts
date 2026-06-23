// Мок-данные среза. Форма повторяет backend-модель декомпозиции:
// тема → микро-навык → задача-в-шагах. На реальном API заменяется фетчем.

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
  // Множества
  inclusion_exclusion: "включения-исключения",
  // Доли пути
  frac_of_remaining: "доля от остатка",
  // Отношения
  ratio_parts: "отношение в частях",
  ratio_diff_vs_part: "разность частей",
  // Совместная работа
  work_rate: "производительность",
  time_from_rate: "время по производительности",
  // Отношение и проценты
  percent_change_from_ratio: "проценты из отношения",
  percent_base_choice: "выбор базы %",
  frac_to_percent: "дробь → проценты",
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
  // Множества
  inclusion_exclusion: {
    instruction:
      "В группе $10$ детей, каждый ест яблоки или груши. Яблоки любят $7$, груши — $5$. Сколько детей любят и яблоки, и груши? Сложи $7$ и $5$, потом убери лишний двойной счёт по числу детей.",
    microSkill: "inclusion_exclusion",
    expected: "2",
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
  ratio_diff_vs_part: {
    instruction:
      "Известно, что три части равны $12$, то есть $3k = 12$. Чему равна одна часть $k$?",
    microSkill: "ratio_diff_vs_part",
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
  // WP01 перезаписан новой задачей на доли пути (см. задачу c)
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
  // Проценты (цепочка изменений)
  PC02: {
    nodeId: "PC02",
    statement:
      "Куртка стоила $40\\,000$ тенге. Цена сначала повысилась на $25\\%$, затем понизилась на $20\\%$. Какова цена после понижения?",
    expected: "40000",
  },
  // Множества (круги Эйлера)
  AR06: {
    nodeId: "AR06",
    statement:
      "В классе $30$ учеников, и каждый занимается хотя бы одним видом спорта. Футболом занимаются $20$, баскетболом — $16$. Сколько учеников занимаются ОБОИМИ видами спорта?",
    expected: "6",
  },
  // Отношения и уравнение
  EQ04: {
    nodeId: "EQ04",
    statement:
      "Три числа относятся как $3 : 5 : 8$. Разность наибольшего и наименьшего равна $40$. Чему равна сумма этих трёх чисел?",
    expected: "128",
  },
  // Совместная работа
  WP05: {
    nodeId: "WP05",
    statement:
      "Двое рабочих вместе выполняют работу за $4$ часа. Один из них в одиночку справляется за $12$ часов. За сколько часов выполнит работу второй рабочий?",
    expected: "6",
  },
  // Отношение и проценты
  PC04: {
    nodeId: "PC04",
    statement:
      "В классе число девочек относится к числу мальчиков как $9 : 6$. На сколько процентов девочек больше, чем мальчиков?",
    expected: "50",
  },
};

export const wrongTasks: WrongTask[] = [
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
          "Цена выросла на $20\\%$. Сколько теперь стоит фотоаппарат?",
        expected: "30000",
        reveal:
          "$20\\%$ от $25\\,000$ — это $5000$. Цена стала $25\\,000+5000=30\\,000$.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "percent_change",
        instruction:
          "Теперь цена падает на $20\\%$. От какой суммы считаем это понижение?",
        options: [
          { id: "p25", label: "от $25\\,000$" },
          { id: "p30", label: "от $30\\,000$" },
        ],
        expected: "p30",
        reveal:
          "Скидку всегда берут от той цены, что стоит сейчас. А сейчас фотоаппарат стоит уже $30\\,000$, а не $25\\,000$.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "percent_change",
        instruction: "Посчитай цену после понижения.",
        expected: "24000",
        reveal:
          "$20\\%$ от $30\\,000$ — это $6000$. Значит $30\\,000-6000=24\\,000$. Вышло меньше $25\\,000$: скидку взяли с большей суммы, чем была прибавка.",
      },
    ],
  },
  {
    id: "b",
    nodeId: "AR06",
    topicLabel: "множества (круги Эйлера)",
    statement:
      "В классе $27$ учеников, и каждый изучает хотя бы один иностранный язык. Английский изучают $18$, французский — $15$. Сколько учеников изучают ОБА языка?",
    answer: "6",
    primaryMicroSkill: "inclusion_exclusion",
    wrongAnswer: "9",
    state: "revisit",
    steps: [
      {
        n: 1,
        kind: "choose",
        microSkill: "inclusion_exclusion",
        instruction:
          "Сложили: $18+15=33$. Но в классе всего $27$ учеников. Почему сумма больше класса?",
        options: [
          {
            id: "both",
            label:
              "Тех, кто учит оба языка, посчитали дважды — и в $18$, и в $15$",
          },
          { id: "err", label: "В классе на самом деле $33$ ученика" },
          { id: "none", label: "Кто-то не учит ни одного языка" },
        ],
        expected: "both",
        reveal:
          "Двуязычные попали в обе группы → посчитаны дважды. Поэтому $33$ больше $27$ ровно на их число.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "inclusion_exclusion",
        instruction: "Сколько учеников изучают оба языка?",
        expected: "6",
        reveal: "$18+15-27=6$ — это и есть двойной счёт.",
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
          "Какая часть всего пути осталась после первого дня (прошёл $\\frac{1}{4}$)?",
        expected: "3/4",
        reveal: "$1-\\frac{1}{4}=\\frac{3}{4}$.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "frac_of_remaining",
        instruction:
          "Во второй день прошёл половину остатка, в третий — оставшиеся $36$ км. Какая часть ВСЕГО пути эти $36$ км?",
        options: [
          { id: "half", label: "$\\frac{1}{2}$ — это же половина" },
          {
            id: "q3",
            label: "$\\frac{3}{4}$ — столько осталось после первого дня",
          },
          { id: "three8", label: "$\\frac{3}{8}$ всего пути" },
        ],
        expected: "three8",
        reveal:
          "Остаток $\\frac{3}{4}$ делится пополам: день 2 $=\\frac{3}{8}$, день 3 $=\\frac{3}{8}$. Значит $36$ км $=\\frac{3}{8}$ (примешь за половину — выйдет неверные $72$).",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "div_frac",
        instruction:
          "Если $\\frac{3}{8}$ всего пути это $36$ км, какова длина всего пути?",
        expected: "96",
        reveal: "$36\\div\\frac{3}{8}=36\\cdot\\frac{8}{3}=96$ км.",
      },
    ],
  },
  {
    id: "d",
    nodeId: "EQ04",
    topicLabel: "отношения и уравнение",
    statement:
      "Три числа относятся как $2 : 3 : 4$. Разность наибольшего и наименьшего равна $30$. Чему равна сумма этих трёх чисел?",
    answer: "135",
    primaryMicroSkill: "ratio_diff_vs_part",
    wrongAnswer: "270",
    state: "revisit",
    steps: [
      {
        n: 1,
        kind: "choose",
        microSkill: "ratio_diff_vs_part",
        instruction:
          "Числа состоят из равных долей: $2$ доли, $3$ доли и $4$ доли. Разность наибольшего и наименьшего — это сколько долей?",
        options: [
          { id: "one", label: "$1$ доля" },
          { id: "two", label: "$2$ доли" },
          { id: "six", label: "$6$ долей" },
        ],
        expected: "two",
        reveal:
          "Наибольшее — $4$ доли, наименьшее — $2$ доли. Разница: $4-2=2$ доли.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "ratio_diff_vs_part",
        instruction: "Эти $2$ доли как раз равны $30$. Чему равна одна доля?",
        expected: "15",
        reveal: "$30\\div2=15$. (А не $30$ — иначе перепутаешь разность с одной долей.)",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "ratio_parts",
        instruction:
          "Во всех трёх числах вместе $2+3+4=9$ долей. Чему равна их сумма?",
        expected: "135",
        reveal: "$9$ долей по $15$: $9\\times15=135$.",
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
          "Хочется сказать $15-6=9$. Но что у рабочих можно вычитать — их $\\textbf{время}$ (часы) или их $\\textbf{производительность}$ (долю работы в час)?",
        options: [
          { id: "time", label: "Время: $15-6=9$ часов" },
          {
            id: "rate",
            label: "Производительность (долю в час); времена вычитать нельзя",
          },
        ],
        expected: "rate",
        reveal:
          "Будь $15-6=9$ верно — двое работали бы медленнее одного, абсурд. Складываются и вычитаются доли работы в час.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "work_rate",
        instruction:
          "Вся работа $=1$. Вместе делают $\\frac{1}{6}$ в час, первый — $\\frac{1}{15}$ в час. Какова производительность второго (доля в час)?",
        expected: "1/10",
        reveal:
          "$\\frac{1}{6}-\\frac{1}{15}=\\frac{5}{30}-\\frac{2}{30}=\\frac{3}{30}=\\frac{1}{10}$.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "time_from_rate",
        instruction:
          "Второй делает $\\frac{1}{10}$ работы в час. За сколько часов выполнит всю работу?",
        expected: "10",
        reveal: "$1\\div\\frac{1}{10}=10$ часов.",
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
          "Мальчиков $8$ частей, девочек $5$. На сколько частей мальчиков больше?",
        expected: "3",
        reveal: "$8-5=3$ части.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "percent_base_choice",
        instruction:
          "«На сколько процентов больше, ЧЕМ девочек» — разницу в $3$ части сравниваем с чем?",
        options: [
          { id: "boys", label: "С мальчиками ($8$ частей)" },
          { id: "girls", label: "С девочками ($5$ частей)" },
          { id: "sum", label: "Со всеми ($13$ частей)" },
        ],
        expected: "girls",
        reveal:
          "«Больше, чем девочек» → база $=$ девочки $=5$ частей. $\\frac{3}{5}=60\\%$. (С мальчиками было бы $\\frac{3}{8}=37{,}5\\%$ — неверная база.)",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "frac_to_percent",
        instruction:
          "Переведи в проценты: $3$ части от $5$ — это сколько процентов?",
        expected: "60",
        reveal: "$\\frac{3}{5}\\cdot100=60\\%$.",
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
  correct: 34,
  // проценты + множества + доли + отношения + совместная работа; ошибок в работе = длина списка
  errors: wrongTasks.length,
};

// Профиль-метрики (мок) — дни разбора и пожизненный счётчик
export const learner = {
  streakDays: 3,
  lifetimeMastered: 47,
};
