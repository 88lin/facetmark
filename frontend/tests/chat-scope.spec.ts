import { expect, test, type Page } from "@playwright/test";

async function fixture(page: Page, count = 2) {
  const records = Array.from({ length: Math.min(count, 30) }, (_, index) => ({
    bookmark_id: 1001 + index, title: `Saved source ${index + 1}`, ai_title: `收藏内容 ${index + 1}`,
    url: `https://synthetic.invalid/${index}`, domain: "synthetic.invalid", folder: "scope",
    tags: [], summary: "用于讨论的合成收藏。", summary_status: "done",
  }));
  const scopes: Record<string, unknown>[] = [], created: Record<string, unknown>[] = [];
  let conversation: Record<string, unknown> | null = null;
  await page.route("**/bookmarks?**", route => route.fulfill({ json: {
    items: records, total: count, offset: 0, limit: 30, has_more: count > 30,
    summary_counts: { total: count, done: count, failed: 0, pending: 0 },
  } }));
  await page.route("**/chat/scopes/resolve", route => {
    scopes.push(route.request().postDataJSON());
    return route.fulfill({ json: { bookmark_ids: records.map(record => record.bookmark_id) } });
  });
  await page.route("**/chat/conversations**", route => {
    if (new URL(route.request().url()).pathname.endsWith("/messages")) {
      conversation = { ...conversation, running: false, messages: [
        { id: 1, role: "user", content: "一起讨论", sources: [], status: "complete", model: "", created_at: 1792886400 },
        { id: 2, role: "assistant", content: "来自两篇收藏的回答。", sources: [], status: "complete", model: "synthetic", created_at: 1792886400 },
      ] };
      return route.fulfill({ json: conversation });
    }
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON(); created.push(body);
      conversation = { id: "selected-conversation", title: body.title, bookmark_ids: body.bookmark_ids,
        running: false, created_at: 1792886400, updated_at: 1792886400, messages: [] };
      return route.fulfill({ json: conversation });
    }
    return route.fulfill({ json: conversation || { items: [], total: 0 } });
  });
  return { records, scopes, created };
}
test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => { localStorage.setItem("fm-language", "zh"); localStorage.removeItem("fm-chat-current"); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});
test("Discuss selected resolves the current select-all scope and keeps the existing toolbar", async ({ page }) => {
  const control = await fixture(page);
  await page.goto("/app");
  await expect(page.locator(".result-card")).toHaveCount(2);
  await page.getByRole("checkbox", { name: "全选当前结果", exact: true }).check();
  await page.locator(".library-manage > summary").click();
  await page.getByRole("button", { name: "聊所选", exact: true }).click();
  await expect(page.locator(".chat-workspace")).toBeVisible();
  await expect(page.locator(".chat-context")).toContainText("讨论所选 2 篇收藏");
  expect(control.scopes).toHaveLength(1);
  expect(control.scopes[0]).toEqual({ scope: { q: "", status: "all", exclude_ids: [] } });
  await page.locator(".chat-composer textarea").fill("一起讨论");
  await page.locator(".chat-composer").getByRole("button", { name: "发送问题", exact: true }).click();
  await expect.poll(() => control.created[0]?.bookmark_ids).toEqual([1001, 1002]);
  await expect(page.locator(".chat-message.assistant")).toContainText("来自两篇收藏的回答");
});
test("a large select-all keeps Discuss disabled while summary generation stays available", async ({ page }) => {
  await fixture(page, 21);
  await page.goto("/app");
  await page.getByRole("checkbox", { name: "全选当前结果", exact: true }).check();
  await page.locator(".library-manage > summary").click();
  await expect(page.getByRole("button", { name: "聊所选", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "生成摘要", exact: true })).toBeEnabled();
  await expect(page.locator(".library-summary-selection")).toHaveCount(1);
});
