/**
 * A karakeep Search plugin that forwards ranking to a facetmark service.
 *
 * karakeep's search is a plugin (`packages/shared/search.ts`): four methods, and
 * nothing else in the codebase assumes MeiliSearch is behind them. This file is
 * the whole TypeScript side of the integration -- all the retrieval logic lives
 * in the Python service, reachable over HTTP on localhost.
 *
 * WHAT IS AND IS NOT CHECKED. `integrations/karakeep/typecheck` runs `tsc` over
 * this file against hand-written stubs of karakeep's two interface modules, so
 * the four method signatures below are known to satisfy `SearchIndexClient` and
 * the registration in ../index.ts is known to typecheck. The stubs are pinned to
 * upstream by git blob SHA; `npm run check-drift` says whether they are stale.
 *
 * The bytes are checked too, as of the wire contract in `../../contract`. That
 * harness drives this class the way karakeep drives it -- environment variables,
 * `getClient()`, the four methods -- with `globalThis.fetch` replaced by a
 * recorder, and commits the resulting request bodies. `tests/test_karakeep_-
 * contract.py` replays those exact bodies through the real FastAPI app and
 * commits the replies, which the capture then feeds back here. So each language
 * asserts against an artifact the other one produced, and a field this file
 * starts sending that the Python model would silently drop is now a test
 * failure rather than a bug report.
 *
 * What none of that covers: this has never run inside a live karakeep, against a
 * real MeiliSearch-shaped index, or with more than one user. A format contract
 * is not an integration test.
 *
 * Install into a karakeep checkout (paths as of the pinned SHAs):
 *   1. copy this folder to `packages/plugins/search-facetmark/` -- it is a
 *      folder inside the `@karakeep/plugins` package, not a package of its own
 *   2. add `"./search-facetmark": "./search-facetmark/index.ts"` to the
 *      `exports` map in `packages/plugins/package.json`
 *   3. add `await import("@karakeep/plugins/search-facetmark");` to
 *      `loadAllPlugins()` in `packages/shared-server/src/plugins.ts`, AFTER the
 *      `search-meilisearch` line -- `PluginManager.getClient` returns the last
 *      registered provider, so ordering is what decides which one serves search
 *   4. set FACETMARK_URL and FACETMARK_TOKEN (from `facetmark token`)
 *
 * Both variables must be set or `isConfigured()` returns false and karakeep
 * falls back to whatever other Search plugin registered -- a missing token is
 * not treated as "no auth needed".
 */

import type { PluginProvider } from "@karakeep/shared/plugins";
import type {
  BookmarkSearchDocument,
  IndexingOptions,
  SearchIndexClient,
  SearchOptions,
  SearchResponse,
} from "@karakeep/shared/search";

const ENV_URL = "FACETMARK_URL";
const ENV_TOKEN = "FACETMARK_TOKEN";

interface FacetmarkSearchReply {
  hits: { id: string; score?: number }[];
  totalHits: number;
  processingTimeMs: number;
  engine?: string;
  truncated?: boolean;
}

class FacetmarkClient implements SearchIndexClient {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
    private readonly timeoutMs = 20_000,
  ) {}

  private async call<T>(path: string, body?: unknown): Promise<T> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${this.token}`,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
      if (!res.ok) {
        throw new Error(`facetmark ${path} -> ${res.status} ${await res.text()}`);
      }
      return (await res.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * karakeep batches these through `batchingDocumentQueue`, so a batch arriving
   * here is already the unit it wants indexed. `batch: false` means karakeep is
   * retrying a single document after a failure, and the Python side is told to
   * embed it inline either way -- the document has to be searchable when this
   * promise resolves.
   */
  async addDocuments(
    documents: BookmarkSearchDocument[],
    _options?: IndexingOptions,
  ): Promise<void> {
    if (documents.length === 0) return;
    await this.call("/karakeep/documents", { documents, embed: true });
  }

  async deleteDocuments(ids: string[], _options?: IndexingOptions): Promise<void> {
    if (ids.length === 0) return;
    await this.call("/karakeep/documents/delete", { ids });
  }

  async search(options: SearchOptions): Promise<SearchResponse> {
    const reply = await this.call<FacetmarkSearchReply>("/karakeep/search", {
      query: options.query ?? "",
      filter: options.filter ?? [],
      limit: options.limit ?? 20,
      offset: options.offset ?? 0,
      sort: options.sort ?? [],
    });
    return {
      hits: reply.hits.map((h) => ({ id: h.id, score: h.score })),
      totalHits: reply.totalHits,
      processingTimeMs: reply.processingTimeMs,
    };
  }

  async clearIndex(): Promise<void> {
    await this.call("/karakeep/clear");
  }
}

export class FacetmarkProvider implements PluginProvider<SearchIndexClient> {
  static isConfigured(): boolean {
    return Boolean(process.env[ENV_URL] && process.env[ENV_TOKEN]);
  }

  private client: FacetmarkClient | null = null;

  async getClient(): Promise<SearchIndexClient> {
    if (!this.client) {
      const url = (process.env[ENV_URL] ?? "").replace(/\/+$/, "");
      const token = process.env[ENV_TOKEN] ?? "";
      if (!url || !token) {
        throw new Error(`${ENV_URL} and ${ENV_TOKEN} must both be set`);
      }
      this.client = new FacetmarkClient(url, token);
    }
    return this.client;
  }
}
