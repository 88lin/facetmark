import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const agents = [
  { id: "codex", name: "Codex", installed: false },
  { id: "claude", name: "Claude Code", installed: false },
  { id: "opencode", name: "OpenCode", installed: true, path: "C:\\Users\\示例\\AppData\\Roaming\\npm\\node_modules\\opencode-ai\\bin\\opencode.exe" },
];

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir("screenshots", { recursive: true });
  await page.route("**/admin/settings/models", route => route.fulfill({ json: { agent: "opencode", default_model: "custom/default", warning: "", models: [
    { id: "custom/default", label: "Default summary", source: "cli" }, { id: "custom/selected", label: "Selected summary", source: "cli" },
  ] } }));
});

test("OpenCode is detected, selected, tested and saved without duplicated credentials", async ({ page }) => {
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents } }));
  let tested: Record<string, unknown> = {};
  let saved: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "opencode/configured default", ms: 42 } } });
  });
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      saved = route.request().postDataJSON().values;
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch();
    const data = await response.json();
    data.settings = data.settings.map((row: { key: string; value: unknown }) => row.key in saved ? { ...row, value: saved[row.key] } : row);
    return route.fulfill({ response, json: data });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  await expect(panel.locator(".agent-detection")).toContainText("将使用 OpenCode");
  await expect(panel.locator('input[name="chat_api_key"]')).toHaveCount(0);
  const save = panel.getByRole("button", { name: "测试并保存", exact: true });
  await expect(save).toBeInViewport({ ratio: 1 });
  await page.setViewportSize({ width: 1024, height: 749 });
  await expect(save).toBeInViewport({ ratio: 1 });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.screenshot({ path: "screenshots/agents-opencode-desktop.png", animations: "disabled" });
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("opencode");
  await save.click();
  await expect.poll(() => saved.chat_agent).toBe("opencode");
  expect(tested).toMatchObject({ channel: "chat", chat_backend: "agent", chat_agent: "opencode" });
  expect(tested.chat_api_key).toBeUndefined();
  await expect(panel.locator(".tested-model")).toHaveText("opencode/configured default");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".page-scroll").evaluate(el => { el.scrollTop = 0; });
  await page.screenshot({ path: "screenshots/agents-opencode-mobile-overview.png", animations: "disabled" });
  await panel.locator(".agent-details > summary").click();
  await expect(panel.locator(".agent-paths")).toContainText("opencode.exe");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: "screenshots/agents-opencode-mobile.png", animations: "disabled" });
});

test("detection failure is retryable and does not erase an agent model draft", async ({ page }) => {
  let fail = true;
  await page.route("**/admin/agents", route => fail
    ? route.fulfill({ status: 503, json: { detail: "fixture failure" } })
    : route.fulfill({ json: { agents } }));
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  await expect(panel.locator(".agent-detection")).toContainText("暂时无法检测");
  await expect(panel.getByRole("button", { name: "测试并保存", exact: true })).toBeDisabled();
  await panel.locator(".agent-details > summary").click();
  await panel.getByRole("button", { name: "手动输入", exact: true }).click();
  await panel.locator('input[name="chat_agent_model"]').fill("custom/keep-my-draft");
  fail = false;
  await panel.getByRole("button", { name: "重新检测", exact: true }).click();
  await expect(panel.locator(".agent-detection")).toContainText("将使用 OpenCode");
  await expect(panel.locator('input[name="chat_agent_model"]')).toHaveValue("custom/keep-my-draft");
  await expect(panel.getByRole("button", { name: "测试并保存", exact: true })).toBeEnabled();
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("claude");
  await expect(panel.locator(".agent-detection")).toContainText("未检测到所选 Agent");
  await expect(panel.getByRole("button", { name: "测试连接", exact: true })).toBeDisabled();
});

test("a failed connection cannot retain a successful status or save settings", async ({ page }) => {
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents } }));
  await page.route("**/admin/settings/test", route => route.fulfill({ json: { chat: { ok: false, model: "opencode/default", error: "Sign into OpenCode first." } } }));
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "PUT" && request.url().endsWith("/admin/settings")) writes.push(request.url()); });
  await page.goto("/app#settings");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  const panel = page.locator(".model-chat");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect(panel.locator("header")).toContainText("测试未通过");
  await expect(panel.locator(".model-test .error")).toContainText("Sign into OpenCode");
  expect(writes).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.locator(".model-test").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "screenshots/agents-connection-error-mobile.png", animations: "disabled" });
});

test("editing embeddings preserves the independent chat test result", async ({ page }) => {
  await page.route("**/admin/settings/test", route => route.fulfill({ json: { chat: { ok: true, model: "fixture/chat", ms: 10 } } }));
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await panel.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect(panel.locator(".test-result")).toContainText("连接成功");
  await page.locator('input[name="embed_model"]').fill("another-embedding-model");
  await expect(panel.locator(".test-result")).toContainText("连接成功");
  await page.locator('input[name="chat_model"]').fill("another-chat-model");
  await expect(panel.locator(".test-result")).toHaveCount(0);
});
