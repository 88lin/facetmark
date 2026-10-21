import { expect, test, type Locator, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Frame = {
  front: string | null; open: string | null; reduced: boolean;
  width: number; height: number; layoutWidth: number; layoutHeight: number;
};

async function observe(page: Page, button: Locator, action: () => Promise<unknown>) {
  // Record the path before activation so a short morph cannot finish before
  // observation starts. The containing button remains the stable hit target.
  await button.evaluate(button => {
    const icon = button.querySelector(".collection-folder-icon")!;
    const frames: Frame[] = [];
    const state = window as typeof window & { __folderFrames: Frame[]; __folderRAF: number };
    state.__folderFrames = frames;
    const sample = () => {
      const bounds = button.getBoundingClientRect();
      frames.push({ front: icon.querySelector(".collection-folder-front")!.getAttribute("d"),
        open: icon.getAttribute("data-open"), reduced: matchMedia("(prefers-reduced-motion: reduce)").matches,
        width: bounds.width, height: bounds.height,
        layoutWidth: (button as HTMLElement).offsetWidth, layoutHeight: (button as HTMLElement).offsetHeight });
      state.__folderRAF = requestAnimationFrame(sample);
    };
    sample();
  });
  await action();
  await page.waitForTimeout(360); // bounded observation interval, not a readiness guess
  return page.evaluate(() => {
    const state = window as typeof window & { __folderFrames: Frame[]; __folderRAF: number };
    cancelAnimationFrame(state.__folderRAF);
    return state.__folderFrames;
  });
}

function expectMotion(frames: Frame[]) {
  expect(new Set(frames.map(frame => frame.front)).size).toBeGreaterThan(2);
}

function expectStableTarget(frames: Frame[]) {
  // HeroUI gives the pressed button a .97 visual scale. The folder path must
  // preserve layout size while that independent feedback remains available.
  expect(Math.max(...frames.map(frame => frame.layoutWidth)) - Math.min(...frames.map(frame => frame.layoutWidth))).toBeLessThan(1);
  expect(Math.max(...frames.map(frame => frame.layoutHeight)) - Math.min(...frames.map(frame => frame.layoutHeight))).toBeLessThan(1);
  for (const frame of frames) {
    expect(frame.width).toBeGreaterThanOrEqual(frame.layoutWidth * .97 - 1);
    expect(frame.width).toBeLessThanOrEqual(frame.layoutWidth + 1);
    expect(frame.height).toBeGreaterThanOrEqual(frame.layoutHeight * .97 - 1);
    expect(frame.height).toBeLessThanOrEqual(frame.layoutHeight + 1);
  }
}

test("folder selection morphs locally and preserves exact paths, keyboard activation and reduced motion", async ({ browser, baseURL }, testInfo) => {
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
  const capture = async (action: string, button: Locator, perform: () => Promise<unknown>) => {
    const frames = await observe(page, button, perform);
    evidence.push({ action, frames });
    expectStableTarget(frames);
    return frames;
  };
  try {
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await settleVisualLayout(page);
    const rail = page.locator(".collection-sidebar");
    const folder = rail.locator(".facet-option[title]").first();
    const icon = folder.locator(".collection-folder-icon");
    const front = icon.locator(".collection-folder-front");
    const path = (await folder.getAttribute("title"))!;
    const closedPath = await front.getAttribute("d");
    await expect(icon).toHaveAttribute("aria-hidden", "true");
    await expect(icon).toHaveAttribute("data-open", "false");
    await rail.screenshot({ path: "screenshots/folder-rest.png" });
    const hover = await capture("悬停保持目录与点击目标稳定", folder, () => folder.hover());
    expect(new Set(hover.map(frame => frame.front)).size).toBe(1);
    await rail.screenshot({ path: "screenshots/folder-hover.png" });
    const focus = await capture("键盘焦点不改变当前筛选", folder, () => folder.focus());
    expect(new Set(focus.map(frame => frame.front)).size).toBe(1);
    await expect(folder).toHaveAttribute("aria-pressed", "false");
    expectMotion(await capture("Enter 选择完整目录", folder, () => folder.press("Enter")));
    await expect(folder).toHaveAttribute("aria-pressed", "true");
    await expect(icon).toHaveAttribute("data-open", "true");
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    const folderValues = await page.locator(".result-folder").allTextContents();
    expect(folderValues.length).toBeGreaterThan(0);
    expect(folderValues.every(value => value.trim() === path)).toBe(true);
    const openedPath = await front.getAttribute("d");
    expect(openedPath).not.toBe(closedPath);
    await rail.screenshot({ path: "screenshots/folder-selected.png" });
    const all = rail.getByRole("button", { name: "全部文件夹", exact: true });
    expectMotion(await capture("Space 返回全部文件夹", folder, () => all.press("Space")));
    await expect(folder).toHaveAttribute("aria-pressed", "false");
    await expect(front).toHaveAttribute("d", closedPath!);
    expectMotion(await capture("快速选择与取消保持最终筛选", folder, async () => {
      await folder.press("Enter"); await page.waitForTimeout(60);
      await all.press("Enter"); await page.waitForTimeout(60);
      await folder.press("Space"); await page.waitForTimeout(60);
      await all.press("Space");
    }));
    await expect(folder).toHaveAttribute("aria-pressed", "false");
    await expect(icon).toHaveAttribute("data-open", "false");
    await expect(front).toHaveAttribute("d", closedPath!);
    await expect(page.locator(".result-row")).toHaveCount(30);
    const interrupted = await capture("选择中途开启减少动态效果", folder, async () => {
      await folder.press("Enter"); await page.waitForTimeout(60);
      await page.emulateMedia({ reducedMotion: "reduce" });
    });
    // Allow React to commit the live preference, then require a static path.
    const reducedFrames = interrupted.filter(frame => frame.reduced).slice(3);
    expect(reducedFrames.length).toBeGreaterThan(0);
    expect(new Set(reducedFrames.map(frame => frame.front)).size).toBe(1);
    await expect(folder).toHaveAttribute("aria-pressed", "true");
    await expect(front).toHaveAttribute("d", openedPath!);
    const reduced = await capture("减少动态时悬停与焦点保持静态", folder, async () => {
      await page.mouse.move(600, 40); await folder.hover(); await folder.focus();
    });
    expect(new Set(reduced.map(frame => frame.front)).size).toBe(1);
    await all.click();
    await expect(front).toHaveAttribute("d", closedPath!);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    expectMotion(await capture("恢复动画后仍可按完整路径选择", folder, () => folder.click()));
    await all.click();

    const add = page.getByRole("button", { name: "新增收藏", exact: true });
    await add.click();
    const dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
    await expect(dialog).toHaveCSS("transform", "none");
    const trigger = dialog.locator(".folder-picker-trigger");
    expectMotion(await capture("打开选择器时图标跟随展开状态", trigger, () => trigger.click()));
    await expect(trigger.locator(".collection-folder-icon")).toHaveAttribute("data-open", "true");
    const search = dialog.getByRole("textbox", { name: "搜索文件夹", exact: true });
    await search.fill(path);
    const choice = dialog.getByTitle(path, { exact: true });
    await expect(choice).toBeVisible();
    await expect(choice.locator(".collection-folder-icon")).toHaveAttribute("aria-hidden", "true");
    await dialog.screenshot({ path: "screenshots/folder-picker-motion.png" });
    await choice.click();
    await expect(trigger).toContainText(path);
    await expect(trigger).toBeFocused();
    await expect(trigger.locator(".collection-folder-icon")).toHaveAttribute("data-open", "false");
    await expect(dialog.locator(".folder-picker-panel")).toHaveCount(0);
    await trigger.press("Enter");
    await search.fill(path);
    await expect(choice).toHaveAttribute("aria-pressed", "true");
    await expect(choice.locator(".collection-folder-icon")).toHaveAttribute("data-open", "true");
    await choice.press("Space");
    await expect(trigger).toBeFocused();
    await expect(trigger).toContainText(path);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(add).toBeFocused();

    await page.locator(".app-header").getByRole("button", { name: "切换主题", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await settleVisualLayout(page);
    await page.evaluate(async () => {
      await Promise.all(document.documentElement.getAnimations().filter(animation =>
        animation.effect?.getComputedTiming().iterations !== Infinity).map(animation => animation.finished.catch(() => {})));
    });
    await rail.screenshot({ path: "screenshots/folder-dark.png" });
    expect(errors).toEqual([]); expect(writes).toEqual([]);
  } finally {
    const report = JSON.stringify({ synthetic: true, errors, writes, evidence }, null, 2);
    await writeFile("recordings/facetmark-folders.json", report);
    await testInfo.attach("folder-selection-frames", { body: report, contentType: "application/json" });
    await context.close();
    await video?.saveAs("recordings/facetmark-folders.webm");
  }
});
