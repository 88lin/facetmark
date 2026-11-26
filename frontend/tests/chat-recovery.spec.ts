import { expect, test as base, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import type { Conversation } from "../src/chat-types";
import type { ModelProfile } from "../src/ModelProfiles";
import { settleVisualLayout } from "./visual-layout";

type Owned = { headers: Record<string, string>; ids: Set<string> };
const test = base.extend<{ owned: Owned }>({
  owned: async ({ request }, use) => {
    const boot = await request.get("/app/boot");
    expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<string>();
    await use({ headers, ids });
    for (const id of ids) {
      await request.post(`/chat/conversations/${id}/cancel`, { headers, data: {} });
      expect([200, 404]).toContain((await request.delete(`/chat/conversations/${id}`, { headers })).status());
    }
  },
});

async function realRecovery(page: Page, owned: Owned) {
  const control = { creations: [] as Record<string, unknown>[], messages: [] as Record<string, unknown>[],
    lostCreation: false, lostMessage: false, failReads: false, creationWait: null as Promise<void> | null };
  await page.route(/\/chat\/conversations\/[^/?]+(?:\?[^#]*)?$/, route => {
    if (route.request().method() === "GET" && control.failReads)
      return route.fulfill({ status: 503, json: { detail: "Synthetic conversation read failure" } });
    return route.continue();
  });
  await page.route("**/chat/conversations", async route => {
    if (route.request().method() !== "POST") return route.continue();
    control.creations.push(route.request().postDataJSON());
    const response = await route.fetch(), value = await response.json() as Conversation;
    expect(response.ok()).toBeTruthy(); owned.ids.add(value.id);
    if (control.creationWait) await control.creationWait;
    if (control.lostCreation) { control.lostCreation = false; return route.abort("failed"); }
    return route.fulfill({ response });
  });
  await page.route(/\/chat\/conversations\/[^/?]+\/messages$/, async route => {
    control.messages.push(route.request().postDataJSON());
    const response = await route.fetch(); expect(response.ok()).toBeTruthy();
    if (control.lostMessage) { control.lostMessage = false; return route.abort("failed"); }
    return route.fulfill({ response });
  });
  return control;
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
});

test("a draft written before the connection is ready stays unsent until an explicit send", async ({ page, owned }) => {
  const control = await realRecovery(page, owned);
  let release!: () => void;
  const ready = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch();
    await ready;
    return route.fulfill({ response });
  });
  try {
    await page.goto("/app#chat");
    const question = page.locator("#chat-question");
    const send = page.getByRole("button", { name: "发送问题", exact: true });
    await question.fill("连接读取完成前先保留这个问题");
    await expect(send).toBeDisabled();
    await expect(page.locator(".chat-connection-notice")).toHaveText("正在读取已保存的聊天连接，草稿会保留。");
    await expect(page.locator(".chat-connection-notice").getByRole("button", { name: "设置 AI 连接", exact: true })).toHaveCount(0);
    await question.press("Enter");
    await expect(question).toHaveValue("连接读取完成前先保留这个问题");
    expect(control.creations).toHaveLength(0); expect(control.messages).toHaveLength(0);
    release();
    await expect(send).toBeEnabled();
    expect(control.creations).toHaveLength(0); expect(control.messages).toHaveLength(0);
    await send.click();
    await expect(page.locator(".chat-message.assistant")).toBeVisible();
    await expect(page.locator(".chat-message.assistant")).not.toHaveAttribute("data-status", "pending");
    await expect(page.locator(".chat-message.user")).toHaveText(/连接读取完成前先保留这个问题/);
    expect(control.creations).toHaveLength(1); expect(control.messages).toHaveLength(1);
  } finally { release(); }
});

test("a lost creation response retains its exact send and selected page through refresh", async ({ page, owned }) => {
  const control = await realRecovery(page, owned);
  control.lostCreation = true; control.failReads = true;
  let release!: () => void;
  control.creationWait = new Promise(resolve => { release = resolve; });
  await page.goto("/app");
  await page.locator(".bookmark-preview").first().click();
  await page.getByRole("button", { name: "聊这篇", exact: true }).click();
  const question = page.locator("#chat-question");
  await question.fill("先整理这篇收藏的结论");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  try {
    await question.press("Enter");
    await expect.poll(() => owned.ids.size).toBe(1);
    await question.fill("发送期间准备好的下一问");
  } finally { release(); control.creationWait = null; }
  await expect(page.locator(".chat-delivery-recovery")).toBeVisible();
  expect(control.messages).toHaveLength(0);
  const original = control.creations[0];
  expect(original.bookmark_ids).toHaveLength(1);
  expect(original.profile_id).toBe("");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "切换语言", exact: true }).click();
  await page.reload();
  await expect(question).toHaveValue("发送期间准备好的下一问");
  await expect(page.locator(".chat-delivery-recovery")).toBeVisible();
  expect(control.creations).toHaveLength(1); expect(control.messages).toHaveLength(0);
  const local = await page.evaluate(() => JSON.parse(localStorage.getItem("fm-chat-drafts")!));
  expect(local.scope.bookmark_ids).toEqual(original.bookmark_ids);
  expect(Object.values(local.operations)[0]).toEqual(expect.objectContaining({ text: "先整理这篇收藏的结论", language: "zh" }));
  control.failReads = false;
  const retry = page.getByRole("button", { name: "Retry submission", exact: true });
  await retry.focus(); await retry.press("Enter");
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await expect(page.locator(".chat-message.assistant")).not.toHaveAttribute("data-status", "pending");
  await expect(page.locator(".chat-delivery-recovery")).toHaveCount(0);
  expect(control.creations).toHaveLength(2); expect(control.creations[1]).toEqual(original);
  expect(control.messages).toHaveLength(1);
  expect(control.messages[0]).toEqual(expect.objectContaining({ text: "先整理这篇收藏的结论", language: "zh", profile_id: "" }));
  await expect(question).toHaveValue("发送期间准备好的下一问");
  const saved = await page.request.get(`/chat/conversations/${original.id}`, { headers: owned.headers });
  expect((await saved.json()).bookmark_ids).toEqual(original.bookmark_ids);
  await page.reload();
  await expect(question).toHaveValue("发送期间准备好的下一问");
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  expect(control.creations).toHaveLength(2); expect(control.messages).toHaveLength(1);
});

test("reading a lost message receipt after refresh confirms the answer without another POST", async ({ page, owned }) => {
  const control = await realRecovery(page, owned);
  control.lostMessage = true; control.failReads = true;
  await page.goto("/app#chat");
  const question = page.locator("#chat-question");
  await question.fill("只发送一次的问题");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await question.press("Enter");
  await expect(page.locator(".chat-delivery-recovery")).toBeVisible();
  await question.fill("未提交的下一问");
  await page.reload();
  await expect(page.locator(".chat-read-failure")).toBeVisible();
  await expect(question).toHaveValue("未提交的下一问");
  expect(control.messages).toHaveLength(1);
  control.failReads = false;
  await page.locator(".chat-delivery-recovery").getByRole("button", { name: "重新读取对话", exact: true }).click();
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await expect(page.locator(".chat-message.user")).toContainText("只发送一次的问题");
  await expect(page.locator(".chat-message.assistant")).not.toHaveAttribute("data-status", "pending");
  await expect(page.locator(".chat-delivery-recovery")).toHaveCount(0);
  await expect(question).toHaveValue("未提交的下一问");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  expect(control.creations).toHaveLength(1); expect(control.messages).toHaveLength(1);
});

test("failed initial and cached history reads preserve drafts and expose a working reload", async ({ page, owned }) => {
  const response = await page.request.post("/chat/conversations", { headers: owned.headers, data: { title: "重新读取的对话" } });
  expect(response.ok()).toBeTruthy();
  const saved = await response.json() as Conversation; owned.ids.add(saved.id);
  expect((await page.request.post(`/chat/conversations/${saved.id}/messages`, { headers: owned.headers,
    data: { text: "保留这条已经发送的问题", request_id: "initial-read-question" } })).ok()).toBeTruthy();
  await page.addInitScript(id => localStorage.setItem("fm-chat-current", id), saved.id);
  const control = await realRecovery(page, owned); control.failReads = true;
  await page.goto("/app#chat");
  await expect(page.locator(".chat-read-failure")).toBeVisible();
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeDisabled();
  control.failReads = false;
  await page.locator(".chat-read-failure").getByRole("button", { name: "重新读取对话", exact: true }).click();
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await page.locator("#chat-question").fill("重新读取时保留的草稿");
  await page.getByRole("button", { name: "返回收藏", exact: true }).click();
  control.failReads = true;
  await page.locator(".header-navigation").getByRole("button", { name: "AI 对话", exact: true }).click();
  await expect(page.locator(".chat-read-recovery")).toBeVisible();
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await expect(page.locator("#chat-question")).toHaveValue("重新读取时保留的草稿");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeDisabled();
  control.failReads = false;
  await page.locator(".chat-read-recovery").getByRole("button", { name: "重新读取对话", exact: true }).click();
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  expect(control.creations).toHaveLength(0); expect(control.messages).toHaveLength(0);
});

test("a lost deletion response can be retried after the server has already removed the chat", async ({ page, owned }) => {
  const response = await page.request.post("/chat/conversations", { headers: owned.headers, data: { title: "仅删除这一段对话" } });
  expect(response.ok()).toBeTruthy();
  const saved = await response.json() as Conversation; owned.ids.add(saved.id);
  let calls = 0;
  await page.route(`**/chat/conversations/${saved.id}`, async route => {
    if (route.request().method() !== "DELETE") return route.continue();
    calls++;
    const result = await route.fetch();
    if (calls === 1) { expect(result.ok()).toBeTruthy(); return route.abort("failed"); }
    expect(result.status()).toBe(404); return route.fulfill({ response: result });
  });
  await page.goto("/app#chat");
  await page.getByRole("button", { name: "历史", exact: true }).click();
  await page.getByRole("button", { name: "删除对话：仅删除这一段对话", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "删除这段对话？", exact: true });
  await dialog.getByRole("button", { name: "删除对话", exact: true }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await dialog.getByRole("button", { name: "删除对话", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "删除对话：仅删除这一段对话", exact: true })).toHaveCount(0);
  expect(calls).toBe(2);
});

async function namedFixture(page: Page) {
  const values = new Map<string, Conversation>(), accepted = new Set<string>();
  const control = { profiles: [
    { id: "careful", name: "独立阅读连接", channel: "chat", backend: "endpoint", model: "careful-model", agent: "",
      base_url: "https://synthetic.invalid/v1", key_set: true, configured: true, tested: true, current: false, updated_at: 1792886400 },
    { id: "untested", name: "尚未测试的本机连接", channel: "chat", backend: "agent", model: "local-draft", agent: "codex",
      base_url: "", key_set: false, configured: true, tested: false, current: false, updated_at: 1792886400 },
  ] as ModelProfile[], messages: [] as Record<string, unknown>[], generations: 0, globalWrites: 0,
    failReads: false, rejectNext: false, values, accepted };
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), value = await response.json();
    return route.fulfill({ response, json: { ...value, demo: false,
      channels: { ...value.channels, chat: { configured: true, tested: true } } } });
  });
  await page.route("**/admin/model-profiles?channel=chat", route => route.fulfill({ json: { profiles: control.profiles } }));
  await page.route(/\/admin\/model-profiles\/[^/?]+\/apply$|\/admin\/settings\/test$/, route => {
    control.globalWrites++; return route.fulfill({ status: 409, json: { detail: "Global connection must stay unchanged" } });
  });
  await page.route(/\/chat\/conversations(?:\/|\?|$)/, route => {
    const request = route.request(), url = new URL(request.url()), parts = url.pathname.split("/"), id = parts[3];
    if (url.pathname === "/chat/conversations") {
      if (request.method() === "GET") return route.fulfill({ json: { items: [...values.values()].map(value => ({ ...value, messages: undefined })), total: values.size } });
      const body = request.postDataJSON(), value: Conversation = { id: body.id, title: body.title, bookmark_ids: body.bookmark_ids,
        profile_id: body.profile_id, messages: [], running: false, created_at: 1792886400, updated_at: 1792886400 };
      values.set(id || value.id, value); return route.fulfill({ json: value });
    }
    const value = values.get(id);
    if (!value) return route.fulfill({ status: 404, json: { detail: "Synthetic conversation not found" } });
    if (parts[4] === "messages") {
      const body = request.postDataJSON(); control.messages.push(body);
      if (control.rejectNext) { control.rejectNext = false; return route.fulfill({ status: 409, json: { detail: "Synthetic saved connection was revoked" } }); }
      control.generations++;
      value.profile_id = body.profile_id;
      value.messages.push({ id: value.messages.length + 1, role: "user", content: body.text, request_id: body.request_id,
        status: "complete", sources: [], model: "", created_at: 1792886400 },
      { id: value.messages.length + 2, role: "assistant", content: "保留收藏里的具体方法，并在来源不足时说明限制。\n\nSaved sources remain readable while choosing an independent connection. ".repeat(4),
        request_id: body.request_id, status: "complete", sources: [], model: body.profile_id ? "careful-model" : "summary-model", created_at: 1792886400 });
      accepted.add(body.request_id);
      return route.fulfill({ json: { ...value, delivery: { request_id: body.request_id, accepted: true, running: false } } });
    }
    if (control.failReads) return route.fulfill({ status: 503, json: { detail: "Synthetic receipt read failure" } });
    const requestId = url.searchParams.get("request_id");
    return route.fulfill({ json: { ...value, ...(requestId ? { delivery: { request_id: requestId, accepted: accepted.has(requestId), running: false } } : {}) } });
  });
  return control;
}

test("a per-conversation connection survives refresh and rejected work can return to an editable draft", async ({ page }) => {
  const control = await namedFixture(page);
  await page.goto("/app#chat");
  const choice = page.locator("#chat-connection"), question = page.locator("#chat-question");
  await expect(choice.locator('option[value="careful"]')).toHaveCount(1);
  await choice.selectOption("careful"); await question.fill("使用独立连接提问");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await question.press("Enter");
  await expect(page.locator(".chat-message.assistant")).toContainText("careful-model");
  await question.fill("刷新后保留的追问"); await page.reload();
  await expect(choice).toHaveValue("careful"); await expect(question).toHaveValue("刷新后保留的追问");
  expect(control.globalWrites).toBe(0);
  control.rejectNext = true; control.failReads = true;
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await question.press("Enter");
  await expect(page.locator(".chat-delivery-recovery")).toBeVisible();
  await expect(choice).toBeDisabled();
  control.failReads = false;
  await page.locator(".chat-delivery-recovery").getByRole("button", { name: "重新读取对话", exact: true }).click();
  await expect(page.locator(".chat-delivery-recovery")).toHaveCount(0);
  await expect(choice).toBeEnabled(); await expect(question).toHaveValue("刷新后保留的追问");
  await choice.selectOption("");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await question.press("Enter");
  await expect(page.locator(".chat-message.user")).toHaveCount(2);
  expect(control.generations).toBe(2); expect(control.messages[1].profile_id).toBe("careful");
  expect(control.messages[2].profile_id).toBe(""); expect(control.globalWrites).toBe(0);
  control.profiles = []; await page.reload();
  await expect(page.locator(".chat-message.user")).toHaveCount(2);
  await expect(choice).toHaveCount(0);
  await question.fill("继续使用摘要连接");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  expect(control.messages).toHaveLength(3);
});

test("an accepted older retry is settled even after another window replaces its message request ID", async ({ page }) => {
  const control = await namedFixture(page);
  await page.goto("/app#chat");
  await page.locator("#chat-question").fill("跨窗口的原问题");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await page.locator("#chat-question").press("Enter");
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  const value = [...control.values.values()][0]; control.accepted.add("old-retry");
  value.messages[1].request_id = "newer-retry";
  await page.evaluate(id => {
    const saved = JSON.parse(localStorage.getItem("fm-chat-drafts")!);
    saved.drafts[id] = "准备好的下一问";
    saved.operations[id] = { id, originKey: id, requestId: "old-retry", mode: "retry", text: "", language: "zh",
      profileId: "", created: true, confirmed: false };
    localStorage.setItem("fm-chat-drafts", JSON.stringify(saved));
  }, value.id);
  await page.reload();
  await expect(page.locator(".chat-message.assistant")).toHaveCount(1);
  await expect(page.locator(".chat-delivery-recovery")).toHaveCount(0);
  await expect(page.locator("#chat-question")).toHaveValue("准备好的下一问");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  expect(control.generations).toBe(1); expect(control.messages).toHaveLength(1);
});

test("removed and untested connections keep saved answers without silently using the summary model", async ({ page }) => {
  const control = await namedFixture(page);
  await page.goto("/app#chat");
  await expect(page.locator('#chat-connection option[value="careful"]')).toHaveCount(1);
  await page.locator("#chat-connection").selectOption("careful");
  await page.locator("#chat-question").fill("保留这个独立连接的回答");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await page.locator("#chat-question").press("Enter");
  await expect(page.locator(".chat-message.assistant")).toHaveCount(1);
  control.profiles = control.profiles.filter(item => item.id !== "careful");
  await page.reload();
  await expect(page.locator("#chat-connection")).toHaveValue("careful");
  await expect(page.locator(".chat-connection-notice")).toBeVisible();
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeDisabled();
  await expect(page.locator(".chat-message.assistant")).toContainText("careful-model");
  await page.locator("#chat-connection").selectOption("untested");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeDisabled();
  expect(control.generations).toBe(1); expect(control.globalWrites).toBe(0);
});

test("chat controls and long connection states remain reachable in both themes and languages", async ({ page }) => {
  test.setTimeout(90_000);
  const control = await namedFixture(page);
  control.profiles[0].name = "保存原文与明确限制的长期阅读连接".repeat(4);
  control.profiles[0].model = "synthetic-long-model-name-for-independent-reading-".repeat(4);
  await page.goto("/app#chat");
  await expect(page.locator('#chat-connection option[value="careful"]')).toHaveCount(1);
  await page.locator("#chat-connection").selectOption("careful");
  await page.locator("#chat-question").fill("查看这个长回答并继续阅读");
  await expect(page.getByRole("button", { name: "发送问题", exact: true })).toBeEnabled();
  await page.locator("#chat-question").press("Enter");
  await expect(page.locator(".chat-message.assistant")).toHaveCount(1);
  await page.locator("#chat-connection").selectOption("untested");
  const draft = "继续保留未发送的阅读草稿";
  await page.locator("#chat-question").fill(draft);
  for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    await page.reload(); await expect(page.locator(".chat-message.assistant")).toHaveCount(1);
    for (const size of [{ width: 1280, height: 850 }, { width: 390, height: 844 }, { width: 320, height: 640 }, { width: 640, height: 480 }]) {
      await page.setViewportSize(size); await settleVisualLayout(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const bounds = await page.locator(".chat-workspace").evaluate(element => {
        const messages = element.querySelector(".chat-messages")!.getBoundingClientRect();
        const composer = element.querySelector(".chat-composer")!.getBoundingClientRect();
        const status = element.querySelector(".chat-composer-status")!.getBoundingClientRect();
        const choice = element.querySelector(".chat-model-choice label")!.getBoundingClientRect();
        const label = element.querySelector(".chat-model-choice label > span")!.getBoundingClientRect();
        const connection = element.querySelector("#chat-connection")!.getBoundingClientRect();
        return { messagesBottom: messages.bottom, messagesHeight: messages.height, composerTop: composer.top,
          controlsHeight: element.querySelector(".chat-composer-area")!.getBoundingClientRect().height,
          composerBottom: composer.bottom, statusBottom: status.bottom, viewport: innerHeight,
          choiceHeight: choice.height, labelRight: label.right, connectionLeft: connection.left,
          connectionHeight: connection.height };
      });
      expect(bounds.messagesHeight).toBeGreaterThan(40); expect(bounds.messagesBottom).toBeLessThanOrEqual(bounds.composerTop);
      if (size.width === 320 && size.height === 640) {
        expect(bounds.messagesHeight).toBeGreaterThanOrEqual(240);
        expect(bounds.controlsHeight).toBeLessThan(230);
      }
      expect(bounds.statusBottom).toBeLessThanOrEqual(bounds.composerTop); expect(bounds.composerBottom).toBeLessThanOrEqual(bounds.viewport);
      if (size.width < 720) {
        expect(bounds.choiceHeight).toBeLessThanOrEqual(bounds.connectionHeight + 1);
        expect(bounds.labelRight).toBeLessThanOrEqual(bounds.connectionLeft);
        expect(bounds.connectionHeight).toBeGreaterThanOrEqual(44);
      }
      await expect(page.getByRole("combobox", { name: language === "zh" ? "本段对话的模型连接" : "Connection for this conversation", exact: true })).toBeVisible();
      await page.screenshot({ path: `screenshots/collection-review/chat-connections-${language}-${theme}-${size.width}-${size.height}.png`, animations: "disabled" });
      if (size.width === 320) {
        const status = page.getByRole("region", { name: language === "zh" ? "连接与发送状态" : "Connection and send status", exact: true });
        await status.focus(); await page.keyboard.press("Tab");
        await expect(page.locator("#chat-connection")).toBeFocused();
        await page.keyboard.press("Tab");
        const detail = page.locator(".chat-connection-details"), disclosure = detail.locator(":scope > summary");
        await expect(disclosure).toBeFocused(); await disclosure.press("Enter");
        await expect(detail.locator(":scope > p")).toBeVisible();
        await expect(detail).toContainText(language === "zh" ? "可以继续写草稿" : "you can keep drafting");
        await disclosure.press("Space"); await expect(detail).toHaveJSProperty("open", false);
        await expect(page.locator("#chat-question")).toHaveValue(draft);
        await page.keyboard.press("Tab");
        const setup = page.getByRole("button", { name: language === "zh" ? "设置 AI 连接" : "Set up AI connection", exact: true });
        await expect(setup).toBeFocused(); await expect(setup).toBeInViewport({ ratio: 1 });
        await page.screenshot({ path: `screenshots/collection-review/quality-chat-state-action-${language}-${theme}-320.png` });
        await status.evaluate(element => { element.scrollTop = 0; });
      }
    }
  }
  expect(control.generations).toBe(1); expect(control.globalWrites).toBe(0);
});

for (const retained of [false, true]) test(`reader fetch failures explain ${retained ? "retained source text" : "missing source text"} and retry the exact page`, async ({ page }) => {
  let bookmarkId = 0;
  const previews: Record<string, unknown>[] = [];
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch(), value = await response.json(); bookmarkId = value.bookmark_id;
    return route.fulfill({ response, json: { ...value, body_text: retained ? "这段已保存的正文必须保留。\n\n第二段原文仍然可以阅读。" : "",
      summary: "", ai_title: "", indexed: { ...value.indexed, enriched_by: "", summary_basis: "",
        error: "Synthetic fetch failed: the source website is temporarily unavailable. 原网页暂时不可访问。" } } });
  });
  await page.route("**/admin/jobs/preview", route => {
    previews.push(route.request().postDataJSON()); return route.fulfill({ json: { total: 1, revision: "synthetic-reader-retry" } });
  });
  await page.goto("/app"); await page.locator(".bookmark-preview").first().click();
  const feedback = page.locator(".reader-fetch-feedback");
  await expect(feedback).toContainText(retained ? "已保留保存的正文" : "正文提取失败");
  if (retained) await expect(page.locator(".body-text")).toContainText("这段已保存的正文必须保留");
  else await expect(page.locator(".body-text")).toHaveCount(0);
  await feedback.getByRole("button", { name: "重试提取正文", exact: true }).focus(); await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "提取网页正文", exact: true })).toBeVisible();
  await expect.poll(() => previews.at(-1)).toEqual(expect.objectContaining({ mode: "fetch", bookmark_ids: [bookmarkId], force: true }));
  await page.getByRole("dialog", { name: "提取网页正文", exact: true }).getByRole("button", { name: "取消", exact: true }).click();
  await page.setViewportSize({ width: 320, height: 640 }); await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `screenshots/collection-review/reader-fetch-${retained ? "retained" : "empty"}-320.png`, animations: "disabled" });
});
