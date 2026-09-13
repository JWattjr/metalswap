# Data feasibility record

Status: synthetic-evidence demo by design; real-price settlement is not claimed.

## Candidate source checks

- XAUS documents a public no-key `/api/v1/intraday` series for both gold and silver, sampled every two minutes and retained for 14 days. It also says its indicative mid-market values are not settlement-grade. Source: https://xaus.com/api/
- AlyawmGold documents no-key history for both metals, but only `daily`, `monthly`, and `yearly` intervals. Source: https://alyawmgold.com/developers
- A free daily-only or key-gated source cannot satisfy this 15-minute boundary without changing the product, so it is not silently mixed into settlement.

## Frozen demo configuration

- Instruments: `SYNTHETIC-XAUUSD-SPOT` and `SYNTHETIC-XAGUSD-SPOT`.
- Currency/unit: USD per troy ounce; positive integer prices with scale `1_000_000`.
- Interval: 900 seconds, UTC quarter-hour start/end.
- Evidence schema: `metalswap-evidence-v1`; exact four observations, exact boundary timestamps in the synthetic fixture.
- Real-feed selection policy to prove before enabling: latest observation at or before each boundary, maximum 180-second observation gap, maximum 60-second cross-metal timestamp skew, reject stale/missing/conflicting observations.
- Settlement deadline: 10 minutes after expiry; three bounded evidence attempts, then deterministic refund.
- Conflict handling: `PENDING_EVIDENCE`, followed by deadline refund without fee.

## Permissions limitation

No secret key is placed in the contract. Any real source must be publicly retrievable by validators or moved behind a documented permissionless, independently auditable source; browser chart data is never settlement evidence.

