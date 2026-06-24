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
  // Лесенки авторил движок cabinet/engine (автор → критик по DoD из 7 пунктов).
  // 3 точечные правки руками (критик пропустил): PC04 слить дробь+%, WP03 голые варианты, DV01 убрать двойной вопрос.
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
        instruction: "Сначала цена выросла на $20\\%$. Чему стала равна цена после повышения?",
        expected: "30000",
        reveal: "$20\\%$ от $25\\,000$ — это $5000$. Прибавляем: $25\\,000 + 5000 = 30\\,000$.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "percent_change",
        instruction: "Теперь цена понижается на $20\\%$. От какой суммы надо взять эти $20\\%$?",
        options: [
          { id: "o0", label: "От текущей цены $30\\,000$" },
          { id: "o1", label: "От исходной цены $25\\,000$" },
        ],
        expected: "o0",
        reveal:
          "Понижение всегда считают от той цены, что есть сейчас, — а сейчас это $30\\,000$. Поэтому $+20\\%$ и $-20\\%$ не компенсируют друг друга: проценты берутся от разных сумм.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "percent_change",
        instruction: "Чему равна цена после понижения на $20\\%$?",
        expected: "24000",
        reveal:
          "$20\\%$ от $30\\,000$ — это $6000$. Вычитаем: $30\\,000 - 6000 = 24\\,000$. Это меньше исходных $25\\,000$.",
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
          "Весь путь — это $1$ (целое). В первый день турист прошёл $\\frac{1}{4}$ пути. Какая доля пути осталась после первого дня?",
        expected: "3/4",
        reveal: "Из целого вычитаем пройденное: $1 - \\frac{1}{4} = \\frac{3}{4}$. Осталось $\\frac{3}{4}$ пути.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "frac_of_remaining",
        instruction:
          "Во второй день турист прошёл половину этого остатка — значит, на третий день остались как раз вторая его половина, и это те самые $36$ км. Какой долей всего пути являются эти $36$ км?",
        options: [
          { id: "o0", label: "$\\frac{1}{2}$ всего пути" },
          { id: "o1", label: "$\\frac{3}{4}$ всего пути" },
          { id: "o2", label: "$\\frac{3}{8}$ всего пути" },
        ],
        expected: "o2",
        reveal:
          "Остаток был $\\frac{3}{4}$, на третий день — его половина: $\\frac{1}{2}\\cdot\\frac{3}{4}=\\frac{3}{8}$. Половина — это от остатка, а не от всего пути, поэтому не $\\frac{1}{2}$.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "div_frac",
        instruction: "Итак, $36$ км — это $\\frac{3}{8}$ всего пути. Чему равна длина всего пути (в км)?",
        expected: "96",
        reveal: "Делим часть на её долю: $36 \\div \\frac{3}{8} = 36\\cdot\\frac{8}{3} = 96$ км.",
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
        kind: "compute",
        microSkill: "work_rate",
        instruction:
          "Вдвоём всю работу делают за $6$ часов. Какую долю всей работы они вместе успевают за $1$ час?",
        expected: "1/6",
        reveal: "Если на всю работу уходит $6$ часов, то за один час сделана $\\frac{1}{6}$ её часть.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "work_rate",
        instruction:
          "Первый рабочий в одиночку делает всю работу за $15$ часов. Какую долю работы он успевает за $1$ час?",
        expected: "1/15",
        reveal: "$15$ часов на всю работу — значит за час это $\\frac{1}{15}$ работы.",
      },
      {
        n: 3,
        kind: "choose",
        microSkill: "work_rate",
        instruction:
          "Мы знаем долю в час у двоих вместе ($\\frac{1}{6}$) и у первого ($\\frac{1}{15}$). Что нужно сделать, чтобы найти долю в час у второго рабочего?",
        options: [
          { id: "o0", label: "Из общей доли вычесть долю первого" },
          { id: "o1", label: "Из времени первого вычесть общее время: $15-6$" },
          { id: "o2", label: "Сложить $\\frac{1}{6}$ и $\\frac{1}{15}$" },
        ],
        expected: "o0",
        reveal:
          "Складываются и вычитаются доли работы в час, а не часы. Общая доля $=$ доля первого $+$ доля второго, поэтому доля второго $=$ общая $-$ первого. Вычесть $15-6=9$ нельзя: это смешивает часы с долями.",
      },
      {
        n: 4,
        kind: "compute",
        microSkill: "addsub_frac",
        instruction: "Найди долю в час у второго: $\\frac{1}{6}-\\frac{1}{15}$. Запиши ответ дробью.",
        expected: "1/10",
        reveal:
          "Общий знаменатель $30$: $\\frac{5}{30}-\\frac{2}{30}=\\frac{3}{30}=\\frac{1}{10}$. Второй делает $\\frac{1}{10}$ работы в час.",
      },
      {
        n: 5,
        kind: "compute",
        microSkill: "time_from_rate",
        instruction: "Второй успевает $\\frac{1}{10}$ работы в час. За сколько часов он сделает всю работу?",
        expected: "10",
        reveal: "Вся работа — это $1$. Делим: $1 \\div \\frac{1}{10}=10$ часов.",
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
        instruction: "Мальчиков $8$ частей, девочек $5$ частей. На сколько частей мальчиков больше?",
        expected: "3",
        reveal: "$8-5=3$ части — вот этот «лишний кусок» у мальчиков. Дальше поймём, сколько это в процентах.",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "percent_base_choice",
        instruction:
          "Вопрос: на сколько процентов мальчиков больше, ЧЕМ девочек. Эти $3$ лишние части мы сравниваем с чем — с числом мальчиков или с числом девочек?",
        options: [
          { id: "o0", label: "С девочками ($5$ частей)" },
          { id: "o1", label: "С мальчиками ($8$ частей)" },
        ],
        expected: "o0",
        reveal:
          "«Больше, ЧЕМ девочек» — значит за $100\\%$ берём девочек. База — то, с чем сравниваем: $5$ частей. Деление на $8$ дало бы ответ на другой вопрос.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "frac_to_percent",
        instruction: "Сколько процентов составляют $3$ лишние части от $5$ частей девочек?",
        expected: "60",
        reveal: "$\\frac{3}{5}\\cdot 100 = 60$. Мальчиков на $60\\%$ больше, чем девочек.",
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
        microSkill: "unit_convert_time",
        instruction:
          "Сначала переведём время движения по течению в часы. Сколько часов в $3$ ч $20$ мин? Запиши неправильной дробью.",
        expected: "10/3",
        reveal:
          "$20$ мин $= \\frac{20}{60} = \\frac{1}{3}$ ч, значит $3$ ч $20$ мин $= 3\\frac{1}{3} = \\frac{10}{3}$ ч. Минуты нельзя приписать к часам — переводим всё в одни единицы.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "distance_speed_time",
        instruction: "Теплоход прошёл $80$ км за $\\frac{10}{3}$ ч по течению. Какая у него скорость по течению (км/ч)?",
        expected: "24",
        reveal: "Скорость $=$ расстояние $\\div$ время $= 80 \\div \\frac{10}{3} = 80\\cdot\\frac{3}{10} = 24$ км/ч.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "distance_speed_time",
        instruction: "Те же $80$ км против течения теплоход прошёл за $5$ ч. Какая у него скорость против течения (км/ч)?",
        expected: "16",
        reveal: "$80 \\div 5 = 16$ км/ч. Против течения медленнее — река мешает.",
      },
      {
        n: 4,
        kind: "choose",
        microSkill: "stream_speed",
        instruction: "По течению скорость $24$, против — $16$. Чему равна скорость течения реки?",
        options: [
          { id: "o0", label: "$8$ км/ч" },
          { id: "o1", label: "$4$ км/ч" },
          { id: "o2", label: "$20$ км/ч" },
        ],
        expected: "o1",
        reveal:
          "По течению река добавляет свою скорость, против — отнимает. Поэтому разность $24-16=8$ — это два течения сразу. Скорость течения $= 8\\div 2 = 4$ км/ч.",
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
        kind: "choose",
        microSkill: "phrase_to_operation",
        instruction:
          "Возраст Адилета обозначим $x$. Старший брат $x+3$, младший $x-3$. А как записать сестрёнку («в $3$ раза младше») и отца («в $3$ раза старше»)?",
        options: [
          { id: "o0", label: "Сестрёнка $\\frac{x}{3}$, отец $3x$" },
          { id: "o1", label: "Сестрёнка $x-3$, отец $x+3$" },
          { id: "o2", label: "Сестрёнка $3x$, отец $\\frac{x}{3}$" },
        ],
        expected: "o0",
        reveal:
          "«В $3$ раза» — это деление/умножение, а не $\\pm 3$. Младше в $3$ раза $\\to \\frac{x}{3}$, старше в $3$ раза $\\to 3x$. «На $3$» было бы $\\pm 3$ — это про братьев.",
      },
      {
        n: 2,
        kind: "compute",
        microSkill: "solve_linear",
        instruction:
          "Теперь сложи возрасты ВСЕХ пятерых — не забудь самого Адилета. Сколько раз чистый $x$ войдёт в сумму, если сложить Адилета, старшего и младшего братьев и отца (сестрёнку пока не трогаем)?",
        expected: "6",
        reveal:
          "Адилет $x$, брат $x+3$, младший $x-3$, отец $3x$: $x+x+x+3x=6x$ (тройки $+3$ и $-3$ гасятся). Сестрёнку $\\frac{x}{3}$ добавим отдельно.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "solve_linear",
        instruction:
          "Добавь сестрёнку $\\frac{x}{3}$ к $6x$ и приравняй сумму к $133$. Запиши коэффициент при $x$ в виде дроби.",
        expected: "19/3",
        reveal: "$6x+\\frac{x}{3} = \\frac{18x}{3} + \\frac{x}{3} = \\frac{19x}{3}$. Значит $\\frac{19x}{3} = 133$.",
      },
      {
        n: 4,
        kind: "compute",
        microSkill: "solve_linear",
        instruction: "Из уравнения $\\frac{19x}{3}=133$ найди $x$ — сколько лет Адилету?",
        expected: "21",
        reveal: "Умножь обе части на $3$: $19x=399$. Раздели на $19$: $x=21$.",
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
          "Наименьшее трёхзначное число, кратное $5$ — это $100$. А какое самое большое трёхзначное число делится на $5$?",
        expected: "995",
        reveal: "Трёхзначные — до $999$, но $999$ на $5$ не делится. Ближайшее кратное $5$ — это $995$ ($1000$ уже четырёхзначное).",
      },
      {
        n: 2,
        kind: "choose",
        microSkill: "count_multiples_in_range",
        instruction: "Сколько всего таких чисел от $100$ до $995$ с шагом $5$? Выбери верный счёт.",
        options: [
          { id: "o0", label: "$179$" },
          { id: "o1", label: "$180$" },
          { id: "o2", label: "$200$" },
        ],
        expected: "o1",
        reveal:
          "$(995-100)/5 = 179$ — это число промежутков между числами, а самих чисел на одно больше: $179+1 = 180$. Классический забор: столбиков на один больше, чем пролётов.",
      },
      {
        n: 3,
        kind: "compute",
        microSkill: "arithmetic_series_sum",
        instruction:
          "Осталось сложить весь ряд. Известно: $180$ чисел, первое $100$, последнее $995$. Чему равна сумма?",
        expected: "98550",
        reveal:
          "Сумма прогрессии $=$ (число членов) $\\cdot$ (первый $+$ последний) $/ 2 = 180\\cdot(100+995)/2 = 180\\cdot1095/2 = 98\\,550$.",
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
