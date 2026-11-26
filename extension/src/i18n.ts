// Minimal i18n for the popup and options page. One file, no fetch: the strings
// are small enough to ship inline, and a fetch off a missing strings file would
// leave the panel blank. The key set is closed -- add a key here and a
// data-i18n="key" in the markup and applyI18n picks it up.
//
// Popup and options share this extension origin's local language preference.

export type Lang = "en" | "zh";

const STRINGS: Record<string, { en: string; zh: string }> = {
  "opt.hint": {
    en: "Copy the address and pairing token from Facetmark Settings → Browser extension, or from facetmark serve.",
    zh: "从 Facetmark 的设置 → 浏览器扩展复制地址和配对令牌；也可以使用 facetmark serve 显示的连接信息。",
  },
  "opt.heading": { en: "Browser extension", zh: "浏览器扩展" },
  "opt.intro": { en: "Search and save to your own Facetmark library.", zh: "检索收藏，把当前页面保存到自己的 Facetmark。" },
  "opt.connection": { en: "Your local connection", zh: "连接自己的 Facetmark" },
  "opt.server": { en: "Server address", zh: "服务地址" },
  "opt.endpointHint": { en: "Use the address of your running Facetmark service.", zh: "使用当前已启动的 Facetmark 服务地址。" },
  "opt.token": { en: "Pairing token", zh: "配对令牌" },
  "opt.tokenPh": { en: "Paste the pairing token", zh: "粘贴配对令牌" },
  "opt.tokenHint": { en: "Stored in this browser only. Keep the token private.", zh: "仅保存在当前浏览器中，请勿分享令牌。" },
  "opt.showToken": { en: "Show", zh: "显示" },
  "opt.hideToken": { en: "Hide", zh: "隐藏" },
  "opt.options": { en: "Reading through the browser", zh: "通过浏览器读取正文" },
  "opt.readingHint": { en: "Optional. Read queued pages in temporary tabs using the browser's current access, then save the text to your local library.", zh: "按需开启。扩展会用浏览器当前的访问权限在临时标签页读取排队页面，再将正文保存到本机收藏库。" },
  "opt.channelB": { en: "Allow browser page reading", zh: "允许浏览器读取排队页面" },
  "opt.paused": { en: "Pause background reading", zh: "暂停后台读取" },
  "opt.switchHint": { en: "These switches take effect immediately on the saved connection. Pausing closes the current temporary tab.", zh: "开关立即应用于已保存的连接。暂停会关闭正在读取的临时标签页。" },
  "opt.save": { en: "Save connection", zh: "保存连接" },
  "opt.drain": { en: "Read queued pages now", zh: "立即读取排队页面" },
  "opt.refresh": { en: "Refresh status", zh: "刷新状态" },
  "opt.reading": { en: "Checking the saved connection…", zh: "正在读取已保存连接的状态…" },
  "opt.saved": { en: "Connection saved", zh: "连接已保存" },
  "opt.awaitPermission": { en: "Waiting for browser access. Respond to the browser's permission request to continue.", zh: "正在等待浏览器访问授权。请在浏览器的权限提示中选择后继续。" },
  "opt.draft": { en: "Connection changes are not saved yet.", zh: "连接信息已修改，尚未保存。" },
  "opt.reloadSettings": { en: "Read changed settings", zh: "读取其他窗口的新设置" },
  "opt.reloadConfirm": { en: "Replace these unsaved connection fields with the currently saved settings?", zh: "读取当前已保存设置，并替换此处尚未保存的连接输入？" },
  "opt.changedElsewhere": { en: "Settings changed in another window. Read the changed settings, review them, then save again.", zh: "设置已在其他窗口变更。先读取新设置、核对内容，再保存。" },
  "opt.permissionDenied": { en: "Website access is missing. Allow access when saving the connection or enabling page reading.", zh: "尚未获得网页访问权限。保存连接或开启正文读取时，请允许所需的访问权限。" },
  "opt.timeout": { en: "The connection timed out. Start Facetmark, check the saved address, then confirm the original result before retrying.", zh: "连接等待超时。启动 Facetmark、核对已保存地址，再确认原结果或继续原请求。" },
  "opt.badResponse": { en: "The response is incomplete. Keep the original request and refresh its result before retrying.", zh: "返回内容不完整。原请求仍保留，请先刷新确认结果，再继续原请求。" },
  "opt.pauseSaved": { en: "Page reading paused", zh: "已暂停正文读取" },
  "opt.resumeSaved": { en: "Page reading resumed", zh: "已恢复正文读取" },
  "opt.readingEnabled": { en: "Browser reading allowed", zh: "已允许浏览器读取正文" },
  "opt.readingDisabled": { en: "Browser reading turned off", zh: "已关闭浏览器正文读取" },
  "opt.connected": { en: "connected · %1 bookmarks", zh: "已连接 · %1 个书签" },
  "opt.queueEmpty": { en: "queue empty", zh: "队列空" },
  "opt.channelOff": { en: "Browser page reading is off", zh: "浏览器正文读取已关闭" },
  "opt.pausedMsg": { en: "Paused · resume the switch to read queued pages", zh: "已暂停 · 恢复开关后可以读取排队页面" },
  "opt.fetching": { en: "Reading queued pages… You can pause below.", zh: "正在读取排队页面… 可以使用暂停开关停止。" },
  "opt.fetchFinished": { en: "Processed %1 queued page(s)", zh: "已处理 %1 个排队页面" },
  "opt.fetched": { en: "fetched %1 page(s)", zh: "已抓取 %1 个页面" },
  "opt.nothingReady": { en: "nothing was ready to fetch", zh: "没有可抓取的内容" },
  "opt.swNoAnswer": { en: "The extension did not answer. Reopen it and confirm the original result in settings.", zh: "扩展后台未响应。重新打开扩展，并在设置中确认原结果。" },
  "opt.pendingHeading": { en: "Original requests to confirm", zh: "待确认的原请求" },
  "opt.pendingCount": { en: "%1 pending", zh: "%1 项待确认" },
  "opt.pendingHint": { en: "The original request stays here when its result is unclear. Confirming only checks what was accepted. Continuing sends the original content.", zh: "结果不明确时，原请求会保留在这里。确认仅查询是否已保存；继续会发送同一份原内容。" },
  "opt.pendingSave": { en: "Page save", zh: "页面保存" },
  "opt.pendingReading": { en: "Reading result", zh: "正文结果" },
  "opt.pendingDate": { en: "Original request · %1", zh: "原请求时间 · %1" },
  "opt.otherConnection": { en: "This request belongs to another saved address or token. Return to that connection to confirm or continue it.", zh: "此请求属于另一组已保存地址或令牌。恢复原连接后，才能确认或继续。" },
  "opt.confirm": { en: "Check accepted results", zh: "确认是否已保存" },
  "opt.confirmed": { en: "Confirmed %1 original result(s)", zh: "已确认 %1 项原结果" },
  "opt.notConfirmed": { en: "No accepted result was found. The original requests are kept below.", zh: "尚未查到已接受结果，原请求继续保留在下方。" },
  "opt.retrySave": { en: "Continue original save", zh: "继续原保存" },
  "opt.originalSaved": { en: "Original page save confirmed", zh: "原页面保存已确认" },
  "opt.retryResults": { en: "Send original reading results", zh: "发送原正文结果" },
  "opt.resultsSent": { en: "Confirmed %1 original reading result(s)", zh: "已确认 %1 项原正文结果" },
  "opt.discard": { en: "Clear these local requests", zh: "清除这些本地请求" },
  "opt.discardConfirm": { en: "Clear the extension's pending original requests? Saved bookmarks and text stay in Facetmark. An unaccepted result will no longer be available to continue.", zh: "清除扩展中待确认的原请求？已保存到 Facetmark 的收藏和正文会保留；未被接受的结果将无法从此处继续。" },
  "opt.discarded": { en: "Local pending requests cleared", zh: "本地待确认请求已清除" },
  "queue.ready": { en: "%1 ready to read", zh: "%1 项可读取" },
  "queue.waiting": { en: "%1 retrying later", zh: "%1 项等待重试" },
  "queue.leased": { en: "%1 being read", zh: "%1 项读取中" },
  "queue.failed": { en: "%1 need review", zh: "%1 项需核对" },
  "pop.placeholder": { en: "Search your saved pages", zh: "检索自己的收藏" },
  "pop.results": { en: "Search results", zh: "检索结果" },
  "pop.save": { en: "save this page", zh: "保存此页面" },
  "pop.saved": { en: "saved", zh: "已保存" },
  "pop.alreadySaved": { en: "already saved", zh: "已保存过" },
  "pop.saving": { en: "Saving…", zh: "正在保存…" },
  "pop.unsupportedPage": { en: "Open a website page before saving. Browser settings and internal pages cannot be saved here.", zh: "请先打开网站页面。浏览器设置和内部页面无法从此处保存。" },
  "pop.recovery": { en: "Confirm or continue the original save in settings", zh: "在设置中确认或继续原保存" },
  "pop.start": { en: "Search by title, tag or a few remembered words.", zh: "输入标题、标签或印象中的几个词。" },
  "pop.searching": { en: "Searching…", zh: "正在检索…" },
  "pop.connectionChanged": { en: "The saved connection changed. Press Enter to search it again.", zh: "已保存连接发生变化。按 Enter 可重新检索。" },
  "pop.page": { en: "%1 of %2", zh: "已显示 %1 / %2 项" },
  "pop.pageCapped": { en: "%1 of %2+ · candidate limit", zh: "已显示 %1 / %2+ 项 · 候选范围有上限" },
  "pop.windowEnded": { en: "%1 shown · Narrow the search to find more", zh: "已显示 %1 项 · 可缩小条件查找更多" },
  "pop.resultCount": { en: "%1 result(s)", zh: "%1 项结果" },
  "pop.settings": { en: "settings", zh: "设置" },
  "pop.empty": { en: "nothing in your library matches that yet", zh: "你的库里还没有匹配项" },
  "pop.group": { en: "saved around these", zh: "同时保存的" },
  "pop.loading": { en: "loading...", zh: "加载中..." },
  "pop.more": { en: "more", zh: "更多" },
  "pop.about": { en: "about", zh: "关于" },
  "pop.askedAs": { en: "asked as", zh: "提问为" },
  "pop.words": { en: "words", zh: "字词" },
  "pop.substring": { en: "substring", zh: "子串" },
  "pop.linked": { en: "linked", zh: "关联" },
  "pop.cold": { en: "Text not indexed", zh: "正文尚未索引" },
  "pop.tokenRejected": { en: "pairing token rejected - open options", zh: "配对令牌被拒绝 - 打开设置" },
  "pop.serverUnreachable": { en: "Cannot reach Facetmark. Start the app or facetmark serve, then check the saved address in settings.", zh: "无法连接 Facetmark。启动应用或 facetmark serve，并在扩展设置中核对已保存地址。" },
  "pop.lexical": { en: "keyword matches", zh: "关键词匹配" },
  "pop.keywordRetained": { en: "Keyword matches are still available", zh: "仍可使用关键词结果" },
  "pop.keywordEmpty": { en: "No keyword matches", zh: "暂无关键词匹配" },
  // The server answered the rest of the query and dropped this token. Marked
  // rather than worded, because the status line has room for the token itself
  // and that is the part the user needs to see.
  "pop.ignored": { en: "⚠ ignored", zh: "⚠ 已忽略" },
};

export function getLang(): Lang {
  try {
    const l = localStorage.getItem("fm-lang");
    if (l === "en" || l === "zh") return l;
  } catch {
    // localStorage can be unavailable in a restricted context; default to en.
  }
  return typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

export function setLang(l: Lang): void {
  try {
    localStorage.setItem("fm-lang", l);
  } catch {
    // ignore
  }
  document.documentElement.lang = l === "zh" ? "zh-CN" : "en";
}

export function t(key: string, ...args: (string | number)[]): string {
  const entry = STRINGS[key];
  const lang = getLang();
  let s = entry ? entry[lang] : key;
  for (let i = 0; i < args.length; i++) s = s.replaceAll(`%${i + 1}`, String(args[i]));
  return s;
}

/** Apply data-i18n (innerHTML, so the hint's <code> survives) and
 *  data-i18n-attr="attr:key[,...]" to every element under root. */
export function applyI18n(root: ParentNode = document): void {
  const lang = getLang();
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  root.querySelectorAll<HTMLElement>("[data-i18n]").forEach((el) => {
    const entry = STRINGS[el.dataset.i18n!];
    if (entry) el.innerHTML = entry[lang];
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-attr]").forEach((el) => {
    for (const part of el.dataset.i18nAttr!.split(",")) {
      const [attr, key] = part.trim().split(":");
      const entry = STRINGS[key];
      if (entry) el.setAttribute(attr, entry[lang]);
    }
  });
}

/** Wire the [data-lang-toggle] button. The label shows the language you would
 *  switch TO, not the one you are on. Dispatches "langchange" on toggle. */
export function initLangToggle(): void {
  const btn = document.querySelector<HTMLButtonElement>("[data-lang-toggle]");
  if (!btn) return;
  const label = () => (getLang() === "en" ? "中文" : "English");
  btn.textContent = label();
  btn.addEventListener("click", () => {
    setLang(getLang() === "en" ? "zh" : "en");
    applyI18n();
    btn.textContent = label();
    document.dispatchEvent(new CustomEvent("langchange"));
  });
  window.addEventListener("storage", (event) => {
    if (event.key !== "fm-lang") return;
    applyI18n();
    btn.textContent = label();
    document.dispatchEvent(new CustomEvent("langchange"));
  });
}
