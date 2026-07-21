# Benchmark contract

## Objective

Дать владельцу продукта пять визуально и пространственно разных, технически жизнеспособных
направлений AiPlus для осознанного выбора до изменения production React.

## Scope

- Один и тот же drill-сценарий на 375×844 и 1280×900.
- Настоящие logo/mascot references.
- Visual hierarchy, responsive composition, controls and first-viewport fit.

## Non-goals

- Не выбирать стиль вместо владельца.
- Не внедрять направление в React PWA.
- Не проектировать все состояния и страницы до выбора.
- Не создавать новый логотип или маскота.

## Immutable inputs

```text
09682771d9783f6ec1311432034f4907d0c512d56dd7f7a732a573f4ee2c0f15  BRIEF.md
74421e289f46393590f1b8747b17c5d7ab294f9825b35b369ccfd3e976eb3aa0  assets/aiplus-logo-reference.jpg
0b5c5ddecba16b0aac67b140e2ee40f00c6eaaa961246e36b455e80c26be4787  assets/aiplus-mascot-reference.jpg
```

## Frozen rubric

```text
ba591ee8a360187034c2e334f301697e7172e7505041336659e1686080e9533c  RUBRIC.md
```

## Mechanical gate

```bash
uv run --with playwright python \
  docs/loops/runs/2026-07-14-webapp-v9-style-selection/render_concepts.py
```

Gate: 10/10 viewports without console errors, horizontal overflow or first-screen scrolling;
official reference images and fonts loaded; all visible controls at least 44 px high; primary CTA
inside the first viewport.

## READY threshold

- Mechanical gate green.
- Ни у одного варианта нет hard fail из `RUBRIC.md`.
- Median двух independent reviewer scores для каждого варианта ≥6.0/10.
- Минимум три варианта имеют median ≥7.0/10.

## Terminal condition

Максимум два maker-checker rounds. После READY — показать пять вариантов владельцу и остановить
production implementation до явного выбора номера или смеси двух направлений.

