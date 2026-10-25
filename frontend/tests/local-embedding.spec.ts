import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Runtime = { supported: boolean; packaged: boolean; reason: "available" | "desktop-unavailable" | "dependency-missing" };
async function fixture(page: Page) {
  const control = { runtime: { supported: false, packaged: true, reason: "desktop-unavailable" } as Runtime,
    active: "local", saved: { embed_backend: "local", local_embed_path: "synthetic/local-model", embed_model: "synthetic-embed", embed_dim: 8,
      embed_base_url: "http://127.0.0.1:11434/v1", embed_allow_no_key: true } as Record<string, unknown>,
    tests: [] as Record<string, unknown>[], writes: [] as Record<string, unknown>[], applies: [] as Record<string, unknown>[],
    tested: false, pending: false, testFails: true, locked: false };
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: [] } }));
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      const values = route.request().postDataJSON().values; control.writes.push(values);
      control.saved = { ...control.saved, ...values }; control.pending = control.saved.embed_backend !== control.active;
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch(), data = await response.json();
    data.settings = data.settings.map((row: { key: string }) => row.key in control.saved
      ? { ...row, value: control.saved[row.key], active_value: row.key === "embed_backend" ? control.active : control.saved[row.key],
        pending_restart: row.key === "embed_backend" && control.pending, locked: row.key === "embed_backend" && control.locked } : row);
    return route.fulfill({ response, json: { ...data, local_embedding_runtime: control.runtime } });
  });
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    return route.fulfill({ response, json: { ...data, demo: false, pending_apply: control.pending,
      has_vectors: true, vector_compatible: true,
      channels: { ...data.channels, embed: { configured: true, tested: control.tested } } } });
  });
  await page.route("**/admin/settings/test", route => {
    const body = route.request().postDataJSON(); control.tests.push(body); control.tested = !control.testFails;
    return route.fulfill({ json: { embed: { ok: !control.testFails, model: "synthetic-embed", ms: 4, dim: 8, dim_matches: true,
      ...(control.testFails ? { error: "Synthetic embedding connection unavailable" } : {}) } } });
  });
  await page.route("**/admin/settings/models", route => route.fulfill({ json: { models: [], warning: "Synthetic manual model entry" } }));
  await page.route("**/admin/settings/apply", route => {
    control.applies.push(route.request().postDataJSON()); control.active = String(control.saved.embed_backend); control.pending = false;
    return route.fulfill({ json: { backup: null } });
  });
  return control;
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("desktop local embeddings explain runtime support and switch through fresh test, save and confirmed rebuild", async ({ page }) => {
  const control = await fixture(page);
  await page.goto("/app#settings/models");
  const panel = page.locator(".model-embed");
  await expect(panel.locator(".local-embedding-runtime")).toHaveAttribute("data-runtime-reason", "desktop-unavailable");
  await expect(panel.locator(".local-embedding-runtime")).toContainText("此桌面安装包不包含 Sentence Transformers");
  await expect(panel.locator('input[name="local_embed_path"]')).toHaveValue("synthetic/local-model");
  await expect(panel.locator('input[name="embed_base_url"]')).toHaveCount(0);
  await expect(panel.getByRole("button", { name: "测试连接", exact: true })).toBeDisabled();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/local-embedding-desktop-unavailable.png", animations: "disabled" });
  await page.setViewportSize({ width: 320, height: 640 });
  const switcher = panel.getByRole("button", { name: "切换到模型端点", exact: true });
  await switcher.scrollIntoViewIfNeeded(); await switcher.focus(); await switcher.press("Space");
  expect(control.tests).toHaveLength(0); expect(control.writes).toHaveLength(0); expect(control.applies).toHaveLength(0);
  await expect(panel.locator(".embedding-backend")).toHaveAttribute("data-active-backend", "local");
  await expect(panel.locator(".embedding-pending")).toContainText("尚未保存，需重新测试");
  await expect(panel.locator('input[name="embed_base_url"]')).toHaveValue("http://127.0.0.1:11434/v1");
  const testSave = panel.getByRole("button", { name: "测试并保存", exact: true });
  await testSave.click();
  await expect(panel.locator(".model-test .error")).toContainText("Synthetic embedding connection unavailable");
  expect(control.writes).toHaveLength(0); expect(control.applies).toHaveLength(0);
  control.testFails = false; await testSave.click();
  await expect(panel.locator(".connection-feedback")).toContainText("向量连接已验证并保存");
  expect(control.tests).toHaveLength(2);
  expect(control.tests.every(value => value.channel === "embed" && value.embed_backend === "endpoint")).toBe(true);
  expect(control.writes).toEqual([expect.objectContaining({ embed_backend: "endpoint" })]);
  await expect(panel.locator(".embedding-pending")).toContainText("已保存，尚未应用");
  const apply = page.getByRole("button", { name: "应用已测试的配置", exact: true });
  await expect(apply).toBeDisabled();
  const consent = page.getByRole("checkbox", { name: "我确认备份并在需要时重建向量", exact: true });
  await consent.focus(); await consent.press("Space");
  await expect(apply).toBeEnabled(); await apply.click();
  await expect.poll(() => control.applies).toEqual([{ confirm_rebuild: true }]);
  await expect(panel.locator(".embedding-backend")).toHaveAttribute("data-active-backend", "endpoint");
  await expect(panel.locator(".local-embedding-runtime")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await panel.locator(".embedding-backend").scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/local-embedding-endpoint-320.png", animations: "disabled" });
});

test("available and missing local dependencies use the real service status without changing the backend", async ({ page }) => {
  const control = await fixture(page);
  control.runtime = { supported: false, packaged: false, reason: "dependency-missing" };
  control.locked = true;
  await page.goto("/app#settings/models");
  const panel = page.locator(".model-embed");
  await expect(panel.locator(".local-embedding-runtime")).toContainText("当前服务环境缺少 Sentence Transformers");
  await expect(panel.getByRole("button", { name: "切换到模型端点", exact: true })).toBeDisabled();
  control.runtime = { supported: true, packaged: false, reason: "available" }; control.locked = false;
  await page.reload();
  await expect(panel.locator(".local-embedding-runtime")).toHaveAttribute("data-runtime-reason", "available");
  await expect(panel.locator(".local-embedding-runtime")).toContainText("配置模型后仍需测试");
  await expect(panel.getByRole("button", { name: "测试连接", exact: true })).toBeEnabled();
  await expect(panel.locator('input[name="local_embed_path"]')).toHaveValue("synthetic/local-model");
  expect(control.tests).toHaveLength(0); expect(control.writes).toHaveLength(0); expect(control.applies).toHaveLength(0);
});
