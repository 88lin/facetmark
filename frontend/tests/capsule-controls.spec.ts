import { test, expect } from "@playwright/test";

test("press ink is discarded when the reader makes its originating surface inactive", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 860 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/app");
  // Extend the paint lifetime so waiting for animationend cannot mask leakage.
  await page.addStyleTag({ content: ".interaction-paint .interaction-ink { animation-duration: 10s; }" });
  const preview = page.locator(".bookmark-preview").first();
  await preview.hover();
  await page.mouse.down();
  await expect(page.locator(".interaction-ink")).toHaveCount(1);
  await page.mouse.up();
  await expect.poll(() => preview.evaluate(element => !!element.closest('[inert], [aria-hidden="true"]'))).toBe(true);
  const remaining = await page.evaluate(async () => {
    for (let frame = 0; frame < 3; frame++) await new Promise(requestAnimationFrame);
    return document.querySelectorAll(".interaction-ink").length;
  });
  expect(remaining).toBe(0);
  await expect(page.getByRole("dialog", { name: "书签预览" })).toBeVisible();
});

test("HeroUI capsules retain keyboard press, native click and preview focus", async ({ page }) => {
  await page.goto("/app");
  const tasks = page.locator(".app-header").getByRole("button", { name: "任务", exact: true });
  await expect(tasks).toHaveClass(/\bbutton\b/);
  await tasks.evaluate(element => {
    element.dataset.clickCount = "0";
    element.addEventListener("click", () => {
      element.dataset.clickCount = String(Number(element.dataset.clickCount) + 1);
    });
  });
  await tasks.focus();
  await page.keyboard.down("Space");
  await expect(tasks).toHaveAttribute("data-pressed", "true");
  await page.keyboard.up("Space");
  await expect(tasks).toHaveAttribute("aria-pressed", "true");
  await expect(tasks).toHaveAttribute("data-click-count", "1");
  await page.keyboard.press("Enter");
  await expect(tasks).toHaveAttribute("data-click-count", "2");
  await page.locator(".app-header").getByRole("button", { name: "全部书签", exact: true }).click();
  const tags = page.locator(".collection-sidebar .facet-types").getByRole("button", { name: "标签", exact: true });
  await expect(tags).toHaveAttribute("type", "button");
  await tags.focus();
  await page.keyboard.down("Space");
  await expect(tags).toHaveAttribute("data-pressed", "true");
  await page.keyboard.up("Space");
  await expect(tags).toHaveAttribute("aria-pressed", "true");
  const folders = page.locator(".collection-sidebar .facet-types").getByRole("button", { name: "文件夹", exact: true });
  await folders.press("Enter");
  await expect(folders).toHaveAttribute("aria-pressed", "true");
  const preview = page.locator(".bookmark-preview").first();
  await preview.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".body-text")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(preview).toBeFocused();
});

test("capsules preserve disabled controls, submit exactly once and stay rounded", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const previous = page.getByRole("button", { name: "上一页", exact: true });
  await expect(previous).toBeDisabled();
  let requests = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname.endsWith("/bookmarks") && url.searchParams.get("offset") === "30") requests += 1;
  });
  await page.getByRole("spinbutton", { name: "跳转页码" }).fill("2");
  await page.getByRole("button", { name: "跳转", exact: true }).press("Enter");
  await expect(page.locator(".results-footer")).toContainText("31–60");
  expect(requests).toBe(1);
  const shapes = await page.locator(".app-header button, .library-tools button, .collection-status button, .bookmark-preview").evaluateAll(elements =>
    elements.filter(element => element.getBoundingClientRect().width > 0).map(element => {
      const box = element.getBoundingClientRect();
      return { radius: parseFloat(getComputedStyle(element).borderTopLeftRadius), height: box.height };
    }));
  expect(shapes.length).toBeGreaterThan(8);
  for (const shape of shapes) expect(shape.radius).toBeGreaterThanOrEqual(shape.height / 2 - 1);
});

test("portal buttons honor live reduced motion and retain keyboard cancellation", async ({ page }) => {
  await page.goto("/app");
  await page.emulateMedia({ reducedMotion: "reduce" });
  const trigger = page.getByRole("button", { name: "新增收藏", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
  const cancel = dialog.getByRole("button", { name: "取消", exact: true });
  await cancel.focus();
  await page.keyboard.down("Space");
  await expect(cancel).toHaveAttribute("data-pressed", "true");
  await expect(cancel).toHaveCSS("transform", "none");
  expect(await cancel.evaluate(el => parseFloat(getComputedStyle(el).borderTopLeftRadius))).toBeGreaterThan(100);
  await page.keyboard.up("Space");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test("theme reveal remains available with HeroUI base styles", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator("html")).toHaveCSS("view-transition-name", "root");
  const revealed = await page.evaluate(async () => {
    const seen: string[] = [];
    const animate = Element.prototype.animate;
    Element.prototype.animate = function (frames, options) {
      if (typeof options === "object" && options.pseudoElement) seen.push(options.pseudoElement);
      return animate.call(this, frames, options);
    };
    try {
      document.querySelector<HTMLButtonElement>('.app-header button[aria-label="切换主题"]')!.click();
      const deadline = performance.now() + 2000;
      while (!seen.length && performance.now() < deadline) await new Promise(requestAnimationFrame);
      return seen;
    } finally { Element.prototype.animate = animate; }
  });
  expect(revealed).toContain("::view-transition-new(root)");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
