import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

const output = "screenshots/collection-review";
const pageErrors = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  pageErrors.set(page, errors);
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.addInitScript(() => { localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light"); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir(output, { recursive: true });
});
test.afterEach(async ({ page }) => { expect(pageErrors.get(page)).toEqual([]); });

async function capture(page: Page, name: string) {
  await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: `${output}/${name}.png`, animations: "disabled" });
}

test("category capsules fill their segments, stay stationary while pressed, and reverse without corner scaling", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  for (const width of [1440, 1280, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    if (width < 960) await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
    const rail = page.locator(width < 960 ? ".sidebar" : ".collection-sidebar");
    await expect(rail.locator(".facet-types")).toBeVisible();
    await settleVisualLayout(page);
    const geometry = await rail.locator(".facet-types").evaluate(group => {
      const style = getComputedStyle(group);
      const expected = (group.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - 2 * parseFloat(style.columnGap)) / 3;
      return [...group.querySelectorAll<HTMLElement>(".facet-type")].map(button => {
        const rect = button.getBoundingClientRect();
        return { expected, width: rect.width, height: rect.height, radius: getComputedStyle(button).borderTopLeftRadius };
      });
    });
    for (const button of geometry) {
      expect(Math.abs(button.width - button.expected)).toBeLessThan(1);
      expect(button.width / button.height).toBeGreaterThan(1.3);
      expect(button.radius).not.toContain("%");
    }
    const tags = rail.getByRole("button", { name: "标签", exact: true });
    const before = await tags.boundingBox();
    await tags.hover(); await page.mouse.down();
    await expect(tags).toHaveAttribute("data-pressed", "true");
    expect(await tags.boundingBox()).toEqual(before);
    await expect(tags).toHaveCSS("transform", "none");
    await page.mouse.up();
    await expect(tags).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => rail.locator(".facet-type[aria-pressed=true] .selection-pill").evaluate(marker =>
      Math.abs(marker.getBoundingClientRect().width - marker.parentElement!.clientWidth))).toBeLessThan(1);
    await capture(page, `polish-capsules-${width}`);
    await rail.getByRole("button", { name: "文件夹", exact: true }).press("Enter");
    if (width < 960) await page.keyboard.press("Escape");
  }
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.evaluate(() => {
    const state = window as typeof window & { __capsuleFrames: unknown[]; __capsuleRAF: number };
    state.__capsuleFrames = [];
    const started = performance.now();
    const sample = () => {
      const marker = document.querySelector(".collection-sidebar .facet-types .selection-pill");
      if (marker) {
        const style = getComputedStyle(marker);
        const matrix = new DOMMatrixReadOnly(style.transform === "none" ? undefined : style.transform);
        const bounds = marker.getBoundingClientRect();
        state.__capsuleFrames.push({ ms: performance.now() - started, scaleX: matrix.a, scaleY: matrix.d,
          x: bounds.x, width: bounds.width, height: bounds.height, radius: style.borderTopLeftRadius });
      }
      state.__capsuleRAF = requestAnimationFrame(sample);
    };
    sample();
  });
  const types = page.locator(".collection-sidebar .facet-types");
  await types.getByRole("button", { name: "标签", exact: true }).press("Enter");
  await page.waitForTimeout(45);
  await types.getByRole("button", { name: "站点", exact: true }).press("Space");
  await page.waitForTimeout(45);
  await types.getByRole("button", { name: "文件夹", exact: true }).press("Enter");
  await settleVisualLayout(page);
  const frames = await page.evaluate(() => {
    const state = window as typeof window & { __capsuleFrames: { scaleX: number; scaleY: number; x: number; width: number; height: number; radius: string }[]; __capsuleRAF: number };
    cancelAnimationFrame(state.__capsuleRAF); return state.__capsuleFrames;
  });
  expect(frames.length).toBeGreaterThan(8);
  expect(new Set(frames.map(frame => Math.round(frame.x)) ).size).toBeGreaterThan(3);
  expect(frames.every(frame => Math.abs(frame.scaleX - 1) < .001 && Math.abs(frame.scaleY - 1) < .001 && !frame.radius.includes("%"))).toBe(true);
  await writeFile(`${output}/capsule-frame-samples.json`, JSON.stringify(frames, null, 2));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await types.getByRole("button", { name: "标签", exact: true }).press("Space");
  await expect(types.locator(".selection-pill")).toHaveCSS("transform", "none");
  await expect(types.getByRole("button", { name: "标签", exact: true })).toHaveAttribute("aria-pressed", "true");
});

test("nested folders expand independently, retain cached branches, and select the complete exact path", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const count = await page.locator(".result-count").textContent();
  const rail = page.locator(".collection-sidebar");
  const parent = "专题资料 001";
  const child = `${parent}/设计与体验`;
  const leaf = `${child}/需要长期保存与反复查阅的项目研究和学习笔记`;
  const parentRow = rail.locator(`[data-folder-node="${parent}"]`);
  const expand = rail.getByRole("button", { name: `展开「${parent}」`, exact: true });
  let branchRequests = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname === "/bookmarks/folders/tree" && url.searchParams.get("parent") === parent) branchRequests++;
  });
  await expand.press("Space");
  await expect(rail.getByTitle(child, { exact: true })).toBeVisible();
  await expect(page.locator(".result-count")).toHaveText(count!);
  expect(branchRequests).toBe(1);
  await rail.getByRole("button", { name: `收起「${parent}」`, exact: true }).press("Enter");
  await expect(rail.getByTitle(child, { exact: true })).toHaveCount(0);
  await expand.press("Enter");
  await expect(rail.getByTitle(child, { exact: true })).toBeVisible();
  expect(branchRequests).toBe(1);
  await rail.getByTitle(child, { exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(rail.getByTitle(leaf, { exact: true })).toBeVisible();
  await expect(page.locator(".result-count")).toHaveText(count!);
  await capture(page, "polish-folders-expanded");
  await page.keyboard.press("ArrowRight");
  await expect(rail.getByTitle(leaf, { exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-row").first()).toBeVisible();
  const folders = await page.locator(".result-folder").allTextContents();
  expect(folders.length).toBeGreaterThan(0);
  expect(folders.every(folder => folder.trim() === leaf)).toBe(true);
  const leafBounds = await rail.getByTitle(leaf, { exact: true }).boundingBox();
  expect(leafBounds!.width / leafBounds!.height).toBeGreaterThan(1.5);
  await expect(page.locator(".toolbar-location h1")).toHaveText(leaf.split("/").at(-1)!);
  await rail.locator(".facet-location > summary").click();
  await expect(rail.locator(".facet-location p")).toHaveText(leaf.split("/").join(" / "));
  await capture(page, "polish-folders-selected");
  await rail.getByRole("button", { name: "全部文件夹", exact: true }).press("Space");
  await expect(page.locator(".result-count")).toHaveText(count!);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await parentRow.locator(":scope > .facet-tree-row > .facet-expand").click();
  await expect(rail.getByTitle(child, { exact: true })).toHaveCount(0);
  await expand.click();
  await expect(rail.getByTitle(child, { exact: true })).toBeVisible();
  await rail.getByTitle(child, { exact: true }).hover();
  await expect(rail.getByTitle(child, { exact: true }).locator(".collection-folder-front")).toHaveCSS("transform", "none");
});

test("a failed subfolder request stays beside its branch and recovers without changing the selection", async ({ page }) => {
  let fail = true;
  const parent = "专题资料 002";
  await page.route("**/bookmarks/folders/tree?**", route => {
    if (fail && new URL(route.request().url()).searchParams.get("parent") === parent)
      return route.fulfill({ status: 503, json: { detail: "Synthetic branch failure" } });
    return route.continue();
  });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const count = await page.locator(".result-count").textContent();
  const rail = page.locator(".collection-sidebar");
  await rail.getByRole("button", { name: `展开「${parent}」`, exact: true }).click();
  await expect(rail.getByRole("alert")).toContainText("子文件夹暂时无法加载");
  await expect(page.locator(".result-count")).toHaveText(count!);
  await capture(page, "polish-subfolder-error");
  fail = false;
  await rail.getByRole("button", { name: "重试", exact: true }).press("Enter");
  await expect(rail.getByTitle(`${parent}/人工智能`, { exact: true })).toBeVisible();
  await expect(rail.getByRole("alert")).toHaveCount(0);
  await expect(page.locator(".result-count")).toHaveText(count!);
});

test("a literal slash name remains one exact folder when supplemental path metadata fails", async ({ page, request }) => {
  const boot = await (await request.get("/app/boot")).json();
  const headers = { Authorization: `Bearer ${boot.token}` };
  const folder = "精确名称 / AI/ML · 验证";
  const created = await request.post("/admin/library/bookmarks", { headers, data: {
    url: "https://literal-folder.example/polish", title: "合成资料 · 单个名称里的斜杠", folder, tags: [],
  } });
  expect(created.ok()).toBe(true);
  const record = await created.json();
  try {
    await page.route("**/bookmarks/folders/path?**", route => route.fulfill({ status: 503,
      json: { detail: "Synthetic supplemental path failure" } }));
    await page.goto("/app");
    const rail = page.locator(".collection-sidebar");
    const option = rail.locator(".facet-options").getByTitle(folder, { exact: true });
    await expect(option).toBeVisible();
    await expect(rail.locator(`[data-folder-node="${folder}"] > .facet-tree-row > .facet-expand`)).toHaveCount(0);
    await option.press("ArrowRight");
    await expect(option).toBeFocused();
    await option.press("Enter");
    await expect(page.locator(".result-row")).toHaveCount(1);
    await expect(page.locator(".result-count")).toHaveText("1");
    await expect(page.locator(".toolbar-location h1")).toHaveText(folder);
    await expect(page.locator(".result-folder")).toHaveText(folder);
    await rail.locator(".facet-location > summary").click();
    await expect(rail.locator(".facet-location p")).toHaveText(folder);
    await capture(page, "polish-literal-folder");
  } finally {
    const removed = await request.delete(`/admin/library/bookmarks/${record.bookmark_id}`, { headers });
    expect(removed.ok()).toBe(true);
  }
});

test("setup steps retain model drafts and show completion from actual setup state", async ({ page }) => {
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({ json: { ...data, bookmarks: 0, has_vectors: false,
      channels: { chat: { configured: false, tested: false }, embed: { configured: false, tested: false } } } });
  });
  await page.goto("/app");
  await expect(page.locator(".setup-flow")).toBeVisible();
  const steps = page.locator(".setup-steps");
  const models = steps.getByRole("button").filter({ hasText: "连接模型" });
  const imports = steps.getByRole("button").filter({ hasText: "导入书签" });
  await capture(page, "polish-setup-import");
  await models.press("Enter");
  const draft = page.locator(".setup-flow input[name=chat_model]");
  await expect(draft).toBeVisible();
  await draft.fill("未保存的模型草稿 / model-2026");
  await imports.press("Space");
  await expect(draft).toBeHidden();
  await models.press("Space");
  await expect(draft).toHaveValue("未保存的模型草稿 / model-2026");
  await expect(models.locator(".setup-step-number")).toHaveText("2");
  await imports.click();
  await page.locator(".setup-flow input[type=file]").setInputFiles({ name: "invalid.exe", mimeType: "application/octet-stream", buffer: Buffer.from("synthetic") });
  await expect(page.locator(".setup-flow .error")).toContainText("请选择 HTML 或 JSON");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, "polish-setup-mobile-error");
  await models.click();
  await expect(draft).toHaveValue("未保存的模型草稿 / model-2026");
});

test("source discovery and import exclude concurrent submissions, then expose completion and validation recovery", async ({ page }) => {
  let releaseSources!: () => void;
  const sourcesGate = new Promise<void>(resolve => { releaseSources = resolve; });
  let releaseImport!: () => void;
  const importGate = new Promise<void>(resolve => { releaseImport = resolve; });
  let sourceRequests = 0;
  let importRequests = 0;
  await page.route("**/admin/import/sources", async route => {
    sourceRequests++;
    await sourcesGate;
    await route.fulfill({ json: { sources: [{ id: "synthetic-source", browser: "Chrome", profile: "研究资料 · 合成来源" }] } });
  });
  await page.route("**/admin/import/source", async route => {
    importRequests++;
    await importGate;
    await route.fulfill({ json: { inserted: 3, updated: 1 } });
  });
  await page.route("**/admin/import", route => { importRequests++; return route.fulfill({ json: { inserted: 1, updated: 0 } }); });
  try {
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await page.locator(".app-header .header-import").click();
    const importer = page.locator(".importer");
    const find = importer.getByRole("button", { name: "查找本机 Chromium 浏览器的书签来源", exact: true });
    await find.evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click(); });
    await expect.poll(() => sourceRequests).toBe(1);
    await expect(importer.getByRole("button", { name: "选择文件", exact: true })).toBeDisabled();
    await importer.locator("input[type=file]").setInputFiles({ name: "concurrent.html", mimeType: "text/html",
      buffer: Buffer.from("<!DOCTYPE NETSCAPE-Bookmark-file-1><DL></DL>") });
    releaseSources();
    const source = importer.locator(".source-list .source");
    await expect(source).toBeVisible();
    expect(importRequests).toBe(0);
    await capture(page, "polish-import-sources");
    await source.evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click(); });
    await expect.poll(() => importRequests).toBe(1);
    await expect(source).toBeDisabled();
    await expect(find).toBeDisabled();
    await capture(page, "polish-import-working");
    releaseImport();
    await expect(importer.locator(".import-result")).toContainText("导入完成 · 新增 3 · 更新 1");
    await capture(page, "polish-import-success");
    await importer.locator("input[type=file]").setInputFiles({ name: "invalid.exe", mimeType: "application/octet-stream", buffer: Buffer.from("synthetic") });
    await expect(importer.getByRole("alert")).toContainText("请选择 HTML 或 JSON");
    await expect(importer.locator(".import-result")).toHaveCount(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await capture(page, "polish-import-validation-error");
    expect(sourceRequests).toBe(1);
    expect(importRequests).toBe(1);
  } finally { releaseSources(); releaseImport(); }
});
