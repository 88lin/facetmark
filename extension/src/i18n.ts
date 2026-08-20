// Minimal i18n for the popup and options page. One file, no fetch: the strings
// are small enough to ship inline, and a fetch off a missing strings file would
// leave the panel blank. The key set is closed -- add a key here and a
// data-i18n="key" in the markup and applyI18n picks it up.
//
// The storage key matches the served /app page (`fm-lang`) so a user who picked
// 中文 there sees 中文 here without asking again.

export type Lang = "en" | "zh";

const STRINGS: Record<string, { en: string; zh: string }> = {
  "opt.hint": {
    en: `Start the server with <code>facetmark serve</code>. It prints a pairing token on first run; paste it below. Nothing leaves your machine except the model calls you configure on the server side.`,
    zh: `运行 <code>facetmark serve</code> 启动服务。首次运行会打印配对令牌，粘贴到下方。除服务端配置的模型调用外，数据不离开你的机器。`,
  },
  "opt.connection": { en: "Connection", zh: "连接" },
  "opt.server": { en: "Server", zh: "服务器" },
  "opt.token": { en: "Pairing token", zh: "配对令牌" },
  "opt.tokenPh": { en: "paste the token printed by facetmark serve", zh: "粘贴 facetmark serve 打印的令牌" },
  "opt.options": { en: "Options", zh: "选项" },
  "opt.channelB": { en: "Let Facetmark read pages the server cannot fetch", zh: "允许 Facetmark 读取服务器无法抓取的页面" },
  "opt.paused": { en: "Pause background fetching", zh: "暂停后台抓取" },
  "opt.save": { en: "save", zh: "保存" },
  "opt.drain": { en: "fetch queued pages now", zh: "立即抓取排队页面" },
  "opt.connected": { en: "connected · %1 bookmarks", zh: "已连接 · %1 个书签" },
  "opt.queueEmpty": { en: "queue empty", zh: "队列空" },
  "opt.channelOff": { en: "channel B is off - nothing will be fetched", zh: "通道 B 已关闭 - 不会抓取任何内容" },
  "opt.pausedMsg": { en: "paused - unpause to let the browser fetch", zh: "已暂停 - 取消暂停以让浏览器抓取" },
  "opt.fetching": { en: "fetching queued pages...", zh: "正在抓取排队页面..." },
  "opt.fetched": { en: "fetched %1 page(s)", zh: "已抓取 %1 个页面" },
  "opt.nothingReady": { en: "nothing was ready to fetch", zh: "没有可抓取的内容" },
  "opt.swNoAnswer": { en: "the service worker did not answer", zh: "服务工作进程未响应" },
  "pop.placeholder": { en: "what were you looking for?", zh: "你在找什么？" },
  "pop.save": { en: "save this page", zh: "保存此页面" },
  "pop.saved": { en: "saved", zh: "已保存" },
  "pop.alreadySaved": { en: "already saved", zh: "已保存过" },
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
  "pop.cold": { en: "cold", zh: "失效" },
  "pop.tokenRejected": { en: "pairing token rejected - open options", zh: "配对令牌被拒绝 - 打开设置" },
  "pop.serverUnreachable": { en: "server unreachable - run `facetmark serve`", zh: "服务器不可达 - 运行 `facetmark serve`" },
  "pop.lexical": { en: "lexical", zh: "词法" },
  "pop.ranked": { en: "ranked", zh: "已排序" },
};

export function getLang(): Lang {
  try {
    const l = localStorage.getItem("fm-lang");
    if (l === "en" || l === "zh") return l;
  } catch {
    // localStorage can be unavailable in a restricted context; default to en.
  }
  return "en";
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
  for (let i = 0; i < args.length; i++) s = s.replace(`%${i + 1}`, String(args[i]));
  return s;
}

/** Apply data-i18n (innerHTML, so the hint's <code> survives) and
 *  data-i18n-attr="attr:key[,...]" to every element under root. */
export function applyI18n(root: ParentNode = document): void {
  const lang = getLang();
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
}
