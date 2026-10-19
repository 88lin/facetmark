import { expect, test, type Locator, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Frame = { front: string; paper: string; shine: string; width: number; height: number };

async function observe(page: Page, button: Locator, action: () => Promise<unknown>) {
  // Record before input: quick focus/selection feedback must include intermediate
  // painted frames, not just two static endpoints or motion on a different node.
  await button.evaluate(button => {
    const glyph = button.querySelector(".folder-glyph")!;
    const frames: Frame[] = [];
    const state = window as typeof window & { __folderFrames: Frame[]; __folderRAF: number };
    state.__folderFrames = frames;
    const sample = () => {
      const bounds = button.getBoundingClientRect();
      frames.push({ front: getComputedStyle(glyph.querySelector(".folder-glyph__front")!).transform,
        paper: getComputedStyle(glyph.querySelector(".folder-glyph__paper")!).transform,
        shine: getComputedStyle(glyph.querySelector(".folder-glyph__shine")!).opacity,
        width: bounds.width, height: bounds.height });
      state.__folderRAF = requestAnimationFrame(sample);
    };
    sample();
  });
  await action();
  await page.waitForTimeout(500); // bounded capture interval, not a readiness guess
  return page.evaluate(() => {
    const state = window as typeof window & { __folderFrames: Frame[]; __folderRAF: number };
    cancelAnimationFrame(state.__folderRAF);
    return state.__folderFrames;
  });
}

function expectMotion(frames: Frame[]) {
  expect(new Set(frames.map(frame => frame.front)).size).toBeGreaterThan(2);
  expect(new Set(frames.map(frame => frame.paper)).size).toBeGreaterThan(2);
}

test("sculpted folders respond to pointer and keyboard while real folder selection stays intact", async ({ browser, baseURL }, testInfo) => {
  test.setTimeout(60000);
  await mkdir("recordings", { recursive: true });
  await mkdir("screenshots", { recursive: true });
  const context = await browser.newContext({ baseURL, viewport: { width: 1280, height: 800 },
    reducedMotion: "no-preference", recordVideo: { dir: "recordings/folders", size: { width: 1280, height: 800 } } });
  const page = await context.newPage();
  const video = page.video();
  const evidence: { action: string; frames: Frame[] }[] = [];
  const errors: string[] = [];
  const writes: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (request.method() !== "GET" && new URL(request.url()).pathname.startsWith("/admin/")) writes.push(request.url()); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light");
  });
  const capture = async (action: string, button: Locator, perform: () => Promise<unknown>, moving = true) => {
    const frames = await observe(page, button, perform);
    evidence.push({ action, frames });
    if (moving) expectMotion(frames);
    return frames;
  };
  try {
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await settleVisualLayout(page);
    const rail = page.locator(".collection-sidebar");
    const folder = rail.locator(".facet-option[title]").first();
    const path = (await folder.getAttribute("title"))!;
    const tone = await folder.locator(".folder-glyph").getAttribute("data-tone");
    await expect(folder.locator(".folder-glyph")).toHaveAttribute("aria-hidden", "true");
    await rail.screenshot({ path: "screenshots/folder-rest.png" });
    const hover = await capture("整行悬停：前盖打开、纸张抬起", folder, () => folder.hover());
    expect(Math.max(...hover.map(f => f.width)) - Math.min(...hover.map(f => f.width))).toBeLessThan(1);
    expect(Math.max(...hover.map(f => f.height)) - Math.min(...hover.map(f => f.height))).toBeLessThan(1);
    await rail.screenshot({ path: "screenshots/folder-hover.png" });
    await capture("移开：收回", folder, () => page.mouse.move(600, 40));
    await page.keyboard.press("Tab");
    await capture("键盘焦点：展开", folder, () => folder.focus());
    await capture("Enter 选择：短促反馈", folder, () => folder.press("Enter"));
    await expect(folder).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    expect((await page.locator(".result-folder").allTextContents()).every(value => value.trim() === path)).toBe(true);
    await rail.screenshot({ path: "screenshots/folder-selected.png" });
    await rail.getByRole("button", { name: "全部文件夹", exact: true }).click();
    await capture("快速打断：悬停、移开、选择、取消筛选", folder, async () => {
      await folder.hover(); await page.waitForTimeout(60);
      await page.mouse.move(600, 40); await page.waitForTimeout(60);
      await folder.focus(); await folder.press("Enter"); await page.waitForTimeout(60);
      const all = rail.getByRole("button", { name: "全部文件夹", exact: true });
      await all.focus(); await all.press("Enter");
    });
    await expect(folder).toHaveAttribute("aria-pressed", "false");
    expect(await folder.locator(".folder-glyph__front").evaluate(node => {
      const transform = getComputedStyle(node).transform;
      return new DOMMatrixReadOnly(transform === "none" ? undefined : transform).isIdentity;
    })).toBe(true);
    await capture("选中动画中途减少动态", folder, async () => {
      await folder.focus(); await folder.press("Enter"); await page.waitForTimeout(60);
      await page.emulateMedia({ reducedMotion: "reduce" });
    });
    await expect(folder).toHaveAttribute("aria-pressed", "true");
    const reducedActive = await observe(page, folder, () => page.mouse.move(600, 40));
    expect(new Set(reducedActive.map(frame => frame.front)).size).toBe(1);
    expect(await folder.locator(".folder-glyph__front").evaluate(node => (node as HTMLElement).style.transform)).toBe("");
    await rail.getByRole("button", { name: "全部文件夹", exact: true }).click();
    await expect(folder.locator(".folder-glyph")).toHaveAttribute("data-active", "false");
    await page.emulateMedia({ reducedMotion: "no-preference" });

    await page.getByRole("button", { name: "新增收藏", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
    const trigger = dialog.locator(".folder-picker-trigger");
    await trigger.click();
    const search = dialog.getByRole("textbox", { name: "搜索文件夹", exact: true });
    await search.fill(path);
    const choice = dialog.getByTitle(path, { exact: true });
    await expect(choice).toBeVisible();
    await expect(choice.locator(".folder-glyph")).toHaveAttribute("data-tone", tone!);
    await capture("选择器整行动效", choice, () => choice.hover());
    await dialog.screenshot({ path: "screenshots/folder-picker-motion.png" });
    await choice.click();
    await expect(trigger).toContainText(path);
    await expect(trigger).toBeFocused();
    await expect(trigger.locator(".folder-glyph")).toHaveAttribute("data-tone", tone!);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.mouse.move(600, 40);
    const reduced = await capture("实时减少动态：保持静态", folder, () => folder.hover(), false);
    expect(new Set(reduced.map(frame => frame.front)).size).toBe(1);
    expect(new Set(reduced.map(frame => frame.paper)).size).toBe(1);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.mouse.move(600, 40);
    await capture("实时恢复动画", folder, () => folder.hover());
    await page.mouse.move(600, 40);
    await page.evaluate(() => document.documentElement.dataset.theme = "dark");
    await rail.screenshot({ path: "screenshots/folder-dark.png" });
    expect(errors).toEqual([]); expect(writes).toEqual([]);
  } finally {
    const report = JSON.stringify({ synthetic: true, errors, writes, evidence }, null, 2);
    await writeFile("recordings/facetmark-folders.json", report);
    await testInfo.attach("folder-painted-frames", { body: report, contentType: "application/json" });
    await context.close();
    await video?.saveAs("recordings/facetmark-folders.webm");
  }
});
