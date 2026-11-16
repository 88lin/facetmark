import { afterEach, mock, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

// Import the shipping client without a bundle or browser. Runtime cases use
// real Response/Headers/AbortController objects rather than unchecked casts.
const source = await readFile(new URL("../../src/api.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { api, ApiError, setToken } = await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
afterEach(() => { mock.restoreAll(); setToken(""); });

test("HTTP error pages retain their status and give a recoverable message", async () => {
  mock.method(globalThis, "fetch", async () => new Response("<html>proxy failed</html>", { status: 502 }));
  await assert.rejects(api("/stats"), error => error instanceof ApiError && error.status === 502 && !error.message.includes("<html>"));
});

test("Headers instances survive with the pairing token and JSON content type", async () => {
  setToken("synthetic-token");
  mock.method(globalThis, "fetch", async (_path, init) => {
    const headers = new Headers(init.headers);
    assert.equal(headers.get("x-custom"), "retained");
    assert.equal(headers.get("authorization"), "Bearer synthetic-token");
    assert.equal(headers.get("content-type"), "application/json");
    return Response.json({ saved: true });
  });
  assert.deepEqual(await api("/admin/settings", { method: "PUT", body: "{}", headers: new Headers({ "X-Custom": "retained" }) }), { saved: true });
});

test("empty successful responses do not produce JSON parsing errors", async () => {
  mock.method(globalThis, "fetch", async () => new Response(null, { status: 204 }));
  assert.equal(await api("/resource", { method: "DELETE" }), undefined);
});

test("unreachable service failures have a stable error type", async () => {
  mock.method(globalThis, "fetch", async () => { throw new TypeError("fetch failed"); });
  await assert.rejects(api("/stats"), error => error instanceof ApiError && error.status === 0);
});

test("malformed success responses identify a service response failure", async () => {
  mock.method(globalThis, "fetch", async () => new Response("<!doctype html>", { status: 200 }));
  await assert.rejects(api("/stats"), error => error instanceof ApiError && error.status === 200);
});

test("read requests stop waiting on an unresponsive service", { timeout: 1000 }, async () => {
  mock.method(globalThis, "fetch", (_path, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(init.signal.reason), { once: true });
  }));
  await assert.rejects(api("/stats", { timeoutMs: 15 }), error => error instanceof ApiError && error.status === 0);
});

test("caller cancellation remains distinguishable from service failure", async () => {
  const abort = new AbortController();
  mock.method(globalThis, "fetch", async (_path, init) => {
    abort.abort();
    throw init.signal.reason;
  });
  await assert.rejects(api("/stats", { signal: abort.signal }), { name: "AbortError" });
});

test("validation messages do not lose the actual field error", async () => {
  mock.method(globalThis, "fetch", async () => Response.json({ detail: [{ msg: "URL is invalid" }] }, { status: 422 }));
  await assert.rejects(api("/bookmark", { method: "POST", body: "{}" }), error => error instanceof ApiError && error.status === 422 && error.message.includes("URL is invalid"));
});
