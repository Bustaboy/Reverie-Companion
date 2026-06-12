import type { CharacterImportPreview, ExtensionCommandRequest, ExtensionCommandResult, ExtensionRegistryResponse } from '$lib/extensions/types';
export class ExtensionServiceError extends Error { constructor(message: string) { super(message); this.name = 'ExtensionServiceError'; } }
export class ExtensionService {
  constructor(private readonly baseUrl = '') {}
  async listExtensions(): Promise<ExtensionRegistryResponse> { return this.request<ExtensionRegistryResponse>('/extensions'); }
  async dispatchCommand(request: ExtensionCommandRequest): Promise<ExtensionCommandResult> { return this.request<ExtensionCommandResult>('/extensions/commands', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) }); }
  async previewCharacterImport(card: Record<string, unknown>, fileName?: string): Promise<CharacterImportPreview> { return this.request<CharacterImportPreview>('/extensions/character-import/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_format: 'auto', file_name: fileName, card }) }); }
  private async request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${this.baseUrl}${path}`, init); if (!response.ok) throw new ExtensionServiceError(`Extension API request failed with HTTP ${response.status}.`); return (await response.json()) as T; }
}
export const extensionService = new ExtensionService();
