export type PlaceHint = {
  name: string;
  city_hint?: string | null;
  address_hint?: string | null;
  category_hint?: string | null;
  evidence?: string | null;
};

export type PlaceCandidate = {
  place_id: string;
  name: string;
  formatted_address?: string | null;
  latitude: number;
  longitude: number;
  primary_type?: string | null;
  confidence: number;
};

export type Memory = {
  id: string;
  source_type: 'note' | 'screenshot' | 'link';
  source_text: string;
  source_url?: string | null;
  note?: string | null;
  resolution_status: 'unresolved' | 'resolved' | 'needs_review';
  hint?: PlaceHint | null;
  place?: PlaceCandidate | null;
};

export type FeasibleMemory = {
  memory: Memory;
  status: 'yes' | 'no' | 'uncertain';
  travel_minutes?: number | null;
  open_now?: boolean | null;
  reasons: string[];
};
