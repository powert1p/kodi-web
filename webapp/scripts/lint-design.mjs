#!/usr/bin/env node
// Гейт дизайн-системы v5 (DESIGN_SYSTEM.md §7): ловит нарушения запретов §2
// прямо в исходниках, без внешних зависимостей.
//
// Проверки:
//   (а) сырые hex-литералы (#fff, #FF8C00…)
//   (б) произвольные Tailwind-значения [#...] / [123px]
//   (в) классы «полушагов» (Tailwind 1.5/2.5/3.5 = 6/10/14px — запрещены сеткой в 4px)
//   (г) запрещённые шрифты (Inter/Roboto/Arial) в font-family
//
// Исключения: theme/tokens.css и theme/fonts.css — единственный источник токенов,
// им разрешён сырой hex/px по определению.

import { globSync } from 'node:fs'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC_ROOT = path.resolve(__dirname, '..', 'src')

// Пути исключений — относительно src/, POSIX-стиль (без учёта платформы Windows).
const EXCLUDED = new Set(['theme/tokens.css', 'theme/fonts.css'])

const RULES = [
  {
    name: 'сырой hex-литерал вне tokens.css',
    re: /#[0-9a-fA-F]{3,8}\b/g,
  },
  {
    name: 'произвольное Tailwind-значение (arbitrary value)',
    re: /\[(#|[0-9]+px)/g,
  },
  {
    name: 'класс-полушаг (Tailwind 1.5/2.5/3.5 — запрещены сеткой 4px)',
    re: /\b(p|m|gap|px|py|mx|my|mt|mb|ml|mr|pt|pb|pl|pr|space-[xy])-(1\.5|2\.5|3\.5)\b/g,
  },
  {
    name: 'запрещённый шрифт (Inter/Roboto/Arial)',
    re: /font-family[^;]*\b(Inter|Roboto|Arial)\b/g,
  },
]

/** Возвращает относительный (от src/) POSIX-путь для файла. */
function toRelPosix(absPath) {
  return path.relative(SRC_ROOT, absPath).split(path.sep).join('/')
}

function main() {
  const files = globSync('**/*.{ts,tsx,css}', { cwd: SRC_ROOT })
    .map((f) => path.join(SRC_ROOT, f))
    .filter((abs) => !EXCLUDED.has(toRelPosix(abs)))

  /** @type {{ file: string, line: number, rule: string, match: string }[]} */
  const violations = []

  for (const file of files) {
    const rel = toRelPosix(file)
    const content = readFileSync(file, 'utf-8')
    const lines = content.split('\n')

    lines.forEach((lineText, idx) => {
      for (const rule of RULES) {
        // Свежий regex на каждую строку — исключаем накопление lastIndex между итерациями.
        const re = new RegExp(rule.re.source, rule.re.flags)
        const match = re.exec(lineText)
        if (match) {
          violations.push({
            file: rel,
            line: idx + 1,
            rule: rule.name,
            match: match[0],
          })
        }
      }
    })
  }

  if (violations.length > 0) {
    console.error(`lint:design — найдено нарушений: ${violations.length}\n`)
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line} — ${v.rule} (\`${v.match}\`)`)
    }
    process.exit(1)
  }

  console.log(`lint:design — чисто (${files.length} файлов проверено).`)
}

main()
