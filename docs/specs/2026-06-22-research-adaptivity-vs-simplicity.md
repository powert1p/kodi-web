# Deep Research: адаптивная машинерия kodi-web vs более простые подходы

> Дата: 2026-06-22 · Режим: deep (8 фаз, 7 параллельных ресёрч-агентов + red-team) · ~70 источников · триангуляция ≥2 источника/вывод
> Вопрос: даёт ли граф знаний + BKT + 3-фазная диагностика + 2-фазный экзамен прирост, пропорциональный сложности — или то же достижимо радикально проще?
> Метрика успеха (владелец): **сбалансированно** результат на экзамене НИШ + durable-усвоение математики.

---

## Вердикт одной строкой

**SIMPLIFY-IN-PLACE (гибрид), уверенность ~80-85% по форме.** Владелец прав на ~75%: **uncalibrated per-node BKT — реальное переусложнение, его надо снять** (самый сильный, количественно подтверждённый вывод). Но рамка «никаких графов» **переусекает**: «разбить задачу на подзадачи» — это и есть когнитивный анализ задачи (cognitive task analysis), а граф — его предвычисленная, проверяемая форма. Правильный разрез: **снять BKT, СЖАТЬ (не удалять) граф до мелкой карты пререквизитов, сохранить доказанные механики** (mastery-gate, spacing, банк ошибок, worked-example декомпозиция, interleaving).

---

## Executive Summary

Исследование по семи направлениям (BKT/knowledge tracing; граф пререквизитов/KST; mastery learning; spacing/retrieval; декомпозиция/scaffolding; продуктовый ландшафт; минимальная модель) сходится к одному заключению: **сложность kodi-web сконцентрирована ровно там, где литература находит наименьшую отдачу, а ценность — в дешёвых механиках, которые владелец и предлагает оставить.**

Per-node BKT с никогда не калиброванными параметрами (T=0.3/G=0.05/S=0.1) находится одновременно в двух худших режимах: **cold-start** (мало попыток на ноду) и **семантическая дегенерация** (несколько разных наборов параметров одинаково описывают данные, но означают разное). Надёжная подгонка BKT требует ~50-100 учеников и ≥15 попыток на навык [6]; персонализация памяти (FSRS/Duolingo HLR) отделяется от фиксированного расписания только после ~1000+ наблюдений [11 sp]. kodi-web на порядки ниже обоих порогов. То, что калибровочный тулинг — мёртвый код, это диагностический признак: BKT-слой никогда не доходил до состояния, в котором литература даёт ему хоть какое-то преимущество.

Одновременно «дешёвые» механики, которые владелец хочет сохранить, — это сильнейшие, наиболее реплицируемые эффекты в области: mastery-to-criterion (d≈0.5-0.59), worked examples в математике (g=0.48), interleaving (d≈0.83-1.21), банк ошибок/error-analysis (t(51)=2.60). Higher KT-AUC **нигде не валидирован** как причина прироста обучения; durable-learning несут инструкционные механики, а не трейсер.

**Ключевая поправка от red-team (анти-bias):** sweep агентов всё же склонялся к «упростить». Два несущих неизвестных НЕ разрешены: (1) надёжность LLM/ad-hoc декомпозиции в правильные пререквизиты — замену не аудировали так, как BKT; (2) траектория роста когорты — если когорт будет много, fit-free-сейчас/калибруемый-потом логистик лучше, чем удаление всякого моделирования. И реальный тай-брейкер — **операционный**: для solo-нетехнаря отлаживаемость и объяснимость решают, и это ортогонально всем статьям.

**Математическая контр-поправка:** именно в МАТЕМАТИКЕ spacing даёт лишь g=0.28, а чистый testing/retrieval **не робастен** (g=0.18, CI пересекает ноль) [Murray 2025]. Значит «банк ошибок + spacing» в одиночку недотягивает по durable-learning. Тяжёлую работу несут interleaving, worked-example декомпозиция и mastery-to-criterion — их и должна нести минимальная модель.

---

## Матрица решения (две строки результата, не усреднять)

| Ось | Текущее: граф+BKT+диагностика | Альтернатива владельца: «чистый банк ошибок, без графов» | **Рекомендуемый гибрид** |
|---|---|---|---|
| **Exam-prep (НИШ)** | Слабо: KT-AUC не → exam; адаптивная последовательность часто не бьёт простую; ALEKS как замена g≈0.05 | Средне: error-bank + difficulty-ladder бьёт по слабым местам, но без routing к корню пробела | **Лучшее: interleaving (exam-like выбор стратегии) + error-bank + ladder** |
| **Durable learning** | Среднее, но не за счёт BKT — за счёт mastery-loop, который случайно работает | Риск: в математике spacing g=0.28 / retrieval не робастен; без декомпозиции в пререквизиты gap не чинится | **Лучшее: worked-example декомпозиция + mastery-gate + мелкая prereq-карта** |
| **Сложность / LOC** | Высокая: diagnostic 1335 + exam 599 + bkt 230 + selector 438 + graph 157 + мёртвые scorers/classifiers ~40 модулей | Низкая, но прячет prereq-модель «в голове», воспроизводит её непоследовательно | **Средне-низкая: одна ability-цифра/навык + мелкая карта + faded декомпозиция** |
| **Стоимость поддержки (solo)** | Высокая: непрозрачные mastery-решения, скрытые magic numbers, дубли/рассинхрон | Низкая | **Низкая: всё прозрачно и объяснимо родителю/ученику** |
| **Поведение при малых данных** | Плохое: ниже data-floor BKT, posterior правят дефолты-приоры, не ученик | Хорошее (но недо-чинит durable-half) | **Хорошее: правила fit-free, граф — авторское знание, не подгонка** |
| **Риск/обратимость** | — | Высокий: удалить граф дёшево, ВОССТАНОВИТЬ дорого, если декомпозиция-на-лету окажется ненадёжной | **Низкий: снять BKT обратимо; граф сжать, не удалять (option value)** |

---

## Механизм → доказательство → решение

| Механизм в kodi-web | Доказательная база | Решение |
|---|---|---|
| **Per-node BKT (uncalibrated)** | Data-floor ~50-100 учеников/≥15 попыток [6]; identifiability + семантическая дегенерация [3][9]; в cold-start простой логистик/Elo бьёт BKT [5] | **CUT** → заменить прозрачным mastery-правилом |
| **118-нодовый DAG как sequencer** | Авторские pre-req edges: kappa≈0.30 согласие экспертов [9c2]; «поверхностные» пререквизиты не дают transfer [8c2]; ALEKS строит структуру из млн записей, не вручную [7c2] | **SHRINK** → мелкая карта высоконадёжных foundational-цепочек, 1 уровень |
| **Mastery-gate (0.85 / 0.7)** | Kulik d≈0.52 [3]; выше критерий → durable retention (логарифмически, монотонно) [8c3]; это и был механизм за «2-сигмой» Блума | **KEEP** (поднять 0.7→0.8); реализовать как простой %-порог, не BKT |
| **Spacing / next_review** | Cepeda 839 замеров [5sp]; НО в математике g=0.28 [Murray 2025] | **KEEP** (дёшево, положительно) → Leitner/фикс-интервалы 1,3,7,16,35д |
| **Банк ошибок / re-practice missed** | Error-analysis t(51)=2.60, p=.012 [12sp]; retrieval силён для изоморфных items | **KEEP, сделать центральным** |
| **Worked-example декомпозиция + subgoal labels** | Math worked examples g=0.48 [1d]; subgoal labeling → transfer [Catrambone] | **KEEP** — это и есть «разбить на подзадачи», сделанное правильно |
| **Interleaving навыков** | d≈0.83 RCT 787 учеников [Rohrer 2020]; 77% vs 38% [Taylor-Rohrer] | **ADD** — нужна мелкая карта навыков; бьёт по ОБЕИМ метрикам |
| **Faded scaffolding** | Помогает novice; рано убрать → хуже [11d]; expertise-reversal [Kalyuga] | **KEEP с fade** по ability-сигналу |
| **Difficulty ladder** | 85%-правило (Wilson 2019, Nature Comms) [13mm]; Elo ≈ логистик по точности, прозрачнее [5mm][7mm] | **REPLACE BKT** → rolling success-rate / Elo, цель ~85% |
| **3-фазная диагностика / 2-фазный экзамен** | Эта вода НЕ оценивалась данным ресёрчем (память-модели ≠ оценка диагностики) | **ОТДЕЛЬНЫЙ обзор** — не трогать на основании этого отчёта |

---

## Минимальная жизнеспособная модель (если упрощать)

Сохраняет все сильно-доказанные механики БЕЗ графа-как-движка и БЕЗ BKT:

1. **Плоский банк задач**, теггированных по навыку + difficulty-tier.
2. **Одна ability-цифра на ученик×навык** = rolling success-rate (последние 5-8) ИЛИ один Elo. Заменяет `p_mastery`/BKT.
3. **Mastery = простой критерий** (≥85% за последние N, или K подряд верных). Заменяет `is_mastered`.
4. **Difficulty ladder целит ~85% успеха**; ниже ~70-75% — шаг вниз + декомпозиция.
5. **Decompose-on-error в FADED worked sub-steps с subgoal-labels**; пара «неверная попытка ученика → верное worked-решение».
6. **Мелкая remediation-карта**: каждый grade-7 target → его 2-3 пререквизита 3-6 класса, 1 уровень. При повторном провале — спуск вниз. (Это «граф», сжатый.)
7. **Interleaving навыков** в очереди по умолчанию (не блочить одну ноду до mastery).
8. **Spaced revisit** (Leitner/фикс-лестница) для освоенных навыков.

**Что реально и навсегда теряется:** вероятностные posterior для тонкого выбора следующего item; многошаговая (>1 уровень) цепочка пререквизитов; будущая калиброванная-BKT персонализация — ни одно из этого недостижимо на текущих данных, так что потеря в основном теоретическая.

---

## Рекомендация: роадмап

**Фаза 1 — низкий риск, делать сейчас (уверенность ~85%):**
- Заменить BKT-mastery на rolling-rate / 85%-правило; снести `core/bkt.py` как движок (формулы оставить в истории).
- Унифицировать рассинхрон порогов 0.7/0.85 в одно определение «освоено».
- Сделать банк ошибок центральным циклом практики; ввести interleaving навыков по умолчанию.
- Удалить мёртвый калибровочный тулинг (`core/scorers` + `core/classifiers`, ~40 модулей) — он подтверждает, что BKT никогда не был load-bearing.
- Сохранить spacing (next_review).

**Фаза 2 — после Фазы 1:**
- Сжать DAG до высоконадёжных foundational-цепочек (арифметика/дроби, реально гейтящие 7-класс НИШ); выкинуть длинный хвост поверхностных рёбер.
- Реализовать faded worked-example декомпозицию + subgoal labels; пара «ошибка → верное решение».

**НЕ делать:**
- НЕ удалять prereq-структуру полностью, пока не проверена надёжность декомпозиции (LLM/ручной) в правильные пререквизиты — это load-bearing неизвестное.
- НЕ ждать «2-сигмы»: при честной оценке в математике, на стандартизованном тесте, все эффекты сжимаются к малому концу.

**Дешёвый эксперимент до коммита:** прогнать текущие BKT-дефолты vs N-подряд-верных на реальных логах попыток — подтвердить, «ведёт ли себя BKT как сглаженный счётчик» (red-team справедливо отметил, что это утверждение теоретическое, не измеренное).

---

## Ограничения и оговорки (red-team против собственного анти-bias)

Red-team-агент поймал реальный simplify-перекос sweep'а. Что важно держать в голове:

1. **Асимметрия бремени доказательства.** BKT требовали доказать пользу на крошечной когорте — или вырезать; замену (LLM-декомпозиция) этой планке НЕ подвергли. Никто не искал данные о надёжности LLM-декомпозиции NIS-задач, о галлюцинированных пререквизитах, о неверном routing. **Это крупнейший пробел.**
2. **«BKT = счётчик» переусилено.** При G=0.05/S=0.1 posterior НЕ идентичен наивному счётчику — slip/guess-толерантность сдвигает точку mastery и сопротивляется «mastery от одного угаданного». Корректно: «ведёт себя как сглаженный счётчик с непрозрачными порогами», а не «не лучше счётчика».
3. **Khajah-Lindsey-Mozer (within-0.01 AUC) — про FITTED BKT на больших данных**, т.е. противоположность режиму kodi. Этот результат бьёт по «не покупай DKT/deep», а НЕ доказывает «дефолтный BKT = счётчик». Cut-кейс для kodi держится на data-floor + identifiability, не на этом AUC-паритете.
4. **kappa≈0.30 — из NLP-корпусов широких тем**, не из K-12 арифметики, где рёбра («сложение дробей требует общего знаменателя») куда менее спорны. «Граф скорее всего сильно неверен» — преувеличение; нужна оценка доли high-confidence vs хвоста.
5. **Нет доказательств, что текущий BKT АКТИВНО вредит** обучению. Cut-кейс держится на «нет пользы + стоимость поддержки», а не на «вред» — это слабее, чем уверенные «cut». Отсюда «shelve, не обязательно delete».
6. **Пропущенные оси:** операционная стоимость для solo-нетехнаря (реальный тай-брейкер, никто не оценил в цифрах); IRT/Rasch как более точный инструмент именно для exam-prep с фиксированным банком (PFA упомянут, IRT — нет); мотивация/удержание (mastery-gate может запирать слабых в циклах); option-value сохранения дешёвого авторского DAG даже при удалении BKT.

**Где уверенность ниже (~55-60%):** удалять граф полностью vs сжать. Не разрешено доказательствами, т.к. не собрали данные о надёжности декомпозиции-на-лету. Лин — сжать, не удалять (DAG дёшев, иммунен к data-floor критике, дорог к восстановлению). Что изменит решение: (1) измеренная точность LLM-декомпозиции NIS-задач; (2) план роста когорт; (3) фактический прогон BKT-дефолтов vs N-in-a-row на логах; (4) если метрика exam-доминантна — занижать ожидания для ЛЮБОЙ архитектуры.

---

## Методология

8 фаз deep-research (Scope → Plan → Retrieve → Triangulate → Synthesize → Critique → Refine → Package). Фаза Retrieve — 7 параллельных агентов, каждый с реальными веб-поисками по своему кластеру, структурированный возврат с источниками/effect-size/credibility. Фаза Critique — отдельный red-team-агент против simplify-bias. Триангуляция: ≥2 источника или источник+факт из кода на ключевой вывод. Факты о коде kodi-web (дефолтные BKT-параметры, мёртвый калибровочный тулинг, рассинхрон порогов 0.7/0.85, размеры модулей) сверены напрямую с `backend/core/*.py` и `db/seed.py`. ~70 источников, преобладают peer-reviewed мета-анализы (Review of Educational Research, Educational Psychology Review, Psychological Bulletin, JEDM/EDM) и крупные RCT.

---

## Библиография (ключевые источники, дедуплицировано по кластерам)

**Knowledge Tracing / BKT:**
1. Khajah, Lindsey & Mozer (2016). "How Deep is Knowledge Tracing?" EDM. — extended BKT ≈ DKT within ~0.01 AUC; DKT-преимущество частью артефакт оценки. https://home.cs.colorado.edu/~mozer/Research/Selected%20Publications/reprints/KhajahLindseyMozer2016.pdf
2. Corbett & Anderson (1995). "Knowledge tracing." UMUAI. — 4 параметра per skill; фреймворк предполагает подгонку per-skill, не глобальные дефолты. https://link.springer.com/article/10.1007/BF01099821
3. Doroudi & Brunskill (2017). "The Misidentified Identifiability Problem of BKT." EDM. — семантическая дегенерация: best-fit параметры нарушают смысл модели. https://www.cs.cmu.edu/~shayand/papers/EDM2017.pdf
4. Badrinath, Liu & Pardos (2021). "pyBKT" + data-sufficiency. — ≥15 попыток/навык, ~50-100 учеников для надёжной EM-оценки. https://arxiv.org/pdf/2105.00385
5. EDM (2025). "Evolutionary Features for Mitigating Cold Starts in LKT." — 7-параметрический логистик бьёт BKT/Elo на сотнях наблюдений, near-peak на <5% данных. https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.short-papers.177/index.html
6. Yudelson, Koedinger & Gordon (2013). "Individualized BKT." — несвязанная EM-подгонка часто даёт дегенеративные решения/локальные минимумы. https://www.cs.cmu.edu/~ggordon/yudelson-koedinger-gordon-individualized-bayesian-knowledge-tracing.pdf
7. van de Sande (2013). "Properties of the BKT Model." JEDM. — множество разных параметров одинаково описывают данные. https://jedm.educationaldatamining.org/index.php/JEDM/article/download/35/pdf_27
8. Liu et al. (2023). "simpleKT." ICLR. — простой baseline top-3 против 12 deep-KT моделей. https://arxiv.org/abs/2302.06881
9. Baker et al. (2024). "AUC Is Not the Problem." — защищает AUC как метрику, но НЕ утверждает, что AUC→обучение. https://arxiv.org/abs/2404.06989
10. Pavlik, Cen & Koedinger (2009). PFA — логистик ≥ BKT на математике, глобальный оптимум, уникальные параметры.
11. arXiv 2511.00704 (2025). KT robustness under concept drift — BKT стабильнее deep-моделей в sparse-режиме.

**Mastery learning / tutoring:**
12. Kulik, Kulik & Bangert-Drowns (1990). "Effectiveness of Mastery Learning Programs." RER. — 108 оценок, d≈0.52, сильнее для слабых. https://journals.sagepub.com/doi/10.3102/00346543060002265
13. VanLehn (2011). "Relative Effectiveness of Human Tutoring, ITS…" Educational Psychologist. — step-based ITS d=0.76 ≈ human 0.79; substep НЕ добавляет (interaction plateau). https://www.tandfonline.com/doi/abs/10.1080/00461520.2011.611369
14. Bloom (1984). "The 2 Sigma Problem." — оригинал; 2-сигма во многом артефакт более строгого порога (90 vs 80%) + время. https://journals.sagepub.com/doi/10.3102/0013189X013006004
15. Slavin (1987). "Mastery Learning Reconsidered." RER. — почти ноль на стандартизованных тестах; time-confound. https://journals.sagepub.com/doi/10.3102/00346543057002175
16. Pitts et al. / criterion-level (2018). — выше критерий → durable maintenance, логарифмически. https://pmc.ncbi.nlm.nih.gov/articles/PMC5843573/
17. EEF (2015). "Mathematics Mastery" RCT. — primary +2 мес (~d=0.10-0.15), secondary +1 мес — скромно. https://educationendowmentfoundation.org.uk/projects-and-evaluation/projects/mathematics-mastery
18. Khan Academy / Oreopoulos et al. (2024, NBER). — RCT n~11k: +0.12-0.22 SD; India enforced +0.44-0.47 SD. https://blog.khanacademy.org/khan-academy-improves-state-test-scores-results-from-new-3-year-efficacy-study/

**KST / граф пререквизитов:**
19. Sun, Else-Quest et al. (2021). "Effects of ALEKS: A Meta-Analysis." — замена g=0.05 (нейтрально), supplement g=0.43. https://www.tandfonline.com/doi/full/10.1080/19477503.2021.1926194
20. Kulik & Fletcher (2016). "Effectiveness of ITS: Meta-Analytic Review." RER. — медиана 0.66 SD, но много меньше на стандартизованных тестах. https://journals.sagepub.com/doi/abs/10.3102/0034654315581420
21. Matayoshi & Cosyn (2021). "A practical perspective on KST: ALEKS and its data." JMP. — структура ALEKS уточнена из больших данных, не ручная. https://jmatayoshi.github.io/publications/JMP2021_KST_ALEKS_preprint.pdf
22. CBE-Life Sci (2016). "A Familiar(ity) Problem." — поверхностно покрытый пререквизит не даёт downstream-преимущества. https://pmc.ncbi.nlm.nih.gov/articles/PMC4733054/
23. Fabbri et al. (2018). "TutorialBank" + prereq-corpora. — согласие по pre-req рёбрам kappa≈0.30. https://arxiv.org/pdf/1805.04617

**Spacing / retrieval / interleaving (durable learning):**
24. Murray, Horner & Göbel (2025). "Spacing and Retrieval Practice for Mathematics." Educational Psychology Review. — МАТЕМАТИКА: spacing g=0.28; retrieval g=0.18, CI пересекает ноль (не робастен). https://link.springer.com/article/10.1007/s10648-025-10035-1
25. Cepeda et al. (2006). "Distributed Practice." Psychological Bulletin. — 839 замеров; spaced > massed на всех интервалах. https://pubmed.ncbi.nlm.nih.gov/16719566/
26. Cepeda et al. (2008). "Temporal Ridgeline of Optimal Retention." — оптимальный gap масштабируется с интервалом удержания. https://files.eric.ed.gov/fulltext/ED505660.pdf
27. Roediger & Karpicke (2006). "Test-Enhanced Learning." — retrieval ~50% больше удержания vs повторное чтение. http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PPS.pdf
28. Adesope et al. (2017). "Meta-Analysis of Practice Testing." RER. — g=0.50-0.61 (но в основном не-математика). https://journals.sagepub.com/doi/abs/10.3102/0034654316689306
29. Dunlosky et al. (2013). "Effective Learning Techniques." — только practice testing и distributed practice = "high utility". https://journals.sagepub.com/doi/abs/10.1177/1529100612453266
30. Karpicke & Roediger (2007). "Expanding vs Equal-interval." — equal-interval лучше long-term; expanding не нужен. https://learninglab.psych.purdue.edu/downloads/2007/2007_Karpicke_Roediger_JEPLMC.pdf
31. Settles & Meeder (2016). "Half-Life Regression." Duolingo/ACL. — но подгонка на ~13M трасс; персонализация требует больших данных. https://research.duolingo.com/papers/settles.acl16.pdf
32. Rohrer, Dedrick, Hartwig & Cheung (2020). RCT interleaved math. — 787 учеников, interleaved d≈0.83. https://gwern.net/doc/psychology/spaced-repetition/2019-rohrer.pdf
33. Taylor & Rohrer (2010). Interleaving 4-й класс. — 77% vs 38% (d=1.21). https://digitalcommons.usf.edu/psy_facpub/1760/

**Декомпозиция / worked examples / scaffolding:**
34. Barbieri et al. (2023). "Worked Examples Effect on Mathematics." Educational Psychology Review. — math g=0.48. https://link.springer.com/article/10.1007/s10648-023-09745-1
35. Catrambone (1998). "Subgoal learning model." JEP:General. — subgoal-структура драйвит transfer на новые задачи.
36. Clark et al. / LearnLab. "Cognitive Task Analysis." — expert blind spot (~70% решений неосознанны); декомпозиция требует явного анализа. https://learnlab.org/cognitive-task-analysis/
37. BJS Open (2021). "CTA-based training in surgery: meta-analysis." — procedural SMD=1.36, technical SMD=2.06: качество декомпозиции = очень большие эффекты. https://pmc.ncbi.nlm.nih.gov/articles/PMC8669793/
38. Pane et al. (2014, RAND). "Cognitive Tutor Algebra I at Scale." — model-tracing: 0 в год 1, +0.21 SD в год 2. https://journals.sagepub.com/doi/abs/10.3102/0162373713507480
39. Kalyuga (2007). "Expertise Reversal Effect." — worked examples помогают novice, вредят expert → fade нужен. https://www.uky.edu/~gmswan3/EDC608/Kalyuga2007_Article_ExpertiseReversalEffectAndItsI.pdf
40. Sweller (1988). "Cognitive Load During Problem Solving." — основа: worked examples vs means-ends для novice.

**Минимальная модель / difficulty:**
41. Wilson, Shenhav, Straccia & Cohen (2019). "The Eighty Five Percent Rule." Nature Communications. — оптимальная ошибка ≈15.87% (≈85% точность). https://www.nature.com/articles/s41467-019-12552-4
42. Pelánek et al. (2019). "Multivariate Elo-based Learner Model." — Elo прост, быстр, robust, order-sensitive. https://arxiv.org/pdf/1910.12581
43. EDM (2025). "Multidimensional Elo for tracking ability." — точность Elo ≈ логистик, прозрачнее. https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.99/index.html
44. Springer Comp Brain & Behav (2021). "Cold Start via Data-Driven Difficulty Estimates." — популяционная сложность бьёт per-node моделирование при sparsity. https://link.springer.com/article/10.1007/s42113-021-00101-6
45. LAK (2025). "Algorithm Appreciation in Education." — педагоги предпочитают сложный (BKT) простому эвристику; объяснения не помогают (perception-риск). https://dl.acm.org/doi/10.1145/3706468.3706535

