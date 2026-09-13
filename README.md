# MetalSwap

MetalSwap is a focused GenLayer testnet prototype for one question: over the next UTC quarter-hour, does gold or silver deliver the stronger relative return?

The interface is deliberately terminal-like: one market, one entry decision, one settlement path. The current build is a synthetic-evidence demo until a settlement-grade, validator-retrievable market feed is proven end to end. Synthetic values are labelled in the UI, and no live liquidity, volume, history, or real-price evidence is implied. Deployment addresses and receipts are recorded separately in [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md).

## What is implemented

- UTC quarter-hour markets with entry closing at the frozen start boundary.
- GOLD / SILVER selection and a fully funded pari-mutuel demo-credit pool.
- A 2% fee frozen in the contract before markets open.
- Four-observation evidence schema: gold open/close and silver open/close.
- Exact integer comparison:

  `gold_close * silver_open` versus `silver_close * gold_open`

  This avoids floating-point return drift. Equal cross-products refund both sides without a fee.
- Independent validator reads through `gl.vm.run_nondet_unsafe`; disagreement or invalid evidence remains pending.
- A frozen settlement deadline and deterministic fee-free deadline refund path.
- A separate `SettlementGate` contract. Claims require a matching finality record from the market contract and are not enabled by an `Accepted`/provisional result.
- Local replay mode so the product can be inspected without a wallet or deployment.
- A dynamic synthetic evidence endpoint at `/evidence/<market-id>.json`.

Demo credits are accounting units for the prototype. They are not USDC, do not represent custody or physical metal, and do not involve leverage or liquidation.

## Data feasibility decision

Real data was checked before choosing the fallback. XAUS provides public no-key intraday XAU and XAG observations, but describes them as indicative mid-market values and retains only a short history; that is not enough to call the feed settlement-grade without additional validation. AlyawmGold exposes both metals but its public historical endpoints are daily/monthly/yearly, not the required 15-minute boundary series. The app therefore ships with an explicit synthetic evidence mode rather than presenting an unverified live feed as fact.

The evidence contract keeps the replacement seam narrow: latest observation at or before each exact boundary, maximum observation gap, maximum cross-metal timestamp skew, strict schema, canonical hash, and deterministic conflict handling. A real source must satisfy those checks and be reachable by validators before the demo source is replaced.

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

## Contract lifecycle

1. Owner freezes the source base URL and finality-gate address.
2. Owner opens a future UTC quarter-hour market.
3. Users claim demo credits and place GOLD or SILVER positions before start.
4. After expiry, anyone requests settlement. Validators independently fetch and validate the same four-field evidence record.
5. Invalid, missing, or conflicting evidence stays pending. If the frozen deadline passes, positions refund without a fee.
6. A valid result is recorded as provisional and sent to `SettlementGate` with `on="finalized"`.
7. Only after a matching finality record exists can users claim a proportional payout. Payouts floor at the smallest demo-credit unit; dust remains undistributed.

The market contract never performs arithmetic with an LLM. The non-deterministic boundary is evidence retrieval and agreement; the outcome, fee, pool conservation, and payout math are deterministic contract code.

## Checks

```powershell
npm run typecheck
npm run build
npm run lint:contract
& "..\\covenant-sentinel\\.venv\\Scripts\\python.exe" -m pytest tests\\direct -q
```

The direct suite covers both metals rising/falling, equal relative returns, one-sided refunds, cutoff enforcement, malformed/missing evidence, and the claim gate failure when finality is not configured. Full two-contract finality / claim integration is kept separate because the installed GLSim direct harness gives sibling direct contracts the same simulated address; use a live/local GenLayer node for the wired gate flow.

## Deployment notes

The repository includes `deploy/deployScript.ts` as a guarded deployment/readback script. It deploys `SettlementGate` and `MetalSwap`, wires the addresses, freezes the source URL, opens the next market, and writes only observed deployment data to `deploy/last-deployment.json`. It must be run only after the frontend is hosted at the exact HTTPS origin used in the evidence URL.

Before calling a build testnet-ready, record:

- network name and RPC used;
- market and gate addresses;
- deployment and configuration transaction hashes;
- lifecycle state for each transaction, including protocol finality where relevant;
- a readback of the frozen source URL, fee, rule version, market interval, and finality gate.

Portal submission is intentionally not automated by this project.

The current observed addresses and finalized deployment receipts are recorded in [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md); the machine-readable readback is in `deploy/last-deployment.json`.

## Primary references

- [GenLayer finality](https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality)
- [GenLayer finalized messages](https://docs.genlayer.com/developers/intelligent-contracts/features/messages)
- [XAUS API feasibility reference](https://xaus.com/api/)
- [AlyawmGold developer API](https://alyawmgold.com/developers)
