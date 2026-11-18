import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh");
    localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

async function collection(page: Page) {
  await page.goto("/app");
  await expect(page.locator(".result-row").first()).toBeVisible();
}

async function settings(page: Page) {
  await page.locator(".header-utilities").getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator(".settings-workspace")).toBeVisible();
}

test("settings opened from the collection remains the current page after refresh", async ({ page }) => {
  await collection(page);
  await settings(page);
  await expect(page.getByRole("tab", { name: "AI 连接", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.reload();
  await expect(page.locator(".settings-workspace")).toBeVisible();
  await expect(page.getByRole("tab", { name: "AI 连接", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.screenshot({ path: "screenshots/collection-review/quality-settings-refresh.png" });
});

test("task navigation survives refresh and browser Back returns to the preceding page", async ({ page }) => {
  await collection(page);
  await page.locator(".header-utilities").getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
  await settings(page);
  await page.goBack();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
});

test("a local connection draft survives finding a bookmark without a save or a connection test", async ({ page }) => {
  let saves = 0, probes = 0;
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path === "/admin/settings" && request.method() === "PUT") saves++;
    if (path === "/admin/test" && request.method() === "POST") probes++;
  });
  await collection(page);
  await settings(page);
  const chat = page.locator(".settings-workspace .model-chat");
  await expect(chat.getByRole("combobox", { name: "摘要来源", exact: true })).toBeEnabled();
  await chat.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("endpoint");
  const model = chat.locator('input[name="chat_model"]');
  await expect(model).toBeEnabled();
  await model.fill("manual-navigation-draft-2026");
  const endpoint = chat.locator('input[name="chat_base_url"]');
  await endpoint.fill("https://draft.example.invalid/v1");
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
  await expect(page.locator(".settings-workspace")).toBeHidden();
  await settings(page);
  await expect(model).toHaveValue("manual-navigation-draft-2026");
  await expect(endpoint).toHaveValue("https://draft.example.invalid/v1");
  expect(saves).toBe(0);
  expect(probes).toBe(0);
  await page.screenshot({ path: "screenshots/collection-review/quality-settings-draft-retained.png" });
});

test("search shortcut closes a narrow reader and focuses the usable collection search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 640 });
  await collection(page);
  await page.locator(".bookmark-preview").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog")).toBeHidden();
  const search = page.getByRole("textbox", { name: "搜索书签", exact: true });
  await expect(search).toBeFocused();
  await search.fill("navigation-source-query");
  await expect(search).toHaveValue("navigation-source-query");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/quality-reader-to-search-390.png" });
});

test("search shortcut leaves the navigation drawer and keeps focus in search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 640 });
  await collection(page);
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await expect(page.locator(".sidebar.is-open")).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(page.locator(".sidebar.is-open")).toHaveCount(0);
  await settleVisualLayout(page);
  await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
});
