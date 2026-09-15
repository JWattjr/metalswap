# Observed deployment and proof package

Captured from authorized GenLayer StudioNet test accounts on 2026-09-14. The current XAUS-bound pair was deployed from source revision [`3adc8ec0bc2a29173db8fcac9f49cc588e3b0041`](https://github.com/JWattjr/metalswap/commit/3adc8ec0bc2a29173db8fcac9f49cc588e3b0041). The earlier synthetic pair and its completed payout remain preserved below.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Current production build: [Vercel deployment `dpl_BJ6HrQc9cyH4iZwSoLgjCy2Y89E3`](https://vercel.com/wattxs-projects/metal-swap/BJ6HrQc9cyH4iZwSoLgjCy2Y89E3)
- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- RPC: `https://studio.genlayer.com/api`
- Public XAUS comparison: [xaus-2026-09-14-09-00-00z](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)
- Preserved synthetic mechanics proof: [metalswap-synthetic-2026-09-14-07-30-00z](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)
- Current MetalSwap: `0xFffDA717B60c1EdeB786592f80Dc73b731738Ef6`
- Current SettlementGate: `0x57fFc7AC20db57e0aBeBdBDCd8a6157Da6982131`
- Owner observed in config: `0xdB433ff614bDD1ecE21Aa97221C3E0a7ecf79c92`

The current pair freezes `https://xaus.com/api/v1/intraday?hours=48` as source identity `xaus-intraday-indicative-v1`, with `XAUUSD` and `XAGUSD` in USD per troy ounce. XAUS's own terms describe the series as indicative mid-market values, not settlement-grade, executable, or contractual prices. The source is used here for a named historical replay/comparison, not fair live trading.

## Fresh XAUS deployment and binding receipts

The deployment script checked protocol consensus `FINALIZED` and execution `SUCCESS` before writing the manifest. It also read back the frozen source, source mode, instruments, alignment limits, gate binding, and prepared market.

| Step | Receipt |
| --- | --- |
| Deploy SettlementGate | [0x17c7cf…1a030](https://genlayer-explorer.vercel.app/tx/0x17c7cf6c4cfc3b237a9de433850574cb72386d7f9b81acc074bccbd99131a030) · `FINALIZED / SUCCESS` |
| Deploy MetalSwap | [0x6a8416…27cd7](https://genlayer-explorer.vercel.app/tx/0x6a84169ecc236d1dfbc0ee1dd0cc9c3f34ed37901562bb9230e66800d2427cd7) · `FINALIZED / SUCCESS` |
| Bind gate → market | [0x25dbf1…529c](https://genlayer-explorer.vercel.app/tx/0x25dbf1d35fcea3b34e69152222d7c1c8da5570b2ab5011e9bcd6825ba51e529c) · `FINALIZED / SUCCESS` |
| Bind market → gate | [0x9ced6e…a21](https://genlayer-explorer.vercel.app/tx/0x9ced6e0d1fe88a278076cc838704c24992ea55601dd1a18951a83c6ff9c68a21) · `FINALIZED / SUCCESS` |
| Freeze XAUS source | [0xddba10…cf8f6](https://genlayer-explorer.vercel.app/tx/0xddba10e5420a5eaf1162d838eea945653fcada965e3e0af70ec4a98c605cf8f6) · `FINALIZED / SUCCESS` |
| Open `market-2026-09-14T10:15:00Z` | [0xd564e5…afe43](https://genlayer-explorer.vercel.app/tx/0xd564e5b77182b977486e8ad2fa14644dc85cbb0d0ce166ec9c2491c1f3cafe43) · `FINALIZED / SUCCESS` |

Deployment-time readback: start `2026-09-14T10:15:00Z`, end `10:30:00Z`, settlement deadline `10:40:00Z`, source mode `XAUS_INDICATIVE_HISTORICAL_REPLAY`, source history `48h`, price scale `1_000_000`, maximum gap `180s`, maximum cross-metal skew `60s`, and `finalized_markets=0`. The prepared market had zero stake, zero evidence, and `AWAITING_SETTLEMENT` at that readback. No XAUS-backed wager or settlement is claimed.

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

- Direct focused regression suite: `26 passed`.
- Contract lint, validation, typecheck, and schema checks: passed.
- Frontend typecheck, production build, and Playwright browser suite: passed (`6 passed`).
- Live synthetic behavior: expiry, settlement, finality gate, 49-credit payout, duplicate rejection, rotation, and old-position readback observed on StudioNet.
- Fresh XAUS deployment: binding/source/readback receipts observed as `FINALIZED / SUCCESS`; no XAUS-backed market was funded or settled.

Synthetic outcomes are public, developer-generated, deterministic, and predictable; delayed publication does not make them unpredictable. Demo credits are not USDC or real funds. This package is a controlled mechanics demonstration and an independently sourced historical comparison, not fair trading, executable pricing, official benchmark settlement, or a real-price trading product.

The machine-readable record is [`last-deployment.json`](last-deployment.json). Paste-ready Portal copy is [`PORTAL_DESCRIPTION.md`](PORTAL_DESCRIPTION.md).
