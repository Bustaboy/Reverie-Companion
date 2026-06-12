export interface MemoryMetadata {
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
  created_at?: string;
  edited_at?: string;
  edited_by?: string;
  stored_by?: string;
  [key: string]: unknown;
}

export interface MemoryRecord {
  id: string;
  text: string;
  score?: number;
  metadata: MemoryMetadata;
  created_at: string;
  updated_at: string;
  source: string;
}

export interface MemoryListResponse {
  memories: MemoryRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MemoryFilters {
  query?: string;
  character?: string;
  theme?: string;
  memory_type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface MemoryUpdateRequest {
  text?: string;
  metadata?: MemoryMetadata;
}

export interface MemoryUpdateResponse {
  memory: MemoryRecord;
}

export interface MemoryBulkDeleteRequest {
  ids?: string[];
  older_than?: string;
  query?: string;
  character?: string;
  theme?: string;
  memory_type?: string;
  max_delete?: number;
}

export interface MemoryBulkDeleteResponse {
  deleted: number;
  deleted_ids: string[];
  requested: number;
}
