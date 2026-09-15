# MetalSwap

MetalSwap is a focused GenLayer testnet prototype for one question: over a 15-minute UTC interval, does gold or silver deliver the stronger relative return? It keeps one pair (Gold versus Silver), one interval length, and demo-credit pari-mutuel mechanics.

The current StudioNet deployment freezes XAUS's public XAU/USD and XAG/USD intraday series as a named, indicative historical-replay source. The public comparison case is not a live wager and the provider does not describe these quotes as settlement-grade or executable. The completed synthetic mechanics demonstration remains available as a separate proof case.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Public XAUS comparison: [Gold vs Silver replay](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)
- Preserved synthetic mechanics proof: [completed market proof](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)
- Exact deployment and receipt record: [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md)

Current XAUS-bound pair on GenLayer StudioNet:

- MetalSwap: `0xFffDA717B60c1EdeB786592f80Dc73b731738Ef6`
- SettlementGate: `0x57fFc7AC20db57e0aBeBdBDCd8a6157Da6982131`
- Open market at deployment readback: `market-2026-09-14T10:15:00Z`
- Source revision used for the pair: [`3adc8ec0bc2a29173db8fcac9f49cc588e3b0041`](https://github.com/JWattjr/metalswap/commit/3adc8ec0bc2a29173db8fcac9f49cc588e3b0041)

## What is implemented

- UTC quarter-hour markets with entry closing at the frozen start boundary.
- GOLD / SILVER selection and a fully funded pari-mutuel demo-credit pool.
- A 2% fee frozen in the contract before markets open.
- Four-observation evidence schema: gold open/close and silver open/close.
- XAUS paired-source mode: two independent validator HTTP reads, one `xau` response and one `xag` response, with exact USD/troy-ounce checks.
- Exact integer comparison:

  `gold_close * silver_open` versus `silver_close * gold_open`

  This avoids floating-point return drift. Equal cross-products refund both sides without a fee.
- Strict transport, UTF-8 byte, JSON, instrument, unit, freshness, ordering, positive-price, staleness, timestamp-skew, and canonical-hash validation.
- Independent validator reads through `gl.vm.run_nondet_unsafe`; disagreement or invalid evidence remains pending.
- A frozen settlement deadline and deterministic fee-free deadline refund path.
- A separate `SettlementGate` contract. Claims require a matching finality record from the market contract and are not enabled by an `Accepted`/provisional result.
- Paginated on-chain history and historical-position inspection after market rotation.
- Wallet-free, stable comparison URLs showing the four observations, alignment checks, arithmetic, source references, and (for the synthetic case) settlement receipts.
- Wallet network checks, account-change handling, bounded finality polling, and explicit submitted/provisional/finalized transaction states.
- Local replay mode so the product can be inspected without a wallet or deployment.

Demo credits are accounting units for the prototype. They are not USDC, do not represent custody or physical metal, and do not involve leverage or liquidation.

## Paired source and frozen policy

The current source is [XAUS](https://xaus.com/api/), using the public no-key endpoints [XAU](https://xaus.com/api/v1/intraday?symbol=xau&hours=48) and [XAG](https://xaus.com/api/v1/intraday?symbol=xag&hours=48). XAUS documents UTC timestamps, two-minute sampling, short historical retention, and indicative mid-market values. It also states that the data is not settlement-grade, executable, or contractual. MetalSwap therefore presents the real-source material as an archived historical comparison, not fair live trading or official benchmark settlement.

The source identity and policy are frozen before entry:

- Instruments: `XAUUSD` and `XAGUSD`.
- Convention: USD per troy ounce, fixed-point scale `1_000_000`.
- Interval: 900 seconds, UTC quarter-hour boundaries.
- Selection: latest source point at or before each opening/closing boundary.
- Maximum boundary staleness: 180 seconds.
- Maximum cross-metal timestamp skew: 60 seconds at each boundary.
- Missing, stale, malformed, conflicting, wrong-unit, wrong-instrument, non-2xx, truncated, or oversized evidence stays pending and can only reach the fee-free deadline refund.

The validators fetch both source responses independently. The contract accepts a bounded UTF-8 JSON body (64 KiB) and at most 1,500 points, enough for the complete 48-hour/two-minute window without accepting unbounded content. The hosted comparison JSON is proof material for people; it is not used as contract evidence. See [`docs/DATA_FEASIBILITY.md`](docs/DATA_FEASIBILITY.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Contract lifecycle

1. The owner freezes the source base URL and finality-gate address.
2. The owner opens a bounded future UTC quarter-hour market.
3. Users claim demo credits and place GOLD or SILVER positions before start.
4. After expiry, anyone requests settlement. Validators independently fetch and validate the same four-field evidence record.
5. Invalid, missing, or conflicting evidence stays pending. If the frozen deadline passes, positions refund without a fee.
6. A valid result is recorded as provisional and sent to `SettlementGate` with `on="finalized"`.
7. Only after a matching finality record exists can users claim a proportional payout. Payouts floor at the smallest demo-credit unit; dust remains undistributed.

The market contract never performs arithmetic with an LLM. The non-deterministic boundary is evidence retrieval and agreement; the outcome, fee, pool conservation, and payout math are deterministic contract code.

## Run locally

From this directory:

```powershell
npm install
npm run dev -- --port 3001
```

Open `http://localhost:3001`. With no contract address configured, the primary action starts a local replay. The replay is useful for product review only; its chart and example evidence are visibly marked synthetic.

### Frontend environment

Copy `frontend/.env.example` to `frontend/.env.local` when a contract deployment is available:

```text
NEXT_PUBLIC_GENLAYER_RPC_URL=<rpc-url>
NEXT_PUBLIC_GENLAYER_NETWORK=testnet_bradbury
NEXT_PUBLIC_METALSWAP_ADDRESS=<metalswap-address>
NEXT_PUBLIC_SETTLEMENT_GATE_ADDRESS=<gate-address>
NEXT_PUBLIC_GENLAYER_EXPLORER_URL=<optional-explorer-base>
```

The UI only enters wallet-backed mode when `NEXT_PUBLIC_METALSWAP_ADDRESS` is set. Transaction hashes are shown as provisional / awaiting finality; a receipt link is not treated as a claim authorization.

## Checks

```powershell
npm run typecheck
npm run build
npm run lint:contract
python -m pytest tests\direct -q
npm run test:e2e
```

The direct suite covers both metals rising/falling, equal relative returns, a less-falling metal winning, one-sided and deadline refunds, cutoff enforcement, malformed/missing/oversized/non-2xx evidence, source alignment, pagination, historical reads, finality gating, duplicate claims, and owner-only opening. The Playwright suite covers local replay, accessible entry controls, evidence-route visibility, and both public comparison pages. The wired integration flow requires a live/local GenLayer RPC plus `METALSWAP_INTEGRATION_SOURCE_BASE_URL`.

## Demonstration status

The preserved synthetic StudioNet demonstration funded GOLD and SILVER with 25 demo credits each, settled to SILVER, finalized the gate, paid 49 credits, rejected a duplicate claim, rotated the market, and retained the old position. Its exact receipts are linked from the [synthetic proof page](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z) and [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md).

The fresh XAUS-bound pair was deployed and read back with all deployment, binding, source-freeze, and market-open receipts `FINALIZED / SUCCESS`. Its deployment-time market was unfunded, so no historical XAUS result was wagered on or settled. The public XAUS page is a comparison-only replay of externally published observations. A later source probe returned HTTP 503; no live interval is claimed while the provider is unavailable.

This is a controlled mechanics demonstration, not fair trading, live-price verification, custody, or real-money trading. Synthetic outcomes are public, developer-generated, deterministic, and predictable; delaying publication does not make them unpredictable. Real-price trading is not ready until a validator-retrievable, settlement-grade XAU/XAG source is proven end to end.

## Deployment notes

The guarded [`deploy/deployScript.ts`](deploy/deployScript.ts) deploys `SettlementGate` and `MetalSwap`, wires the addresses, freezes the source URL, opens the next market, verifies finalized/successful receipts, and writes observed data to [`deploy/last-deployment.json`](deploy/last-deployment.json). Portal submission is intentionally not automated.

For the linked Vercel project, deploy from the Next.js app directory:

```powershell
vercel --prod --yes --cwd frontend
```
