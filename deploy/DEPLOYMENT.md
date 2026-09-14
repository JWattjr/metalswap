# Observed deployment and live demonstration

Captured from the authorized StudioNet test accounts on 2026-09-14. The deployed contract source is revision `6a31ea0ca02d7f08ae8c67f7fa6cd1384d4e05c1`; later documentation commits do not change the deployed contract bytes.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Production build: [Vercel deployment `dpl_3otmuZRV9XGBwsXPnXEDrHcoVRuk`](https://vercel.com/wattxs-projects/metal-swap/3otmuZRV9XGBwsXPnXEDrHcoVRuk)
- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- RPC: `https://studio.genlayer.com/api`
- Frozen evidence origin: `https://metal-swap.vercel.app/evidence/`
- MetalSwap: `0x04d331073ba620FC165Cf7841e71e9F1270f44c7`
- SettlementGate: `0x7EfCc55ccD29Eb63bf727e5b5213a1D44c450759`
- Owner observed in config: `0xdB433ff614bDD1ecE21Aa97221C3E0a7ecf79c92`

The explorer links below use the configured public StudioNet explorer route (`https://genlayer-explorer.vercel.app/tx/<hash>`). The explorer returned HTTP 503 during this capture, so the links are preserved for later loading; the receipt statuses and state readbacks below were obtained directly from StudioNet.

## Deployment and binding receipts

The deployment script awaited `FINALIZED` and checked execution `SUCCESS` before writing `deploy/last-deployment.json`.

| Step | Receipt |
| --- | --- |
| Deploy SettlementGate | [0xb42a8e…1c28bdc](https://genlayer-explorer.vercel.app/tx/0xb42a8e932069559416f67d450aa233e2776e17704be13df82037cb4dd1c28bdc) · `FINALIZED / SUCCESS` |
| Deploy MetalSwap | [0x2fd9a9…981e4b7](https://genlayer-explorer.vercel.app/tx/0x2fd9a91733205a1ddfd5d923375791add8b0d7940b9be3522ac611647981e4b7) · `FINALIZED / SUCCESS` |
| Bind gate → market | [0x172604…01393e](https://genlayer-explorer.vercel.app/tx/0x1726045eba6f7b6c86fc9dc27b7b38362a615eb0f49ea11fe0df2be04a01393e) · `FINALIZED / SUCCESS` |
| Bind market → gate | [0x8191cb…20530ff](https://genlayer-explorer.vercel.app/tx/0x8191cbd648a58956333af57ca72067e86b92931fb0fb7fa804c39d61120530ff) · `FINALIZED / SUCCESS` |
| Freeze evidence source | [0x57747f…29c531](https://genlayer-explorer.vercel.app/tx/0x57747f1ed3ecff7d3056c8416712a32cc704b70b9967fe2090de91b77129c531) · `FINALIZED / SUCCESS` |
| Open `market-2026-09-14T07:30:00Z` | [0x7a00a6…e287a](https://genlayer-explorer.vercel.app/tx/0x7a00a6677f38928819bb2f882b68bb626446771fc62153b6d9232d1855ce287a) · `FINALIZED / SUCCESS` |

The opening readback was observed at `2026-09-14T07:18:26.665Z`: start `07:30:00Z`, end `07:45:00Z`, settlement deadline `07:55:00Z`, status `UPCOMING`, and both pools at zero.

## Completed market proof

Market: [`market-2026-09-14T07:30:00Z`](https://metal-swap.vercel.app/evidence/market-2026-09-14T07:30:00Z.json)

- Interval: `2026-09-14T07:30:00Z → 07:45:00Z`
- Funded pools: `GOLD=25`, `SILVER=25`, `total_staked=50`
- Public evidence response after expiry: `FINALIZED`
- Evidence hash: `sha256:866d6458d151cb8de0c0067cad14671657855878770cebef0e55ac8c3335c23d`
- Boundary values: Gold `2,371,000,000 → 2,371,700,000`; Silver `28,310,000 → 28,420,000`
- Outcome: `SILVER`
- Fee: `1` credit; distributable pool: `49` credits
- Settlement receipt: [0x77f9b0…0487f](https://genlayer-explorer.vercel.app/tx/0x77f9b06920f64204b163ab3214e5b9e5299a7a5a033fe314dba951e60e40487f) · `FINALIZED`, `MAJORITY_AGREE`, successful contract execution
- Gate readback: `finalized=true`, `finalized_at=2026-09-14T07:46:17.148801Z`, same outcome/hash/payload, `finalized_markets=1`
- Payout receipt: [0x8a4a12…5eddb2](https://genlayer-explorer.vercel.app/tx/0x8a4a122e4a93431c5a35436d695bb8337a241009beaf011b8b80a5cef75eddb2) · `FINALIZED`, `MAJORITY_AGREE`, successful contract execution
- Payout readback: Silver stake `25`, `claimed=true`, payout `49`; market `claimed_amount=49`
- Duplicate claim: [0xbea5d8…367ae4](https://genlayer-explorer.vercel.app/tx/0xbea5d8c7f671b661d750d7ef68ea81e28a632301bfdf15e0f7c0eaed05367ae4) · `FINALIZED`, execution rejected with `[EXPECTED] position already claimed`

Supporting live transaction receipts:

| Action | Receipt |
| --- | --- |
| First account claims demo credits | [0x629f34…0e55c](https://genlayer-explorer.vercel.app/tx/0x629f3405166bc4d506090df5692c22e96875bc54e085232594b86f85e110e55c) · `FINALIZED / SUCCESS` |
| Second account claims demo credits | [0x59e599…e23983](https://genlayer-explorer.vercel.app/tx/0x59e599729913ca6cb063c27c10b01b55bab4992a6b33bc7164ce738979e23983) · `FINALIZED / SUCCESS` |
| Silver position | [0x10225b…69bd37](https://genlayer-explorer.vercel.app/tx/0x10225b4828769ab9744a917a8e7cf2148cd275505a73140a95cf7005c369bd37) · `FINALIZED / SUCCESS` |
| Gold position | [0x62c8d3…2d0e74](https://genlayer-explorer.vercel.app/tx/0x62c8d3e9d1f30c9cbfaf6f1bf0f63519570bc539af6744db6a6ff6c2642d0e74) · `FINALIZED / SUCCESS` |
| Finality callback from settlement | included in [0x77f9b0…0487f](https://genlayer-explorer.vercel.app/tx/0x77f9b06920f64204b163ab3214e5b9e5299a7a5a033fe314dba951e60e40487f) |
| Silver payout | [0x8a4a12…5eddb2](https://genlayer-explorer.vercel.app/tx/0x8a4a122e4a93431c5a35436d695bb8337a241009beaf011b8b80a5cef75eddb2) |
| Intentional duplicate claim | [0xbea5d8…367ae4](https://genlayer-explorer.vercel.app/tx/0xbea5d8c7f671b661d750d7ef68ea81e28a632301bfdf15e0f7c0eaed05367ae4) |

## Rotation and historical access

The owner rotated the completed market with [0x49b1b2…089dc4](https://genlayer-explorer.vercel.app/tx/0x49b1b2e1eb7a04fa87d0d7120c63aa1aef6022fe0b3f40bf99c6f59547089dc4), observed `FINALIZED / SUCCESS`, returning `market-2026-09-14T08:00:00Z`. The new current market was `UPCOMING` with zero stake, while the old Silver position remained queryable after rotation with `claimed=true`, `stake=25`, and `payout=49`. The public UI visibly listed both markets and allowed selection of the finalized historical row; a wallet-connected view exposes the old position and claim control.

## What validators actually verify

- The owner freezes one HTTPS evidence origin and the contract records the exact market URL.
- Each nondeterministic read requires a 2xx HTTP status, a non-empty body, a UTF-8 body no larger than 16 KiB, valid JSON, exact four-observation fields, bounded strings, positive bounded integer prices, exact boundary timestamps, gap/skew limits, and a canonical SHA-256 payload hash.
- Consensus closures receive ordinary snapshotted values only; they do not capture `self` or storage-backed `Market` objects.
- Deterministic contract code performs the relative-return cross multiplication, equal/one-sided/deadline refunds, fixed fee, pool conservation, proportional floor payout, cutoff and owner checks.
- Claims require a matching `SettlementGate` record from the authenticated market contract. The gate is idempotent for an identical payload and rejects conflicting retries; `retry_finality` re-emits only the exact stored payload when needed.
- Position history is indexed per owner and read through bounded pages, so both sides of one market remain visible across a page boundary.

## Test status and limitations

- Direct mocked regression suite: `18 passed` (deadline ordering, transport/truncation, evidence bounds, pagination, historical reads, arithmetic, refunds, finality gating, owner-only opening).
- Contract lint/validation: MetalSwap and SettlementGate passed.
- Frontend typecheck and production build: passed.
- Browser smoke suite: `4 passed`.
- Live behavior: fresh StudioNet deployment, two demo-credit positions, expiry, public synthetic evidence fetch, finalized settlement, gate acknowledgment, payout, duplicate-claim rejection, rotation, and historical readback were all observed above.

This is a controlled mechanics demonstration only. The evidence generator is public, synthetic, deterministic, and predictable; delaying its endpoint does not make outcomes unpredictable. Demo credits are not USDC or real funds. The prototype is not fair trading, real-price verification, custody, leverage, AMM, or order-book infrastructure. Real-price trading is not ready until an independently retrievable, settlement-grade XAU/XAG source is proven end to end.

## Raw readback

The full observed deployment record and post-demo proof are in [`last-deployment.json`](last-deployment.json). Portal copy is in [`PORTAL_DESCRIPTION.md`](PORTAL_DESCRIPTION.md).
