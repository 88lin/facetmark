export type SyncConfig = { folder: string; enabled: boolean; auto_sync: boolean; poll_seconds: number };
export type SyncCounts = {
  upload_new: number; upload_update: number; upload_delete: number;
  download_new: number; download_update: number; download_delete: number;
  unchanged: number; conflicts: number;
};
export type SyncPending = { request_id: string; created_at: number; folder: string; counts: SyncCounts; backup_path: string | null; error: string };
export type SyncStatus = SyncConfig & {
  configured: boolean; last_sync_at: number | null; last_sync_id?: string | null; last_error: string;
  pending_conflicts: number; needs_review: boolean; pending_operations?: SyncPending[]; config_revision?: string;
};
export type SyncMetadata = { url: string; title: string; folder: string; tags: string[]; date_added: number | null };
export type SyncConflict = {
  id: string; reason: string; can_delete?: boolean; local: SyncMetadata | null; remote: SyncMetadata | null;
  remote_versions: { choice: string; record: SyncMetadata | null }[];
};
export type SyncChange = {
  id: string; local: SyncMetadata | null; remote: SyncMetadata | null; target: SyncMetadata | null;
  directions: ("upload" | "download")[];
};
export type SyncPreview = {
  preview_id: string; expires_at: number; counts: SyncCounts; conflicts: SyncConflict[]; changes: SyncChange[];
  excluded_karakeep: number; excluded_unsupported: number;
  stale?: boolean;
};
export type SyncApplied = {
  request_id?: string; accepted?: boolean; complete?: boolean; error?: string; folder?: string;
  counts: SyncCounts; backup_path: string | null; published_commit?: string | null; status: SyncStatus;
};
export type SyncReceipt = { request_id: string; action: "configure" | "apply"; state: "pending" | "done";
  result: SyncStatus | SyncApplied; current_status: SyncStatus };
export type SyncDraft = Omit<SyncConfig, "poll_seconds"> & { poll_seconds: string };
