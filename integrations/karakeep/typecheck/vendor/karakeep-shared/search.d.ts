/**
 * Hand-translated stub of karakeep's `packages/shared/search.ts`.
 *
 * The upstream file derives `BookmarkSearchDocument` from a zod schema and
 * imports `PluginManager`, so it cannot be dropped in here without pulling zod
 * and the rest of `@karakeep/shared` along with it. This file states the same
 * types directly, with the zod inference resolved by hand:
 *
 *   - `z.string().nullish()`          -> `key?: string | null`
 *   - `z.date().nullish()`            -> `key?: Date | null`
 *   - `z.array(z.string()).default([])` -> `tags: string[]`  (output type, required)
 *
 * Provenance is pinned in ../../upstream-pins.json by git blob SHA. Run
 * ../../check-upstream-drift.sh to find out whether upstream has moved; if it
 * has, this stub is stale and the typecheck it backs is worth less than it
 * looks.
 */

export interface BookmarkSearchDocument {
  id: string;
  userId: string;
  url?: string | null;
  title?: string | null;
  linkTitle?: string | null;
  description?: string | null;
  content?: string | null;
  metadata?: string | null;
  fileName?: string | null;
  createdAt?: string | null;
  note?: string | null;
  summary?: string | null;
  tags: string[];
  publisher?: string | null;
  author?: string | null;
  datePublished?: Date | null;
  dateModified?: Date | null;
}

export type SortOrder = "asc" | "desc";
export type SortableAttributes = "createdAt";

export type FilterableAttributes = "userId" | "id";
export type FilterQuery =
  | {
      type: "eq";
      field: FilterableAttributes;
      value: string;
    }
  | {
      type: "in";
      field: FilterableAttributes;
      values: string[];
    };

export interface SearchResult {
  id: string;
  score?: number;
}

export interface SearchOptions {
  query: string;
  filter?: FilterQuery[];
  limit?: number;
  offset?: number;
  sort?: { field: SortableAttributes; order: SortOrder }[];
}

export interface SearchResponse {
  hits: SearchResult[];
  totalHits: number;
  processingTimeMs: number;
}

export interface IndexingOptions {
  /**
   * Whether to batch requests. Defaults to true.
   * Set to false to bypass batching for improved reliability (e.g., on retries).
   */
  batch?: boolean;
}

export interface SearchIndexClient {
  addDocuments(
    documents: BookmarkSearchDocument[],
    options?: IndexingOptions,
  ): Promise<void>;
  deleteDocuments(ids: string[], options?: IndexingOptions): Promise<void>;
  search(options: SearchOptions): Promise<SearchResponse>;
  clearIndex(): Promise<void>;
}

export declare function getSearchClient(): Promise<SearchIndexClient | null>;
