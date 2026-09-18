export type PlaceHint = {
  name?: string | null;
  city_hint?: string | null;
  address_hint?: string | null;
  category_hint?: string | null;
  activity_hint?: string | null;
  evidence?: string | null;
};

export type PlaceCandidate = {
  place_id: string;
  provider: string;
  provider_place_id?: string | null;
  name: string;
  aliases?: string[];
  formatted_address?: string | null;
  latitude: number;
  longitude: number;
  primary_type?: string | null;
  types: string[];
  confidence: number;
  confidence_reasons?: string[];
};

export type Memory = {
  id: string;
  source_type: 'note' | 'screenshot' | 'link';
  source_text: string;
  source_url?: string | null;
  note?: string | null;
  resolution_status: 'unresolved' | 'resolved' | 'needs_review';
  resolution_method?: 'auto' | 'manual' | 'abstained' | null;
  pre_resolution_confidence?: number | null;
  pre_resolution_gap?: number | null;
  hint?: PlaceHint | null;
  place?: PlaceCandidate | null;
  candidates: PlaceCandidate[];
};

export type FeasibleMemory = {
  memory: Memory;
  status: 'yes' | 'no' | 'uncertain';
  travel_minutes?: number | null;
  open_now?: boolean | null;
  reasons: string[];
};
