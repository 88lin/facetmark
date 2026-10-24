import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { settleVisualLayout } from "./visual-layout";

const output = "screenshots/collection-review";
test.use({ locale: "zh-CN" });
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (location.protocol !== "file:") {
      localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light");
    }
  });
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    return url.protocol === "file:" || url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
});
type StartupWindow = typeof window & {
  __restartCount: number;
  __facetmarkStartupError?: string;
  showStartupError: (message: string) => void;
  __TAURI_INTERNALS__: { invoke: (command: string) => Promise<void> };
};

for (const locale of ["zh-CN", "en-US"]) test.describe(`native splash ${locale}`, () => {
test.use({ locale });
test("keeps an error received during restart, supports keyboard retry, and stops reduced-motion loading", async ({ page }) => {
  const suffix = locale === "zh-CN" ? "" : "-en";
  await page.setViewportSize({ width: 500, height: 320 });
  await mkdir(output, { recursive: true });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.addInitScript(() => {
    const state = window as StartupWindow;
    state.__restartCount = 0;
    state.__facetmarkStartupError = "合成启动失败：" + "服务路径与失败原因需要能完整阅读。".repeat(8);
    state.__TAURI_INTERNALS__ = { invoke: async command => {
      if (command !== "restart_backend") throw new Error("Unexpected synthetic command");
      state.__restartCount++;
      if (state.__restartCount === 1) state.showStartupError("Synthetic native failure delivered before restart resolved");
      else if (state.__restartCount === 2) throw new Error("Synthetic restart rejection");
    } };
  });
  await page.goto(pathToFileURL(resolve("../desktop/splash/index.html")).href);
  const retry = page.locator("#retry");
  await expect(retry).toBeVisible();
  await expect(retry).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: `${output}/polish-native-startup-error${suffix}.png` });
  await retry.press("Enter");
  await expect(retry).toBeEnabled();
  await expect(retry).toBeVisible();
  await expect(page.locator("body")).toHaveAttribute("data-phase", "error");
  await expect(page.locator("#hint")).toContainText("before restart resolved");
  await expect(retry).toBeFocused();
  expect(await page.evaluate(() => (window as StartupWindow).__restartCount)).toBe(1);
  await retry.press("Space");
  await expect(page.locator("#hint")).toContainText("Synthetic restart rejection");
  await expect(retry).toBeEnabled();
  await expect(retry).toBeFocused();
  await retry.press("Enter");
  await expect(page.locator("body")).toHaveAttribute("data-phase", "connecting");
  await expect(page.locator("#track")).toBeVisible();
  await expect(retry).toBeHidden();
  expect(await page.evaluate(() => (window as StartupWindow).__restartCount)).toBe(3);
  await page.setViewportSize({ width: 500, height: 360 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator("#track span")).toHaveCSS("animation-name", "none");
  await page.screenshot({ path: `${output}/polish-native-startup-light${suffix}.png` });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.screenshot({ path: `${output}/polish-native-startup-dark${suffix}.png` });
  expect(errors).toEqual([]);
});
});

test("workbench boot and pairing keep their recovery state and submit exactly once", async ({ page, request }) => {
  await mkdir(output, { recursive: true });
  const boot = await (await request.get("/app/boot")).json();
  let releaseBoot!: () => void;
  const bootGate = new Promise<void>(resolve => { releaseBoot = resolve; });
  let bootRequests = 0;
  await page.route("**/app/boot", async route => {
    if (++bootRequests === 1) return route.fulfill({ status: 503, json: { detail: "合成启动连接失败，请重试" } });
    await bootGate; await route.fulfill({ json: { paired: false, token: "" } });
  });
  let attempts = 0;
  let releasePairing!: () => void;
  const gate = new Promise<void>(resolve => { releasePairing = resolve; });
  await page.route("**/stats", async route => {
    attempts++;
    if (route.request().headers().authorization !== `Bearer ${boot.token}`)
      return route.fulfill({ status: 401, json: { detail: "合成配对令牌错误，请重新输入" } });
    await gate; return route.continue();
  });
  try {
    await page.goto("/app");
    await expect(page.locator(".connection-error")).toContainText("合成启动连接失败");
    await settleVisualLayout(page);
    await page.screenshot({ path: `${output}/polish-workbench-startup-error.png` });
    await page.getByRole("button", { name: "重新连接", exact: true }).evaluate(button => {
      (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click();
    });
    await expect.poll(() => bootRequests).toBe(2);
    await expect(page.locator(".startup-track")).toBeVisible();
    await settleVisualLayout(page);
    await page.screenshot({ path: `${output}/polish-workbench-opening.png` });
    releaseBoot();
    await expect(page.locator(".pairing-screen")).toBeVisible();
    await settleVisualLayout(page);
    await page.screenshot({ path: `${output}/polish-pairing-desktop.png` });
    const token = page.getByLabel("配对令牌", { exact: true });
    const connect = page.getByRole("button", { name: "连接", exact: true });
    await expect(connect).toBeDisabled();
    await token.fill("synthetic-invalid-token");
    await token.press("Enter");
    await expect(page.locator(".pairing-error")).toContainText("合成配对令牌错误");
    await expect(token).toHaveValue("synthetic-invalid-token");
    await expect(token).toBeFocused();
    await expect(page.locator(".connection-error")).toHaveCount(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await settleVisualLayout(page);
    await page.screenshot({ path: `${output}/polish-pairing-mobile-error.png` });
    await token.fill(boot.token);
    await connect.evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click(); });
    await expect.poll(() => attempts).toBe(2);
    await expect(token).toBeDisabled();
    await expect(page.locator(".pairing-screen .primary")).toBeDisabled();
    releasePairing();
    await expect(page.locator(".result-row")).toHaveCount(30);
    await expect(page.locator(".pairing-screen")).toHaveCount(0);
  } finally { releaseBoot(); releasePairing(); }
});
