import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Profile = { id: string; name: string; channel: string; model: string; backend: string; agent: string;
  base_url: string; key_set: boolean; configured: boolean; tested: boolean; current: boolean; updated_at: number };
async function fixture(page: Page) {
  const saved: Record<string, unknown> = { chat_backend: "endpoint", chat_model: "summary-a",
    chat_base_url: "https://synthetic.invalid/v1", chat_api_key: "SYNTHETIC_KEY_NEVER_RENDER", chat_allow_no_key: false };
  const control = { saves: [] as Record<string, unknown>[], applies: [] as string[], tests: 0,
    lostSave: false, failSettingsRead: false, failSetupRead: false, failList: false,
    wait: null as Promise<void> | null,
    profiles: [
      { id: "daily", name: "日常摘要", channel: "chat", model: "summary-a", backend: "endpoint", agent: "",
        base_url: "https://synthetic.invalid/v1", key_set: true, configured: true, tested: true, current: true, updated_at: 1700000000000 },
      { id: "local", name: "本机深入阅读", channel: "chat", model: "local-careful", backend: "agent", agent: "codex",
        base_url: "", key_set: false, configured: true, tested: true, current: false, updated_at: 1700000000000 },
    ] as Profile[],
  };
  let baseSettings: { settings: { key: string; secret?: boolean }[]; channels: Record<string, unknown> };
  const settings = () => ({ ...baseSettings, settings: baseSettings.settings.map(row => row.key in saved
    ? { ...row, value: row.secret ? "••••" : saved[row.key], set: Boolean(saved[row.key]), locked: false } : row) });
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: [{ id: "codex", name: "Codex", installed: true, path: "/synthetic/codex" }] } }));
  await page.route("**/admin/settings/models", route => route.fulfill({ json: { agent: "codex", models: [], default_model: "local-careful", warning: "configured_catalog" } }));
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      control.saves.push(route.request().postDataJSON()); Object.assign(saved, route.request().postDataJSON().values);
      return route.fulfill({ json: {} });
    }
    if (control.failSettingsRead) return route.fulfill({ status: 503, json: { detail: "Synthetic settings read failure" } });
    const response = await route.fetch(); baseSettings = await response.json();
    baseSettings.channels.chat = { configured: true };
    return route.fulfill({ response, json: settings() });
  });
  await page.route("**/admin/setup-status", async route => {
    if (control.failSetupRead) return route.fulfill({ status: 503, json: { detail: "Synthetic status read failure" } });
    const response = await route.fetch(), data = await response.json();
    data.channels.chat = { configured: true, tested: true, validation: "ready", tested_model: saved.chat_model };
    return route.fulfill({ response, json: data });
  });
  await page.route("**/admin/settings/test", route => { control.tests++; return route.fulfill({ json: { chat: { ok: true, model: "summary-a", ms: 1 } } }); });
  await page.route(/\/admin\/model-profiles(?:\?.*)?$/, async route => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON(); control.saves.push(body);
      if (control.wait) await control.wait;
      let profile = control.profiles.find(item => item.id === body.id);
      if (!profile) {
        profile = { ...control.profiles[0], id: body.id, name: body.name, model: body.values.chat_model || String(saved.chat_model), current: false };
        control.profiles.push(profile);
      }
      if (control.lostSave) { control.lostSave = false; return route.abort("failed"); }
      return route.fulfill({ json: { profile } });
    }
    if (control.failList) return route.fulfill({ status: 503, json: { detail: "Synthetic connection list failure" } });
    const channel = new URL(route.request().url()).searchParams.get("channel");
    return route.fulfill({ json: { profiles: control.profiles.filter(item => !channel || item.channel === channel) } });
  });
  await page.route(/\/admin\/model-profiles\/[^/?]+(?:\/apply)?$/, async route => {
    const path = new URL(route.request().url()).pathname.split("/"), identity = path[3];
    const profile = control.profiles.find(item => item.id === identity)!;
    if (path[4] === "apply") {
      control.applies.push(identity);
      Object.assign(saved, { chat_backend: profile.backend, chat_agent: profile.agent, chat_agent_model: profile.model, chat_model: profile.model });
      control.profiles = control.profiles.map(item => ({ ...item, current: item.id === identity }));
      return route.fulfill({ json: { ...settings(), restart_required: [], profile: { ...profile, current: true } } });
    }
    if (route.request().method() === "DELETE") {
      control.profiles = control.profiles.filter(item => item.id !== identity);
      return route.fulfill({ json: { removed: identity } });
    }
    profile.name = route.request().postDataJSON().name;
    return route.fulfill({ json: { profile } });
  });
  return { control, saved };
}
async function enter(page: Page) {
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat"), profiles = panel.locator(".model-profiles");
  await profiles.locator("summary").click();
  await expect(profiles.getByLabel("连接名称", { exact: true })).toBeEnabled();
  return { panel, profiles };
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => { localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light"); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("named connections apply, reopen and rename without a repeat test or exposing keys", async ({ page }) => {
  const { control } = await fixture(page), { panel, profiles } = await enter(page);
  await profiles.getByRole("button", { name: "使用连接：本机深入阅读", exact: true }).click();
  await expect(panel.getByRole("combobox", { name: "摘要来源", exact: true })).toHaveValue("agent");
  await expect(panel.locator(".connection-feedback")).toContainText("无需再次测试");
  expect(control.tests).toBe(0); expect(control.applies).toEqual(["local"]);
  await profiles.getByRole("button", { name: "重命名连接：本机深入阅读", exact: true }).click();
  await profiles.getByLabel("新连接名称", { exact: true }).fill("研究阅读连接");
  await profiles.getByRole("button", { name: "保存连接名称", exact: true }).click();
  await expect(profiles).toContainText("研究阅读连接");
  await page.reload(); await panel.locator(".model-profiles > summary").click();
  await expect(profiles).toContainText("研究阅读连接");
  await expect(panel.locator(".model-picker-trigger")).toContainText("local-careful");
  expect(control.tests).toBe(0);
  expect(await page.locator("body").innerText()).not.toContain("SYNTHETIC_KEY_NEVER_RENDER");
});

test("a lost save response retries the same named snapshot and concurrent keyboard submissions send once", async ({ page }) => {
  const { control } = await fixture(page), { panel, profiles } = await enter(page);
  await panel.locator('input[name="chat_model"]').fill("summary-draft");
  await profiles.getByLabel("连接名称", { exact: true }).fill("可恢复的摘要连接");
  control.lostSave = true;
  const save = profiles.getByRole("button", { name: "保存当前连接", exact: true });
  await save.click(); await expect(profiles.getByRole("alert")).toBeVisible();
  await expect(profiles.getByLabel("连接名称", { exact: true })).toHaveValue("可恢复的摘要连接");
  let release!: () => void; control.wait = new Promise(resolve => { release = resolve; });
  await save.focus(); await save.press("Enter");
  await expect.poll(() => control.saves.length).toBe(2);
  await page.keyboard.press("Enter"); expect(control.saves).toHaveLength(2);
  release();
  await expect(profiles).toContainText("已保存“可恢复的摘要连接”");
  expect(control.saves[0]).toEqual(control.saves[1]);
  expect((control.saves[0].values as Record<string, unknown>).chat_model).toBe("summary-draft");
  expect(control.profiles.filter(item => item.name === "可恢复的摘要连接")).toHaveLength(1);
});

test("saved configuration with a failed read keeps its receipt and retries only reads", async ({ page }) => {
  const { control, saved } = await fixture(page), { panel } = await enter(page);
  await panel.locator('input[name="chat_model"]').fill("saved-before-refresh");
  control.failSettingsRead = true; control.failSetupRead = true;
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(page.locator(".settings-read-recovery")).toContainText("已保存的配置和测试结果仍保留");
  expect(saved.chat_model).toBe("saved-before-refresh"); expect(control.saves).toHaveLength(1);
  await expect(page.getByRole("button", { name: "保存配置", exact: true })).toBeDisabled();
  control.failSettingsRead = false; control.failSetupRead = false;
  await page.getByRole("button", { name: "重新读取设置状态", exact: true }).click();
  await expect(page.locator(".settings-read-recovery")).toHaveCount(0);
  await expect(panel.locator('input[name="chat_model"]')).toHaveValue("saved-before-refresh");
  expect(control.saves).toHaveLength(1); expect(control.tests).toBe(0);
});

test("removing a name requires a deliberate choice and retains the active configuration", async ({ page }) => {
  const { control, saved } = await fixture(page), { profiles } = await enter(page);
  await profiles.getByRole("button", { name: "移除连接：日常摘要", exact: true }).click();
  await expect(profiles.locator(".model-profile-confirm")).toContainText("当前配置和收藏不会删除");
  await profiles.locator(".model-profile-confirm").getByRole("button", { name: "取消", exact: true }).click();
  expect(control.profiles).toHaveLength(2);
  await profiles.getByRole("button", { name: "移除连接：日常摘要", exact: true }).click();
  await profiles.getByRole("button", { name: "确认移除连接", exact: true }).click();
  await expect(profiles.locator(".model-profile-info > strong")).toHaveCount(1);
  expect(saved.chat_model).toBe("summary-a");
});

for (const [language, theme, width, height] of [
  ["zh", "light", 1280, 850], ["en", "dark", 1024, 600], ["zh", "dark", 390, 700], ["en", "light", 320, 640],
] as const) test(`named connections fit long text, keyboard and reduced motion at ${language} ${theme} ${width}`, async ({ page }) => {
  const { control } = await fixture(page);
  control.profiles[0].name = "中文连接名称与说明 Long named connection ".repeat(2).slice(0, 80);
  control.profiles[0].model = "provider/" + "long-model-id-".repeat(12);
  control.profiles[0].base_url = "https://synthetic.invalid/v1/" + "long-endpoint-".repeat(12);
  await page.addInitScript(([lang, color]) => { localStorage.setItem("fm-language", lang); localStorage.setItem("fm-theme", color); }, [language, theme]);
  await page.setViewportSize({ width, height }); await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app#settings");
  const profiles = page.locator(".model-chat .model-profiles");
  await profiles.locator("summary").focus(); await profiles.locator("summary").press("Enter");
  await expect(profiles.locator(".model-profile-info > strong")).toHaveCount(2);
  await profiles.locator(".model-profile-list").scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `screenshots/collection-review/model-profiles-${language}-${theme}-${width}.png`, animations: "disabled" });
});
