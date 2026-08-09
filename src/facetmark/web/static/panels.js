// The callouts: pairing, offline, empty, setup, and anything that failed.
//
// One module because these are the screens a first-time reader is most likely
// to see, and they were the part of this page most likely to be written five
// slightly different ways across five views.

import { ApiError, setToken } from "./api.js";
import { btn, el } from "./dom.js";
import { S, t } from "./state.js";

const TOKEN_KEY = "fm-token";

/**
 * A titled block with optional prose, a shell command, and extra nodes.
 * `tone` is "" for information, "warn" for a caution, "bad" for a failure.
 */
export function showPanel({ title, body, cmd, tone = "", extra = [], into }) {
  const box = el("div", tone ? `panel ${tone}` : "panel");
  box.appendChild(el("h2", null, title));
  for (const line of [].concat(body ?? [])) {
    if (line) box.appendChild(el("p", null, line));
  }
  if (cmd) {
    const pre = el("pre", "cmd");
    pre.appendChild(el("code", null, cmd));
    box.appendChild(pre);
  }
  for (const node of extra) box.appendChild(node);
  into?.replaceChildren(box);
  return box;
}

export function tokenPanel(rejected, into) {
  const form = el("form", "pair");
  const input = el("input", "field");
  input.type = "password";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.placeholder = t("token.placeholder");
  input.setAttribute("aria-label", t("token.placeholder"));
  const submit = btn(t("token.save"), "primary");
  submit.type = "submit";
  form.append(input, submit);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const v = input.value.trim();
    if (!v) return;
    setToken(v);
    try {
      localStorage.setItem(TOKEN_KEY, v);
    } catch {
      /* private mode: the token then lives for this tab only, which is fine */
    }
    into?.replaceChildren();
    S.stats = null;
    S.health = null;
    void S.redraw();
  });
  return showPanel({
    title: t("err.token.title"),
    body: [t("err.token.body"), rejected ? t("token.bad") : ""],
    cmd: t("err.token.cmd"),
    tone: rejected ? "bad" : "",
    extra: [form],
    into,
  });
}

export function failPanel(e, into) {
  if (e instanceof ApiError && e.status === 401) return tokenPanel(true, into);
  if (e instanceof ApiError && e.status === 0) {
    return showPanel({
      title: t("err.offline.title"),
      body: t("err.offline.body"),
      cmd: t("err.offline.cmd"),
      tone: "bad",
      into,
    });
  }
  return showPanel({
    title: t("err.generic.title"),
    body: e?.message ?? String(e),
    tone: "bad",
    into,
  });
}
