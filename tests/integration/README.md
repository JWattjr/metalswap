# Live finality / claim runbook

The production deployment is deliberately not driven through Portal by this repository. Use the configured GenLayer account and the observed addresses in `deploy/last-deployment.json` when a live end-to-end pass is needed.

The corrected live application bindings are MetalSwap `0xeB7AB5de64139fD9F9F42D451076c62F22865dE7` and SettlementGate `0x49dE8861037C76d4a955091b16020aBF5818f90B`. The deployment-time market is empty and source-bound; it is not a completed XAUS settlement. The preserved completed synthetic proof is linked from `deploy/DEPLOYMENT.md`.

The direct suite proves the deterministic paths locally. `test_metalswap_flow.py` deploys a fresh wired gate/market pair and checks the live write/read boundary; this runbook covers the longer settlement and claim lifecycle that requires a real GenLayer message lifecycle:

1. Preflight both XAUS URLs and require HTTP 2xx before opening/funding a real-source market. The exact source is `https://xaus.com/api/v1/intraday?hours=48`; validators append `&symbol=xau` and `&symbol=xag`. If either returns 503, stop and record the source outage; do not call the archived comparison proof a live settlement.
2. The owner calls `open_next_market` (or `open_market`) for a future UTC quarter-hour. `open_next_market` is owner-only; `request_settlement` is permissionless after expiry. Read `get_current_market` and confirm `status=UPCOMING`, the XAUS source URL, and the interval.
3. Have two testnet accounts call `claim_demo_credits`, then place one GOLD and one SILVER position before `start_at`.
4. After `end_at`, a non-owner may call `request_settlement`. Wait for the parent transaction to be `FINALIZED` and execution `SUCCESS`, then read `SettlementGate.get_finality(market_id)`. The gate record must be present before any claim is attempted.
5. Read `get_market` and confirm a non-empty evidence hash, four stored prices/timestamps, outcome, `fee_amount`, `distributable_pool`, and `finality_status` match the gate record. A second `request_settlement(market_id)` must leave `settlement_attempts` unchanged.
6. From the winning account, call `claim_position(market_id, side)` and wait for its finalized receipt. Read `get_position` and `get_account`; the position must be marked `claimed` and the payout must be credited once. Repeating the same `claim_position` call must fail with `[EXPECTED] position already claimed`.
7. To exercise the late path, use a fresh market whose evidence response is unavailable or invalid. Call settlement until it remains `PENDING_EVIDENCE`, then after `settlement_deadline` call `refund_after_deadline`. The market must become `REFUND`, `fee_amount` must remain zero, and each position must quote its original stake.

Run the automated wiring smoke test with:

```powershell
$env:METALSWAP_INTEGRATION_SOURCE_BASE_URL = "https://xaus.com/api/v1/intraday"
gltest tests/integration/test_metalswap_flow.py -v -s
```

Use an HTTPS directory such as `https://<host>/evidence/` only for disposable synthetic integration fixtures. It does not prove independent XAUS retrieval. The `live_demo` test with the exact XAUS source is the real-source path and should not be reported as complete unless both validator reads agree and the gate, payout, duplicate rejection, and post-rotation historical read are observed.

Useful read-only commands:

```powershell
genlayer network set studionet
genlayer call 0xeB7AB5de64139fD9F9F42D451076c62F22865dE7 get_current_market
genlayer call 0xeB7AB5de64139fD9F9F42D451076c62F22865dE7 get_protocol_config
genlayer call 0x49dE8861037C76d4a955091b16020aBF5818f90B get_gate_status
```

Do not record a market as claimable from an `ACCEPTED` receipt alone. The UI and contract both treat the `SettlementGate` record as the claim boundary.
