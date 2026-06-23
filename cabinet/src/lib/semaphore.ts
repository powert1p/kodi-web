import type { Mastery } from "../mock/srez";

// Семафор освоения: цвет + ярлык + мягкий тинт-подложка для статуса задачи.
// Тон — поддерживающий, без наказания.
export interface SemaphoreStyle {
  label: string; // дружелюбный ярлык состояния
  dot: string; // tailwind-класс цвета точки
  wash: string; // tailwind-класс мягкой подложки
  ring: string; // tailwind-класс рамки/кольца
  text: string; // tailwind-класс цвета текста-ярлыка
}

export const semaphore: Record<Mastery, SemaphoreStyle> = {
  revisit: {
    label: "Вернёмся вместе",
    dot: "bg-revisit",
    wash: "bg-paper",
    ring: "ring-line",
    text: "text-ink-soft",
  },
  almost: {
    label: "Почти получилось",
    dot: "bg-almost",
    wash: "bg-almost-wash",
    ring: "ring-almost/30",
    text: "text-almost",
  },
  got: {
    label: "Разобрано",
    dot: "bg-got",
    wash: "bg-got-wash",
    ring: "ring-got/30",
    text: "text-got",
  },
};
