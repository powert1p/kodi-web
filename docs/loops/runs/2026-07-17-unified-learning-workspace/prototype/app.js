(() => {
  const params = new URLSearchParams(window.location.search);
  const concept = ["a", "b", "c"].includes(params.get("concept")) ? params.get("concept") : "a";
  const requestedState = params.get("state") || "independent";

  const concepts = {
    a: { letter: "A", name: "Поля мысли" },
    b: { letter: "B", name: "Точный верстак" },
    c: { letter: "C", name: "Нить решения" },
  };

  const states = {
    independent: {
      kicker: "Перед отправкой",
      title: "Покажи весь ход решения",
      body: `
        <p class="lead-note">Одного ответа недостаточно: на фото должны быть видны вычисления и итог.</p>
        <div class="micro-check" aria-label="Что должно быть видно">
          <span><i aria-hidden="true">1</i> условие или номер задачи</span>
          <span><i aria-hidden="true">2</i> вычисления по шагам</span>
        </div>`,
      note: "Фото позволяет проверить ход решения, а не только ответ.",
      actions: [
        ["photo", "Сфотографировать решение", "primary", "camera"],
        ["typed", "Ввести только ответ", "secondary", "keyboard"],
      ],
    },
    needs_revision: {
      kicker: "AI-проверка · шаг 1",
      title: "Сначала найди, сколько книг осталось",
      body: `
        <p class="feedback-evidence"><span>В твоём решении</span><strong>2/5</strong></p>
        <p class="lead-note">Ты взял <span class="math">2/5</span> от всех книг. Но в условии сказано
          <strong>«из оставшихся»</strong> — сначала вырази остаток после <span class="math">3/8</span>.</p>
        <p class="ai-boundary">Ответ пока не раскрыт. Исправь только первый шаг.</p>`,
      note: "Исправленная попытка останется в этой же задаче.",
      actions: [
        ["retry", "Исправить решение", "primary", "pencil"],
        ["hint", "Взять подсказку", "secondary", "spark"],
        ["tutor", "Спросить помощника", "secondary", "chat"],
      ],
      attempt: true,
    },
    hint_h2: {
      kicker: "Подсказка 2 из 4 · стратегия",
      title: "Какой шаг должен быть первым?",
      body: `
        <p class="socratic">Что нужно найти <strong>до того</strong>, как брать
          <span class="math">2/5</span>?</p>
        <div class="hint-scale" aria-label="Открыта вторая подсказка из четырёх">
          <span class="seen"></span><span class="active"></span><span></span><span></span>
        </div>
        <p class="support-note">Эта попытка теперь тренировочная. Для зачёта позже будет новая похожая задача.</p>`,
      note: "Вернись к своей записи — подсказка не содержит готового ответа.",
      actions: [
        ["return", "Вернуться к решению", "primary", "back"],
        ["next-hint", "Ещё одна подсказка", "secondary", "spark"],
        ["tutor", "Обсудить этот шаг", "secondary", "chat"],
      ],
      support: true,
    },
    tutor_open: {
      kicker: "Помощник · эта задача, шаг 1",
      title: "Разберём только место, где ты застрял",
      body: `
        <div class="tutor-turn">
          <span class="tutor-avatar" aria-hidden="true">AI</span>
          <p>Ты сразу взял <span class="math">2/5</span>. Как записать долю книг, которая осталась после
            приключений? Напиши только выражение — считать пока не нужно.</p>
        </div>
        <label class="tutor-field">
          <span>Твой ответ помощнику</span>
          <input type="text" inputmode="text" placeholder="Например: 1 − …" autocomplete="off" />
        </label>
        <p class="support-note">Помощник видит условие и твою попытку. Готовый ответ не показывается.</p>`,
      note: "Ответ в чате сохраняется рядом с этой задачей.",
      actions: [
        ["send", "Отправить помощнику", "primary", "send"],
        ["close", "Закрыть и продолжить самому", "secondary", "close"],
      ],
      close: true,
      attempt: true,
      support: true,
    },
    uncertain: {
      kicker: "Проверка не завершена",
      title: "Математический вердикт не вынесен",
      body: `
        <p class="lead-note">Нижняя часть вычислений размыта. Это <strong>не ошибка в решении</strong> — AI
          пока не может надёжно прочитать второй шаг.</p>
        <div class="saved-photo">
          <span class="photo-icon" aria-hidden="true">▧</span>
          <span><strong>IMG_4979.heic</strong><small>Фото сохранено · 1,2 МБ</small></span>
        </div>
        <p class="recovery-note">Пересними страницу сверху при ровном свете или введи нечитабельный фрагмент.</p>`,
      note: "Предыдущая попытка сохранена; начинать задачу заново не нужно.",
      actions: [
        ["rephoto", "Переснять фото", "primary", "camera"],
        ["typed", "Ввести нечитабельный фрагмент", "secondary", "keyboard"],
        ["retry-check", "Повторить проверку", "secondary", "refresh"],
      ],
      attempt: true,
    },
  };

  const stateId = Object.prototype.hasOwnProperty.call(states, requestedState)
    ? requestedState
    : "independent";
  const state = states[stateId];

  document.body.classList.add(`concept-${concept}`, `state-${stateId}`);
  document.body.dataset.concept = concept;
  document.body.dataset.state = stateId;
  document.querySelector("#concept-letter").textContent = concepts[concept].letter;
  document.querySelector("#concept-name").textContent = concepts[concept].name;
  document.querySelector("#context-kicker").textContent = state.kicker;
  document.querySelector("#context-title").textContent = state.title;
  document.querySelector("#context-body").innerHTML = state.body;
  document.querySelector("#response-note").textContent = state.note;

  const attempt = document.querySelector("#task-attempt");
  const paperPrompt = document.querySelector("#paper-prompt");
  attempt.hidden = !state.attempt;
  paperPrompt.hidden = Boolean(state.attempt);

  const closeButton = document.querySelector(".context-close");
  closeButton.hidden = !state.close;

  if (state.support) {
    document.querySelector(".task-mode").textContent = "С поддержкой";
    document.querySelector(".mode-pill span:last-child").textContent = "Тренировочная попытка";
    document.querySelector(".mode-pill").classList.add("supported");
  }

  const icon = (name) => {
    const paths = {
      camera: '<path d="M8 7.5 9.6 5h4.8L16 7.5h2.2A1.8 1.8 0 0 1 20 9.3v7.4a1.8 1.8 0 0 1-1.8 1.8H5.8A1.8 1.8 0 0 1 4 16.7V9.3a1.8 1.8 0 0 1 1.8-1.8H8Z"/><circle cx="12" cy="13" r="3.2"/>',
      keyboard: '<rect x="3.5" y="6" width="17" height="12" rx="2"/><path d="M7 10h.01M10.5 10h.01M14 10h.01M17.5 10h.01M7 13.5h.01M10.5 13.5h.01M14 13.5h.01M17.5 13.5h.01M8 16h8"/>',
      pencil: '<path d="m5 19 3.2-.7L18.5 8a1.8 1.8 0 0 0 0-2.5 1.8 1.8 0 0 0-2.5 0L5.7 15.8 5 19Z"/><path d="m14.8 6.7 2.5 2.5"/>',
      spark: '<path d="M12 3.5 13.4 8l4.6 1.4-4.6 1.4L12 15.3l-1.4-4.5L6 9.4 10.6 8 12 3.5Z"/><path d="m18 14 .7 2.2L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.8L18 14Z"/>',
      chat: '<path d="M5.5 17.5 4 20l3.5-1.2h9A3.5 3.5 0 0 0 20 15.3V8.7a3.5 3.5 0 0 0-3.5-3.5h-9A3.5 3.5 0 0 0 4 8.7v5.1a3.5 3.5 0 0 0 1.5 2.9v.8Z"/><path d="M8 10h8M8 14h5"/>',
      back: '<path d="m10 6-6 6 6 6M5 12h15"/>',
      send: '<path d="m4 5 16 7-16 7 2-7-2-7Z"/><path d="M6 12h14"/>',
      close: '<path d="m7 7 10 10M17 7 7 17"/>',
      refresh: '<path d="M19 8V4l-2 2a8 8 0 1 0 2 10M19 4h-4"/>',
    };
    return `<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.spark}</svg>`;
  };

  const actions = document.querySelector("#response-actions");
  state.actions.forEach(([id, label, kind, iconName]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `action action-${kind}`;
    button.dataset.action = id;
    if (kind === "primary") button.dataset.primary = "true";
    button.innerHTML = `${icon(iconName)}<span>${label}</span>`;
    button.addEventListener("click", () => {
      document.querySelector("#action-status").textContent = `Выбрано действие: ${label}`;
    });
    actions.appendChild(button);
  });

  closeButton.addEventListener("click", () => {
    document.querySelector("#action-status").textContent = "Помощник закрыт. Фокус возвращён к задаче.";
    document.querySelector("#task-title").focus({ preventScroll: true });
  });

  document.querySelector("#task-title").setAttribute("tabindex", "-1");
})();
