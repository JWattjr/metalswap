# Data feasibility record

Status: XAUS paired observations are verified for a named, wallet-free historical replay. The completed payout proof remains synthetic. No official benchmark or executable-price claim is made.

## Time-boxed source investigation

On 2026-09-14, both public XAUS requests were fetched successfully without credentials:

- `GET https://xaus.com/api/v1/intraday?symbol=xau&hours=48`
- `GET https://xaus.com/api/v1/intraday?symbol=xag&hours=48`

The observed responses were HTTP 200 JSON with `symbol` values `xau` and `xag`, `currency=USD`, `unit=troy_oz`, `interval_seconds=120`, fresh `data_state.source=sampler`, and usable 48-hour response windows. The documented retention is 14 days. XAUS documents no API key, no hard rate limit for reasonable use, a 30-second client cache expectation, and contact above 10,000 requests/day. Source policy and field semantics: https://xaus.com/api/

The provider identifies the instruments as XAU/USD spot and XAG/USD spot in USD per troy ounce. It explicitly describes the values as indicative mid-market rates and says they are not settlement-grade, tradable quotes, or suitable for execution or contractual valuation. MetalSwap therefore uses the source only for a clearly labeled historical replay/comparison case. A future market must not be presented as fair trading or official benchmark settlement.

The public case `xaus-2026-09-14-09-00-00z` records the actual selected observations, source URLs, retrieval metadata, canonical hash, and the comparison result. The archived case is proof material, not a substitute for validator-side source retrieval.

Other checks:

- AlyawmGold documents no-key history for both metals, but only `daily`, `monthly`, and `yearly` intervals. Source: https://alyawmgold.com/developers
- A daily-only or key-gated source cannot satisfy this 15-minute boundary without changing the product, so it is not silently mixed into settlement.

## Frozen observation policy

- Synthetic instruments: `SYNTHETIC-XAUUSD-SPOT` and `SYNTHETIC-XAGUSD-SPOT`.
- XAUS instruments: `XAUUSD` and `XAGUSD`, sourced from the provider's `xau` and `xag` series.
- Currency/unit: USD per troy ounce; positive integer prices with scale `1_000_000`.
- Interval: 900 seconds, UTC quarter-hour start/end.
- Evidence schema: `metalswap-evidence-v1`.
- Synthetic selection: exact boundary observation.
- XAUS selection: latest observation at or before each boundary; maximum 180-second boundary staleness; maximum 60-second cross-metal timestamp skew; reject stale, missing, out-of-order, conflicting, wrong-instrument, wrong-unit, malformed, or overlarge source data.
- Validators fetch both XAUS endpoints independently inside the nondeterministic settlement call. The contract does not use the hosted comparison page as settlement evidence.
- Settlement deadline: 10 minutes after expiry; three bounded evidence attempts, then deterministic refund.
- Conflict handling: `PENDING_EVIDENCE`, followed by deadline refund without fee.

## Permissions limitation

No secret key is placed in the contract. The XAUS path is explicitly indicative and replay-oriented; it is not a production oracle. Browser chart data and the self-hosted comparison archive are never settlement evidence.
