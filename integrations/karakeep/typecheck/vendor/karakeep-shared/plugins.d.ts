/**
 * Hand-translated stub of karakeep's `packages/shared/plugins.ts`.
 *
 * Only the Search branch of `PluginTypeMap` is reproduced faithfully. The other
 * client types are declared as opaque brands so `register()` rejects a Search
 * provider under the wrong `PluginType`.
 *
 * Provenance is pinned in ../../upstream-pins.json by git blob SHA.
 */

import type { SearchIndexClient } from "./search";

export declare enum PluginType {
  AssetStore = "assetstore",
  Search = "search",
  Queue = "queue",
  RateLimit = "ratelimit",
  VectorStore = "vectorstore",
}

declare const ASSET_STORE: unique symbol;
declare const QUEUE_CLIENT: unique symbol;
declare const RATE_LIMIT_CLIENT: unique symbol;
declare const VECTOR_STORE_CLIENT: unique symbol;

export interface QueueClient {
  readonly [QUEUE_CLIENT]: never;
}
export interface RateLimitClient {
  readonly [RATE_LIMIT_CLIENT]: never;
}
export interface VectorStoreClient {
  readonly [VECTOR_STORE_CLIENT]: never;
}

interface PluginTypeMap {
  [PluginType.AssetStore]: { readonly [ASSET_STORE]: never };
  [PluginType.Search]: SearchIndexClient;
  [PluginType.Queue]: QueueClient;
  [PluginType.RateLimit]: RateLimitClient;
  [PluginType.VectorStore]: VectorStoreClient;
}

export interface PluginProvider<T> {
  getClient(): Promise<T | null>;
}

export interface TPlugin<T extends PluginType> {
  type: T;
  name: string;
  provider: PluginProvider<PluginTypeMap[T]>;
}

export declare class PluginManager {
  static register<T extends PluginType>(plugin: TPlugin<T>): void;
  static getClient<T extends PluginType>(
    type: T,
  ): Promise<PluginTypeMap[T] | null>;
  static isRegistered<T extends PluginType>(type: T): boolean;
  static getPluginName<T extends PluginType>(type: T): string | null;
  static logAllPlugins(): void;
}
