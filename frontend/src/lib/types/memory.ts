export interface MemoryRecordMetadata {
  user_id?: string;
  session_id?: string | null;
  memory_type?: string;
  source?: string;
  character?: string;
  character_id?: string;
  theme?: string;
  themes?: string[];
  tags?: string[];
  importance?: number;
  confidence?: number;
  journal_entry_id?: string;
  rollback_id?: string;
  provenance?: Record<string, unknown>;
  source_turn_indices?: number[];
  edited_at?: string;
  edited_by?: string;
  [key: string]: unknown;
}

export interface MemoryRecord {
  id: string;
  text: string;
  score?: number;
  metadata: MemoryRecordMetadata;
  created_at?: string;
  updated_at?: string;
  source?: string;
}

export interface MemoryListResponse {
  items: MemoryRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface MemoryDetailResponse {
  memory: MemoryRecord;
}

export interface MemoryQuery {
  q?: string;
  character?: string;
  theme?: string;
  source?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export interface MemoryUpdateInput {
  text: string;
  tags: string[];
  importance?: number | null;
  metadata?: Record<string, unknown>;
}

export interface MemoryBulkDeleteInput {
  ids?: string[];
  older_than?: string | null;
}

export interface MemoryBulkDeleteResponse {
  deleted_count: number;
}
