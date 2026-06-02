/** Solo operator supervisor session quick-start presets (mirrors backend ids). */

export interface SoloSessionPreset {
  id: string;
  label: string;
  lane: string;
  goal: string;
  runtime_mode: "inprocess" | "durable";
  roles: string[];
  retrieval_contract: string;
  skills: string[];
}

export interface SoloSessionPresetsResponse {
  count: number;
  presets: SoloSessionPreset[];
}

export const SOLO_PRESET_LANE_LABEL: Record<string, string> = {
  po: "Bank PO",
  marketing: "Marketing",
  trading: "Trading",
  sales: "Sales / Lead Gen",
  ops: "Ops",
};
