# Observed deployment and proof package

Captured from authorized GenLayer StudioNet test accounts on 2026-09-15. The current XAUS-bound pair was deployed from source revision [`2da9680c7cd21bdabcd8bf2e8cbfae31d607c175`](https://github.com/JWattjr/metalswap/commit/2da9680c7cd21bdabcd8bf2e8cbfae31d607c175). The earlier synthetic pair and its completed payout remain preserved below.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Current production build: [Vercel deployment `dpl_EbSfpRimnwuz8C4PxMU2xNP6yUvJ`](https://vercel.com/wattxs-projects/metal-swap/EbSfpRimnwuz8C4PxMU2xNP6yUvJ)
- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- RPC: `https://studio.genlayer.com/api`
- Public XAUS comparison: [xaus-2026-09-14-09-00-00z](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)
- Preserved synthetic mechanics proof: [metalswap-synthetic-2026-09-14-07-30-00z](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)
- Current MetalSwap: `0xeB7AB5de64139fD9F9F42D451076c62F22865dE7`
- Current SettlementGate: `0x49dE8861037C76d4a955091b16020aBF5818f90B`
- Owner observed in config: `0x2C8EB5dB1105A85BE66BadafeD88D10cF393CDD8`

The current pair freezes `https://xaus.com/api/v1/intraday?hours=48` as source identity `xaus-intraday-indicative-v1`, with `XAUUSD` and `XAGUSD` in USD per troy ounce. XAUS's own terms describe the series as indicative mid-market values, not settlement-grade, executable, or contractual prices. The source is used here for a named historical replay/comparison, not fair live trading.

## Fresh XAUS deployment and binding receipts

The deployment script checked protocol consensus `FINALIZED` and execution `SUCCESS` before writing the manifest. It also read back the frozen source, source mode, instruments, alignment limits, gate binding, and prepared market.

| Step | Receipt |
| --- | --- |
| Deploy SettlementGate | [0x4aa6ce…2a83](https://genlayer-explorer.vercel.app/tx/0x4aa6ce979ee826124e8f12f387da4c6196df4a583f034cfc13bcbf0d75cd2a83) · `FINALIZED / SUCCESS` |
| Deploy MetalSwap | [0xc49456…eda82](https://genlayer-explorer.vercel.app/tx/0xc4945682330f5f11b80570fd29e7eb6a97a1c24d41226547793cdaf66cbeda82) · `FINALIZED / SUCCESS` |
| Bind gate → market | [0x746a6f…9ada](https://genlayer-explorer.vercel.app/tx/0x746a6fb6985c81d3c704f41cf3cf4819fc5956f3ef8b3dfbce1892145eb49ada) · `FINALIZED / SUCCESS` |
| Bind market → gate | [0x1a1464…a0cd5](https://genlayer-explorer.vercel.app/tx/0x1a14641faa05deb9f60edf040e9f7f5f6ff30d328c6f409de015f97d6bfa0cd5) · `FINALIZED / SUCCESS` |
| Freeze XAUS source | [0x74ee87…067f0](https://genlayer-explorer.vercel.app/tx/0x74ee87a2a9fed32b92dec68ebf81ab30bb2639be0406dd464a22f032eb5067f0) · `FINALIZED / SUCCESS` |
| Open `market-2026-09-15T23:15:00Z` | [0xdbb88d…7940](https://genlayer-explorer.vercel.app/tx/0xdbb88d58628480ac1e3e19115e8ead49bd01ee267479449eb39bbff31e767940) · `FINALIZED / SUCCESS` |

Deployment-time readback: start `2026-09-15T23:15:00Z`, end `23:30:00Z`, settlement deadline `23:40:00Z`, source mode `XAUS_INDICATIVE_HISTORICAL_REPLAY`, source history `48h`, price scale `1_000_000`, maximum gap `180s`, maximum cross-metal skew `60s`, and `finalized_markets=0`. The prepared market had zero stake, zero evidence, and `AWAITING_SETTLEMENT` at that readback. No XAUS-backed wager or settlement is claimed.

Live-source preflight on `2026-09-15T23:00:30.831Z` returned HTTP `503` for both required URLs (`xau` and `xag`). The prepared market was therefore not funded, and no settlement, finality, payout, or duplicate-claim receipt is claimed for this XAUS pair.

## Public XAUS comparison case

Case: [xaus-2026-09-14-09-00-00z](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)

- Mode: `HISTORICAL_REPLAY`; comparison-only, no pool or claim.
- Interval: `2026-09-14T09:00:00Z → 2026-09-14T09:15:00Z`.
- Source capture: `2026-09-14T09:36:02Z`.
- Gold (`XAUUSD`, USD/troy oz): `4305.100098` at `08:58:02Z` → `4307.600098` at `09:14:02Z`.
- Silver (`XAGUSD`, USD/troy oz): `63.307999` at `08:58:02Z` → `63.294998` at `09:14:02Z`.
- Selection: latest published point at or before each boundary.
- Actual maximum boundary staleness: `118s`; actual cross-metal skew: `0s`.
- Display-only returns: Gold approximately `+0.06%`; Silver approximately `−0.02%`.
- Exact decision products: `gold_close × silver_open = 272705542696583902`; `silver_close × gold_open = 272491302092709804`; Gold is higher and therefore outperforms.
- Canonical evidence hash: `sha256:c140120075b4319ae799c64e4dfef4fc21589e363f093fa4611279d8eeca7692`.
- Source responses: [XAU](https://xaus.com/api/v1/intraday?symbol=xau&hours=48), [XAG](https://xaus.com/api/v1/intraday?symbol=xag&hours=48), [terms/API policy](https://xaus.com/api/).

The source was externally reachable and returned HTTP 200 JSON during the capture. A later verification probe returned HTTP 503, so this page remains an archived observation replay and does not claim live-source availability. The provider's terms are the authority for its indicative/non-executable limitation.

## Preserved synthetic mechanics demonstration

Case: [market-2026-09-14T07:30:00Z evidence](https://metal-swap.vercel.app/evidence/market-2026-09-14T07:30:00Z.json) and [wallet-free proof](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)

- Previous source revision: `6a31ea0ca02d7f08ae8c67f7fa6cd1384d4e05c1`.
- Previous MetalSwap: `0x04d331073ba620FC165Cf7841e71e9F1270f44c7`.
- Previous SettlementGate: `0x7EfCc55ccD29Eb63bf727e5b5213a1D44c450759`.
- Interval: `07:30:00Z → 07:45:00Z`; settlement deadline `07:55:00Z`.
- Funded pools: `GOLD=25`, `SILVER=25`, `total_staked=50` demo credits.
- Synthetic evidence hash: `sha256:866d6458d151cb8de0c0067cad14671657855878770cebef0e55ac8c3335c23d`.
- Outcome: `SILVER`; fee `1`; distributable pool `49`.
- Settlement: [0x77f9b0…0487f](https://genlayer-explorer.vercel.app/tx/0x77f9b06920f64204b163ab3214e5b9e5299a7a5a033fe314dba951e60e40487f) · `FINALIZED / SUCCESS`.
- Gate acknowledgment: included in the settlement callback; finality readback `finalized=true`, `finalized_markets=1` at `2026-09-14T07:46:17.148801Z`.
- Payout: [0x8a4a12…5eddb2](https://genlayer-explorer.vercel.app/tx/0x8a4a122e4a93431c5a35436d695bb8337a241009beaf011b8b80a5cef75eddb2) · Silver paid `49` credits · `FINALIZED / SUCCESS`.
- Duplicate claim rejection: [0xbea5d8…367ae4](https://genlayer-explorer.vercel.app/tx/0xbea5d8c7f671b661d750d7ef68ea81e28a632301bfdf15e0f7c0eaed05367ae4) · `FINALIZED`, expected error `[EXPECTED] position already claimed`.
- Rotation and historical readback: [0x49b1b2…089dc4](https://genlayer-explorer.vercel.app/tx/0x49b1b2e1eb7a04fa87d0d7120c63aa1aef6022fe0b3f40bf99c6f59547089dc4), with the old Silver position still readable after the new market opened.

## What validators actually verify

- The owner-only frozen source and exact market evidence URL.
- Successful 2xx transport, non-empty UTF-8 body no larger than 64 KiB, valid JSON, at most 1,500 points, exact symbols/currency/unit/hours/interval, fresh sampler state, ordered timestamps, positive six-decimal prices, and bounded coverage. The larger bound admits the complete 48-hour, two-minute XAUS window while remaining explicitly bounded.
- Latest-at-or-before boundary selection, maximum `180s` boundary gap, maximum `60s` cross-metal timestamp skew, recomputed gap/skew fields, and canonical SHA-256 payload matching.
- Independent `xau` and `xag` reads by leader and validator; disagreement, missing data, malformed data, or source failure remains pending.
- Snapshot ordinary values before consensus closures; no `self` or storage-backed Market object is captured.
- Deterministic relative-return cross multiplication, equal/one-sided/deadline refunds, fee and pool conservation, proportional floor payout, cutoff enforcement, owner-only opening, authenticated finality, idempotent finality retry, pagination, and duplicate-claim rejection.

## Test and readiness status

- Direct focused regression suite: `27 passed`.
- Contract lint, validation, typecheck, and schema checks: passed.
- Frontend typecheck, production build, and Playwright browser suite: passed (`6 passed`).
- Live synthetic behavior: expiry, settlement, finality gate, 49-credit payout, duplicate rejection, rotation, and old-position readback observed on StudioNet.
- Fresh full-window XAUS deployment from `2da9680c7cd21bdabcd8bf2e8cbfae31d607c175`: binding/source/readback receipts observed as `FINALIZED / SUCCESS`; the prepared market was not funded or settled because both validator source URLs returned HTTP 503 during the live preflight. No XAUS-backed payout is claimed.

Synthetic outcomes are public, developer-generated, deterministic, and predictable; delayed publication does not make them unpredictable. Demo credits are not USDC or real funds. This package is a controlled mechanics demonstration and an independently sourced historical comparison, not fair trading, executable pricing, official benchmark settlement, or a real-price trading product.

The machine-readable record is [`last-deployment.json`](last-deployment.json). Paste-ready Portal copy is [`PORTAL_DESCRIPTION.md`](PORTAL_DESCRIPTION.md).
