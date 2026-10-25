import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import type { Conversation, ChatMessage } from "../src/chat-types";
import { settleVisualLayout } from "./visual-layout";

async function chatFixture(page: Page, options: { tested?: boolean; delayed?: boolean; seed?: boolean;
  delayRegistration?: boolean; delayedReplies?: number[]; failedReplies?: number[]; cancelFailure?: boolean; missingSources?: boolean } = {}) {
  const values = new Map<string, Conversation>();
  const created: Record<string, unknown>[] = [], sent: Record<string, unknown>[] = [];
  const cancelled: string[] = [], deleted: string[] = [];
  const cancelRequests: { id: string; request_id?: string }[] = [], generated: string[] = [];
  const registrationOrder: string[] = [];
  let count = 0, messageId = 0, sourceId = 1;
  const waiting = new Map<string, () => void>();
  const registering = new Map<string, { requestId: string; resolve: () => void }>();
  const activeRequests = new Map<string, string>(), cancelIntents = new Map<string, Set<string>>();
  const now = 1792886400;
  const make = (id: string, title: string, bookmark_ids: number[] = []): Conversation => ({
    id, title, bookmark_ids, created_at: now, updated_at: now, running: false, messages: [],
  });
  if (options.seed) {
    const saved = make("saved-chat", "已保存的任务讨论");
    saved.messages = [
      { id: ++messageId, role: "user", content: "怎样保存任务进度？", status: "complete", sources: [], model: "", created_at: now },
      { id: ++messageId, role: "assistant", content: "将任务目标保存为快照，并保留完成状态。[1]", status: "complete",
        sources: [{ n: 1, bookmark_id: sourceId, title: "Saved source", ai_title: "用 SQLite 保存可恢复的任务", url: "https://synthetic.test/tasks", basis: "body" }],
        model: "synthetic-chat", created_at: now },
    ];
    if (options.missingSources) {
      saved.messages[1].sources = [{ ...saved.messages[1].sources[0], bookmark_id: null,
        source_hash: "synthetic-removed-source", content_updated_at: now },
      { n: 2, bookmark_id: null, title: "已移除的第二篇收藏", url: "https://synthetic.invalid/removed-source", basis: "body" }];
      saved.messages[1].content += "\n\n第二个来源也已不在书库中。[2]";
    }
    values.set(saved.id, saved);
  }
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    return route.fulfill({ response, json: { ...data, demo: false,
      channels: { ...data.channels, chat: { configured: true, tested: options.tested !== false } },
    } });
  });
  await page.route("**/bookmark/*?body=true", async route => {
    const match = /\/bookmark\/(\d+)/.exec(route.request().url());
    if (match) sourceId = Number(match[1]);
    return route.continue();
  });
  await page.route(/\/chat\/conversations(?:\/|\?|$)/, async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const id = path.split("/")[3], action = path.split("/")[4];
    if (path === "/chat/conversations" && request.method() === "GET") {
      const offset = Number(new URL(request.url()).searchParams.get("offset")) || 0;
      return route.fulfill({ json: { items: [...values.values()].slice(offset, offset + 50)
        .map(value => ({ ...value, messages: undefined, message_count: value.messages.length })), total: values.size } });
    }
    if (path === "/chat/conversations" && request.method() === "POST") {
      const body = request.postDataJSON(); created.push(body);
      const value = make("chat-" + ++count, body.title, body.bookmark_ids || []);
      values.set(value.id, value);
      return route.fulfill({ json: value });
    }
    const value = values.get(id);
    if (!value) return route.fulfill({ status: 404, json: { detail: "No such conversation" } });
    if (!action && request.method() === "GET") return route.fulfill({ json: value });
    if (!action && request.method() === "DELETE") {
      deleted.push(id); values.delete(id);
      return route.fulfill({ json: { ok: true } });
    }
    if (action === "cancel") {
      const body = request.postDataJSON(), requestId: string | undefined = body?.request_id;
      cancelRequests.push({ id, request_id: requestId });
      if (options.cancelFailure && cancelRequests.length === 1)
        return route.fulfill({ status: 503, json: { detail: "Cancel service unavailable" } });
      if (requestId) {
        const intents = cancelIntents.get(id) || new Set<string>();
        intents.add(requestId); cancelIntents.set(id, intents);
      }
      cancelled.push(id); registrationOrder.push("cancel:" + requestId);
      if (!requestId || activeRequests.get(id) === requestId) {
        const last = value.messages.at(-1);
        if (last?.status === "pending" && (!requestId || last.request_id === requestId)) {
          last.status = "cancelled"; last.content = "回答已停止，可以重试这个问题。";
          value.running = false;
          waiting.get(id)?.(); waiting.delete(id);
        }
      }
      const deferred = registering.get(id);
      if (deferred && (!requestId || deferred.requestId === requestId)) {
        deferred.resolve(); registering.delete(id);
        await Promise.resolve();
      }
      return route.fulfill({ json: { cancelled: true } });
    }
    if (action === "messages") {
      const body = request.postDataJSON(); sent.push(body);
      const sequence = sent.length;
      if (options.delayRegistration && sequence === 1)
        await new Promise<void>(resolve => registering.set(id, { requestId: body.request_id, resolve }));
      registrationOrder.push("messages:" + body.request_id);
      if (!body.retry && !body.regenerate) value.messages.push({ id: ++messageId, role: "user", content: body.text,
        status: "complete", sources: [], model: "", created_at: now, request_id: body.request_id });
      const assistant: ChatMessage = body.retry ? value.messages.at(-1)! : { id: ++messageId,
        role: "assistant", content: "", status: "pending", sources: [], model: "synthetic-chat", created_at: now };
      assistant.request_id = body.request_id; assistant.content = ""; assistant.sources = [];
      assistant.status = "pending"; value.running = true;
      if (!body.retry) value.messages.push(assistant);
      if (cancelIntents.get(id)?.has(body.request_id)) {
        assistant.status = "cancelled"; assistant.content = "回答已停止，可以重试这个问题。";
        value.running = false;
        try { return await route.fulfill({ json: value }); }
        catch { return; /* Stop can abort the response after cancellation was accepted. */ }
      }
      activeRequests.set(id, body.request_id); generated.push(body.request_id);
      if ((options.delayed && sequence === 1) || options.delayedReplies?.includes(sequence)) {
        await new Promise<void>(resolve => waiting.set(id, resolve));
      }
      if (value.messages.find(message => message.id === assistant.id)?.status !== "cancelled") {
        assistant.status = options.failedReplies?.includes(sequence) ? "error" : "complete";
        assistant.content = assistant.status === "error" ? "Synthetic reply could not complete. Please retry."
          : body.regenerate ? "重新回答：从新的保存片段整理任务步骤。[1]" : body.retry ? "已重新整理：保存目标快照，继续未完成项目。[1]"
          : sequence > 1 ? "继续上一个问题：恢复时保留已完成的状态。[1]" : "**关键方法**：保存目标快照，再继续未完成的项目。[1]";
        assistant.sources = assistant.status === "error" ? [] : [{ n: 1, bookmark_id: sourceId, title: "Saved source",
          ai_title: "用 SQLite 保存可恢复的任务", url: "https://synthetic.test/tasks", basis: "body" }];
      }
      if (activeRequests.get(id) === body.request_id) { activeRequests.delete(id); value.running = false; }
      try { return await route.fulfill({ json: value }); } catch { /* Explicit Stop aborts the long response. */ }
    }
    return route.fulfill({ status: 404, json: { detail: "Unknown chat action" } });
  });
  return { values, created, sent, cancelled, deleted, cancelRequests, generated, registrationOrder,
    finish: (id: string) => waiting.get(id)?.() };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("reader chat sends once, keeps follow-up drafts through navigation and restores cited history", async ({ page }) => {
  const fixture = await chatFixture(page);
  await page.goto("/app");
  await page.locator(".bookmark-preview").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.getByRole("button", { name: "聊这篇", exact: true }).click();
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeVisible();
  expect(fixture.created).toHaveLength(0);
  await question.fill("如何保存可恢复任务？");
  await question.dispatchEvent("keydown", { key: "Enter", isComposing: true, keyCode: 229 });
  expect(fixture.sent).toHaveLength(0);
  await question.press("Enter");
  await expect(page.locator(".chat-message.assistant")).toContainText("保存目标快照");
  expect(fixture.created).toHaveLength(1);
  expect(fixture.created[0].bookmark_ids).toHaveLength(1);
  expect(fixture.sent).toHaveLength(1);
  expect(fixture.sent[0]).toEqual(expect.objectContaining({ text: "如何保存可恢复任务？", language: "zh", request_id: expect.any(String) }));
  await question.fill("下一步该注意什么？");
  await page.getByRole("button", { name: "返回收藏", exact: true }).click();
  await page.locator(".header-navigation").getByRole("button", { name: "AI 对话", exact: true }).click();
  await expect(question).toHaveValue("下一步该注意什么？");
  await question.press("End"); await question.press("Shift+Enter");
  await question.press("a");
  await question.press("Enter");
  await expect(page.locator(".chat-message.user")).toHaveCount(2);
  await expect(page.locator(".chat-message.assistant").last()).toContainText("恢复时保留");
  expect(fixture.sent[1].text).toBe("下一步该注意什么？\na");
  await page.getByRole("button", { name: "查看引用：用 SQLite 保存可恢复的任务", exact: true }).last().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.locator(".header-navigation").getByRole("button", { name: "AI 对话", exact: true }).click();
  await page.reload();
  await expect(page.locator(".chat-message.user")).toHaveCount(2);
  await expect(page.locator(".chat-message.assistant").last()).toContainText("恢复时保留");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/chat-reading-1280.png", animations: "disabled" });
  for (const size of [{ width: 390, height: 844 }, { width: 320, height: 640 }]) {
    await page.setViewportSize(size); await settleVisualLayout(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const bounds = await page.locator(".chat-workspace").evaluate(element => {
      const area = element.querySelector(".chat-messages")!.getBoundingClientRect();
      const composer = element.querySelector(".chat-composer")!.getBoundingClientRect();
      return { messagesBottom: area.bottom, composerTop: composer.top, composerBottom: composer.bottom, height: innerHeight };
    });
    expect(bounds.messagesBottom).toBeLessThanOrEqual(bounds.composerTop);
    expect(bounds.composerBottom).toBeLessThanOrEqual(bounds.height);
    await page.screenshot({ path: "screenshots/collection-review/chat-reading-" + size.width + ".png", animations: "disabled" });
  }
});

test("background generation can be reopened, stopped and retried without duplicating the question", async ({ page }) => {
  const fixture = await chatFixture(page, { delayed: true });
  await page.goto("/app#chat");
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeEnabled();
  await question.fill("第一个问题"); await question.press("Enter");
  await expect(page.getByRole("button", { name: "停止生成", exact: true })).toBeVisible();
  await expect.poll(() => fixture.sent.length).toBe(1);
  await page.getByRole("button", { name: "新对话", exact: true }).click();
  await question.fill("另一个问题"); await question.press("Enter");
  await expect(page.locator(".chat-message.user")).toHaveText(/另一个问题/);
  await expect(page.locator(".chat-message.assistant")).toContainText("恢复时保留");
  await page.getByRole("button", { name: "历史", exact: true }).click();
  const history = page.getByRole("dialog", { name: "对话历史", exact: true });
  await history.locator(".chat-history-open").filter({ hasText: "第一个问题" }).click();
  await expect(page.getByRole("button", { name: "停止生成", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "停止生成", exact: true }).click();
  await expect(page.getByRole("button", { name: "重试回答", exact: true })).toBeVisible();
  expect(fixture.cancelled).toEqual(["chat-1"]);
  await page.getByRole("button", { name: "重试回答", exact: true }).click();
  await expect(page.locator(".chat-message.assistant")).toContainText("已重新整理");
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  expect(fixture.sent.at(-1)?.retry).toBe(true);
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/chat-retry-dark.png", animations: "disabled" });
});

test("a finishing reply preserves the next draft typed while it was running", async ({ page }) => {
  const fixture = await chatFixture(page, { delayed: true });
  await page.goto("/app#chat");
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeEnabled();
  await question.fill("先回答这个问题"); await question.press("Enter");
  await expect.poll(() => fixture.sent.length).toBe(1);
  await question.fill("我准备接着问这个问题");
  fixture.finish("chat-1");
  await expect(page.locator(".chat-message.assistant")).toContainText("保存目标快照");
  await expect(question).toHaveValue("我准备接着问这个问题");
});

test("stop before message registration uses its request ID and an old cancel cannot stop a new question", async ({ page }) => {
  const fixture = await chatFixture(page, { delayRegistration: true, delayedReplies: [2] });
  await page.goto("/app#chat");
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeEnabled();
  await question.fill("在登记之前停止这个问题"); await question.press("Enter");
  await expect.poll(() => fixture.sent.length).toBe(1);
  expect(fixture.values.get("chat-1")?.messages).toHaveLength(0);
  await page.getByRole("button", { name: "停止生成", exact: true }).click();
  await expect(page.getByRole("button", { name: "重试回答", exact: true })).toBeVisible();
  const firstId = fixture.sent[0].request_id as string;
  expect(fixture.cancelRequests[0]).toEqual({ id: "chat-1", request_id: firstId });
  expect(fixture.registrationOrder).toEqual(["cancel:" + firstId, "messages:" + firstId]);
  expect(fixture.generated).toHaveLength(0);
  await expect(page.locator(".chat-message.user")).toHaveText("在登记之前停止这个问题");
  await expect(page.locator(".chat-message.assistant")).toHaveAttribute("data-status", "cancelled");

  await question.fill("这是一个新的问题"); await question.press("Enter");
  await expect.poll(() => fixture.sent.length).toBe(2);
  const secondId = fixture.sent[1].request_id as string;
  expect(secondId).not.toBe(firstId);
  await expect(page.locator(".chat-message.assistant").last()).toHaveAttribute("data-status", "pending");
  // Repeat an old cancellation after the next question starts, as a delayed
  // request or another window could do. It must remain scoped to its old ID.
  await page.evaluate(async requestId => {
    const response = await fetch("/chat/conversations/chat-1/cancel", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: requestId }) });
    if (!response.ok) throw new Error("Synthetic stale cancellation failed");
    return response.json();
  }, firstId);
  expect(fixture.values.get("chat-1")?.running).toBe(true);
  await expect(page.locator(".chat-message.assistant").last()).toHaveAttribute("data-status", "pending");
  fixture.finish("chat-1");
  await expect(page.locator(".chat-message.assistant").last()).toContainText("恢复时保留");
  await expect(page.locator(".chat-message.assistant").first()).toHaveAttribute("data-status", "cancelled");
  expect(fixture.generated).toEqual([secondId]);
  await expect(page.locator(".chat-message.user")).toHaveCount(2);
});

test("a restored running conversation retains its request ID and a failed stop keeps generation active", async ({ page }) => {
  const fixture = await chatFixture(page, { delayed: true, cancelFailure: true });
  await page.goto("/app#chat");
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeEnabled();
  await question.fill("刷新后仍然能够停止这个问题"); await question.press("Enter");
  await expect.poll(() => fixture.sent.length).toBe(1);
  const requestId = fixture.sent[0].request_id as string;
  await page.reload();
  await expect(page.locator(".chat-message.assistant")).toHaveAttribute("data-status", "pending");
  const stop = page.getByRole("button", { name: "停止生成", exact: true });
  await expect(stop).toBeEnabled(); await stop.click();
  await expect(page.locator(".chat-feedback")).toContainText("Cancel service unavailable");
  await expect(stop).toBeEnabled();
  await expect(page.locator(".chat-message.assistant")).toHaveAttribute("data-status", "pending");
  expect(fixture.values.get("chat-1")?.running).toBe(true);
  expect(fixture.cancelRequests[0]).toEqual({ id: "chat-1", request_id: requestId });
  await expect(page.getByRole("button", { name: "重试回答", exact: true })).toHaveCount(0);

  await stop.click();
  await expect(page.getByRole("button", { name: "重试回答", exact: true })).toBeVisible();
  expect(fixture.cancelRequests[1]).toEqual({ id: "chat-1", request_id: requestId });
  expect(fixture.values.get("chat-1")?.running).toBe(false);
  await expect(page.locator(".chat-message.assistant")).toHaveAttribute("data-status", "cancelled");
  await expect(page.locator(".chat-feedback")).toHaveCount(0);
});

test("missing models lead to settings and deleting history requires confirmation", async ({ page }) => {
  const fixture = await chatFixture(page, { tested: false, seed: true });
  await page.addInitScript(() => localStorage.setItem("fm-chat-current", "saved-chat"));
  await page.goto("/app#chat");
  await expect(page.getByRole("textbox", { name: "对收藏提问", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "设置 AI 连接", exact: true })).toBeVisible();
  await expect(page.locator(".chat-message.assistant")).toContainText("将任务目标保存为快照");
  await page.getByRole("button", { name: "历史", exact: true }).click();
  const history = page.getByRole("dialog", { name: "对话历史", exact: true });
  await history.getByRole("button", { name: "删除对话：已保存的任务讨论", exact: true }).click();
  const confirm = page.getByRole("dialog", { name: "删除这段对话？", exact: true });
  await confirm.getByRole("button", { name: "取消", exact: true }).click();
  expect(fixture.deleted).toHaveLength(0);
  await history.getByRole("button", { name: "删除对话：已保存的任务讨论", exact: true }).click();
  await confirm.getByRole("button", { name: "删除对话", exact: true }).click();
  await expect(confirm).toHaveCount(0);
  expect(fixture.deleted).toEqual(["saved-chat"]);
  await page.getByRole("button", { name: "设置 AI 连接", exact: true }).click();
  await expect(page.locator(".model-chat")).toBeVisible();
  expect(fixture.sent).toHaveLength(0);
});

test("removed citation records disable preview while preserving original URLs and separate source keys", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
  await chatFixture(page, { seed: true, missingSources: true });
  await page.addInitScript(() => localStorage.setItem("fm-chat-current", "saved-chat"));
  await page.goto("/app#chat");
  const sources = page.locator(".chat-source");
  await expect(sources).toHaveCount(2);
  await expect(sources.nth(0).getByRole("button")).toBeDisabled();
  await expect(sources.nth(1).getByRole("button")).toBeDisabled();
  await expect(page.locator(".chat-citation")).toHaveCount(2);
  for (const citation of await page.locator(".chat-citation").all()) await expect(citation).toBeDisabled();
  await expect(sources.nth(0).getByRole("link")).toHaveAttribute("href", "https://synthetic.test/tasks");
  await expect(sources.nth(1).getByRole("link")).toHaveAttribute("href", "https://synthetic.invalid/removed-source");
  await sources.nth(1).getByRole("link").focus();
  await expect(sources.nth(1).getByRole("link")).toBeFocused();
  expect(consoleErrors.filter(value => /same key|unique.*key|Encountered two children/i.test(value))).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 }); await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/chat-missing-sources.png", animations: "disabled" });
});

test("answer again keeps old replies and drafts through cancellation, failed retry and another regeneration", async ({ page }) => {
  const fixture = await chatFixture(page, { delayedReplies: [2], failedReplies: [3] });
  await page.goto("/app#chat");
  const question = page.getByRole("textbox", { name: "对收藏提问", exact: true });
  await expect(question).toBeEnabled();
  await question.fill("先整理这个任务"); await question.press("Enter");
  await expect(page.locator(".chat-message.assistant")).toContainText("保存目标快照");
  await question.fill("我还想接着问这个问题");
  const regenerate = page.getByRole("button", { name: "重新回答", exact: true });
  await regenerate.focus(); await regenerate.press("Enter");
  await expect.poll(() => fixture.sent.length).toBe(2);
  expect(fixture.sent[1]).toEqual(expect.objectContaining({ regenerate: true, language: "zh", request_id: expect.any(String) }));
  expect(fixture.sent[1].text).toBeUndefined();
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await expect(page.locator(".chat-message.assistant")).toHaveCount(2);
  await expect(page.locator(".chat-message.assistant").first()).toContainText("保存目标快照");
  await page.getByRole("button", { name: "停止生成", exact: true }).click();
  await expect(page.getByRole("button", { name: "重试回答", exact: true })).toBeVisible();
  await expect(regenerate).toHaveCount(0);
  expect(fixture.cancelRequests[0].request_id).toBe(fixture.sent[1].request_id);
  await page.getByRole("button", { name: "重试回答", exact: true }).click();
  await expect(page.locator(".chat-message.assistant").last()).toHaveAttribute("data-status", "error");
  await expect(page.locator(".chat-message.assistant").first()).toContainText("保存目标快照");
  await expect(question).toHaveValue("我还想接着问这个问题");
  await page.getByRole("button", { name: "重试回答", exact: true }).click();
  await expect(page.locator(".chat-message.assistant").last()).toContainText("已重新整理");
  await regenerate.click();
  await expect(page.locator(".chat-message.assistant").last()).toContainText("重新回答：从新的保存片段");
  await expect(page.locator(".chat-message.assistant")).toHaveCount(3);
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await expect(question).toHaveValue("我还想接着问这个问题");
  expect(fixture.sent.filter(value => value.regenerate)).toHaveLength(2);
  expect(new Set(fixture.sent.map(value => value.request_id)).size).toBe(5);
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" }); await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/chat-regenerated-dark.png", animations: "disabled" });
});
