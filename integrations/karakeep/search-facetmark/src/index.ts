/**
 * A karakeep Search plugin that forwards ranking to a facetmark service.
 *
 * karakeep's search is a plugin (`packages/shared/search.ts`): four methods, and
 * nothing else in the codebase assumes MeiliSearch is behind them. This file is
 * the whole TypeScript side of the integration -- all the retrieval logic lives
 * in the Python service, reachable over HTTP on localhost.
 *
 * NOT BUILT OR TESTED IN THIS REPOSITORY. facetmark has no Node toolchain and no
 * karakeep checkout in CI, so this file is typechecked by karakeep's build and by
 * nothing here. The Python side it talks to is covered by
 * `tests/test_karakeep_bridge.py` and `tests/test_api.py::TestKarakeepRoutes`,
 * which pin the exact request and response shapes used below.
 *
 * Install into a karakeep checkout:
 *   1. copy this folder to `packages/plugins/search-facetmark/`
 *   2. add `@karakeep/plugin-search-facetmark` to the web app's dependencies and
 *      import it next to the other plugin imports in the server entrypoint
 *   3. set FACETMARK_URL and FACETMARK_TOKEN (from `facetmark token`)
 *
 * Both variables must be set or `isConfigured()` returns false and karakeep
 * falls back to whatever other Search plugin registered -- a missing token is
 * not treated as "no auth needed".
 */

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

export class FacetmarkProvider {
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
