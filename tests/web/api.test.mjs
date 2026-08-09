// The one request helper. `node --test tests/web/*.test.mjs`
//
// `call` is the only place the pairing token, the JSON content type and the
// error mapping are decided, so it is the only place they are tested. fetch is
// stubbed rather than mocked at the network layer: what matters is what the
// helper sends and how it reads the response, not the wire.

import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

import { ApiError, setToken, getToken, call, qs } from "../../src/facetmark/web/static/api.js";

// A fetch that records what it was asked for and answers however the test set
// it up. `globalThis.fetch` is restored after every test.
let seen;
let answer;
const realFetch = globalThis.fetch;

beforeEach(() => {
  seen = [];
  answer = { ok: true, status: 200, body: {} };
  setToken("");
  globalThis.fetch = async (path, init) => {
    seen.push({ path, init });
    return {
      ok: answer.ok,
      status: answer.status,
      json: async () => answer.body,
    };
  };
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("qs", () => {
  test("builds a query string from the surviving pairs", () => {
    assert.equal(qs({ q: "rust", limit: 10 }), "?q=rust&limit=10");
  });

  test("drops undefined, null and the empty string", () => {
    assert.equal(qs({ a: undefined, b: null, c: "", d: 1 }), "?d=1");
  });

  test("returns an empty string when nothing survives", () => {
    assert.equal(qs({}), "");
    assert.equal(qs({ a: undefined }), "");
  });

  test("encodes a stray ampersand instead of letting it split the parameter", () => {
    // `?q=` takes whatever the reader typed. A template literal would turn
    // "a&b" into a second parameter; URLSearchParams must not.
    assert.equal(qs({ q: "a&b" }), "?q=a%26b");
  });

  test("keeps a zero, which is falsy and would be dropped by a lazier check", () => {
    assert.equal(qs({ offset: 0 }), "?offset=0");
  });
});

describe("setToken / getToken", () => {
  test("round-trips the pairing token", () => {
    setToken("abc123");
    assert.equal(getToken(), "abc123");
  });

  test("treats null and undefined as no token", () => {
    setToken(null);
    assert.equal(getToken(), "");
    setToken(undefined);
    assert.equal(getToken(), "");
  });
});

describe("call", () => {
  test("sends the bearer token only when one is set", async () => {
    await call("/stats");
    assert.equal(seen[0].init.headers.authorization, undefined);

    setToken("sekret");
    await call("/stats");
    assert.equal(seen[1].init.headers.authorization, "Bearer sekret");
  });

  test("sets the JSON content type only when there is a body", async () => {
    await call("/health");
    assert.equal(seen[0].init.headers["content-type"], undefined);

    await call("/search", { method: "POST", body: JSON.stringify({ q: "x" }) });
    assert.equal(seen[1].init.headers["content-type"], "application/json");
  });

  test("parses a JSON response on success", async () => {
    answer = { ok: true, status: 200, body: { bookmarks: 42 } };
    const out = await call("/stats");
    assert.deepEqual(out, { bookmarks: 42 });
  });

  test("maps an HTTP error to an ApiError carrying the status and detail", async () => {
    answer = { ok: false, status: 404, body: { detail: "no such bookmark" } };
    await assert.rejects(call("/bookmark/9"), (err) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 404);
      assert.equal(err.message, "no such bookmark");
      return true;
    });
  });

  test("falls back to the status when the error body has no detail", async () => {
    answer = { ok: false, status: 500, body: {} };
    await assert.rejects(call("/stats"), (err) => {
      assert.equal(err.status, 500);
      assert.equal(err.message, "HTTP 500");
      return true;
    });
  });

  test("survives an error body that is not JSON", async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError("not json");
      },
    });
    await assert.rejects(call("/stats"), (err) => {
      assert.equal(err.status, 502);
      assert.equal(err.message, "HTTP 502");
      return true;
    });
  });

  test("maps a network failure to status 0, distinct from any server status", async () => {
    // A rejected fetch to our own origin means the server went away. Status 0
    // is the convention for "never got an HTTP response at all".
    globalThis.fetch = async () => {
      throw new TypeError("fetch failed");
    };
    await assert.rejects(call("/stats"), (err) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 0);
      return true;
    });
  });

  test("lets a caller-supplied header win over the default", async () => {
    setToken("tok");
    await call("/stats", { headers: { authorization: "Bearer other" } });
    assert.equal(seen[0].init.headers.authorization, "Bearer other");
  });
});
