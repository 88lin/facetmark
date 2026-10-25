import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import type { Setting } from "../src/api";
import { settleVisualLayout } from "./visual-layout";

const defaults: Record<string, number> = {
  enrich_concurrency: 4, agent_concurrency: 2, chat_concurrency: 2,
  fetch_concurrency: 30, fetch_per_host_concurrency: 2, fetch_per_host_min_interval: 0.5,
  model_requests_per_minute: 0, max_retries: 3,
};

async function processingFixture(page: Page, initial: Record<string, unknown> = {}, options: {
  locked?: string[]; omitted?: string[]; failWrites?: number;
} = {}) {
  const saved: Record<string, unknown> = { ...defaults, chat_backend: "endpoint", chat_model: "synthetic-summary", ...initial };
  const writes: { values: Record<string, unknown> }[] = [];
  let failures = options.failWrites || 0;
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON(); writes.push(body);
      if (failures > 0) {
        failures--;
        return route.fulfill({ status: 503, json: { detail: "Synthetic settings write failure" } });
      }
      Object.assign(saved, body.values);
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch(), data = await response.json();
    data.channels.chat.configured = true;
    const rows: Setting[] = data.settings;
    for (const [key, value] of Object.entries(saved)) {
      if (!rows.some(row => row.key === key)) rows.push({ key, value, set: true,
        locked: false, secret: false, pending_restart: false, source: "file" });
    }
    data.settings = rows.filter(row => !options.omitted?.includes(row.key)).map(row => ({ ...row,
      ...(row.key in saved ? { value: saved[row.key] } : {}),
      locked: options.locked?.includes(row.key) || false,
      source: options.locked?.includes(row.key) ? "env" : "file",
    }));
    return route.fulfill({ response, json: data });
  });
  return { saved, writes };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: [{
    id: "codex", name: "Codex", installed: true, path: "C:\\synthetic\\codex.exe",
  }] } }));
  await page.route("**/admin/settings/models", route => route.fulfill({ json: {
    agent: "codex", default_model: "synthetic-summary", models: [{ id: "synthetic-summary", label: "Synthetic summary", source: "config" }],
  } }));
});

test("processing limits save independently and preserve connection drafts and successful tests", async ({ page }) => {
  const { writes } = await processingFixture(page);
  const probes: Record<string, unknown>[] = [];
  await page.route("**/admin/settings/test", route => {
    const body = route.request().postDataJSON(); probes.push(body);
    return route.fulfill({ json: { chat: { ok: true, model: String(body.chat_model), ms: 1 } } });
  });
  await page.goto("/app#settings");
  const connection = page.locator(".model-chat"), panel = page.locator(".processing-preferences");
  await connection.locator("input[name=chat_model]").fill("connection-draft-kept");
  await connection.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect(connection.locator(".tested-model")).toHaveText("connection-draft-kept");
  await panel.locator(".processing-reliability > summary").click();
  const changed = { enrich_concurrency: 9, agent_concurrency: 5, chat_concurrency: 4,
    fetch_concurrency: 12, fetch_per_host_concurrency: 6, fetch_per_host_min_interval: 0.25,
    model_requests_per_minute: 120, max_retries: 4 };
  for (const [key, value] of Object.entries(changed)) await panel.locator(`input[name=${key}]`).fill(String(value));
  await expect(panel.locator(".processing-effective-summary dd")).toHaveText("4 个并发请求");
  await panel.getByRole("button", { name: "保存处理设置", exact: true }).click();
  await expect.poll(() => writes).toEqual([{ values: changed }]);
  await expect(panel.locator(".processing-footer [role=status]")).toContainText("处理设置已保存");
  await expect(panel.locator(".processing-effective-summary dd")).toHaveText("9 个并发请求");
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("4 个同时对话");
  await expect(panel.locator(".processing-host-limit")).toHaveText("单个站点最多 6 个请求，启动间隔至少 0.25 秒。");
  await expect(connection.locator("input[name=chat_model]")).toHaveValue("connection-draft-kept");
  await expect(connection.locator(".tested-model")).toHaveText("connection-draft-kept");
  await expect(connection.locator("header .quiet")).toContainText("草稿已测试");
  expect(probes).toHaveLength(1);
  await connection.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect.poll(() => probes.length).toBe(2);
  expect(probes[1].chat_model).toBe("connection-draft-kept");
  for (const key of Object.keys(defaults)) expect(probes[1]).not.toHaveProperty(key);
});

test("effective agent limits use the saved provider and the smaller process cap", async ({ page }) => {
  const { saved, writes } = await processingFixture(page, { chat_backend: "agent", chat_agent: "codex",
    enrich_concurrency: 6, chat_concurrency: 7, fetch_concurrency: 1, fetch_per_host_concurrency: 8 });
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences"), provider = page.getByRole("combobox", { name: "摘要来源", exact: true });
  await expect(panel.locator(".processing-source")).toHaveText("已保存 · 本机 Agent");
  await expect(panel.locator(".processing-effective-summary dd")).toHaveText("2 个并发请求");
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("2 个同时对话");
  await expect(panel.locator(".processing-host-limit")).toContainText("最多 1 个请求");
  await provider.selectOption("endpoint");
  await panel.locator("input[name=enrich_concurrency]").fill("8");
  await panel.locator("input[name=agent_concurrency]").fill("3");
  await panel.locator("input[name=chat_concurrency]").fill("4");
  await panel.getByRole("button", { name: "保存处理设置", exact: true }).click();
  await expect.poll(() => writes[0]).toEqual({ values: { enrich_concurrency: 8, agent_concurrency: 3, chat_concurrency: 4 } });
  expect(saved.chat_backend).toBe("agent");
  await expect(provider).toHaveValue("endpoint");
  await expect(panel.locator(".processing-effective-summary dd")).toHaveText("3 个并发请求");
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("3 个同时对话");
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(panel.locator(".processing-source")).toHaveText("已保存 · API 接入");
  await expect(panel.locator(".processing-effective-summary dd")).toHaveText("8 个并发请求");
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("4 个同时对话");
});

test("empty and out-of-range numbers stay unsaved, while fractional and zero intervals are valid", async ({ page }) => {
  const { writes } = await processingFixture(page);
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences"), save = panel.getByRole("button", { name: "保存处理设置", exact: true });
  await panel.locator(".processing-reliability > summary").click();
  const limits = [
    { key: "enrich_concurrency", minimum: 1, maximum: 64 },
    { key: "agent_concurrency", minimum: 1, maximum: 8 },
    { key: "chat_concurrency", minimum: 1, maximum: 8 },
    { key: "fetch_concurrency", minimum: 1, maximum: 64 },
    { key: "fetch_per_host_concurrency", minimum: 1, maximum: 16 },
    { key: "fetch_per_host_min_interval", minimum: 0, maximum: 60 },
    { key: "model_requests_per_minute", minimum: 0, maximum: 6000 },
    { key: "max_retries", minimum: 1, maximum: 10 },
  ];
  for (const limit of limits) {
    const input = panel.locator(`input[name=${limit.key}]`), interval = limit.key === "fetch_per_host_min_interval";
    await expect(input).toHaveAttribute("min", String(limit.minimum));
    await expect(input).toHaveAttribute("max", String(limit.maximum));
    await expect(input).toHaveAttribute("step", interval ? "any" : "1");
    for (const invalid of ["", String(limit.minimum - 1), String(limit.maximum + 1), ...(interval ? [] : ["1.5"])]) {
      await input.fill(invalid);
      await expect(input).toHaveAttribute("aria-invalid", "true");
      await expect(save).toBeDisabled();
      expect(writes).toHaveLength(0);
    }
    await input.fill(String(defaults[limit.key]));
  }
  const maxima = Object.fromEntries(limits.map(limit => [limit.key, limit.maximum]));
  for (const [key, value] of Object.entries(maxima)) await panel.locator(`input[name=${key}]`).fill(String(value));
  await save.click();
  await expect.poll(() => writes[0]).toEqual({ values: maxima });
  const interval = panel.locator("input[name=fetch_per_host_min_interval]");
  await interval.fill("0"); await interval.press("Enter");
  await expect.poll(() => writes[1]).toEqual({ values: { fetch_per_host_min_interval: 0 } });
  await expect(panel.locator(".processing-host-limit")).toContainText("至少 0 秒");
});

test("environment-controlled and unavailable fields cannot enter the saved patch", async ({ page }) => {
  const { writes } = await processingFixture(page, {}, { locked: ["agent_concurrency", "fetch_per_host_min_interval", "max_retries", "model_requests_per_minute"],
    omitted: ["fetch_per_host_concurrency"] });
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences");
  await panel.locator(".processing-reliability > summary").click();
  for (const key of ["agent_concurrency", "fetch_per_host_min_interval", "fetch_per_host_concurrency", "max_retries", "model_requests_per_minute"])
    await expect(panel.locator(`input[name=${key}]`)).toBeDisabled();
  await expect(panel.locator(".processing-lock")).toHaveCount(4);
  await expect(panel.locator(".processing-field:has(input[name=fetch_per_host_min_interval]) .processing-range")).toContainText("默认 0.5");
  await expect(panel).toContainText("此服务版本尚未提供该设置");
  await expect(panel.locator(".processing-host-limit")).toHaveCount(0);
  await panel.locator("input[name=enrich_concurrency]").fill("5");
  await panel.getByRole("button", { name: "保存处理设置", exact: true }).click();
  await expect.poll(() => writes).toEqual([{ values: { enrich_concurrency: 5 } }]);
});

test("a failed save retains numeric drafts and allows a successful retry", async ({ page }) => {
  const { saved, writes } = await processingFixture(page, {}, { failWrites: 1 });
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences"), input = panel.locator("input[name=chat_concurrency]");
  const save = panel.getByRole("button", { name: "保存处理设置", exact: true });
  await input.fill("6"); await save.click();
  await expect(panel.getByRole("alert")).toContainText("处理设置未保存");
  await expect(panel.getByRole("alert")).toContainText("Synthetic settings write failure");
  await expect(input).toHaveValue("6");
  expect(saved.chat_concurrency).toBe(2);
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("2 个同时对话");
  await save.click();
  await expect.poll(() => writes.length).toBe(2);
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel.locator(".processing-effective-chat dd")).toHaveText("6 个同时对话");
  await expect(save).toBeDisabled();
});

test("HTTP rate and total attempts expose truthful defaults, single attempts and unlimited mode", async ({ page }) => {
  const { writes } = await processingFixture(page);
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences"), details = panel.locator(".processing-reliability");
  const summary = details.locator("summary");
  await expect(details).not.toHaveAttribute("open", "");
  await expect(summary).toContainText("不限速 · 最多 3 次尝试");
  await summary.focus(); await summary.press("Enter");
  await expect(details).toHaveAttribute("open", "");
  const rate = details.getByRole("spinbutton", { name: "每分钟请求上限", exact: true });
  const attempts = details.getByRole("spinbutton", { name: "最大尝试次数", exact: true });
  await expect(rate).toHaveValue("0");
  await expect(attempts).toHaveValue("3");
  await expect(details).toContainText("同一接口与账号的请求共享限速");
  await expect(details).toContainText("包含首次请求");
  await rate.fill("120"); await attempts.fill("1");
  await summary.click();
  await panel.getByRole("button", { name: "保存处理设置", exact: true }).click();
  await expect.poll(() => writes[0]).toEqual({ values: { model_requests_per_minute: 120, max_retries: 1 } });
  await expect(summary).toContainText("120 次/分钟 · 最多 1 次尝试");
  await summary.click(); await rate.fill("0"); await rate.press("Enter");
  await expect.poll(() => writes[1]).toEqual({ values: { model_requests_per_minute: 0 } });
  await expect(summary).toContainText("不限速 · 最多 1 次尝试");
});

test("limit drafts retain native keyboard behavior and fit narrow light and dark windows", async ({ page }) => {
  const { writes } = await processingFixture(page);
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.addInitScript(() => localStorage.setItem("fm-language", "en"));
  await page.goto("/app#settings");
  const panel = page.locator(".processing-preferences"), input = panel.getByRole("spinbutton", { name: "Concurrent conversations", exact: true });
  await input.focus(); await input.press("ArrowUp");
  await expect(input).toHaveValue("3");
  await page.getByRole("tab", { name: "Browser extension", exact: true }).click();
  await page.getByRole("tab", { name: "AI connections", exact: true }).click();
  await expect(input).toHaveValue("3");
  const discard = panel.getByRole("button", { name: "Discard limit changes", exact: true });
  await discard.focus(); await discard.press("Space");
  await expect(input).toHaveValue("2");
  expect(writes).toHaveLength(0);
  await panel.locator(".processing-reliability > summary").click();
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    if (width === 320) {
      await page.getByRole("button", { name: "Toggle theme", exact: true }).first().click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    }
    await expect(panel.getByRole("spinbutton", { name: "Host request interval (seconds)", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await settleVisualLayout(page);
    await panel.locator(".processing-heading").evaluate(element => element.scrollIntoView({ block: "start", inline: "nearest" }));
    await page.screenshot({ path: "screenshots/collection-review/processing-limits-" + width + ".png", animations: "disabled" });
    await panel.locator(".processing-reliability").evaluate(element => element.scrollIntoView({ block: "start", inline: "nearest" }));
    await expect(panel.getByRole("spinbutton", { name: "HTTP requests per minute", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await settleVisualLayout(page);
    await page.screenshot({ path: "screenshots/collection-review/processing-retries-" + width + ".png", animations: "disabled" });
  }
  expect(pageErrors).toHaveLength(0);
});
