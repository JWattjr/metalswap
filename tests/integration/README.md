# Live finality / claim runbook

The production deployment is deliberately not driven through Portal by this repository. Use the configured GenLayer account and the observed addresses in `deploy/last-deployment.json` when a live end-to-end pass is needed.

The direct suite proves the deterministic paths locally. `test_metalswap_flow.py` deploys a fresh wired gate/market pair and checks the live write/read boundary; this runbook covers the longer settlement and claim lifecycle that requires a real GenLayer message lifecycle:

1. Read `get_current_market` and confirm `status=UPCOMING`, the source URL is `https://metal-swap.vercel.app/evidence/`, and the market interval is a future UTC quarter-hour.
2. Have two testnet accounts call `claim_demo_credits`, then place one GOLD and one SILVER position before `start_at`.
3. After `end_at`, call `request_settlement`. Wait for the parent transaction to be `FINALIZED`, then read `SettlementGate.get_finality(market_id)`. The gate record must be present before any claim is attempted.
4. Read `get_market` and confirm the outcome, `fee_amount`, `distributable_pool`, four stored prices, and `finality_status` match the gate record. A second `request_settlement(market_id)` must leave `settlement_attempts` unchanged.
5. From the winning account, call `claim_position(market_id, side)` and wait for its finalized receipt. Read `get_position` and `get_account`; the position must be marked `claimed` and the payout must be credited once. Repeating the same `claim_position` call must fail with `[EXPECTED] position already claimed`.
6. To exercise the late path, use a fresh market whose evidence response is unavailable or invalid. Call settlement until it remains `PENDING_EVIDENCE`, then after `settlement_deadline` call `refund_after_deadline`. The market must become `REFUND`, `fee_amount` must remain zero, and each position must quote its original stake.

Run the automated wiring smoke test with:

```powershell
$env:METALSWAP_INTEGRATION_SOURCE_BASE_URL = "https://<host>/evidence/"
gltest tests/integration/test_metalswap_flow.py -v -s
```

Useful read-only commands:

```powershell
genlayer network set studionet
genlayer call 0xB615a841A33e79CC9EDB67D7dcf7C42eEeE0ce7E get_current_market
genlayer call 0xB615a841A33e79CC9EDB67D7dcf7C42eEeE0ce7E get_protocol_config
genlayer call 0x88862E86176887CE7fc611EEe3105b00eCcaac17 get_gate_status
```

Do not record a market as claimable from an `ACCEPTED` receipt alone. The UI and contract both treat the `SettlementGate` record as the claim boundary.
