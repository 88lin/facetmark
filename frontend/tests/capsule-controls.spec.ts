import { test, expect } from "@playwright/test";

test("pointer activation opens one reader and returns focus from its inactive collection", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 860 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/app");
  const preview = page.locator(".bookmark-preview").first();
  await preview.evaluate(element => {
    element.dataset.clickCount = "0";
    element.addEventListener("click", () => {
      element.dataset.clickCount = String(Number(element.dataset.clickCount) + 1);
    });
  });
  await preview.hover();
  await page.mouse.down();
  await expect(preview).toHaveAttribute("data-pressed", "true");
  await page.mouse.up();
  await expect(preview).toHaveAttribute("data-click-count", "1");
  await expect.poll(() => preview.evaluate(element => !!element.closest('[inert], [aria-hidden="true"]'))).toBe(true);
  const reader = page.getByRole("dialog", { name: "书签预览" });
  await expect(reader).toHaveCount(1);
  await expect(reader).toBeVisible();
  await expect.poll(() => reader.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await expect(page.locator(".interaction-paint, .interaction-ink")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(reader).toHaveCount(0);
  await expect(preview).toBeFocused();
});

test("shared controls retain keyboard press, native click and preview focus", async ({ page }) => {
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

test("shared controls preserve disabled state and submit a page jump exactly once", async ({ page }) => {
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
  await expect(previous).toBeEnabled();
  await expect(page.getByRole("spinbutton", { name: "跳转页码" })).toHaveValue("2");
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
