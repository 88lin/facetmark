import { test, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
});

test("real library: stable paging, preview, filters and keyboard", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const first = await page.locator(".result-title").first().innerText();
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toContainText("synthetic content");
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator(".results-footer")).toContainText("31–60");
  await expect(page.locator(".result-title").first()).not.toHaveText(first);
  await page.getByRole("button", { name: "上一页", exact: true }).click();
  await expect(page.locator(".result-title").first()).toHaveText(first);
  await page.locator(".result-row").first().focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.locator(".result-row").nth(1)).toBeFocused();
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("textbox", { name: "搜索书签" })).toBeFocused();
  await page.getByRole("textbox", { name: "搜索书签" }).fill("SQLite");
  await expect(page.locator(".result-row").first()).toContainText("SQLite");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("textbox", { name: "搜索书签" })).toHaveValue("SQLite");
});

test("IME and stale responses cannot replace the current query", async ({ page }) => {
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  await expect(page.locator(".result-row")).toHaveCount(30);
  const queries: string[] = [];
  await page.route("**/quick?**", async (route) => {
    const q = new URL(route.request().url()).searchParams.get("q") || "";
    queries.push(q);
    if (q === "old") await new Promise((resolve) => setTimeout(resolve, 900));
    await route.fulfill({
      json: {
        hits: [
          {
            bookmark_id: q === "old" ? 1 : 2,
            title: q,
            url: "https://example.test",
            domain: "example.test",
          },
        ],
        total: 1,
        offset: 0,
        limit: 30,
        depth: 120,
        has_more: false,
      },
    });
  });
  await input.dispatchEvent("compositionstart");
  await input.fill("拼");
  await page.waitForTimeout(350);
  expect(queries).toEqual([]);
  await input.dispatchEvent("compositionend");
  await expect.poll(() => queries.length).toBe(1);
  await input.fill("old");
  await expect.poll(() => queries.includes("old")).toBe(true);
  await input.fill("new");
  await expect(page.locator(".result-title").first()).toHaveText("new");
  await page.waitForTimeout(1000);
  await expect(page.locator(".result-title").first()).toHaveText("new");
});

test("setup, separate model tests, consent and persistent tasks", async ({ page }) => {
  await page.goto("/app");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  const requests: string[] = [];
  await page.route("**/admin/settings/test", async (route) => {
    const data = route.request().postDataJSON();
    requests.push(data.channel);
    await route.fulfill({
      json: {
        ok: true,
        [data.channel]: { ok: true, model: "ci-model", ms: 8, dim: 32, dim_matches: true },
      },
    });
  });
  await page.locator("input[name=chat_base_url]").fill("http://127.0.0.1:11434/v1");
  await page.locator(".model-panel").first().getByRole("button", { name: "测试连接" }).click();
  await expect(page.locator(".test-result")).toContainText("连接成功");
  await page.locator(".model-panel").nth(1).getByRole("button", { name: "测试连接" }).click();
  expect(requests).toEqual(["chat", "embed"]);
  await page.getByRole("button", { name: "任务", exact: true }).click();
  const start = page.getByRole("button", { name: "开始索引", exact: true });
  await expect(start).toBeDisabled();
  await page.getByLabel("我已了解并确认开始处理").check();
  await page.getByLabel("先访问原网页，提取正文").uncheck();
  await expect(start).toBeEnabled();
  await start.click();
  await page.getByRole("button", { name: "全部书签", exact: false }).click();
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.locator(".tasks h2")).not.toHaveText("尚未开始");
});

test("import uses the real endpoint and survives a reload", async ({ page }) => {
  await page.goto("/app");
  await page.locator(".app-header").getByRole("button", { name: "导入书签", exact: true }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "synthetic.html",
    mimeType: "text/html",
    buffer: Buffer.from(
      '<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><DT><A HREF="https://import.example/unique">CI imported bookmark</A></DL>',
    ),
  });
  await expect(page.getByRole("status")).toContainText("导入完成");
  await page.getByRole("button", { name: "全部书签", exact: false }).click();
  await page.getByRole("textbox", { name: "搜索书签" }).fill("CI imported");
  await expect(page.locator(".result-row").first()).toContainText("CI imported bookmark");
  await page.reload();
  await expect(page.locator(".result-row").first()).toContainText("CI imported bookmark");
});

test("query suggestions and cited synthesis preserve the query", async ({ page }) => {
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  await input.fill("dom");
  await page.locator(".query-help summary").click();
  await page.getByRole("option", { name: "domain:", exact: true }).click();
  await expect(input).toHaveValue("domain:");
  await input.fill("SQLite");
  await expect(page.locator(".result-row").first()).toContainText("SQLite");
  await page.locator(".search-answer>summary").click();
  await page.getByRole("button", { name: "确认并生成回答" }).click();
  await expect(page.getByRole("button", { name: "查看来源 1" }).first()).toBeVisible();
  await page.getByRole("button", { name: "查看来源 1" }).first().click();
  await expect(page.locator(".preview-title h1")).toContainText("SQLite");
  await expect(input).toHaveValue("SQLite");
});

test("query menu supports keyboard insertion, Escape and a readable narrow layout", async ({
  page,
}) => {
  await mkdir("screenshots", { recursive: true });
  await page.setViewportSize({ width: 1440, height: 960 });
  const suggestions = [
    { label: "Architecture Notes", insert: "folder:Architecture Notes", detail: "12 saved" },
    { label: "Reading Queue", insert: "folder:Reading Queue", detail: "8 saved" },
    {
      label: "产品研究 / 知识整理与长文阅读体验 / 待继续阅读的参考资料",
      insert: "folder:产品研究 / 知识整理与长文阅读体验 / 待继续阅读的参考资料",
      detail: "用于验证长文件夹名称与真实建议说明的合成测试数据",
    },
    { label: "Reference Guides", insert: "folder:Reference Guides", detail: "6 saved" },
    { label: "Product Research", insert: "folder:Product Research", detail: "4 saved" },
    { label: "Writing Notes", insert: "folder:Writing Notes", detail: "3 saved" },
  ];
  const requests: { text: string; limit: number }[] = [];
  await page.route("**/suggest/query", async (route) => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({ json: { suggestions } });
  });
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  const trigger = page.locator(".query-help summary");
  const menu = page.locator(".query-suggestions-panel");
  const list = page.getByRole("listbox", { name: "可插入的检索条件" });
  await input.fill("SQLite folder:");
  await trigger.focus();
  await page.keyboard.press("ArrowDown");
  await expect(list).toBeFocused();
  await expect(list.getByRole("option")).toHaveCount(6);
  expect(requests[0]).toEqual({ text: "folder:", limit: 6 });
  await expect(
    list.getByRole("option", { name: "Architecture Notes", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  const second = list.getByRole("option", { name: "Reading Queue", exact: true });
  await expect(second).toHaveAccessibleDescription("8 saved");
  await page.keyboard.press("ArrowDown");
  await expect(second).toHaveAttribute("aria-selected", "true");
  await page.screenshot({ path: "screenshots/query-menu-zh-1440.png", animations: "disabled" });
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue('SQLite folder:"Reading Queue"');
  await expect(input).toBeFocused();
  await expect(menu).toHaveCount(0);

  await trigger.press("Enter");
  await expect(list).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await expect(input).toHaveValue('SQLite folder:"Reading Queue"');

  await page.setViewportSize({ width: 390, height: 960 });
  await input.fill("SQLite folder:");
  await trigger.click();
  await expect(list.getByRole("option")).toHaveCount(6);
  const box = await menu.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(await menu.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await page.screenshot({ path: "screenshots/query-menu-zh-390.png", animations: "disabled" });
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});

test("query suggestions expose request failures and recover through keyboard-ready retry", async ({
  page,
}) => {
  let attempts = 0;
  let release!: () => void;
  const retryResponse = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/suggest/query", async (route) => {
    attempts += 1;
    if (attempts === 1) {
      await route.fulfill({
        status: 503,
        json: { detail: "Synthetic suggestion service failure" },
      });
      return;
    }
    await retryResponse;
    await route.fulfill({
      json: {
        suggestions: [{ label: "domain:", insert: "domain:", detail: "Filter saved sites" }],
      },
    });
  });
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  await input.fill("dom");
  await page.locator(".query-help summary").click();
  const menu = page.locator(".query-suggestions-panel");
  const list = menu.getByRole("listbox");
  await expect(menu.getByRole("alert")).toContainText("暂时无法获取建议");
  await expect(list.getByRole("option")).toHaveCount(0);
  await expect(input).toHaveValue("dom");
  await menu.getByRole("button", { name: "重试", exact: true }).click();
  try {
    await expect(menu.getByRole("status")).toHaveText("正在查找建议…");
    await expect(list).toHaveAttribute("aria-busy", "true");
    await expect(list).toBeFocused();
  } finally {
    release();
  }
  await expect(list.getByRole("option", { name: "domain:", exact: true })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(menu.getByRole("alert")).toHaveCount(0);
  await expect(list).toHaveAttribute("aria-busy", "false");
  expect(attempts).toBe(2);
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue("domain:");
  await expect(input).toBeFocused();
});

test("query suggestions distinguish an empty response from a failed request", async ({ page }) => {
  await page.route("**/suggest/query", (route) => route.fulfill({ json: { suggestions: [] } }));
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  const trigger = page.locator(".query-help summary");
  await input.fill("SQLite folder:missing");
  await trigger.click();
  const menu = page.locator(".query-suggestions-panel");
  await expect(menu.getByRole("status")).toHaveText("没有匹配的建议，可以继续输入搜索。");
  await expect(menu.getByRole("option")).toHaveCount(0);
  await expect(menu.getByRole("alert")).toHaveCount(0);
  await expect(menu.getByRole("button", { name: "重试", exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await expect(input).toHaveValue("SQLite folder:missing");
});

test("folder suggestions preserve earlier terms and quote spaces without double quoting", async ({
  page,
}) => {
  const cases = [
    {
      label: "Reading Notes",
      insert: "-folder:Reading Notes",
      expected: 'SQLite -folder:"Reading Notes"',
    },
    {
      label: 'Reading "Later" Notes',
      insert: '-folder:Reading "Later" Notes',
      expected: 'SQLite -folder:"Reading \\"Later\\" Notes"',
    },
    {
      label: "Already Quoted",
      insert: '-folder:"Already Quoted"',
      expected: 'SQLite -folder:"Already Quoted"',
    },
  ];
  let current = cases[0];
  await page.route("**/suggest/query", (route) =>
    route.fulfill({
      json: {
        suggestions: [
          { label: current.label, insert: current.insert, detail: "Synthetic saved folder" },
        ],
      },
    }),
  );
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  for (const example of cases) {
    current = example;
    await input.fill("SQLite -folder:Re");
    await page.locator(".query-help summary").click();
    await page.getByRole("option", { name: example.label, exact: true }).click();
    await expect(input).toHaveValue(example.expected);
    await expect(input).toBeFocused();
    await expect(page.locator(".query-suggestions-panel")).toHaveCount(0);
  }
});

test("mobile navigation traps focus and restores it on Escape", async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  await page.setViewportSize({ width: 390, height: 960 });
  await page.goto("/app");
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  const trigger = page.getByRole("button", { name: "打开导航" });
  await trigger.click();
  await expect(page.getByRole("dialog", { name: "导航" })).toBeVisible();
  await expect(page.locator(".sidebar .brand")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator(".sidebar .language")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator(".sidebar .brand")).toBeFocused();
  await page.screenshot({
    path: "screenshots/fix-mobile-navigation.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
});

test("draft status, filtered emptiness and contextual request recovery", async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  await page.route("**/admin/setup-status", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.channels.chat.tested = true;
    data.channels.embed.tested = true;
    data.pending_apply = true;
    await route.fulfill({ json: data });
  });
  await page.goto("/app");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator(".model-panel").first().locator("header")).toContainText("已测试");
  await page.locator("input[name=chat_model]").fill("edited-model");
  await expect(page.locator(".model-panel").first().locator("header")).toContainText("尚未保存");
  await page.getByLabel("我确认备份并在需要时重建向量").check();
  await expect(page.getByRole("button", { name: "应用已测试的配置" })).toBeDisabled();
  await page.screenshot({ path: "screenshots/fix-model-draft.png", fullPage: true });
  await page.getByRole("button", { name: "全部书签", exact: false }).click();
  await page.route("**/bookmarks?**", (route) =>
    route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 30, has_more: false } }),
  );
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  await page.locator(".facet-nav .facet-option[title]").first().click();
  await expect(page.getByRole("button", { name: "清除条件，查看全部" })).toBeVisible();
  await expect(page.getByText("收藏，从这里汇合")).toHaveCount(0);
  await page.screenshot({
    path: "screenshots/fix-filter-empty.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.unroute("**/bookmarks?**");
  await page.getByRole("button", { name: "清除条件，查看全部" }).click();
  await page.route("**/bookmark/*/related", (route) =>
    route.fulfill({ status: 503, json: { detail: "Related temporarily unavailable" } }),
  );
  await page.locator(".result-row").first().click();
  await page.getByRole("tab", { name: "相关书签" }).click();
  await expect(page.getByRole("button", { name: "重试相关书签" })).toBeVisible();
  await expect(page.getByText("暂时无法读取相关书签", { exact: true })).toBeVisible();
  await expect(page.locator(".reading-progress-track")).toHaveCount(0);
  await page.screenshot({ path: "screenshots/fix-related-error.png", fullPage: true });
  await page.unroute("**/bookmark/*/related");
  await page.getByRole("button", { name: "重试相关书签" }).click();
  await expect(page.getByRole("button", { name: "重试相关书签" })).toHaveCount(0);
  await page.route("**/sessions?**", (route) =>
    route.fulfill({ status: 503, json: { detail: "Sessions temporarily unavailable" } }),
  );
  await page.getByRole("button", { name: "浏览批次", exact: true }).click();
  await expect(page.getByRole("button", { name: "重试浏览批次" })).toBeVisible();
  await expect(page.getByText("还没有浏览批次")).toHaveCount(0);
  await page.screenshot({ path: "screenshots/fix-sessions-error.png", fullPage: true });
  await page.unroute("**/sessions?**");
  await page.getByRole("button", { name: "重试浏览批次" }).click();
  await expect(page.getByRole("button", { name: "重试浏览批次" })).toHaveCount(0);
});

test("render matrix: Chinese, English, light, dark, desktop and narrow", async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  for (const language of ["zh", "en"])
    for (const theme of ["light", "dark"])
      for (const width of [1440, 1280, 1024, 390]) {
        await page.setViewportSize({ width, height: 960 });
        await page.addInitScript(
          ({ language, theme }) => {
            localStorage.setItem("fm-language", language);
            localStorage.setItem("fm-theme", theme);
          },
          { language, theme },
        );
        await page.goto("/app");
        await expect(page.locator(".result-row").first()).toBeVisible();
        await page
          .getByRole("textbox", { name: language === "zh" ? "搜索书签" : "Search bookmarks" })
          .fill("tag:demo");
        await expect(page.locator(".result-row").first()).not.toContainText("CI imported bookmark");
        if (width >= 1120)
          await page
            .locator(".result-row")
            .nth(language === "zh" ? 0 : 1)
            .click();
        if (width >= 1120) await expect(page.locator(".body-text")).toBeVisible();
        if (language === "zh" && theme === "light" && width === 1440) {
          const cdp = await page.context().newCDPSession(page);
          await cdp.send("DOM.enable");
          await cdp.send("CSS.enable");
          const { root } = await cdp.send("DOM.getDocument");
          const { nodeId } = await cdp.send("DOM.querySelector", {
            nodeId: root.nodeId,
            selector: ".body-text p",
          });
          const fonts = await cdp.send("CSS.getPlatformFontsForNode", { nodeId });
          const styles = await page.evaluate(() =>
            Object.fromEntries(
              ["body", ".result-title", ".result-meta", ".reading", ".preview-title h1"].map(
                (selector) => {
                  const element = document.querySelector(selector)!;
                  const style = getComputedStyle(element);
                  return [
                    selector,
                    {
                      family: style.fontFamily,
                      size: style.fontSize,
                      weight: style.fontWeight,
                      lineHeight: style.lineHeight,
                      color: style.color,
                      background: style.backgroundColor,
                    },
                  ];
                },
              ),
            ),
          );
          await writeFile(
            "screenshots/rendering-styles.json",
            JSON.stringify({ fonts, styles }, null, 2),
          );
          await cdp.detach();
        }
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        await page.screenshot({
          path: `screenshots/${language}-${theme}-${width}.png`,
          fullPage: true,
          animations: "disabled",
        });
        if (width === 390) {
          await page.locator(".result-row").first().click();
          await expect(page.getByRole("dialog")).toBeVisible();
          await page.keyboard.press("Escape");
          await expect(page.getByRole("dialog")).toHaveCount(0);
          await expect(page.locator(".result-row").first()).toBeFocused();
        }
      }
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto("/app");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(page.locator("input[name=chat_model]")).toBeVisible();
  await page.screenshot({
    path: "screenshots/settings-en-dark.png",
    fullPage: true,
    animations: "disabled",
  });
});
