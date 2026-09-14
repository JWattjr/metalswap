# MetalSwap architecture boundary

MetalSwap keeps the browser useful but untrusted.

```text
wallet -> place_position() -> frozen market + position
                         |
expiry -> request_settlement() -> GenLayer validators independently fetch frozen source
                         |
                         +-> exact canonical four-observation result (synthetic or XAUS replay)
                         +-> deterministic cross multiplication + pari-mutuel accounting
                         |
protocol finality -> finalized claim gate -> claim_position() / refund
```

## Browser/frontend owns

- The compact terminal, countdown, chart rendering, non-authoritative payout preview, cached public reads, wallet connection, transaction links, and explicit loading/stale/RPC/error states.
- Synthetic replay fixtures, the wallet-free comparison pages, and convenience history, with a label at every point where a visitor could mistake them for live settlement evidence.

## GenLayer contract owns

- Frozen market terms, quarter-hour cutoff, positions, pool accounting, fee, settlement retries/deadline, canonical evidence schema, validator agreement, exact fixed-point comparison, deterministic refund/payout arithmetic, and duplicate/double-claim guards.
- No LLM arithmetic, no frontend-selected winner, no arbitrary admin winner, and no claim before a separately recorded finalized settlement boundary.
- In XAUS mode, the contract independently fetches the `xau` and `xag` JSON series, validates USD/troy-ounce semantics and fresh sampler state, selects the latest point at or before each boundary, records actual staleness/skew, and hashes the normalized result.

## External sources own

Raw observations. XAUS publishes a public pair of intraday endpoints for XAU and XAG. The contract accepts that source only as a named indicative historical-replay mode; its own terms disclaim settlement-grade and executable-price use. The completed market payout proof remains the separately documented synthetic demonstration.
