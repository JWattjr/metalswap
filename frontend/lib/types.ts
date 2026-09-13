export type Side = "GOLD" | "SILVER";

export type ContractNumber = bigint | number | string;

export type MarketState =
  | "UPCOMING"
  | "LIVE"
  | "AWAITING_SETTLEMENT"
  | "PENDING_EVIDENCE"
  | "AWAITING_FINALITY"
  | "CLAIMABLE"
  | "REFUND";

export type TransactionState = "IDLE" | "SUBMITTED" | "PROVISIONAL" | "FINALIZED" | "FAILED";

export interface ContractMarket {
  exists?: boolean;
  market_id?: string;
  start_at?: string;
  end_at?: string;
  settlement_deadline?: string;
  evidence_url?: string;
  source_id?: string;
  rule_version?: string;
  fee_bps?: ContractNumber;
  fee_percent_display?: string;
  price_scale?: ContractNumber;
  gold_pool?: ContractNumber;
  silver_pool?: ContractNumber;
  total_staked?: ContractNumber;
  settlement_state?: string;
  settlement_attempts?: ContractNumber;
  last_reason_code?: string;
  gold_opening_timestamp?: string;
  gold_closing_timestamp?: string;
  silver_opening_timestamp?: string;
  silver_closing_timestamp?: string;
  gold_opening_price?: ContractNumber;
  gold_closing_price?: ContractNumber;
  silver_opening_price?: ContractNumber;
  silver_closing_price?: ContractNumber;
  evidence_hash?: string;
  outcome?: string;
  distributable_pool?: ContractNumber;
  fee_amount?: ContractNumber;
  claimed_amount?: ContractNumber;
  finality_status?: string;
  status?: MarketState | string;
  created_at?: string;
}
export interface ContractAccount {
  owner?: string;
  demo_balance?: ContractNumber;
  demo_credits_claimed?: boolean;
  position_count?: ContractNumber;
  total_staked?: ContractNumber;
  claimed_payouts?: ContractNumber;
}

export interface ContractPosition {
  exists?: boolean;
  market_id?: string;
  owner?: string;
  side?: Side;
  stake?: ContractNumber;
  claimed?: boolean;
  payout?: ContractNumber;
  entered_at?: string;
}

export interface ClaimQuote {
  exists?: boolean;
  market_id?: string;
  side?: Side;
  stake?: ContractNumber;
  payout?: ContractNumber;
  claimed?: boolean;
  finality_status?: string;
  rounding_policy?: string;
}

export interface ChainPositionView {
  position: ContractPosition;
  market: ContractMarket | null;
  quote: ClaimQuote | null;
}

export interface LocalPosition {
  id: string;
  marketId: string;
  side: Side;
  stake: bigint;
  status: "LOCAL_REPLAY";
  payout: bigint | null;
  enteredAt: string;
}

export interface ProtocolConfig {
  fee_percent_display: string;
  max_settlement_attempts: ContractNumber;
  max_market_horizon_seconds?: ContractNumber;
  settlement_grace_seconds: ContractNumber;
  max_gap_seconds: ContractNumber;
  max_skew_seconds: ContractNumber;
  price_scale: ContractNumber;
  source_id: string;
  source_base_url: string;
  source_base_configured?: boolean;
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
