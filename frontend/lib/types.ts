export type Side = "GOLD" | "SILVER";

export type MarketState =
  | "UPCOMING"
  | "LIVE"
  | "AWAITING_SETTLEMENT"
  | "PENDING_EVIDENCE"
  | "AWAITING_FINALITY"
  | "CLAIMABLE"
  | "REFUND";

export type TransactionState = "IDLE" | "SUBMITTED" | "DECIDED" | "FINALIZED" | "FAILED";

export interface ContractMarket {
  exists?: boolean;
  market_id?: string;
  start_at?: string;
  end_at?: string;
  settlement_deadline?: string;
  evidence_url?: string;
  source_id?: string;
  rule_version?: string;
  fee_bps?: number;
  fee_percent_display?: string;
  price_scale?: number;
  gold_pool?: number;
  silver_pool?: number;
  total_staked?: number;
  settlement_state?: string;
  settlement_attempts?: number;
  last_reason_code?: string;
  gold_opening_timestamp?: string;
  gold_closing_timestamp?: string;
  silver_opening_timestamp?: string;
  silver_closing_timestamp?: string;
  gold_opening_price?: number;
  gold_closing_price?: number;
  silver_opening_price?: number;
  silver_closing_price?: number;
  evidence_hash?: string;
  outcome?: string;
  distributable_pool?: number;
  fee_amount?: number;
  claimed_amount?: number;
  finality_status?: string;
  status?: MarketState | string;
  created_at?: string;
}

export interface ContractAccount {
  owner?: string;
  demo_balance?: number;
  demo_credits_claimed?: boolean;
  position_count?: number;
  total_staked?: number;
  claimed_payouts?: number;
}

export interface ContractPosition {
  exists?: boolean;
  market_id?: string;
  owner?: string;
  side?: Side;
  stake?: number;
  claimed?: boolean;
  payout?: number;
  entered_at?: string;
}

export interface ClaimQuote {
  exists?: boolean;
  market_id?: string;
  side?: Side;
  stake?: number;
  payout?: number;
  claimed?: boolean;
  finality_status?: string;
  rounding_policy?: string;
}

export interface LocalPosition {
  id: string;
  marketId: string;
  side: Side;
  stake: number;
  status: "SUBMITTED" | "LOCAL_REPLAY";
  payout: number | null;
  enteredAt: string;
  txHash?: string;
}

export interface ProtocolConfig {
  fee_percent_display: string;
  max_settlement_attempts: number;
  settlement_grace_seconds: number;
  max_gap_seconds: number;
  max_skew_seconds: number;
  price_scale: number;
  source_id: string;
  source_base_url: string;
  evidence_schema_version: string;
  rule_version: string;
  selection_rule: string;
  gold_instrument: string;
  silver_instrument: string;
  currency: string;
  unit: string;
  synthetic_demo: boolean;
  finality_gate_configured: boolean;
}
