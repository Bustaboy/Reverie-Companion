export interface CharacterSummary {
  character_id: string;
  display_name: string;
  pronouns: string;
  adult_age_range: string;
  species_or_type: string;
  relationship_dynamic: string;
  core_traits: string[];
  updated_at: string;
}

export interface CharacterIdentity {
  display_name: string;
  pronouns: string;
  adult_age_range: string;
  species_or_type: string;
  origin_archetype?: string | null;
  tags: string[];
  creator_notes?: string | null;
  adult_only_confirmed: boolean;
}

export interface CharacterBlueprint {
  schema_version: number;
  character_id: string;
  identity: CharacterIdentity;
  relationship?: {
    relationship_dynamic?: string | null;
    default_intimacy_level?: string | null;
    [key: string]: unknown;
  };
  personality?: {
    core_traits?: string[];
    self_concept?: string | null;
    [key: string]: unknown;
  };
  communication?: {
    style_notes?: string | null;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface CharacterListResponse {
  characters: CharacterSummary[];
}

export interface CharacterResponse {
  character: CharacterBlueprint;
}

export interface CharacterCreateInput {
  character_id?: string;
  display_name: string;
  pronouns?: string;
  species_or_type?: string;
  relationship_dynamic?: string;
  core_traits?: string[];
  creator_notes?: string;
}
