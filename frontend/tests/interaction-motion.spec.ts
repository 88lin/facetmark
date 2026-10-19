import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

type MotionNode = {
  key: string; transform: string; opacity: string; filter: string; x: number; y: number;
  translateX: number; translateY: number;
  inline: { transform: string; opacity: string; filter: string; willChange: string };
  inert: boolean; hidden: string | null; pointerEvents: string; phase: string | null;
  animations: { state: string; progress: number | null; properties: string[] }[];
};
type MotionFrame = { time: number; targets: Record<string, MotionNode[]> };
type MotionEvidence = { action: string; frames: MotionFrame[] };

declare global {
  interface Window {
    __interactionProbe: { start: (selectors: string[]) => void; stop: () => MotionFrame[] };
  }
}

// Start before the real input, so a fast animation cannot finish between click()
// and an assertion. Capture painted GSAP/Motion states as well as WAAPI/CSS.
function installMotionProbe() {
  let frame = 0;
  let nextNode = 0;
  const identities = new WeakMap<Element, string>();
  let samples: MotionFrame[] = [];
  window.__interactionProbe = {
    start(selectors) {
      cancelAnimationFrame(frame);
      samples = [];
      const started = performance.now();
      const sample = () => {
        const targets: MotionFrame["targets"] = {};
        for (const selector of selectors) {
          targets[selector] = [...document.querySelectorAll<HTMLElement>(selector)].slice(0, 4).map(element => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            const matrix = new DOMMatrixReadOnly(style.transform === "none" ? undefined : style.transform);
            if (!identities.has(element)) identities.set(element, `node-${++nextNode}`);
            return {
              key: identities.get(element)!,
              transform: style.transform, opacity: style.opacity, filter: style.filter,
              translateX: matrix.m41, translateY: matrix.m42,
              inline: { transform: element.style.transform, opacity: element.style.opacity,
                filter: element.style.filter, willChange: element.style.willChange },
              x: Math.round(rect.x * 100) / 100, y: Math.round(rect.y * 100) / 100,
              inert: element.inert, hidden: element.getAttribute("aria-hidden"),
              pointerEvents: style.pointerEvents, phase: element.dataset.overlayPhase || null,
              animations: element.getAnimations().filter(animation => {
                const timing = animation.effect?.getComputedTiming();
                return timing && timing.iterations !== Infinity;
              }).map(animation => ({
                state: animation.playState,
                progress: animation.effect?.getComputedTiming().progress ?? null,
                properties: Object.keys((animation.effect as KeyframeEffect)?.getKeyframes()[0] || {}),
              })),
            };
          });
        }
        samples.push({ time: Math.round(performance.now() - started), targets });
        frame = requestAnimationFrame(sample);
      };
      sample();
    },
    stop() { cancelAnimationFrame(frame); return samples; },
  };
}

async function record(page: Page, evidence: MotionEvidence[], action: string, selectors: string[], perform: () => Promise<unknown>) {
  await page.evaluate(selectors => window.__interactionProbe.start(selectors), selectors);
  try {
    await perform();
    // A bounded observation interval, not a product timing assertion. Keep
    // enough running and settled frames to inspect the continuous recording.
    await page.evaluate(() => new Promise<void>(resolve => {
      const until = performance.now() + 650;
      const observe = () => performance.now() >= until ? resolve() : requestAnimationFrame(observe);
      requestAnimationFrame(observe);
    }));
  } finally {
    evidence.push({ action, frames: await page.evaluate(() => window.__interactionProbe.stop()) });
  }
  return evidence.at(-1)!;
}

function nodes(step: MotionEvidence, selector: string) {
  return step.frames.flatMap(frame => frame.targets[selector] || []);
}

function expectAnimation(step: MotionEvidence, selector: string) {
  expect(nodes(step, selector).some(node => node.animations.some(animation =>
    animation.state === "running" && animation.progress !== null)), `${step.action}: running DOM animation`).toBe(true);
}

function expectPaintedMotion(step: MotionEvidence, selector: string, layout = false) {
  const statesByNode = new Map<string, Set<string>>();
  for (const node of nodes(step, selector)) {
    const states = statesByNode.get(node.key) || new Set<string>();
    states.add(layout ? `${node.x},${node.y}` : `${node.transform},${node.opacity},${node.filter}`);
    statesByNode.set(node.key, states);
  }
  // More than the before/after states demonstrates an intermediate painted frame.
  // Positions from distinct, stationary cards must never satisfy this check.
  expect([...statesByNode.values()].some(states => states.size > 2),
    `${step.action}: one node has intermediate ${layout ? "positions" : "painted states"}`).toBe(true);
}

function expectContentMotion(step: MotionEvidence, selector: string, direction?: 1 | -1) {
  const samples = nodes(step, selector);
  const grouped = new Map<string, MotionNode[]>();
  for (const node of samples) grouped.set(node.key, [...(grouped.get(node.key) || []), node]);
  // GSAP writes inline styles and does not appear in getAnimations(). Require
  // multiple intermediate values for all three properties on one actual node.
  expect([...grouped.values()].some(values =>
    new Set(values.map(node => node.transform)).size > 2 &&
    new Set(values.filter(node => +node.opacity > 0 && +node.opacity < 1).map(node => node.opacity)).size > 2 &&
    new Set(values.filter(node => node.filter !== "none" && node.filter !== "blur(0px)").map(node => node.filter)).size > 2),
  `${step.action}: same node paints travel, opacity and bounded focus`).toBe(true);
  if (direction) expect(samples.some(node => node.translateX * direction > 1),
    `${step.action}: travel follows destination order`).toBe(true);
  for (const node of step.frames.at(-1)?.targets[selector] || []) {
    expect(node.inline, `${step.action}: settled content releases owned inline styles`).toEqual({
      transform: "", opacity: "", filter: "", willChange: "",
    });
  }
}

function expectInertExit(step: MotionEvidence, selector: string) {
  const closing = nodes(step, selector).filter(node => node.phase === "closing");
  expect(closing.length, `${step.action}: observed exit phase`).toBeGreaterThan(0);
  expect(closing.every(node => node.inert && node.hidden === "true" && node.pointerEvents === "none"),
    `${step.action}: exiting nodes cannot receive input`).toBe(true);
}

test("everyday navigation has visible motion without losing drafts, focus or input safety", async ({ browser, baseURL }, testInfo) => {
  test.setTimeout(90000);
  await mkdir("recordings", { recursive: true });
  const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 960 },
    reducedMotion: "no-preference", recordVideo: { dir: "recordings/raw", size: { width: 1440, height: 960 } } });
  const page = await context.newPage();
  const video = page.video();
  const evidence: MotionEvidence[] = [];
  const errors: string[] = [];
  const writes: string[] = [];
  page.on("pageerror", error => errors.push(String(error)));
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET" && (path.startsWith("/admin/library/") || path === "/admin/settings")) writes.push(request.url());
  });
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh");
    localStorage.setItem("fm-theme", "light");
    localStorage.setItem("fm-collection-layout", "grid");
  });
  await page.addInitScript(installMotionProbe);
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await page.route("**/admin/settings/models", route => route.fulfill({ json: {
    default_model: "synthetic/fast", warning: "", models: [
      { id: "synthetic/fast", label: "合成演示 · 快速模型", source: "fixture" },
      { id: "synthetic/careful", label: "合成演示 · 详细模型", source: "fixture" },
    ],
  } }));
  try {
    await page.goto("/app");
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator(".result-row")).toHaveCount(30);
    const header = page.locator(".app-header");
    let step = await record(page, evidence, "收藏 → 任务", [".page-scroll", ".app-header .selection-pill"],
      () => header.getByRole("button", { name: "任务", exact: true }).click());
    expectContentMotion(step, ".page-scroll", 1);
    step = await record(page, evidence, "任务 → 设置，快速往返后停在设置", [".page-scroll", ".app-header .selection-pill"], async () => {
      await header.getByRole("button", { name: "设置", exact: true }).click();
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await header.getByRole("button", { name: "任务", exact: true }).click();
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await header.getByRole("button", { name: "设置", exact: true }).click();
    });
    expectContentMotion(step, ".page-scroll");
    await expect(page.getByRole("heading", { name: "设置", exact: true })).toBeVisible();

    // The summary input can become an Agent picker after local discovery. The
    // embedding input remains available without changing the selected provider.
    const draft = page.locator('input[name="embed_model"]');
    await draft.fill("synthetic-unsaved-motion-draft");
    const visiblePanel = ".settings-panel:not([hidden])";
    step = await record(page, evidence, "设置标签保留草稿", [visiblePanel, ".settings-tabs .selection-pill"], async () => {
      await page.getByRole("tab", { name: "AI 连接", exact: true }).focus();
      await page.keyboard.press("ArrowRight");
    });
    expectContentMotion(step, visiblePanel, 1);
    await expect(page.getByRole("tab", { name: "设备同步", exact: true })).toBeFocused();
    await expect(draft).toBeHidden();
    step = await record(page, evidence, "键盘返回 AI 连接", [visiblePanel], () => page.keyboard.press("Home"));
    expectContentMotion(step, visiblePanel, -1);
    await expect(draft).toHaveValue("synthetic-unsaved-motion-draft");
    await expect(page.getByRole("tabpanel")).toHaveCount(1);

    const modelTrigger = page.locator(".model-embed .model-picker-trigger");
    step = await record(page, evidence, "打开模型目录", [".model-picker-menu"], () => modelTrigger.click());
    expectPaintedMotion(step, ".model-picker-menu");
    await expect(page.getByRole("combobox", { name: "搜索模型", exact: true })).toBeFocused();
    step = await record(page, evidence, "退出模型目录", [".model-picker-menu"], () => page.keyboard.press("Escape"));
    expectInertExit(step, ".model-picker-menu");
    await expect(page.locator(".model-picker-menu")).toHaveCount(0);
    await expect(modelTrigger).toBeFocused();

    step = await record(page, evidence, "设置 → 收藏", [".results-column"],
      () => header.getByRole("button", { name: "全部书签", exact: true }).click());
    expectContentMotion(step, ".results-column", -1);
    const categories = page.locator(".collection-sidebar");
    for (const name of ["标签", "文件夹"]) {
      step = await record(page, evidence, `分类切换：${name}`, [".collection-sidebar .facet-options"],
        () => categories.getByRole("button", { name, exact: true }).click());
      expectContentMotion(step, ".collection-sidebar .facet-options", name === "标签" ? 1 : -1);
      await expect(categories.locator(".facet-options")).toHaveAttribute("aria-busy", "false");
    }
    const bookmark = await page.locator(".result-row").nth(2).getAttribute("data-bookmark-id");
    const movingCard = `.result-row[data-bookmark-id="${bookmark}"]`;
    for (const name of ["列表视图", "卡片视图"]) {
      step = await record(page, evidence, `收藏布局：${name}`, [movingCard],
        () => page.getByRole("button", { name, exact: true }).first().click());
      expectPaintedMotion(step, movingCard, true);
    }

    step = await record(page, evidence, "按压反馈与打开新增收藏", [".interaction-ink", ".library-dialog"],
      () => page.getByRole("button", { name: "新增收藏", exact: true }).click());
    expectAnimation(step, ".interaction-ink");
    expectPaintedMotion(step, ".library-dialog");
    await expect(page.locator(".interaction-paint")).toHaveCSS("pointer-events", "none");
    const dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
    await dialog.getByRole("textbox", { name: "收藏网址", exact: true }).fill("https://motion-fixture.example/never-saved");
    const folderTrigger = dialog.locator(".folder-picker-trigger");
    step = await record(page, evidence, "打开完整文件夹目录", [".folder-picker-panel"], () => folderTrigger.click());
    expectPaintedMotion(step, ".folder-picker-panel");
    const folderSearch = dialog.getByRole("textbox", { name: "搜索文件夹", exact: true });
    await folderSearch.fill("synthetic-unsaved-folder");
    await folderSearch.press("Enter");
    await expect(dialog).toBeVisible();
    expect(writes).toEqual([]);
    step = await record(page, evidence, "Escape 只关闭文件夹目录", [".folder-picker-panel"], () => folderSearch.press("Escape"));
    expectInertExit(step, ".folder-picker-panel");
    await expect(dialog).toBeVisible();
    await expect(folderTrigger).toBeFocused();

    await record(page, evidence, "目录退出期间立即重开", [".folder-picker-panel"], async () => {
      await folderTrigger.press("Enter");
      await expect(folderSearch).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(dialog.locator(".folder-picker-panel")).toHaveAttribute("data-overlay-phase", "closing");
      await page.keyboard.press("Enter");
    });
    await expect(dialog.locator(".folder-picker-panel")).toHaveCount(1);
    await expect(dialog.locator(".folder-picker-panel")).not.toHaveAttribute("inert", "");
    await expect(folderSearch).toBeFocused();
    await folderSearch.press("Escape");
    step = await record(page, evidence, "关闭操作窗口并返回触发器", [".library-dialog", ".library-dialog-overlay"],
      () => folderTrigger.press("Escape"));
    expectInertExit(step, ".library-dialog");
    expectInertExit(step, ".library-dialog-overlay");
    await expect(page.locator(".library-dialog, .library-dialog-overlay")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "新增收藏", exact: true })).toBeFocused();

    await page.emulateMedia({ reducedMotion: "reduce" });
    step = await record(page, evidence, "实时减少动态效果", [".page-scroll", ".interaction-ink"],
      () => header.getByRole("button", { name: "设置", exact: true }).click());
    expect(nodes(step, ".page-scroll").flatMap(node => node.animations).some(animation => animation.state === "running")).toBe(false);
    expect(nodes(step, ".page-scroll").every(node => node.transform === "none" && node.filter === "none" && +node.opacity === 1)).toBe(true);
    await expect(page.locator(".interaction-ink")).toHaveCount(0);
    await page.getByRole("tab", { name: "设备同步", exact: true }).click();
    await expect(page.getByRole("tabpanel")).toHaveCount(1);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    step = await record(page, evidence, "实时恢复动态效果", [visiblePanel, ".interaction-ink"],
      () => page.getByRole("tab", { name: "AI 连接", exact: true }).click());
    expectContentMotion(step, visiblePanel, -1);
    expectAnimation(step, ".interaction-ink");
    await header.getByRole("button", { name: "全部书签", exact: true }).click();
    expect(errors).toEqual([]);
    expect(writes).toEqual([]);
  } finally {
    const report = JSON.stringify({ synthetic: true, errors, writes, evidence }, null, 2);
    await writeFile("recordings/facetmark-interactions.json", report);
    await testInfo.attach("interaction-motion-frames", { body: report, contentType: "application/json" });
    await context.close();
    await video?.saveAs("recordings/facetmark-interactions.webm");
  }
});
