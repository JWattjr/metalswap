# MetalSwap

MetalSwap is a focused GenLayer testnet prototype for one question: over a 15-minute UTC interval, does gold or silver deliver the stronger relative return? It keeps one pair (Gold versus Silver), one interval length, and demo-credit pari-mutuel mechanics.

The current StudioNet deployment freezes XAUS's public XAU/USD and XAG/USD intraday series as a named indicative source. A completed 15-minute live-interval demonstration proves the full testnet lifecycle with those externally published observations and demo credits. XAUS does not describe the quotes as settlement-grade or executable, so this is a mechanics demonstration—not fair real-money trading or benchmark settlement. The earlier synthetic proof remains available separately.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Completed XAUS live-interval proof: [Gold vs Silver, 2026-09-16 12:15 UTC](https://metal-swap.vercel.app/comparison/xaus-live-2026-09-16-12-15-00z)
- Archived XAUS comparison: [Gold vs Silver replay](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)
- Preserved synthetic mechanics proof: [completed market proof](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)
- Exact deployment and receipt record: [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md)

Current XAUS-bound pair on GenLayer StudioNet:

- MetalSwap: `0x3D5ccf7e160031EC049c52815283269b95D8DbD7`
- SettlementGate: `0x5b00b98fa2a530E1b0E676b96A2FEC74012AFb20`
- Completed market: `market-2026-09-16T12:15:00Z`
- Post-demo rotation readback: `market-2026-09-16T12:45:00Z`
- Exact deployed source revision: [`f21a67be03e7d40dd68cff63a38de1f31d3ad2e1`](https://github.com/JWattjr/metalswap/commit/f21a67be03e7d40dd68cff63a38de1f31d3ad2e1)

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
- Wallet-free, stable comparison URLs showing the four observations, alignment checks, arithmetic, source references, and settlement/finality/claim receipts.
- Wallet network checks, account-change handling, bounded finality polling, and explicit submitted/provisional/finalized transaction states.
- Local replay mode so the product can be inspected without a wallet or deployment.

Demo credits are accounting units for the prototype. They are not USDC, do not represent custody or physical metal, and do not involve leverage or liquidation.

## Paired source and frozen policy

The current source is [XAUS](https://xaus.com/api/), using the public no-key endpoints [XAU](https://xaus.com/api/v1/intraday?hours=48&symbol=xau) and [XAG](https://xaus.com/api/v1/intraday?hours=48&symbol=xag). XAUS documents UTC timestamps, two-minute sampling, short historical retention, and indicative mid-market values. It also states that the data is not settlement-grade, executable, or contractual. MetalSwap therefore labels the completed live-interval market as an indicative testnet mechanics demonstration, not fair trading or official benchmark settlement.

The source identity and policy are frozen before entry:

- Instruments: `XAUUSD` and `XAGUSD`.
- Convention: USD per troy ounce, fixed-point scale `1_000_000`.
- Interval: 900 seconds, UTC quarter-hour boundaries.
- Selection: latest source point at or before each opening/closing boundary.
- Maximum boundary staleness: 180 seconds.
- Maximum cross-metal timestamp skew: 60 seconds at each boundary.
- Missing, stale, malformed, conflicting, wrong-unit, wrong-instrument, non-2xx, truncated, or oversized evidence stays pending and can only reach the fee-free deadline refund.

The validators fetch both source responses independently. The contract accepts a bounded UTF-8 JSON body (96 KiB) and at most 1,500 points. The byte ceiling gives conservative headroom for the expected response shape while the point and schema limits remain independently enforced. A 2026-09-16 live preflight returned 91 points per metal in roughly 3 KiB; a maximum-size live response has not been captured, so the full-envelope fit is not claimed as empirical proof. The hosted comparison JSON is proof material for people; it is not used as contract evidence. See [`docs/DATA_FEASIBILITY.md`](docs/DATA_FEASIBILITY.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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

The direct suite covers both metals rising/falling, equal relative returns, a less-falling metal winning, one-sided and deadline refunds, cutoff enforcement, malformed/missing/oversized/non-2xx evidence, source alignment, pagination, historical reads, finality gating, duplicate claims, and owner-only opening. The Playwright suite covers local replay, accessible entry controls, evidence-route visibility, and all three public comparison pages. The wired integration flow requires a live/local GenLayer RPC plus `METALSWAP_INTEGRATION_SOURCE_BASE_URL`.

## Demonstration status

The preserved synthetic StudioNet demonstration funded GOLD and SILVER with 25 demo credits each, settled to SILVER, finalized the gate, paid 49 credits, rejected a duplicate claim, rotated the market, and retained the old position. Its exact receipts are linked from the [synthetic proof page](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z) and [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md).

The fresh XAUS-bound pair was deployed and read back with all deployment, binding, source-freeze, and market-open receipts `FINALIZED / SUCCESS`. A subsequent live market funded both sides with 25 demo credits before cutoff. Validators independently fetched the paired source, accepted four aligned observations, selected SILVER because it fell less (`-0.0540%` versus Gold's `-0.0875%`), finalized the gate, paid 49 credits, rejected a duplicate claim, rotated, and retained the old claimed position. The exact public record is the [live-interval proof](https://metal-swap.vercel.app/comparison/xaus-live-2026-09-16-12-15-00z).

This is a controlled mechanics demonstration, not fair trading, benchmark-grade price verification, custody, or real-money trading. Synthetic outcomes are public, developer-generated, deterministic, and predictable; delaying publication does not make them unpredictable. Production trading is not ready until a reliable settlement-grade XAU/XAG source—preferably provider-diverse—is proven end to end.

## Deployment notes

The guarded [`deploy/deployScript.ts`](deploy/deployScript.ts) deploys `SettlementGate` and `MetalSwap`, wires the addresses, freezes the source URL, opens the next market, verifies finalized/successful receipts, and writes observed data to [`deploy/last-deployment.json`](deploy/last-deployment.json). Portal submission is intentionally not automated.

For the linked Vercel project, deploy from the Next.js app directory:

```powershell
vercel --prod --yes --cwd frontend
```
