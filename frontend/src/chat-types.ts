export type ChatSource = {
  n?: number;
  bookmark_id: number | null;
  title: string;
  ai_title?: string;
  url: string;
  summary?: string;
  basis: string;
  source_hash?: string;
  content_updated_at?: number | null;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "pending" | "error" | "cancelled";
  sources: ChatSource[];
  model: string;
  created_at: number;
  request_id?: string;
};

export type ConversationSummary = {
  id: string;
  title: string;
  bookmark_ids: number[];
  created_at: number;
  updated_at: number;
  message_count?: number;
  running: boolean;
  profile_id?: string;
};

export type Conversation = ConversationSummary & {
  messages: ChatMessage[];
  delivery?: { request_id: string; accepted: boolean; running: boolean };
};

export type ChatLaunch = { nonce: number; bookmark_ids: number[]; title?: string };
