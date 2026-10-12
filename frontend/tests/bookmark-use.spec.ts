import { expect, test } from "@playwright/test";

test("titles use native external links and summaries are readable without preview", async ({ page, context }) => {
  await context.route("https://**/*", route => route.fulfill({ contentType: "text/html", body: "<h1>Synthetic original page</h1>" }));
  await page.route("**/bookmarks?**", async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.items[0].summary = "直接浏览书签摘要，保留上下文，快速决定是否打开原网页。".repeat(12);
    await route.fulfill({ response, json: data });
  });
  await page.goto("/app");
  const row = page.locator(".result-row").first();
  const title = row.locator("a.result-title");
  await expect(title).toHaveAttribute("target", "_blank");
  const url = await title.getAttribute("href");
  expect(url).toMatch(/^https?:\/\//);
  await expect(row.locator(".result-summary")).toBeVisible();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  await row.getByRole("button", { name: "展开全文", exact: true }).click();
  expect(await row.locator(".result-summary").evaluate(el => el.scrollHeight <= el.clientHeight + 1)).toBe(true);
  await row.getByRole("button", { name: "收起", exact: true }).click();
  await page.screenshot({ path: "screenshots/bookmark-summaries-desktop.png", animations: "disabled" });
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
  await page.screenshot({ path: "screenshots/local-agent-settings.png", animations: "disabled" });
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect.poll(() => saved.chat_backend).toBe("agent");
  expect(tested.chat_backend).toBe("agent");
  expect(tested.channel).toBe("chat");
  expect(tested.chat_api_key).toBeUndefined();
});

test("display and batch-summary options expose the current collection scope", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const options = page.locator(".collection-options-menu");
  await options.locator("summary").click();
  await options.getByRole("button", { name: "原文摘录", exact: true }).click();
  await expect(page.locator(".summary-basis").first()).toHaveText("正文摘录");
  await options.getByRole("button", { name: "摘要", exact: true }).click();
  await expect(page.locator(".summary-basis").first()).toHaveText("AI 摘要");
  await page.screenshot({ path: "screenshots/collection-options-desktop.png", animations: "disabled" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(options.getByRole("button", { name: "批量生成摘要", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: "screenshots/collection-options-mobile.png", animations: "disabled" });
  await options.getByRole("combobox", { name: "摘要处理范围", exact: true }).selectOption("failed");
  const request = page.waitForRequest(r => r.url().includes("/admin/jobs/preview"));
  await options.getByRole("button", { name: "批量生成摘要", exact: true }).click();
  const payload = (await request).postDataJSON();
  expect(payload.scope.status).toBe("failed");
  expect(payload.bookmark_ids).toBeUndefined();
  const dialog = page.getByRole("dialog", { name: "生成 AI 摘要", exact: true });
  await expect(dialog).toContainText("本次将处理");
  await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await options.getByRole("combobox", { name: "摘要处理范围", exact: true }).selectOption("current");
  await options.getByRole("button", { name: "批量生成摘要", exact: true }).click();
  await expect(dialog.locator(".processing-count")).toHaveText("本次将处理 0 条。已完成且未变化的内容会跳过。");
  await page.screenshot({ path: "screenshots/summary-skip-completed-mobile.png", animations: "disabled" });
  const reprocess = dialog.getByLabel("重新处理已完成的内容", { exact: true });
  await reprocess.check();
  await expect(dialog.locator(".processing-count")).toHaveText("本次将处理 1,892 条。包括已完成且未变化的内容，将重新处理。");
  await page.screenshot({ path: "screenshots/summary-reprocess-mobile.png", animations: "disabled" });
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.screenshot({ path: "screenshots/summary-reprocess-desktop.png", animations: "disabled" });
  await reprocess.uncheck();
  await expect(dialog.locator(".processing-count")).toHaveText("本次将处理 0 条。已完成且未变化的内容会跳过。");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
});
