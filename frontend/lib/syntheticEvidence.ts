import { createHash } from "node:crypto";

export const SYNTHETIC_SOURCE_ID = "metalswap-synthetic-evidence-v1";
export const EVIDENCE_SCHEMA_VERSION = "metalswap-evidence-v1";
export const SELECTION_RULE = "exact_boundary_observation";

function canonicalJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, Object.keys(value).sort());
}

function hashPayload(value: Record<string, unknown>): string {
  return `sha256:${createHash("sha256").update(canonicalJson(value), "utf8").digest("hex")}`;
}

function parseMarketId(marketId: string): string | null {
  const match = /^market-(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$/.exec(marketId);
  return match?.[1] ?? null;
}

export function makeSyntheticEvidence(marketId: string, origin: string) {
  const start = parseMarketId(marketId);
  if (!start) return null;
  const startDate = new Date(start);
  if (Number.isNaN(startDate.valueOf()) || startDate.getUTCMinutes() % 15 !== 0 || startDate.getUTCSeconds() !== 0) return null;
  const end = new Date(startDate.valueOf() + 900_000).toISOString().replace(".000Z", "Z");
  const seed = startDate.getUTCHours() * 4 + startDate.getUTCMinutes() / 15;
  const evidenceUrl = `${origin.replace(/\/$/, "")}/evidence/${marketId}.json`;
  const payload = {
    schema_version: EVIDENCE_SCHEMA_VERSION,
    status: "FINALIZED",
    market_id: marketId,
    source_id: SYNTHETIC_SOURCE_ID,
    evidence_url: evidenceUrl,
    currency: "USD",
    unit: "USD_PER_TROY_OUNCE",
    selection_rule: SELECTION_RULE,
    max_gap_seconds: 0,
    max_skew_seconds: 0,
    gold_opening_timestamp: start,
    gold_opening_price: 2350000000 + seed * 700000,
    gold_closing_timestamp: end,
    gold_closing_price: 2350000000 + seed * 700000 + (seed % 3 === 0 ? 700000 : -300000),
    silver_opening_timestamp: start,
    silver_opening_price: 28160000 + seed * 5000,
    silver_closing_timestamp: end,
    silver_closing_price: 28160000 + seed * 5000 + (seed % 3 === 0 ? 110000 : -20000),
    evidence_hash: "",
    reason_code: "NONE",
  };
  const { evidence_hash: _unused, ...withoutHash } = payload;
  return { ...payload, evidence_hash: hashPayload(withoutHash) };
}
