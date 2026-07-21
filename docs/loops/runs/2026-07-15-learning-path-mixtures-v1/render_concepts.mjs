import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const runDir = path.dirname(new URL(import.meta.url).pathname);
const outputArg = process.argv.indexOf("--output");
const output = path.resolve(
  outputArg >= 0 ? process.argv[outputArg + 1] : path.join(runDir, "round2-states"),
);
await mkdir(output, { recursive: true });

const conceptUrl = pathToFileURL(path.join(runDir, "concept.html")).href;
const screensByConcept = {
  a: ["today", "lesson", "wrong", "retry", "resume", "result"],
  b: ["today", "lesson"],
  c: ["today", "lesson"],
};
const viewports = {
  mobile: { width: 375, height: 844 },
  desktop: { width: 1280, height: 900 },
};

const browser = await chromium.launch({ headless: true });
try {
  for (const [concept, screens] of Object.entries(screensByConcept)) {
    for (const screen of screens) {
      for (const [name, viewport] of Object.entries(viewports)) {
        const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
        const errors = [];
        page.on("console", (message) => {
          if (message.type() === "error") errors.push(message.text());
        });
        page.on("pageerror", (error) => errors.push(error.message));
        await page.goto(`${conceptUrl}?concept=${concept}&screen=${screen}`, {
          waitUntil: "networkidle",
        });
        const state = await page.evaluate(() => ({
          empty: !document.querySelector("#app")?.textContent?.trim(),
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        }));
        if (state.empty) errors.push("empty concept render");
        if (state.overflow) errors.push("horizontal overflow");
        if (errors.length > 0) {
          throw new Error(`${concept}/${screen}/${name}: ${errors.join("; ")}`);
        }
        await page.screenshot({
          path: path.join(output, `${concept}-${screen}-${name}.png`),
          fullPage: false,
        });
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
}
