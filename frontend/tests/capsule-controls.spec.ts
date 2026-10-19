import { test, expect } from "@playwright/test";

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
