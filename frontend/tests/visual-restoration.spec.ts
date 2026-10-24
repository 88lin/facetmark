import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1"
    ? route.continue() : route.abort());
  await mkdir("screenshots", { recursive: true });
});

for (const { width, theme } of [{ width: 1440, theme: "light" }, { width: 390, theme: "dark" }]) {
  test(`floating reader controls remain reachable and keep the final text clear at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(value => {
      localStorage.setItem("fm-language", "zh");
      localStorage.setItem("fm-theme", value);
    }, theme);
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await page.locator(".bookmark-preview").first().click();
    await expect(page.locator(".body-text")).toBeVisible();
    const surface = page.locator(".reading-position-surface");
    const picker = page.getByRole("combobox", { name: "跳转到章节" });
    await expect(surface).toHaveCSS("transform", "none");
    await expect(surface).toBeInViewport({ ratio: 1 });
    // Opening preview intentionally reflows the grid into an index and reveals
    // the selected row. Chapter navigation must preserve that established view.
    const listPosition = await page.locator(".result-list").evaluate(el => el.scrollTop);
    expect(await surface.evaluate(el => getComputedStyle(el).backdropFilter)).not.toBe("none");
    await picker.focus();
    await expect(picker).toBeFocused();
    await picker.selectOption({ label: "保持思考的上下文" });
    await expect.poll(() => page.locator(".preview-scroll").evaluate(el => el.scrollTop)).toBeGreaterThan(0);
    await expect(page.locator(".section-picker-copy")).toContainText("保持思考的上下文");
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
    expect(await page.locator(".result-list").evaluate(el => el.scrollTop)).toBe(listPosition);

    await page.locator(".preview-scroll").evaluate(el => {
      el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
    });
    await expect(page.locator(".reading-percent")).toHaveText("100%");
    const lastText = await page.locator(".body-text > p").last().boundingBox();
    const control = await surface.boundingBox();
    expect(lastText!.y + lastText!.height).toBeLessThanOrEqual(control!.y);
    expect(control!.x).toBeGreaterThanOrEqual(0);
    expect(control!.x + control!.width).toBeLessThanOrEqual(width);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);

    await page.getByRole("button", { name: "回到顶部", exact: true }).press("Enter");
    await expect.poll(() => page.locator(".preview-scroll").evaluate(el => el.scrollTop)).toBe(0);
    await page.screenshot({ path: `screenshots/restored-glass-${theme}-${width}.png`, animations: "disabled" });
  });
}

test("paper plane follows rapid chapter changes and settles immediately with reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.goto("/app");
  await page.locator(".bookmark-preview").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.locator(".focus-reading").click();
  await page.evaluate(() => document.fonts.ready);
  const outline = page.getByRole("navigation", { name: "文章目录", exact: true });
  const plane = outline.locator(".reader-outline-plane");
  await expect(plane).toBeVisible();
  const alignment = () => outline.evaluate(el => {
    const marker = el.querySelector(".reader-outline-plane")!.getBoundingClientRect();
    const current = el.querySelector('[aria-current="location"]')!.getBoundingClientRect();
    return Math.abs(marker.y + marker.height / 2 - current.y - current.height / 2);
  });
  const first = outline.getByRole("button").first();
  const last = outline.getByRole("button").last();
  await last.press("Enter");
  await first.press("Enter");
  await last.press("Enter");
  await expect(last).toHaveAttribute("aria-current", "location");
  await expect.poll(alignment).toBeLessThan(1.5);
  await page.setViewportSize({ width: 1180, height: 860 });
  await expect.poll(alignment).toBeLessThan(1.5);
  await expect(page.locator(".section-picker-copy")).toContainText((await last.textContent())!);
  await expect(page.locator(`#${await last.getAttribute("aria-controls")}`)).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: "screenshots/restored-paper-plane.png", animations: "disabled" });

  await page.emulateMedia({ reducedMotion: "reduce" });
  await first.press("Enter");
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  expect(await alignment()).toBeLessThan(1.5);
  await expect(page.locator(".section-picker-copy")).toContainText((await first.textContent())!);
  await expect(plane.locator("span")).toHaveCSS("transform", "none");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await expect(page.locator(".result-row").first()).toHaveCSS("animation-name", "none");
  await expect(page.locator(".bookmark-preview").first()).toBeFocused();
});
