# MetalSwap architecture boundary

MetalSwap keeps the browser useful but untrusted.

```text
wallet -> place_position() -> frozen market + position
                         |
expiry -> request_settlement() -> GenLayer validators independently fetch evidence
                         |
                         +-> exact canonical four-observation result
                         +-> deterministic cross multiplication + pari-mutuel accounting
                         |
protocol finality -> finalized claim gate -> claim_position() / refund
```

## Browser/frontend owns

- The compact terminal, countdown, chart rendering, non-authoritative payout preview, cached public reads, wallet connection, transaction links, and explicit loading/stale/RPC/error states.
- Synthetic replay fixtures and convenience history, with a label at every point where a visitor could mistake them for live settlement evidence.

## GenLayer contract owns

- Frozen market terms, quarter-hour cutoff, positions, pool accounting, fee, settlement retries/deadline, canonical evidence schema, validator agreement, exact fixed-point comparison, deterministic refund/payout arithmetic, and duplicate/double-claim guards.
- No LLM arithmetic, no frontend-selected winner, no arbitrary admin winner, and no claim before a separately recorded finalized settlement boundary.

## External sources own

Raw observations. The target real source is an approved pair of public XAUS intraday endpoints for XAU and XAG, but the current build defaults to synthetic evidence until validator-side retrieval, timestamp coverage, and permissions are proven.

