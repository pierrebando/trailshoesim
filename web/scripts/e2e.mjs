// End-to-end check of the BUILT app in a headless browser, served under the GitHub
// Pages sub-path, plus the screenshots used by the README.
//   npm run e2e          (builds first, then runs this script)
//
// Each check prints PASS or FAIL; the script exits with an error if one fails.

import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const IMG = join(here, "..", "..", "docs", "img");
const PORT = 4174;
const BASE = `http://localhost:${PORT}/trailshoesim/`;
const PROFILE = "?kg=72&km=25&fs=midfoot&t=technical_rocky%2Cmuddy_soft";
const COMPARE = "?cmp=saucony-peregrine-15,brooks-cascadia-20,nnormal-kjerag-2";

const results = [];
function check(name, ok, detail = "") {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
}

async function waitForServer() {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(BASE)).ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error("preview server did not start");
}

const server = spawn("npx", ["vite", "preview", "--base", "/trailshoesim/", "--port", String(PORT), "--strictPort"], {
  cwd: join(here, ".."),
  stdio: "ignore",
});

try {
  await waitForServer();
  mkdirSync(IMG, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: "light" });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(String(e)));

  // Results page, profile restored from the URL
  await page.goto(`${BASE}${PROFILE}#/`);
  await page.locator(".card").first().waitFor();
  check("results render", (await page.locator(".card").count()) > 0);
  check("URL restores the weight", (await page.getByLabel(/Body weight/).inputValue()) === "72");
  check("URL restores the terrains", await page.getByRole("checkbox", { name: /Technical \/ rocky/ }).isChecked());
  check("URL restores the foot strike", await page.getByRole("radio", { name: "Midfoot" }).isChecked());
  const footer = await page.locator("footer").innerText();
  check("footer shows build date and price dates", /Data built on .+ · prices checked/.test(footer), footer.split("\n")[0]);
  await page.screenshot({ path: join(IMG, "results.png") });
  await page.screenshot({ path: join(IMG, "screenshot.png") });

  // The form works: moving the weight slider with the keyboard updates URL and results
  // Top 5 as "name score" lines: weights change the scores even when the order holds.
  const top5 = async () =>
    (await page.locator(".card").evaluateAll((cards) => cards.slice(0, 5).map((c) => c.querySelector("h3").textContent + " " + c.querySelector(".score-value").textContent))).join(" | ");
  const before = await top5();
  const slider = page.getByLabel(/Body weight/);
  await slider.focus();
  for (let i = 0; i < 25; i++) await page.keyboard.press("ArrowRight");
  const saved = await page
    .waitForFunction(() => new URL(window.location.href).searchParams.get("kg") === "97", null, { timeout: 3000 })
    .then(() => true, () => false);
  check("weight slider works with the keyboard and is saved in the URL", saved, "72 -> 97 kg");
  await page.getByRole("checkbox", { name: /Road to trail/ }).check();
  const after = await top5();
  check("changing the profile updates the ranking", after !== before, `top 1 now ${after.split(" | ")[0]}`);
  await page.getByLabel("Max price (€)").fill("1");
  check("filters that remove everything show the plain message", await page.getByText("No shoe matches your filters.").isVisible());

  // Keyboard navigation through the profile form
  await page.goto(`${BASE}#/`);
  await page.locator(".card").first().waitFor();
  await page.locator("body").press("Tab");
  const reached = new Set();
  let visibleFocus = true;
  for (let i = 0; i < 40; i++) {
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      const style = el ? getComputedStyle(el) : null;
      const label = el?.labels?.[0]?.innerText ?? el?.getAttribute("aria-label") ?? el?.textContent ?? "";
      return { tag: el?.tagName, type: el?.getAttribute("type"), label: label.trim().slice(0, 30), outline: style?.outlineStyle };
    });
    if (["INPUT", "SELECT"].includes(info.tag)) {
      reached.add(`${info.tag.toLowerCase()}:${info.type ?? ""}:${info.label}`);
      if (info.outline === "none") visibleFocus = false;
    }
    await page.keyboard.press("Tab");
  }
  const expected = ["Gender", "Body weight", "Foot width", "Typical distance", "Road to trail"];
  const missing = expected.filter((e) => ![...reached].some((r) => r.includes(e)));
  check("keyboard reaches every profile control", missing.length === 0, missing.length ? `missing ${missing}` : `${reached.size} controls`);
  check("keyboard focus is visible", visibleFocus);

  // Model page, comparator, how it works
  await page.goto(`${BASE}${PROFILE}#/shoe/saucony-peregrine-15`);
  await page.getByRole("heading", { name: "Saucony Peregrine 15" }).waitFor();
  check("model page renders with radar and sources", (await page.locator(".radar svg").count()) === 1 && (await page.locator(".specs tr").count()) > 10);
  await page.screenshot({ path: join(IMG, "model.png"), fullPage: false });

  await page.goto(`${BASE}${COMPARE}#/compare`);
  await page.locator("table.compare").waitFor();
  check("comparator renders 3 shoes", (await page.locator("table.compare thead th[scope=col]").count()) === 3);
  await page.screenshot({ path: join(IMG, "comparator.png") });

  await page.goto(`${BASE}#/similar/saucony-peregrine-15`);
  await page.locator(".cards .card").first().waitFor();
  check("'I like this model' lists similar shoes", (await page.locator(".cards .card").count()) > 0);

  await page.goto(`${BASE}#/how`);
  check("how-it-works page renders", await page.getByRole("heading", { name: "How it works" }).isVisible());

  // Mobile viewport
  const mobile = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, colorScheme: "light" });
  const phone = await mobile.newPage();
  phone.on("pageerror", (e) => consoleErrors.push(String(e)));
  for (const [name, url] of [["results", `${BASE}${PROFILE}#/`], ["model", `${BASE}#/shoe/saucony-peregrine-15`], ["comparator", `${BASE}${COMPARE}#/compare`]]) {
    await phone.goto(url);
    await phone.locator("main h2").first().waitFor();
    const { scroll, width } = await phone.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
    check(`mobile 375 px: no horizontal scroll on ${name}`, scroll <= width, `${scroll} <= ${width}`);
  }
  await phone.goto(`${BASE}${PROFILE}#/`);
  await phone.locator(".card").first().waitFor();
  check("mobile: 'jump to the results' link is visible", await phone.getByText(/Jump to the results/).isVisible());
  await phone.getByText(/Jump to the results/).click();
  await phone.waitForTimeout(300);
  await phone.screenshot({ path: join(IMG, "mobile-results.png") });

  check("no console errors", consoleErrors.length === 0, consoleErrors.slice(0, 3).join(" | "));
  await browser.close();
} finally {
  server.kill();
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed; screenshots in docs/img/`);
process.exit(failed.length ? 1 : 0);
