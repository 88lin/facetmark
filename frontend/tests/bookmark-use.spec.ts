import { expect, test } from "@playwright/test";

test("titles use native external links and summaries are readable without preview", async ({ page, context }) => {
  await context.route("https://**/*", route => route.fulfill({ contentType: "text/html", body: "<h1>Synthetic original page</h1>" }));
  await page.goto("/app");
  const row = page.locator(".result-row").first();
  const title = row.locator("a.result-title");
  await expect(title).toHaveAttribute("target", "_blank");
  const url = await title.getAttribute("href");
  expect(url).toMatch(/^https?:\/\//);
  await expect(row.locator(".result-summary")).toBeVisible();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  const opened = context.waitForEvent("page");
  await title.click();
  const original = await opened;
  await expect(original).toHaveURL(url!);
  await original.close();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  const middle = context.waitForEvent("page");
  await title.click({ button: "middle" });
  const other = await middle;
  await expect(other).toHaveURL(url!);
  await other.close();
  await page.getByRole("button", { name: "列表视图", exact: true }).first().click();
  await expect(row.locator(".result-summary")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(row.locator(".result-summary")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "screenshots/bookmark-summaries-mobile.png", animations: "disabled" });
});

test("local agent can be detected, tested and saved without API fields", async ({ page }) => {
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: [
    { id: "codex", name: "Codex", installed: true }, { id: "claude", name: "Claude Code", installed: false },
  ] } }));
  let tested: Record<string, unknown> = {};
  let saved: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "codex/default", ms: 100 } } });
  });
  await page.route("**/admin/settings", async route => {
    if (route.request().method() !== "PUT") return route.continue();
    saved = route.request().postDataJSON().values;
    return route.fulfill({ json: { settings: [] } });
  });
  await page.goto("/app#settings");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  const panel = page.locator(".model-panel").first();
  await expect(panel.locator(".agent-detection")).toContainText("Codex");
  await expect(panel.locator('input[name="chat_api_key"]')).toHaveCount(0);
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect.poll(() => saved.chat_backend).toBe("agent");
  expect(tested.chat_backend).toBe("agent");
  expect(tested.channel).toBe("chat");
  expect(tested.chat_api_key).toBeUndefined();
  await page.screenshot({ path: "screenshots/local-agent-settings.png", animations: "disabled" });
});
