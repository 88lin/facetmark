/**
 * Cross-language wire contract: what the TypeScript plugin actually sends.
 *
 * The gap this closes was stated plainly in ../search-facetmark/src/index.ts:
 * the Python routes are pinned by Python tests and the TypeScript signatures are
 * pinned by `tsc`, but *nothing asserted that the JSON one side emits is the
 * JSON the other side parses*. Two type systems agreeing about a shape they each
 * describe separately is not the same as one program agreeing with another.
 *
 * How it works. `FacetmarkProvider` is driven exactly the way karakeep drives
 * it -- environment variables, `getClient()`, then the four `SearchIndexClient`
 * methods -- with `globalThis.fetch` replaced by a recorder. Nothing about the
 * plugin is stubbed or re-implemented here; the request bodies written to
 * `wire.json` are the bytes a real karakeep would put on the socket.
 *
 *   node --experimental-transform-types capture.ts           # rewrite wire.json
 *   node --experimental-transform-types capture.ts --check   # fail if it changed
 *
 * `--transform-types`, not `--strip-types`: the plugin declares its constructor
 * with parameter properties, which strip-only mode cannot erase. Bending the
 * plugin's source to suit the test tool would defeat the purpose of driving the
 * real thing, so the flag moves instead of the code.
 *
 * `tests/test_karakeep_contract.py` then replays `wire.json` through the real
 * FastAPI routes, and writes `replies.json` back for this script to parse. So
 * each side consumes an artifact the *other* side produced, and CI runs both
 * halves: the Python job needs no Node, the plugin job needs no Python.
 *
 * The fixtures below are chosen for the places a wire format usually breaks
 * rather than for coverage: `Date` objects that only exist on the TypeScript
 * side of the schema, a document that is nothing but the two required fields,
 * explicit nulls where the schema says nullish, both `FilterQuery` variants,
 * a body-less POST, and the two early returns that must not produce a request
 * at all.
 */

import { FacetmarkProvider } from "../search-facetmark/src/index.ts";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import type {
  BookmarkSearchDocument,
  SearchOptions,
  SearchResponse,
} from "@karakeep/shared/search";

const HERE = dirname(fileURLToPath(import.meta.url));
const WIRE = join(HERE, "wire.json");
const REPLIES = join(HERE, "replies.json");

const BASE = "http://127.0.0.1:8787";
const TOKEN = "contract-token";

interface Recorded {
  label: string;
  method: string;
  path: string;
  headers: Record<string, string>;
  /** Parsed request body, or null when the plugin sent no body at all. */
  body: unknown;
}

const recorded: Recorded[] = [];
let label = "";
let reply: unknown = {};

const realFetch = globalThis.fetch;
globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
  const url = String(input);
  if (!url.startsWith(BASE)) {
    throw new Error(`plugin called an unexpected host: ${url}`);
  }
  const raw = init?.body;
  recorded.push({
    label,
    method: String(init?.method ?? "GET"),
    path: url.slice(BASE.length),
    headers: Object.fromEntries(
      Object.entries((init?.headers ?? {}) as Record<string, string>).map(
        ([k, v]) => [k.toLowerCase(), k.toLowerCase() === "authorization" ? "Bearer <token>" : v],
      ),
    ),
    body: raw === undefined || raw === null ? null : JSON.parse(String(raw)),
  });
  return new Response(JSON.stringify(reply), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}) as typeof fetch;

function fail(msg: string): never {
  console.error(`contract: ${msg}`);
  process.exit(1);
}

// --- fixtures ---------------------------------------------------------------

const DOCS: BookmarkSearchDocument[] = [
  {
    // Every field populated, including the two the Python side does not read.
    // `Date` exists only in TypeScript: the schema says `z.date().nullish()`,
    // and what crosses the wire is whatever `JSON.stringify` decides. Pinning
    // that is the entire point of including it.
    id: "kk-full",
    userId: "u1",
    url: "https://example.com/a",
    title: "A page",
    linkTitle: "A page (link)",
    description: "described",
    content: "body text of the page",
    metadata: '{"kind":"link"}',
    fileName: null,
    createdAt: "2026-01-02T03:04:05.000Z",
    note: "a note",
    summary: "a summary",
    tags: ["Reading", "AI/LLM"],
    publisher: "Example",
    author: "Someone",
    datePublished: new Date("2025-06-01T00:00:00.000Z"),
    dateModified: new Date("2025-06-02T12:30:00.000Z"),
  },
  {
    // Only the two required fields. `tags` is `.default([])` upstream, so the
    // output type makes it required even though a caller may not have set it.
    id: "kk-min",
    userId: "u1",
    tags: [],
  },
  {
    // Explicit nulls where the schema says nullish -- distinct from absent, and
    // the case a hand-written parser is most likely to trip over.
    id: "kk-nulls",
    userId: "u2",
    url: null,
    title: null,
    content: null,
    createdAt: null,
    summary: null,
    tags: ["单个中文标签"],
    datePublished: null,
    dateModified: null,
  },
];

const SEARCH_FULL: SearchOptions = {
  query: "kubernetes 探针",
  filter: [
    { type: "eq", field: "userId", value: "u1" },
    { type: "in", field: "id", values: ["kk-full", "kk-min"] },
  ],
  limit: 5,
  offset: 1,
  sort: [{ field: "createdAt", order: "asc" }],
};

// --- run --------------------------------------------------------------------

// Keyed by label, so each captured call is answered with the reply the Python
// routes really produced for *that* call rather than a shared stand-in. The file
// is written by tests/test_karakeep_contract.py; a missing key means the two
// artifacts have drifted apart and the assertions below would be testing a `{}`.
const replies = (JSON.parse(readFileSync(REPLIES, "utf8")) as {
  by_label?: Record<string, unknown>;
}).by_label;
if (!replies) fail("replies.json has no `by_label`; run the Python contract test first");

function step(name: string): void {
  label = name;
  if (!(name in replies!)) fail(`replies.json has no reply for ${name}`);
  reply = replies![name];
}

process.env.FACETMARK_URL = `${BASE}/`;   // trailing slash on purpose: getClient strips it
process.env.FACETMARK_TOKEN = TOKEN;

if (!FacetmarkProvider.isConfigured()) fail("isConfigured() false with both vars set");
const client = await new FacetmarkProvider().getClient();

step("addDocuments");
await client.addDocuments(DOCS);

step("addDocuments_retry_unbatched");
await client.addDocuments([DOCS[1]!], { batch: false });

step("deleteDocuments");
await client.deleteDocuments(["kk-nulls", "kk-does-not-exist"]);

step("search_full");
const full: SearchResponse = await client.search(SEARCH_FULL);

step("search_minimal");
const minimal: SearchResponse = await client.search({ query: "sourdough" });

step("clearIndex");
await client.clearIndex();

// The two early returns must not reach the network at all.
const before = recorded.length;
label = "must_not_request";
await client.addDocuments([]);
await client.deleteDocuments([]);
if (recorded.length !== before) fail("an empty batch produced an HTTP request");

globalThis.fetch = realFetch;

// --- assert this side parsed the Python reply correctly ---------------------

let hitsSeen = 0;
for (const [name, r] of [["search_full", full], ["search_minimal", minimal]] as const) {
  if (!Array.isArray(r.hits)) fail(`${name}: hits is not an array`);
  for (const h of r.hits) {
    hitsSeen += 1;
    if (typeof h.id !== "string") {
      fail(`${name}: hit id is ${typeof h.id}, karakeep's SearchResult.id is string`);
    }
    if (h.score !== undefined && typeof h.score !== "number") {
      fail(`${name}: hit score is ${typeof h.score}`);
    }
  }
  // Both are required in karakeep's SearchResponse. A route that omits either
  // one type-checks here and breaks there, which is exactly the class of bug
  // a single-language test cannot see.
  if (typeof r.totalHits !== "number") fail(`${name}: totalHits is ${typeof r.totalHits}`);
  if (typeof r.processingTimeMs !== "number") {
    fail(`${name}: processingTimeMs is ${typeof r.processingTimeMs}`);
  }
}
// An assertion that never runs is not an assertion. `search_full` legitimately
// comes back empty -- it asks for offset 1 of a single match, which is the
// pagination contract working -- so the check above would be vacuous if the
// other query did not return a row.
if (hitsSeen === 0) fail("no reply carried a hit; the per-hit checks never ran");
if (full.hits.length !== 0 || full.totalHits !== 1) {
  fail(`search_full should page past its only match: got ${full.hits.length}/${full.totalHits}`);
}

// --- emit -------------------------------------------------------------------

const out = JSON.stringify({ base: BASE, calls: recorded }, null, 2) + "\n";
const check = process.argv.includes("--check");
if (check) {
  const have = readFileSync(WIRE, "utf8");
  if (have !== out) {
    fail(
      "wire.json is stale -- the plugin now sends something different.\n" +
      "  Run `npm run contract` and commit the result, then make sure\n" +
      "  tests/test_karakeep_contract.py still passes against it.",
    );
  }
  console.log(`contract: wire.json matches (${recorded.length} calls)`);
} else {
  writeFileSync(WIRE, out);
  console.log(`contract: wrote wire.json (${recorded.length} calls)`);
}
