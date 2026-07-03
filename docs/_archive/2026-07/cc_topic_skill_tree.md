# Граф тем Common Core + микро-навыки под ними — kodi (v2)

> /brainstorming 2026-06-23. Реструктуризация 372→**337** навыков под граф Common Core. Источник: full_micro_skill_catalog.md (372) + Common Core Coherence Map (стандарты + 542 ребра).

## 🔑 Итог
- **Микро-навыков: 337** (было 372 → слито 35 дублей/синонимов)
- **Тем: 43** = **39 стандартов Common Core** (кластеры-узлы графа) + **4 НИШ-темы**
- **Рёбер графа: 61** — готовые стрелки-пререквизиты Common Core между темами
- Покрытие задач сохранено полностью (372/372 кода, Σ частот 7037); ни один навык не потерян

## Как устроено (3 уровня)
**РАЗДЕЛ CC** (домен графа) → **ТЕМА** (стандарт/кластер CC, напр `4.NF.B`, — узел графа со стрелками) → **микро-навык** (атом). НИШ-ветка — для логики/комбинаторики/теории чисел/продвинутой алгебры, которых нет в CC на 2-7 классах.

`⟵` = что слили в этот навык · `·N` = частота (шагов) · `← пререкв` = темы-предшественники по графу

---
## 📘 Отношения, пропорции и проценты (RP) · 61 навыков, 2 тем
### `6.RP.A` · кл.6 — Understand ratio concepts and use ratio reasoning to solve problems. ← пререкв: `4.MD.A`, `4.OA.A`, `5.NF.B`
- `work_rate` — Производительность за единицу времени (доля работы) ·100
- `distance_speed_time` — Расстояние = скорость × время ·74
- `percent_of_number` — Найти процент от числа ·68
- `ratio_simplify` — Упрощение отношения (записать как частное и сократить) ·40
- `ratio_distribution` — Разделить целое по отношению через части (3x, 5x) и найти доли ·38  ⟵ ratio_to_parts
- `number_from_percent` — Найти число по его проценту ·37
- `time_from_distance_speed` — Время = расстояние ÷ скорость ·31
- `speed_downstream` — Скорость по течению (собственная + течение) ·29
- `closing_speed` — Скорость сближения/удаления (скорости складываются) ·23
- `speed_from_distance_time` — Скорость = расстояние ÷ время ·18
- `unit_rate` — Найти величину на одну единицу (производительность, цена за единицу) ·18
- `work_time_from_rate` — Время работы = работа ÷ производительность ·16
- `stream_speed` — Скорость течения = полуразность (по − против) ·16
- `unit_convert_speed` — Перевод единиц скорости (км/ч↔м/с) ·16
- `work_total` — Объём работы = производительность × время ·13
- `angle_ratio_split` — Деление угла/целого в заданном отношении ·11
- `percent_to_fraction` — Перевести проценты в обыкновенную дробь ·10
- `own_speed_from_downstream_upstream` — Собственная скорость = полусумма (по + против) ·9
- `percent_complement` — Найти оставшийся процент / остаток (дополнение до 100%) ·9
- `decimal_to_percent` — Перевести десятичную дробь в проценты ·9
- `ratio_concept` — Составить отношение из условия задачи ·9
- `yield_per_area` — Урожайность = урожай ÷ площадь ·8
- `man_days_work` — Метод человеко-дней (рабочие × дни) ·7
- `percent_ratio` — Какой процент одно число составляет от другого ·7
- `percent_to_decimal` — Перевести проценты в десятичную дробь (долю) ·7
- `average_speed` — Средняя скорость = весь путь ÷ всё время ·7
- `proportion_setup` — Составление и решение прямой пропорции (rate/масштабирование) ·6
- `combine_ratios` — Объединить цепочку отношений через общий член (a:b, b:c → a:b:c) ·6
- `yield_total` — Урожай = урожайность × площадь ·5
- `ratio_parts` — Распределение целого по долям (частям) ·3
- `slope_from_two_points` — Угловой коэффициент прямой по двум точкам ·3
- `rate_of_change` — Скорость изменения величины (изменение ÷ время, наибольшее изменение) ·3
- `catch_up_speed` — Скорость догона (разность скоростей) ·2
- `train_passing_object` — Поезд проходит мост/объект (длина моста + длина поезда) ·2
- `catch_up_time` — Время встречи/догона = расстояние ÷ относительную скорость ·2
- `speed_upstream` — Скорость против течения (собственная − течение) ·2
- `total_work_product` — Совокупная работа как произведение величин ·2
- `divide_segment_ratio` — Деление отрезка в заданном отношении ·2
- `fraction_to_percent` — Перевести обыкновенную дробь в проценты ·2
- `own_speed_from_downstream` — Собственная скорость = по течению − течение ·1
- `area_from_total_yield` — Площадь = урожай ÷ урожайность ·1
- `proportional_share` — Деление пропорционально долям ·1
- `compare_yield_rates` — Сравнение урожайностей (разность ставок) ·1
- `average_speed_harmonic` — Средняя скорость при равных половинах пути (среднее гармоническое) ·1
- `rate_per_unit` — Нахождение производительности на единицу (на 1 объект) ·1

### `7.RP.A` · кл.7 — Analyze proportional relationships and use them to solve real-world and mathematical problems. ← пререкв: `6.RP.A`
- `cross_multiply` — Решить пропорцию крест-накрест (основное свойство пропорции) ·60  ⟵ proportion_property
- `percent_increase` — Увеличить число на процент / цена после повышения ·31  ⟵ percent_increase_overall
- `inverse_proportion` — Обратная пропорциональность (постоянное произведение, человеко-дни) ·29
- `mixture_concentration` — Концентрация смеси/раствора в процентах ·23  ⟵ set_up_mixture_equation
- `percent_change_factor` — Перевести процентное изменение в множитель ·22
- `percent_decrease` — Уменьшить число на процент / цена после скидки ·21
- `percent_difference_of_two` — На сколько процентов одно число больше/меньше другого ·15
- `compound_proportion` — Сложная (составная) пропорция — несколько величин ·15
- `successive_percent_change` — Последовательные процентные изменения (цепочка множителей) ·14
- `reverse_percent_change` — Найти исходное число до процентного изменения ·13
- `factor_to_percent_change` — Из множителя/кратности выразить процент ·13
- `direct_proportion` — Прямая пропорциональность (во столько же раз больше) ·10  ⟵ proportion_direct
- `percent_area_change` — Изменение площади в процентах ·7  ⟵ percent_change_area
- `percent_change_product` — Как процентное изменение множителя влияет на произведение/частное/сумму ·5
- `percent_remainder_diagram` — Найти оставшуюся долю круговой диаграммы (дополнение до 100%) ·2
- `percent_change` — На сколько процентов больше/меньше (из частей отношения) ·2


## 📘 Выражения, уравнения и неравенства (EE) · 34 навыков, 4 тем
### `6.EE.A` · кл.6 — Apply and extend previous understandings of arithmetic to algebraic expressions. ← пререкв: `4.OA.B`, `5.NBT.A`, `5.OA.A`
- `powers` — Возведение в степень и сравнение степеней ·108
- `substitute_value` — Подставить значение и вычислить выражение ·49
- `custom_operation_eval` — Нестандартная операция по заданному правилу ·34
- `collect_like_terms` — Привести подобные слагаемые / упростить линейное выражение ·33
- `square_root` — Извлечение квадратного корня (сторона по площади) ·16
- `powers_negative_base` — Степень отрицательного числа ·15
- `factor_out_common` — Вынесение общего множителя за скобки ·14
- `identify_coefficient` — Определить коэффициент при переменной ·9
- `identify_constant_term` — Определить свободный член ·5
- `cube_root` — Сторона/число кубиков через кубический корень ·4
- `power_rules` — Свойства степеней (умножение, деление, вынесение) ·4
- `difference_of_squares` — Разность квадратов как приём вычисления ·3
- `nearest_perfect_square` — Ближайший полный квадрат к числу ·3
- `side_from_area_square` — Сторона квадрата по площади (√площади) ·2
- `factor_common_term` — Вынесение общего множителя в многоэтажной дроби ·1
- `distributive_property` — Распределительный закон с десятичными (вынесение общего множителя) ·1

### `6.EE.B` · кл.6 — Reason about and solve one-variable equations and inequalities. ← пререкв: `5.NF.A`, `5.NF.B`, `6.EE.A`, `6.NS.A`
- `verify_solution` — Проверка корня подстановкой и отсев посторонних ·22
- `introduce_variable` — Ввод переменной / запись величины по условию ·10
- `setup_word_problem` — Составление уравнения по текстовой задаче ·9
- `translate_to_equations` — Перевод условия задачи в уравнение или систему ·5
- `count_solutions` — Подсчёт количества решений уравнения ·5
- `consecutive_numbers_setup` — Обозначение подряд идущих чисел ·2
- `solve_system_sum_diff` — Решение системы сложением (сумма и разность) ·2
- `solve_by_trial` — Решение уравнения подбором (guess-and-check) ·2
- `find_factor` — Поиск неизвестного множителя/делителя в дробном равенстве ·2
- `interpret_strict_inequality` — Определить, входят ли границы (строгий / нестрогий знак неравенства) ·2
- `linear_equation_word` — Решение линейного уравнения из текста задачи ·1
- `sum_difference_problem` — Задача на сумму и разность двух чисел ·1

### `7.EE.A` · кл.7 — Use properties of operations to generate equivalent expressions.
- `expand_brackets` — Раскрытие скобок (распределительный закон) ·60
- `combine_like_terms` — Приведение подобных слагаемых, перенос членов ·37

### `7.EE.B` · кл.7 — Solve real-life and mathematical problems using numerical and algebraic expressions and equations. ← пререкв: `7.NS.A`
- `solve_linear` — Решение линейного уравнения (обратные операции, изоляция переменной) ·331
- `translate_words_to_equation` — Составление уравнения по тексту задачи (ввод переменной) ·96
- `solve_linear_inequality` — Решить линейное неравенство ·38  ⟵ solve_inequality_one_step
- `clear_denominator` — Избавление от дробей в уравнении (умножение на знаменатель, крест-накрест) ·20


## 📘 Целые/рациональные числа и координаты (NS) · 33 навыков, 4 тем
### `6.NS.A` · кл.6 — Apply and extend previous understandings of multiplication and division to divide fractions by fractions. ← пререкв: `3.OA.B`, `5.NF.B`
- `div_frac` — Деление дробей (на дробь, на целое, многоэтажная дробь) ·154
- `number_from_frac` — Нахождение числа по его дроби (целого по части) ·31
- `reciprocal` — Обратная (взаимно обратная) дробь ·5

### `6.NS.B` · кл.6 — Compute fluently with multi-digit numbers and find common factors and multiples. ← пререкв: `4.OA.B`, `5.OA.A`
- `int_div` — Деление целых чисел (в т.ч. с округлением вниз) ·229
- `decimal_add_sub` — Сложение и вычитание десятичных дробей (с выравниванием запятой) ·77
- `gcd` — Наибольший общий делитель (НОД), включая обратную задачу и текстовые на НОД ·60
- `lcm` — Наименьшее общее кратное (НОК), включая текстовые задачи на НОК ·60
- `decimal_mul` — Умножение десятичных дробей (подсчёт знаков, сдвиг запятой) ·47
- `decimal_div` — Деление десятичных дробей ·37
- `coprime_check` — Проверка взаимной простоты (НОД = 1) ·11

### `6.NS.C` · кл.6 — Apply and extend previous understandings of numbers to the system of rational numbers.
- `absolute_value` — Понятие и вычисление модуля числа ·57
- `solve_abs_equation` — Решение уравнения с модулем (раскрытие по случаям) ·27
- `distance_on_number_line` — Расстояние между точками на числовой прямой (модуль разности) ·19
- `compare_integers` — Сравнение и упорядочивание чисел на числовой прямой ·17
- `abs_sum_geometric` — Сумма модулей как сумма расстояний на числовой прямой ·8
- `number_line_coordinate` — Координата и сдвиг точки на числовой прямой ·7
- `midpoint_number_line` — Середина отрезка (полусумма концов) и поиск конца по середине ·6
- `min_max` — Найти наибольшее и наименьшее число в наборе ·6
- `sort_data` — Упорядочить числа по возрастанию ·5
- `reflect_over_x_axis` — Отражение точки относительно оси координат ·4
- `distance_two_points` — Расстояние между точками на координатной плоскости ·4
- `reflect_over_origin` — Отражение точки относительно начала координат ·3
- `coordinate_read` — Чтение координат точки (абсцисса, ордината) ·2
- `identify_negatives` — Выделение и подсчёт отрицательных чисел ·2
- `opposite_number` — Противоположное число (смена знака) ·1
- `quadrant_identify` — Определение координатной четверти по знакам x и y ·1

### `7.NS.A` · кл.7 — Apply and extend previous understandings of operations with fractions to add, subtract, multiply, and divide rational numbers. ← пререкв: `4.OA.A`, `6.NS.B`
- `int_add_sub` — Сложение и вычитание целых чисел ·649
- `int_mul` — Умножение целых чисел ·339
- `repeating_decimal_to_frac` — Перевод периодической дроби в обыкновенную (алгебраический метод) ·65
- `frac_to_decimal` — Перевод обыкновенной дроби в десятичную ·43
- `signed_number_ops` — Сложение и вычитание чисел со знаком (включая десятичные и рациональные) ·42
- `repeating_decimal_notation` — Запись периодической дроби и определение периода ·14
- `sign_rules_mul` — Правило знаков при умножении и делении ·4


## 📘 Геометрия (G) · 30 навыков, 4 тем
### `4.G.A` · кл.4 — Draw and identify lines and angles, and classify shapes by properties of their lines and angles. ← пререкв: `4.MD.C`
- `axes_of_symmetry` — Оси симметрии фигуры ·15
- `reflect_over_axis` — Отражение точки относительно оси/прямой ·6
- `answer_encoding_convention` — Соглашение о форме ответа (бесконечно/нет) ·1
- `identify_right_triangle` — Распознавание прямоугольного треугольника по катетам на осях ·1

### `6.G.A` · кл.6 — Solve real-world and mathematical problems involving area, surface area, and volume. ← пререкв: `4.MD.A`, `5.NF.B`, `6.NS.C`
- `area_composite` — Площадь составной фигуры (сложением и вычитанием частей) ·15  ⟵ area_composite_subtract, area_composite_add
- `cube_properties` — Свойства куба и призмы, развёртки (грани/вершины) ·8
- `surface_area_cube` — Площадь поверхности куба ·2
- `cube_edges_count` — Рёбра куба: число и суммарная длина ·2
- `surface_area_box` — Площадь поверхности прямоугольного параллелепипеда ·2
- `area_rhombus_diagonals` — Площадь ромба по диагоналям ·2
- `area_triangle` — Площадь треугольника ·1
- `area_trapezoid` — Площадь трапеции ·1
- `area_right_triangle` — Площадь прямоугольного треугольника ·1
- `area_frame_difference` — Площадь рамки/дорожки через разность площадей ·1

### `7.G.A` · кл.7 — Draw, construct, and describe geometrical figures and describe the relationships between them. ← пререкв: `6.G.A`, `7.RP.A`
- `scale_map_to_real` — Реальное расстояние по карте и масштабу ·41
- `scale_ratio` — Определение/запись масштаба как отношения ·16
- `scale_real_to_map` — Расстояние на карте по реальному и масштабу ·11
- `scale_area_conversion` — Пересчёт площади по масштабу (масштаб в квадрате) ·5

### `7.G.B` · кл.7 — Solve real-life and mathematical problems involving angle measure, area, surface area, and volume. ← пререкв: `4.MD.C`, `6.G.A`
- `area_circle` — Площадь круга и обратное (радиус по площади) ·26
- `circle_circumference` — Длина окружности по радиусу ·25
- `radius_from_circumference` — Радиус по длине окружности ·7
- `supplementary_angles` — Смежные и дополнительные углы (до 180°/90°) ·6
- `area_annulus` — Площадь кольца / разности двух кругов ·6
- `triangle_angle_sum` — Сумма углов треугольника (вкл. равнобедренный) ·4
- `radius_from_diameter` — Радиус по диаметру ·4
- `angle_bisector` — Биссектриса угла ·4
- `circle_rotations_distance` — Расстояние/число оборотов колеса через длину окружности ·3
- `area_semicircle` — Площадь полукруга ·3
- `semicircle_arc_length` — Длина дуги полуокружности ·1
- `area_quarter_circle` — Площадь четверти круга ·1


## 📘 Измерения, единицы и данные (MD) · 25 навыков, 7 тем
### `3.MD.A` · кл.3 — Solve problems involving measurement and estimation of intervals of time, liquid volumes, and masses of objects.
- `elapsed_time` — Разность/вычитание времени (с заёмом разрядов) ·6

### `3.MD.B` · кл.3 — Represent and interpret data. ← пререкв: `3.NF.A`, `3.OA.D`
- `read_graph_value` — Считать значение по диаграмме/графику (в т.ч. сумма/разность нескольких значений) ·12  ⟵ read_chart_combine

### `3.MD.D` · кл.3 — Geometric measurement: recognize perimeter as an attribute of plane figures and distinguish between linear and area measures. ← пререкв: `3.OA.D`
- `perimeter_rectangle` — Периметр прямоугольника ·16
- `perimeter_square` — Периметр квадрата (и сторона по периметру) ·11
- `perimeter_composite` — Периметр составной фигуры ·5
- `perimeter_triangle` — Периметр треугольника ·4
- `perimeter_concept` — Понятие периметра как длины замкнутой границы ·1
- `perimeter_ratio_side` — Сторона по периметру и отношению сторон ·1
- `perimeter_polygon` — Периметр правильного многоугольника ·1

### `4.MD.A` · кл.4 — Solve problems involving measurement and conversion of measurements from a larger unit to a smaller unit. ← пререкв: `3.MD.A`, `3.MD.D`, `3.OA.A`, `4.NF.C`, `4.OA.A`
- `area_rectangle` — Площадь прямоугольника (и обратное: сторона по площади) ·42
- `area_square` — Площадь квадрата и связь сторона↔площадь ·24
- `days_between_dates` — Число дней между датами (в т.ч. между днями недели) ·3  ⟵ days_of_week_count
- `days_of_week_count` — Сколько дней проходит между днями недели ·1
- `time_add` — Прибавление времени (время прибытия/начала) ·1
- `calendar_days` — Число дней в месяце/календаре ·1

### `4.MD.C` · кл.4 — Geometric measurement: understand concepts of angle and measure angles. ← пререкв: `4.G.A`
- `clock_angle` — Угол между стрелками часов ·5

### `5.MD.A` · кл.5 — Convert like measurement units within a given measurement system. ← пререкв: `4.MD.A`
- `unit_convert_length` — Перевод единиц длины (км↔м↔см↔мм) ·70
- `unit_convert_time` — Перевод единиц времени (ч↔мин↔с) ·38
- `unit_convert_mass` — Перевод единиц массы (кг↔г↔т) ·33
- `unit_convert_area` — Перевод единиц площади (м²↔см²↔га) ·31
- `unit_convert_volume` — Перевод единиц объёма/вместимости (л↔мл↔м³) ·26
- `chained_conversion` — Цепочка пересчёта через коэффициенты ·2

### `5.MD.C` · кл.5 — Geometric measurement: understand concepts of volume and relate volume to multiplication and to addition.
- `painted_cube_count` — Окрашенные/внутренние кубики в разрезанном кубе ·18
- `volume_cube` — Объём куба ·4
- `volume_box` — Объём прямоугольного параллелепипеда (д×ш×в) ·4


## 📘 Операции и алгебраическое мышление (OA) · 25 навыков, 7 тем
### `3.OA.A` · кл.3 — Represent and solve problems involving multiplication and division.
- `find_unknown_divisor` — Нахождение неизвестного делителя ·1

### `3.OA.B` · кл.3 — Understand properties of multiplication and the relationship between multiplication and division. ← пререкв: `3.OA.A`
- `mental_math_strategy` — Приёмы устного счёта: перегруппировка множителей и слагаемых через свойства операций ·8  ⟵ regroup_factors, regroup_addends

### `3.OA.D` · кл.3 — Solve problems involving the four operations, and identify and explain patterns in arithmetic. ← пререкв: `3.MD.A`, `3.OA.A`, `3.OA.B`
- `compute_target_quantity` — Нахождение искомого числа по условию ·6
- `word_problem_trap` — Внимательное чтение вопроса (ловушка в условии) ·1

### `4.OA.A` · кл.4 — Use the four operations with whole numbers to solve problems. ← пререкв: `3.OA.A`, `3.OA.D`, `4.NBT.A`, `4.NBT.B`
- `round_up_ceiling` — Округление вверх по смыслу задачи (доски, забор) ·1
- `round_down_floor` — Округление вниз по смыслу задачи (полные круги) ·1

### `4.OA.B` · кл.4 — Gain familiarity with factors and multiples.
- `prime_factorization` — Разложение числа на простые множители (в т.ч. подсчёт простых множителей) ·95
- `divisibility_rules` — Признаки делимости (на 2, 3, 6, 9, 11 и составные условия) ·48
- `prime_composite` — Определение: число простое или составное ·26
- `divisor_multiple` — Проверка: одно число делитель/кратное другого ·16
- `list_divisors` — Выписывание делителей числа (в т.ч. общих делителей) ·7
- `divisibility_constraint_logic` — Логика делимости в текстовой задаче ·2

### `4.OA.C` · кл.4 — Generate and analyze patterns. ← пререкв: `3.OA.D`
- `sequence_pattern` — Поиск закономерности числового ряда ·53
- `arithmetic_nth_term` — n-й член арифметической прогрессии ·17  ⟵ arithmetic_sequence_term
- `arithmetic_series_sum` — Сумма арифметической прогрессии ·15  ⟵ sum_arithmetic_sequence
- `gauss_sum` — Сумма ряда методом Гаусса (попарная группировка) ·10
- `find_common_difference` — Поиск разности арифметической прогрессии ·9
- `count_terms` — Подсчёт числа членов прогрессии ·9  ⟵ count_in_arithmetic_sequence
- `geometric_seq_ratio` — Знаменатель геометрической прогрессии ·4
- `geometric_seq_nth_term` — n-й член геометрической прогрессии ·4
- `second_difference_sequence` — Вторые разности (квадратичный рост ряда) ·4
- `pattern_recognition` — Распознавание числовой закономерности в сумме ·1
- `linear_extrapolation` — Продолжить линейную закономерность (экстраполяция) ·1

### `5.OA.A` · кл.5 — Write and interpret numerical expressions. ← пререкв: `5.NF.B`
- `order_of_ops` — Порядок действий в выражении ·24
- `insert_parentheses` — Расстановка скобок для нужного результата ·3


## 📘 Обыкновенные дроби (NF) · 13 навыков, 6 тем
### `3.NF.A` · кл.3 — Develop understanding of fractions as numbers. ← пререкв: `3.MD.A`
- `frac_concept` — Запись доли как дроби (часть/целое, закрашенная часть) ·28

### `4.NF.A` · кл.4 — Extend understanding of fraction equivalence and ordering. ← пререкв: `3.NF.A`, `4.OA.A`
- `reduce_frac` — Сокращение дроби ·110
- `common_denom` — Приведение к общему знаменателю / эквивалентные дроби ·76
- `compare_frac` — Сравнение дробей ·31

### `4.NF.B` · кл.4 — Build fractions from unit fractions by applying and extending previous understandings of operations on whole numbers.
- `mixed_improper` — Перевод между смешанным и неправильным числом ·79

### `4.NF.C` · кл.4 — Understand decimal notation for fractions, and compare decimal fractions. ← пререкв: `4.NF.A`
- `decimal_to_fraction` — Перевод десятичной дроби в обыкновенную или смешанное число ·16

### `5.NF.A` · кл.5 — Use equivalent fractions as a strategy to add and subtract fractions. ← пререкв: `4.NF.A`
- `addsub_frac` — Сложение и вычитание дробей (включая смешанные, с заёмом) ·238
- `telescoping_sum` — Телескопическая сумма (разложение 1/(n(n+1))) ·4
- `complement_fraction` — Оставшаяся часть = 1 − известная доля ·2

### `5.NF.B` · кл.5 — Apply and extend previous understandings of multiplication and division to multiply and divide fractions. ← пререкв: `3.NF.A`, `3.OA.B`, `4.MD.A`, `4.NF.A`, `4.NF.B`
- `mul_frac` — Умножение дробей (на дробь, на целое, дробь от дроби) ·124
- `frac_of_number` — Нахождение дроби от числа (в т.ч. от остатка) ·65
- `mixed_to_decimal` — Перевод смешанного числа в десятичную дробь ·2
- `zero_numerator` — Дробь с нулевым числителем равна нулю ·1


## 📘 Числа, разряды и десятичные дроби (NBT) · 10 навыков, 3 тем
### `4.NBT.A` · кл.4 — Generalize place value understanding for multi-digit whole numbers.
- `place_value` — Разрядные цифры и восстановление цифры по примеру ·41
- `rounding` — Округление числа до разряда ·29
- `form_extreme_number` — Составление наибольшего/наименьшего числа из цифр (в т.ч. вычёркиванием) ·14  ⟵ remove_digits_extreme
- `compare_numbers` — Сравнение и выбор наибольшего/наименьшего из подходящих чисел ·5
- `count_digits` — Подсчёт количества цифр в числе ·1

### `4.NBT.B` · кл.4 — Use place value understanding and properties of operations to perform multi-digit arithmetic. ← пререкв: `3.OA.B`, `4.NBT.A`
- `int_div_remainder` — Деление с остатком и поиск числа по остаткам ·54
- `multidigit_ops` — Вычисления в столбик (поразрядно) ·8

### `5.NBT.A` · кл.5 — Understand the place value system. ← пререкв: `4.NBT.A`, `4.NF.C`
- `compare_decimals` — Сравнение и упорядочивание десятичных дробей по величине ·23  ⟵ order_decimals, compare_decimal
- `decimal_place_value` — Разряды и запись десятичной дроби, выделение целой части ·8
- `estimate_decimal_sum` — Оценка результата действий с десятичными через округление ·4


## 📘 Статистика и вероятность (SP) · 9 навыков, 2 тем
### `6.SP.B` · кл.6 — Summarize and describe distributions.
- `sum_from_mean` — Сумма = среднее × количество ·22
- `arithmetic_mean` — Среднее арифметическое = сумма ÷ количество ·18  ⟵ mean_arithmetic
- `median` — Медиана упорядоченного ряда (чётное и нечётное число элементов) ·13
- `mean_find_missing` — Найти недостающее число по известному среднему ·10  ⟵ find_value_from_mean
- `mode` — Мода ряда — наиболее частое значение (подсчёт частот) ·10
- `range` — Размах ряда = наибольшее − наименьшее ·5
- `range_find_unknown` — Найти неизвестный элемент по заданному размаху ·2
- `weighted_average` — Средневзвешенное (общий итог ÷ общий объём) ·1

### `7.SP.C` · кл.7 — Investigate chance processes and develop, use, and evaluate probability models. ← пререкв: `7.RP.A`
- `probability_basic` — Классическая вероятность (благоприятные / всего) ·50


---
## 🏅 НИШ-ветка (вне Common Core 2-7) · 97 навыков
### `NIS.LOGIC` — Логика и рассуждения (30) ← опирается на: `4.OA.A`, `3.OA.D`, `5.OA.A`
- `logic_grid_elimination` — Логическая таблица: метод исключения ·31
- `cuts_pieces_relation` — Распилы/столбы: частей на 1 больше числа разрезов ·29  ⟵ fencepost_counting, interval_counting
- `inclusion_exclusion` — Формула включений-исключений для двух множеств: |A∪B| = |A| + |B| − |A∩B| (находим объединение, пересечение или недостающую часть) ·29  ⟵ set_inclusion_exclusion, inclusion_exclusion_counting
- `knights_liars_reasoning` — Задачи о рыцарях и лжецах (предположение и проверка) ·27
- `solve_inequality_system` — Решить систему неравенств (пересечение решений, в т.ч. пустое) ·15
- `cryptarithm` — Криптарифм: запись по разрядам, подбор и решение ·12  ⟵ cryptarithm_setup, cryptarithm_solve
- `logic_ordering` — Упорядочивание объектов по условиям ·7
- `decimal_neighbors` — Поиск десятичной дроби между границами и соседних значений ·7
- `set_complement` — Дополнение множества — все элементы универсума, не входящие в данное подмножество ·7
- `guess_and_check` — Подбор и проверка (перебор вариантов) ·6
- `inclusion_exclusion_three` — Формула включений-исключений для трёх множеств (учёт двойного и тройного пересечения) ·6
- `set_cardinality` — Мощность множества — перечислить элементы и сосчитать их количество (n(A)) ·6
- `set_difference` — Разность множеств A\B — элементы, которые есть в A, но не в B ·6
- `set_only_one` — Элементы ровно в одном множестве — «только A» = |A| − |A∩B| ·5
- `set_union` — Объединение множеств A∪B — выписать все элементы из обоих без повторов ·5
- `work_backwards` — Решение с конца (обратное удвоение/деление пополам) ·4
- `set_intersection` — Пересечение множеств A∩B — найти и сосчитать общие элементы обоих множеств ·4
- `assume_all_one_type` — Метод предположения (все объекты одного типа) ·3
- `intersect_solution_sets` — Пересечение множеств решений (системы неравенств) ·3
- `objects_around_closed_path` — Объекты по замкнутому контуру (число = промежуткам) ·2
- `frog_well_last_jump` — Лягушка в колодце (последний прыжок выводит наверх) ·2
- `doubling_concept` — Удвоение/деление пополам по дням (рост/обратный ход) ·2
- `syllogism` — Силлогизм (логический вывод) ·2
- `cipher_substitution` — Шифр-подстановка (буквы в цифры) ·2
- `insert_operation_signs` — Расстановка знаков действий для получения результата ·2
- `non_numeric_step` — Шаг без вычислений (величина остаётся без изменений) ·2
- `cuts_3d_per_dimension` — Разрезы куба по каждому из трёх измерений ·1
- `cuts_ring` — Разрезы кольца = число частей (замкнутая фигура) ·1
- `find_digits_from_sum_product` — Подбор цифр по их сумме и произведению ·1
- `logic_deduction` — Логический вывод недостающей цифры/значения ·1

### `NIS.COMB` — Комбинаторика и перебор (26) ← опирается на: `7.SP.C`, `3.OA.D`, `6.EE.A`
- `count_integers_in_interval` — Перечислить / сосчитать / суммировать целые числа в промежутке ·74  ⟵ count_integers_between, count_integers_in_range_logic
- `count_without_repetition` — Подсчёт размещений без повторений ·47
- `counting_product_rule` — Правило произведения (умножения) в комбинаторике ·43
- `factorial` — Вычисление факториала n! ·37  ⟵ int_sub
- `count_with_constraint` — Подсчёт вариантов с ограничением на разряд (в т.ч. запрет нуля в старшем разряде) ·31  ⟵ exclude_leading_zero
- `count_segments_combinations` — Число отрезков через сочетания из точек ·30
- `permutations_with_repetition` — Перестановки с повторяющимися элементами (в т.ч. буквы слова с повторами) ·17  ⟵ count_repeated_elements
- `count_triangles_figure` — Подсчёт треугольников на чертеже ·16
- `permutations` — Перестановки n! (расстановка по порядку) ·16
- `count_with_repetition` — Подсчёт размещений с повторениями (n^k) ·9
- `count_numbers_in_range` — Подсчёт чисел в диапазоне (в т.ч. по признаку) ·8
- `factorial_ratio` — Сокращение отношения факториалов ·7
- `handshake_count` — Подсчёт пар или встреч (рукопожатия, круговой турнир) ·6
- `complementary_counting` — Подсчёт через дополнение (все минус запрещённые) ·6  ⟵ complement_counting
- `count_locks_structure` — Подсчёт объектов во вложенной структуре (сундук-ящики) ·4
- `count_angles_figure` — Подсчёт углов/лучей на чертеже ·2
- `count_grid_lines` — Подсчёт линий, делящих фигуру ·2
- `counting_sum_rule` — Правило суммы (выбор «или») в комбинаторике ·2
- `factorial_inverse` — Подбор n по значению n! ·2
- `count_distinct_digit_numbers` — Подсчёт чисел с различными цифрами ·2
- `count_decimals_in_range` — Подсчёт количества десятичных дробей в промежутке ·2
- `count_squares_grid` — Подсчёт квадратов на сетке ·1
- `count_rectangles_grid` — Подсчёт прямоугольников на сетке ·1
- `position_count_overlap` — Подсчёт позиции в очереди с устранением двойного счёта ·1
- `conditional_probability_without_replacement` — Условная вероятность без возвращения ·1
- `enumerate_pairs` — Перебор пар чисел с заданным условием ·1

### `NIS.NT` — Теория чисел (цифры, остатки, инварианты) (24) ← опирается на: `4.OA.B`, `4.NBT.A`, `6.NS.B`
- `units_digit_cycle` — Последняя цифра степени по циклу ·60
- `classify_number_type` — Классификация числа: натуральное, целое, рациональное, иррациональное ·37  ⟵ classify_natural_number
- `page_numbering_digits` — Подсчёт цифр в нумерации страниц/диапазоне чисел ·28
- `count_elements` — Подсчёт количества чисел, удовлетворяющих условию ·27
- `last_digit_of_operation` — Последняя цифра суммы, произведения или разности ·24
- `weekday_cycle` — День недели вперёд по счёту цикла/остатку ·22
- `count_divisors` — Подсчёт количества делителей числа (по формуле степеней) ·18
- `euler_totient` — Подсчёт чисел, взаимно простых с n (функция Эйлера φ) ·12
- `modular_remainder` — Остаток от деления для циклической задачи (mod) ·9
- `simplify_perfect_square_root` — Извлечение корня из точного квадрата и проверка иррациональности ·9
- `count_multiples_in_range` — Подсчёт кратных/членов в диапазоне по формуле (последнее−первое)/d+1 ·9  ⟵ count_multiples
- `gcd_lcm_product` — Свойство НОД(a,b) × НОК(a,b) = a × b ·7
- `trailing_zeros_factorial` — Число нулей в конце факториала ·6
- `digit_sum` — Сумма цифр числа ·5
- `page_sheet_sum` — Сумма номеров страниц одного листа ·4
- `finite_decimal_test` — Признак конечной/периодической десятичной записи по знаменателю ·4
- `integer_bound_from_decimal` — Найти наименьшее / наибольшее целое, удовлетворяющее границе ·4
- `modular_last_digit` — Последняя цифра числа/степени/суммы через модульную арифметику ·3
- `count_digit_occurrences` — Сколько раз встречается цифра в диапазоне ·2
- `coprime_proof` — Доказательство взаимной простоты (напр. соседних чисел через делитель разности) ·2
- `sum_of_divisors` — Сумма делителей числа (σ через суммы степеней простых) ·2
- `last_nonzero_digit` — Последняя ненулевая цифра числа ·1
- `digit_reversal_number` — Число и его перевёртыш через разряды (10a+b) ·1
- `digit_sum_search` — Поиск числа/года по заданной сумме цифр ·1

### `NIS.ALG` — Продвинутая алгебра (системы, модуль, квадратные) (17) ← опирается на: `7.EE.B`, `7.EE.A`, `6.EE.B`
- `solve_system_substitution` — Решение системы методом подстановки ·36
- `solve_system_elimination` — Решение системы методом сложения/вычитания (исключения) ·25
- `solve_abs_inequality` — Решение неравенства с модулем ·24
- `solve_double_inequality` — Решить двойное неравенство (a < выражение < b) ·17
- `sum_and_difference_method` — Метод суммы и разности (нахождение двух чисел) ·11
- `algebraic_identity` — Применить формулу сокращённого умножения / тождество ·11
- `interval_notation` — Запись промежутков и перечисление целых внутри ·8
- `setup_system_from_words` — Составление системы уравнений по условию задачи ·7
- `factor_quadratic` — Решение квадратного уравнения разложением на множители ·4
- `product_with_zero` — Произведение с нулём равно нулю ·4  ⟵ zero_product, zero_product_property
- `inequality_sign_flip` — Смена знака неравенства при делении на отрицательное ·3  ⟵ inequality_sign_flip_neg
- `monomial_mult` — Умножить одночлены ·3
- `expand_square` — Раскрытие квадрата суммы/разности ·2
- `linear_equation_from_points` — Найти свободный член b / уравнение прямой по точке ·2
- `expand_binomial_product` — Раскрыть скобки в произведении двучленов (почленно) ·2
- `factor_difference_squares` — Разложение по формуле разности квадратов ·1
- `solve_sum_product` — Найти два числа по их сумме и произведению ·1

---
## Что слили (372→337)
**Кросс-доменные дубли (12) + ревью-слияния (9):**
- `inclusion_exclusion` ⟵ `set_inclusion_exclusion` — Один и тот же навык — формула включений-исключений для двух множеств (общий pare
- `inclusion_exclusion` ⟵ `inclusion_exclusion_counting` — Дубль той же формулы включений-исключений (общий parent NIS.COMB.inclusion_exclu
- `complementary_counting` ⟵ `complement_counting` — Один навык — подсчёт через дополнение «все минус запрещённые» (общий parent NIS.
- `count_integers_in_interval` ⟵ `count_integers_between` — Один навык — перечисление/подсчёт целых чисел в промежутке. keep в algebra (freq
- `count_integers_in_interval` ⟵ `count_integers_in_range_logic` — Тот же навык — целые числа в промежутке (границы, перечисление, сумма). keep в a
- `arithmetic_mean` ⟵ `mean_arithmetic` — Идентичное определение — среднее арифметическое = сумма ÷ количество. keep в wor
- `mean_find_missing` ⟵ `find_value_from_mean` — Один навык — найти недостающий элемент по известному среднему. keep в word_probl
- `cuts_pieces_relation` ⟵ `fencepost_counting` — Один навык fencepost — промежутки против объектов, распилы/столбы (общий parent 
- `cuts_pieces_relation` ⟵ `interval_counting` — Тот же fencepost-навык (off-by-one, забор/распилы). keep в word_problems (freq 2
- `direct_proportion` ⟵ `proportion_direct` — Идентичный навык — прямая пропорциональность / масштабирование величины. keep в 
- `inequality_sign_flip` ⟵ `inequality_sign_flip_neg` — Один навык — смена знака неравенства при делении на отрицательное (общий parent 
- `solve_linear_inequality` ⟵ `solve_inequality_one_step` — Тот же навык — решение простейшего линейного неравенства. keep в algebra (профил
- arithmetic_series_sum←sum_arithmetic_sequence
- arithmetic_nth_term←arithmetic_sequence_term
- compare_decimals←compare_decimal
- product_with_zero←zero_product
- product_with_zero←zero_product_property
- percent_increase←percent_increase_overall
- count_multiples_in_range←count_multiples
- percent_area_change←percent_change_area
- count_terms←count_in_arithmetic_sequence

**Перенесено НИШ→CC (по якорю):** `square_root`, `cube_root`, `side_from_area_square`, `nearest_perfect_square`, `repeating_decimal_to_frac`

## ⚠️ На ручное ревью маппинга (0)
—