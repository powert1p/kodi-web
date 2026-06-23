import katex from "katex";

// Рендер смешанного текста: сегменты $$...$$ (блок) и $...$ (инлайн) → KaTeX,
// остальное — как обычный текст. Возвращаем массив HTML-строк-частей,
// которые компонент собирает через dangerouslySetInnerHTML по сегментам.

export interface MathSegment {
  type: "text" | "inline" | "block";
  value: string; // для math — уже отрендеренный HTML; для text — сырой текст
}

const escapeHtml = (s: string): string =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

// Разбиваем строку на сегменты по $$...$$ и $...$
export function parseMath(input: string): MathSegment[] {
  const segments: MathSegment[] = [];
  // Сначала ловим блочные $$...$$, затем инлайн $...$
  const regex = /\$\$([^$]+)\$\$|\$([^$]+)\$/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(input)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: input.slice(lastIndex, match.index) });
    }
    const isBlock = match[1] !== undefined;
    const tex = isBlock ? match[1] : match[2];
    try {
      const html = katex.renderToString(tex, {
        displayMode: isBlock,
        throwOnError: false,
        output: "html",
      });
      segments.push({ type: isBlock ? "block" : "inline", value: html });
    } catch {
      // Падать нельзя — показываем исходный tex как текст
      segments.push({ type: "text", value: tex });
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < input.length) {
    segments.push({ type: "text", value: input.slice(lastIndex) });
  }
  return segments;
}

// Превью того, что ученик печатает: ASCII-дробь 2/3 → KaTeX \frac{2}{3}
export function asciiToTex(raw: string): string {
  const t = raw.trim();
  if (!t) return "";
  // Простая дробь a/b
  const frac = t.match(/^(-?\d+)\s*\/\s*(\d+)$/);
  if (frac) {
    return katex.renderToString(`\\frac{${frac[1]}}{${frac[2]}}`, {
      throwOnError: false,
      output: "html",
    });
  }
  // Целое число — просто крупно
  if (/^-?\d+$/.test(t)) {
    return katex.renderToString(t, { throwOnError: false, output: "html" });
  }
  // Иначе показываем как есть (экранированный)
  return escapeHtml(t);
}

// Обернуть ASCII-ответ (2/5, 15) в инлайн-KaTeX-строку для MathText.
export function answerToTex(raw: string): string {
  const t = raw.trim();
  const frac = t.match(/^(-?\d+)\s*\/\s*(\d+)$/);
  if (frac) return `$\\frac{${frac[1]}}{${frac[2]}}$`;
  if (/^-?\d+$/.test(t)) return `$${t}$`;
  return t;
}

// Нормализация ответа для сравнения: дроби сокращаем к каноничному виду,
// убираем пробелы, унифицируем разделитель.
function gcd(a: number, b: number): number {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b) [a, b] = [b, a % b];
  return a || 1;
}

export function normalizeAnswer(raw: string): string {
  const t = raw.trim().replace(/\s+/g, "").replace(",", ".");
  const frac = t.match(/^(-?\d+)\/(\d+)$/);
  if (frac) {
    const num = parseInt(frac[1], 10);
    const den = parseInt(frac[2], 10);
    if (den === 0) return t;
    const g = gcd(num, den);
    const sign = den < 0 ? -1 : 1;
    return `${(num / g) * sign}/${Math.abs(den / g)}`;
  }
  return t;
}

// Сравнение ответа с эталоном через нормализацию
export function answersMatch(input: string, expected: string): boolean {
  if (!input.trim()) return false;
  return normalizeAnswer(input) === normalizeAnswer(expected);
}
