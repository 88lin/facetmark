import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

async function preferences(page: Page, initial: Record<string, unknown> = {}) {
  const saved = { summary_language: "auto", summary_prompt: "", ...initial };
  const writes: Record<string, unknown>[] = [];
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      const values = route.request().postDataJSON().values;
      writes.push(values); Object.assign(saved, values);
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch(), data = await response.json();
    data.settings = data.settings.map((row: { key: string }) => row.key in saved
      ? { ...row, value: saved[row.key as keyof typeof saved] } : row);
    return route.fulfill({ response, json: data });
  });
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    data.demo = false; data.summary_language = saved.summary_language;
    data.channels = { ...data.channels, chat: { configured: true, tested: true } };
    return route.fulfill({ response, json: data });
  });
  return { saved, writes };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
});

test("built-in instructions can be edited, saved separately and restored without a connection test", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  const { saved, writes } = await preferences(page);
  let tested = 0;
  await page.route("**/admin/settings/test", route => {
    tested++; return route.fulfill({ json: { chat: { ok: true, model: "synthetic-model" } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".summary-preferences");
  await panel.locator(".summary-prompt-editor > summary").click();
  const prompt = panel.getByRole("textbox", { name: "摘要提示词", exact: true });
  await expect(prompt).toHaveValue(/中文标题、摘要和要点/);
  const builtIn = await prompt.inputValue();
  await prompt.fill("");
  await expect(prompt).toHaveValue("");
  const custom = "请突出具体做法和适用场景。\n保留 {必要的技术术语}，不要写空泛评价。";
  await prompt.fill(custom);
  await panel.getByRole("combobox", { name: "摘要目标语言", exact: true }).selectOption("zh");
  await panel.getByRole("button", { name: "保存摘要设置", exact: true }).click();
  await expect.poll(() => writes[0]).toEqual({ summary_language: "zh", summary_prompt: custom });
  await expect(panel.getByRole("button", { name: "保存摘要设置", exact: true })).toBeDisabled();
  expect(tested).toBe(0);
  await page.reload();
  await panel.locator(".summary-prompt-editor > summary").click();
  await expect(prompt).toHaveValue(custom);
  await panel.getByRole("button", { name: "恢复默认", exact: true }).click();
  await expect(prompt).toHaveValue(builtIn);
  await panel.getByRole("button", { name: "保存摘要设置", exact: true }).click();
  await expect.poll(() => saved.summary_prompt).toBe("");
  expect(writes[1]).toEqual({ summary_prompt: "" });
  expect(tested).toBe(0);
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(prompt).toBeVisible();
    await settleVisualLayout(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: "screenshots/collection-review/summary-prompt-" + width + ".png", animations: "disabled" });
  }
});

for (const [ui, target, expected] of [["zh", "auto", "zh"], ["en", "auto", "en"], ["en", "zh", "zh"]]) {
  test("generation uses target " + target + " with interface " + ui, async ({ page }) => {
    await page.addInitScript(language => localStorage.setItem("fm-language", language), ui);
    await preferences(page, { summary_language: target });
    let generated: Record<string, unknown> = {};
    await page.route("**/admin/jobs/preview", route => route.fulfill({ json: {
      total: 1, revision: "synthetic-language-scope", prompt_hash: "synthetic-language-prompt",
    } }));
    await page.route("**/admin/jobs/start", route => {
      generated = route.request().postDataJSON();
      return route.fulfill({ json: { id: "synthetic-language-summary", state: "done", params: generated } });
    });
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await page.getByRole("button", { name: ui === "zh" ? "生成摘要" : "Summarize", exact: true }).click();
    await expect.poll(() => generated).toEqual(expect.objectContaining({
      mode: "summarize", summary_language: expected, confirmed: true,
      preview_revision: "synthetic-language-scope", preview_prompt_hash: "synthetic-language-prompt",
    }));
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
}

test("semantic paging keeps actual selections and unselected generation skips completed items", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    return route.fulfill({ response, json: { ...data, demo: false, has_vectors: true,
      vector_compatible: true, pending_apply: false,
      channels: { ...data.channels, chat: { configured: true, tested: true }, embed: { configured: true, tested: true } },
    } });
  });
  const rows = Array.from({ length: 60 }, (_, index) => ({ bookmark_id: index + 10001,
    title: "Semantic result " + (index + 1), url: "https://synthetic.test/" + index,
    domain: "synthetic.test", folder: "", tags: [], summary: "A synthetic reading summary.",
    summary_basis: "body", privacy_skipped: false,
  }));
  const result = (offset: number) => ({ hits: rows.slice(offset, offset + 30), total: rows.length,
    offset, limit: 30, has_more: offset + 30 < rows.length, depth: 100 });
  await page.route("**/quick?**", route => route.fulfill({ json: result(Number(new URL(route.request().url()).searchParams.get("offset")) || 0) }));
  await page.route("**/search", route => route.fulfill({ json: result(route.request().postDataJSON().offset || 0) }));
  const starts: Record<string, unknown>[] = [];
  await page.route("**/admin/jobs/preview", route => route.fulfill({ json: {
    total: route.request().postDataJSON().bookmark_ids.length, revision: "synthetic-semantic-selection",
  } }));
  await page.route("**/admin/jobs/start", route => {
    const body = route.request().postDataJSON(); starts.push(body);
    return route.fulfill({ json: { state: "done", params: body } });
  });
  await page.goto("/app");
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("recoverable task");
  await page.getByRole("combobox", { name: "检索方式", exact: true }).selectOption("semantic");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(page.locator(".result-title").first()).toHaveText("Semantic result 1");
  await page.getByRole("button", { name: "生成摘要", exact: true }).click();
  await expect.poll(() => starts[0]).toEqual(expect.objectContaining({
    bookmark_ids: rows.slice(0, 30).map(row => row.bookmark_id), force: false,
  }));
  const selectAll = page.getByRole("checkbox", { name: "全选当前结果", exact: true });
  await expect(selectAll).toBeEnabled();
  await selectAll.check();
  const jump = page.getByRole("spinbutton", { name: "跳转页码", exact: true });
  await jump.fill("2"); await jump.press("Enter");
  await expect(page.locator(".result-title").first()).toHaveText("Semantic result 31");
  await expect(page.locator(".bookmark-check:checked")).toHaveCount(0);
  await expect(selectAll).not.toBeChecked();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 30");
  await selectAll.check();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 60");
  await expect(page.locator(".bookmark-check:checked")).toHaveCount(30);
  await page.getByRole("button", { name: "生成摘要", exact: true }).click();
  await expect.poll(() => starts[1]).toEqual(expect.objectContaining({
    bookmark_ids: rows.map(row => row.bookmark_id), force: true,
  }));
});

test("AI title, overview and key points share a reading panel with the unchanged source text", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/bookmarks?**", async route => {
    const response = await route.fetch(), data = await response.json();
    data.items[0].ai_title = "用 SQLite 保存可恢复的任务";
    return route.fulfill({ response, json: data });
  });
  let originalTitle = "";
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch(), record = await response.json();
    originalTitle = record.title;
    return route.fulfill({ response, json: { ...record, ai_title: "用 SQLite 保存可恢复的任务",
      summary: "把任务目标保存为快照，失败后只处理尚未完成的项目。",
      key_points: ["启动时保存目标快照。", "继续原任务时保留已完成项目。"],
      body_text: "## Durable tasks\n\nThis is the saved English source.\n\n## Resume\n\nKeep completed items.",
      indexed: { ...record.indexed, enriched_by: "synthetic-model", summary_basis: "body" },
    } });
  });
  await page.goto("/app");
  const first = page.locator(".result-row").first();
  await expect(first.locator(".result-title")).toHaveText("用 SQLite 保存可恢复的任务");
  await first.locator(".bookmark-preview").click();
  await expect(page.locator(".preview-title h1")).toHaveText("用 SQLite 保存可恢复的任务");
  await expect(page.locator(".reader-summary")).toContainText("把任务目标保存为快照");
  await expect(page.locator(".reader-summary li")).toHaveCount(2);
  await expect(page.locator(".reader-source .body-text")).toContainText("This is the saved English source.");
  await expect(page.locator(".preview-tabs [role=tab]")).toHaveCount(2);
  await expect(page.getByRole("tab", { name: "AI 摘要", exact: true })).toHaveCount(0);
  await page.locator(".article-details > summary").click();
  await expect(page.locator(".reader-original-title")).toContainText(originalTitle);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  const edit = page.getByRole("dialog", { name: "编辑收藏", exact: true });
  await expect(edit.getByRole("textbox", { name: "收藏标题", exact: true })).toHaveValue(originalTitle);
  await edit.getByRole("button", { name: "取消", exact: true }).click();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/summary-reading-unified.png", animations: "disabled" });
});
