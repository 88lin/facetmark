import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => { localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light"); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("saved thinking choice remains ready on reopening and can select max outside the catalog", async ({ page }) => {
  const saved: Record<string, unknown> = { chat_backend: "agent", chat_agent: "codex", chat_agent_model: "saved-model", chat_agent_reasoning_effort: "high" };
  let tests = 0, catalogs = 0;
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: [{ id: "codex", name: "Codex", installed: true, path: "/synthetic/codex" }] } }));
  await page.route("**/admin/settings/models", route => { catalogs++; return route.fulfill({ json: { agent: "codex", default_model: "daily-model", warning: "", models: [{ id: "saved-model", label: "Saved model", source: "cli", reasoning_levels: [{ id: "low" }, { id: "high" }] }] } }); });
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") { Object.assign(saved, route.request().postDataJSON().values); return route.fulfill({ json: {} }); }
    const response = await route.fetch(), data = await response.json();
    data.channels.chat.configured = true;
    data.settings = data.settings.map((row: { key: string }) => row.key in saved ? { ...row, value: saved[row.key] } : row);
    return route.fulfill({ response, json: data });
  });
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    data.channels.chat = { configured: true, tested: true, validation: "ready", tested_model: "codex/saved-model" };
    return route.fulfill({ response, json: data });
  });
  await page.route("**/admin/settings/test", route => {
    tests++; expect(route.request().postDataJSON().chat_agent_reasoning_effort).toBe("max");
    return route.fulfill({ json: { chat: { ok: true, model: "codex/saved-model", ms: 2 } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat"), thinking = panel.getByRole("combobox", { name: "思考模式", exact: true });
  await expect(panel.locator(".connection-saved")).toContainText("重新打开无需再选模型或测试");
  await expect(thinking).toHaveValue("high");
  await panel.getByRole("button", { name: "high", exact: true }).click();
  await expect(panel.locator(".connection-saved")).toBeVisible();
  expect(tests).toBe(0);
  await panel.getByRole("button", { name: "max", exact: true }).click();
  await expect(thinking).toHaveValue("max");
  await expect(panel.locator(".connection-saved")).toHaveCount(0);
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect(panel.locator(".connection-feedback")).toContainText("连接已验证并保存");
  await expect.poll(() => saved.chat_agent_reasoning_effort).toBe("max");
  expect(tests).toBe(1);
  expect(catalogs).toBe(1);
  await page.reload();
  await expect(thinking).toHaveValue("max");
  await expect(panel.locator(".connection-saved")).toBeVisible();
  expect(tests).toBe(1);
  await page.screenshot({ path: "screenshots/collection-review/connection-reused-max.png", animations: "disabled" });
});

test("clearing a saved API key is an explicit edit despite its blank masked input", async ({ page }) => {
  let savedKey = true;
  const writes: Record<string, unknown>[] = [];
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      const values = route.request().postDataJSON().values;
      writes.push(values);
      if ("chat_api_key" in values) savedKey = Boolean(values.chat_api_key);
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch(), data = await response.json();
    data.channels.chat.configured = true;
    data.settings = data.settings.map((row: { key: string }) => row.key === "chat_backend"
      ? { ...row, value: "endpoint", locked: false } : row.key === "chat_api_key"
        ? { ...row, value: "", secret: true, set: savedKey, locked: false } : row);
    return route.fulfill({ response, json: data });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat"), save = page.getByRole("button", { name: "保存配置", exact: true });
  const clear = panel.getByRole("button", { name: "清除已保存的密钥", exact: true });
  await expect(clear).toBeVisible();
  await expect(panel.locator('input[name="chat_api_key"]')).toHaveValue("");
  await expect(save).toBeDisabled();
  await clear.click();
  await expect(save).toBeEnabled();
  await save.click();
  await expect.poll(() => writes).toEqual([{ chat_api_key: "" }]);
  await expect(clear).toHaveCount(0);
  await page.reload();
  await expect(panel.locator('input[name="chat_api_key"]')).toBeVisible();
  await expect(clear).toHaveCount(0);
});

test("session rows wrap long titles, keep loaded rows during paging and reset summary filters", async ({ page }) => {
  const title = "保存当时一起研究的内容与相关页面，长标题应当完整换行 ".repeat(6);
  let release = () => {}, paging = false;
  const hold = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/sessions?**", async route => {
    const offset = Number(new URL(route.request().url()).searchParams.get("offset") || 0);
    if (offset) { paging = true; await hold; }
    return route.fulfill({ json: Array.from({ length: offset ? 1 : 40 }, (_, index) => ({ session_id: offset + index + 1,
      label: index === 0 ? title : "合成浏览批次 " + (index + 1), started_at: 1700000000, ended_at: 1700001200, size: 12, method: "temporal" })) });
  });
  await page.goto("/app");
  const pending = page.locator('.collection-status [data-status="pending"]');
  await pending.click();
  await expect(pending).toHaveAttribute("aria-pressed", "true");
  await page.locator(".workspace-search input").fill("previous-filter");
  await page.locator(".workspace-search input").press("Enter");
  await page.getByRole("button", { name: "浏览批次", exact: true }).click();
  await expect(page.locator(".session-row")).toHaveCount(40);
  const first = page.locator(".session-row").first();
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await first.scrollIntoViewIfNeeded();
    expect(await first.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
    expect(await first.locator(".session-copy strong").evaluate(element => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `screenshots/collection-review/sessions-long-${width}.png`, animations: "disabled" });
  }
  await page.getByRole("button", { name: "加载更多", exact: true }).click();
  try {
    await expect.poll(() => paging).toBe(true);
    await expect(page.locator(".session-row")).toHaveCount(40);
  } finally { release(); }
  await expect(page.locator(".session-row")).toHaveCount(41);
  const request = page.waitForRequest(req => new URL(req.url()).pathname === "/bookmarks" && new URL(req.url()).searchParams.get("session") === "1");
  await first.click();
  const params = new URL((await request).url()).searchParams;
  expect(params.get("status") || "all").toBe("all");
  expect(params.get("q") || "").toBe("");
  await expect(page.locator('.collection-status [data-status="all"]')).toHaveAttribute("aria-pressed", "true");
});

test("sessions can be organized from the empty page without configuring AI", async ({ page }) => {
  let organized = false;
  await page.route("**/sessions?**", route => route.fulfill({ json: organized ? [{ session_id: 1, label: "合成批次", started_at: 1700000000, size: 2 }] : [] }));
  await page.route("**/admin/sessions/rebuild", route => { organized = true; return route.fulfill({ json: { sessions: 1, assigned: 2 } }); });
  await page.goto("/app#sessions");
  await expect(page.locator(".sessions-empty")).toContainText("还没有整理好的批次");
  await page.getByRole("button", { name: "整理浏览批次", exact: true }).click();
  await expect(page.locator(".session-row")).toHaveCount(1);
  await expect(page.locator(".sessions-section .notice")).toContainText("已整理 1 个批次");
});

test("select all has a visible hit area, mixed state and native keyboard operation", async ({ page }) => {
  await page.goto("/app");
  const toolbar = page.locator(".library-tools"), all = toolbar.getByRole("checkbox", { name: "全选当前结果", exact: true });
  await expect(all).toBeEnabled();
  const bounds = await toolbar.locator(".library-summary-selection").boundingBox();
  expect(bounds!.height).toBeGreaterThanOrEqual(40);
  expect(bounds!.width).toBeGreaterThan(90);
  await page.locator(".bookmark-check").first().check();
  await expect(all).toHaveJSProperty("indeterminate", true);
  await all.focus(); await page.keyboard.press("Space"); await expect(all).toBeChecked();
  await page.keyboard.press("Space"); await expect(all).not.toBeChecked();
  await expect(all).toHaveJSProperty("indeterminate", false);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "screenshots/collection-review/select-all-mobile.png", animations: "disabled" });
  await page.emulateMedia({ forcedColors: "active", reducedMotion: "reduce" });
  await all.check(); await expect(all).toBeChecked();
  await page.screenshot({ path: "screenshots/collection-review/select-all-forced-colors.png", animations: "disabled" });
});

test("reading size persists after reopening without changing collection typography", async ({ page }) => {
  await page.goto("/app");
  const title = page.locator(".result-title").first();
  await expect(title).toBeVisible();
  const collectionSize = await title.evaluate(element => getComputedStyle(element).fontSize);
  await page.locator(".result-row").first().getByRole("button", { name: /^预览：/ }).click();
  const reading = page.locator(".reading").first();
  await expect(reading).toBeVisible();
  const initial = await reading.evaluate(element => parseFloat(getComputedStyle(element).fontSize));
  await page.getByRole("button", { name: "增大阅读字号", exact: true }).click();
  await expect.poll(() => reading.evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThan(initial);
  await page.getByRole("button", { name: "返回收藏", exact: true }).last().click();
  expect(await title.evaluate(element => getComputedStyle(element).fontSize)).toBe(collectionSize);
  await page.locator(".result-row").first().getByRole("button", { name: /^预览：/ }).click();
  await expect(page.locator(".reader-type-reset")).toHaveText("112%");
  await page.getByRole("button", { name: "恢复默认阅读字号", exact: true }).click();
  await expect(page.locator(".reader-type-reset")).toHaveText("100%");
});
