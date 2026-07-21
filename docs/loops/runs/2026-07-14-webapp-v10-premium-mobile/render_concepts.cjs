/* Рендерит три clean-slate spatial systems на одном product slice. */

const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { chromium } = require('playwright')

const root = __dirname
const source = path.join(root, 'prototype.html')
const out = path.join(root, 'renders', 'concepts')
const executablePath = path.join(
  process.env.HOME,
  'Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
)
const concepts = ['atelier', 'equality', 'cut']
const screens = ['hub', 'drill', 'feedback']
const viewports = [
  { width: 375, height: 844 },
  { width: 1280, height: 900 },
]

async function main() {
  fs.mkdirSync(out, { recursive: true })
  const report = {}
  const failures = []
  const browser = await chromium.launch({ headless: true, executablePath })

  for (const concept of concepts) {
    for (const screen of screens) {
      for (const viewport of viewports) {
        const context = await browser.newContext({
          viewport,
          colorScheme: 'light',
          reducedMotion: 'reduce',
          deviceScaleFactor: 1,
        })
        const page = await context.newPage()
        const errors = []
        page.on('pageerror', (error) => errors.push('pageerror: ' + error))
        page.on('console', (message) => {
          if (message.type() === 'error') errors.push('console: ' + message.text())
        })

        const url = new URL(pathToFileURL(source))
        url.searchParams.set('concept', concept)
        url.searchParams.set('screen', screen)
        await page.goto(url.href, { waitUntil: 'load' })
        await page.evaluate(() => document.fonts.ready)
        await page.waitForTimeout(160)
        const details = await page.evaluate(() => {
          const visible = (element) => {
            const style = getComputedStyle(element)
            const rect = element.getBoundingClientRect()
            return (
              style.display !== 'none' &&
              style.visibility !== 'hidden' &&
              rect.width > 0 &&
              rect.height > 0
            )
          }
          const controls = [...document.querySelectorAll('button,a,input')].filter(visible)
          const images = [...document.querySelectorAll('img')].filter(visible)
          const primary = document.querySelector('.primary, .thread-action, .object-action')
          const primaryRect = primary?.getBoundingClientRect()
          const inputs = [...document.querySelectorAll('input')].filter(visible)
          const headings = [...document.querySelectorAll('h1,h2')].filter(visible)
          return {
            viewport: { width: innerWidth, height: innerHeight },
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight,
            overflowX: document.documentElement.scrollWidth > innerWidth + 1,
            fonts: document.fonts.status,
            imagesLoaded: images.every((image) => image.complete && image.naturalWidth > 0),
            minControlHeight: controls.length
              ? Math.min(...controls.map((element) => element.getBoundingClientRect().height))
              : null,
            minInputFont: inputs.length
              ? Math.min(...inputs.map((element) => Number.parseFloat(getComputedStyle(element).fontSize)))
              : null,
            primaryVisible: primaryRect
              ? primaryRect.top >= -1 && primaryRect.bottom <= innerHeight + 1
              : null,
            largestHeading: headings.length
              ? Math.max(
                  ...headings.map((element) => Number.parseFloat(getComputedStyle(element).fontSize)),
                )
              : null,
          }
        })

        const key = concept + '-' + screen + '-' + viewport.width
        report[key] = { details, errors }
        await page.screenshot({ path: path.join(out, key + '.png'), fullPage: false })

        if (errors.length) failures.push(key + ': console=' + errors.join('; '))
        if (details.overflowX) failures.push(key + ': horizontal overflow')
        if (!details.imagesLoaded) failures.push(key + ': image failed to load')
        if (details.fonts !== 'loaded') failures.push(key + ': fonts=' + details.fonts)
        if (details.minControlHeight !== null && details.minControlHeight < 44) {
          failures.push(key + ': min control height=' + details.minControlHeight)
        }
        if (details.minInputFont !== null && details.minInputFont < 16) {
          failures.push(key + ': input font=' + details.minInputFont)
        }
        if (details.primaryVisible === false) {
          failures.push(key + ': primary action outside first viewport')
        }
        await context.close()
      }
    }
  }

  await browser.close()
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 2))
  if (failures.length) {
    throw new Error('concept render failed:\n- ' + failures.join('\n- '))
  }
  process.stdout.write(
    'concept render passed: ' + Object.keys(report).length + ' screenshots, output=' + out + '\n',
  )
}

main().catch((error) => {
  process.stderr.write(String(error.stack || error) + '\n')
  process.exitCode = 1
})
