/**
 * Hand-translated stub of karakeep's `packages/shared/plugins.ts`.
 *
 * Only the Search branch of `PluginTypeMap` is reproduced faithfully. The three
 * other client types are declared as opaque brands: this plugin never registers
 * a Queue, RateLimit or VectorStore provider, and giving them real shapes would
 * mean vendoring three more upstream modules for no added checking. Branding
 * them (rather than aliasing them to `unknown`) keeps `register()` from silently
 * accepting a Search provider under the wrong `PluginType`.
 *
 * Provenance is pinned in ../../upstream-pins.json by git blob SHA.
 */

import type { SearchIndexClient } from "./search";

export declare enum PluginType {
  Search = "search",
  Queue = "queue",
  RateLimit = "ratelimit",
  VectorStore = "vectorstore",
}

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
