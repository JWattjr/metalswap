# Observed deployment and proof package

Captured from authorized GenLayer StudioNet test accounts on 2026-09-16. The current XAUS-bound pair was deployed from exact source revision [`f21a67be03e7d40dd68cff63a38de1f31d3ad2e1`](https://github.com/JWattjr/metalswap/commit/f21a67be03e7d40dd68cff63a38de1f31d3ad2e1). The earlier synthetic lifecycle proof remains preserved.

## Public package

- App: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Repository: [github.com/JWattjr/metalswap](https://github.com/JWattjr/metalswap)
- Production build: [Vercel deployment `dpl_7Wq3FRUYZzqDQfYpwJxjLiy7dEbo`](https://vercel.com/wattxs-projects/metal-swap/7Wq3FRUYZzqDQfYpwJxjLiy7dEbo), release package `b4e5d7bc8bf7ebba781052c507a50eb5c1ff1270`
- Completed XAUS market: [wallet-free proof](https://metal-swap.vercel.app/comparison/xaus-live-2026-09-16-12-15-00z)
- Archived XAUS replay: [comparison proof](https://metal-swap.vercel.app/comparison/xaus-2026-09-14-09-00-00z)
- Preserved synthetic proof: [completed market](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z)
- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- MetalSwap: `0x3D5ccf7e160031EC049c52815283269b95D8DbD7`
- SettlementGate: `0x5b00b98fa2a530E1b0E676b96A2FEC74012AFb20`
- Owner observed in config: `0x2C8EB5dB1105A85BE66BadafeD88D10cF393CDD8`

The pair freezes `https://xaus.com/api/v1/intraday?hours=48` as `xaus-intraday-indicative-v1`, with `XAUUSD` and `XAGUSD` in USD per troy ounce. XAUS describes the values as indicative mid-market data, not settlement-grade, executable, or contractual pricing. This is a controlled testnet mechanics demonstration, not fair real-money trading.

## Deployment, binding, and source identity

Every receipt below reached protocol `FINALIZED` with execution `SUCCESS`.

| Step | Receipt |
| --- | --- |
| Deploy SettlementGate | [0x616c8f…e9d79](https://genlayer-explorer.vercel.app/tx/0x616c8f2d506dc3b9566389814bca63481cabff39a43c6620d22e5167796e9d79) |
| Deploy MetalSwap | [0x10821e…a05b7](https://genlayer-explorer.vercel.app/tx/0x10821e0dbd710fd00d91a2973f71b52c546256a681cf898a2e8148afc46a05b7) |
| Bind gate → market | [0x190496…795b7](https://genlayer-explorer.vercel.app/tx/0x1904963249b3fb657557fd91b2a414e59376e261b8ca706e78a895b93a9795b7) |
| Bind market → gate | [0x9286af…c028](https://genlayer-explorer.vercel.app/tx/0x9286af305cb46e4db58afc996f9cdc8bec518bf4031544d2884931e4bfd9c028) |
| Freeze XAUS source | [0xeb1782…b1a56](https://genlayer-explorer.vercel.app/tx/0xeb17824f24c5881579502be75751cdc12fa3c5d74daff2d5067536d4ee8b1a56) |
| Open initial future market | [0xe12ce5…03e0](https://genlayer-explorer.vercel.app/tx/0xe12ce5414d07c8c02cb328bc2853302d026cec81fb894b2ec124af8e32dc03e0) |

Deployed-source reads matched local source byte for byte:

- `contracts/metalswap.py`: 61,889 bytes, SHA-256 `2415cdc3125c483394235fc30c3cf8fec7303e02e0e23fc7f99b39519733871a`.
- `contracts/settlement_gate.py`: 6,275 bytes, SHA-256 `909f0aa4e7c571ab11c2fa3af91fcaaa36782a6283769e4501630d649d830965`.
- Contract bindings and the expected 18-method schema were read back from StudioNet.

## Completed indicative live interval

Case: [`market-2026-09-16T12:15:00Z`](https://metal-swap.vercel.app/comparison/xaus-live-2026-09-16-12-15-00z), interval `12:15:00Z → 12:30:00Z`, frozen deadline `12:40:00Z`.

- Source preflight at `2026-09-16T12:14:09.700Z` / `12:14:10.451Z`: both exact XAU and XAG URLs returned HTTP 200, fresh state, 132 points, and bounded bodies (4,488 / 4,329 bytes).
- Gold position: 25 credits, [0x5d4755…dc79](https://genlayer-explorer.vercel.app/tx/0x5d4755afcd89b07530c5def74924133df179824919aba83761d8001abbb9dc79), non-owner `0xdB433ff614bDD1ecE21Aa97221C3E0a7ecf79c92`.
- Silver position: 25 credits, [0xb8b738…74d1](https://genlayer-explorer.vercel.app/tx/0xb8b738ffff3d4999dc0b149282ddf2f539da4de0f01ac7af8569963f58c374d1), non-owner `0x0839A6DDCeC7aA5E6028490266D6D3EFabE316B5`.
- Accepted Gold observations: `4345.100098` at `12:14:01Z` and `4341.299805` at `12:28:02Z`.
- Accepted Silver observations: `64.767998` at `12:14:01Z` and `64.733002` at `12:28:02Z`.
- Actual maximum boundary staleness: `118s`; actual cross-metal skew: `0s`.
- Display returns: Gold approximately `-0.0875%`; Silver approximately `-0.0540%`. Silver won because it fell less.
- Exact products: `gold_close × silver_open = 281177297087640390`; `silver_close × gold_open = 281271373334034196`.
- Canonical evidence hash: `sha256:bd579dfd253e080eaef8dde52772922dff07c190a4b991a122710d4464a77ed0`.
- Non-owner settlement: [0x21e46a…380a0](https://genlayer-explorer.vercel.app/tx/0x21e46aa26516af78addda3b4209f41cc74fb8e18a8c933fd7779a105a24380a0) · `FINALIZED / SUCCESS / MAJORITY_AGREE`.
- Gate acknowledgment: [0xe04a66…636f4](https://genlayer-explorer.vercel.app/tx/0xe04a66361130a55b836a4cb729a1ce32397790ea7bce72c9db0ce40c42e636f4) · exact matching payload · finalized at `2026-09-16T12:31:25.462287Z`.
- Result: `SILVER`; total pool `50`; fee `1`; distributable `49`.
- Winner payout: [0x7dcbb…bc721](https://genlayer-explorer.vercel.app/tx/0x7dcbbab916742de34b334442ea799188cf65fc7a51734e0a0ad93079fb4bc721) · `FINALIZED / SUCCESS`; readback `claimed=true`, payout `49`.
- Duplicate claim: [0xa1a47d…baca2](https://genlayer-explorer.vercel.app/tx/0xa1a47df856dfe64340826cbf56be0f166bb80a247fc5b9d6f8dc037ce39baca2) · `FINALIZED`, expected rollback `[EXPECTED] position already claimed`.
- Owner rotation: [0x1d4f0f…d8840](https://genlayer-explorer.vercel.app/tx/0x1d4f0f4ebbe5500ac925f8a21296411fa7f37ffdc96fe0fa32604680651d8840) · `FINALIZED / SUCCESS`; current market read back as `market-2026-09-16T12:45:00Z`, while the old Silver position remained readable and claimed.

## Deadline-refund live check

The initially prepared market `market-2026-09-16T11:15:00Z` was funded 25/25 but not adjudicated after its frozen deadline. A non-owner settlement request [0x9b509f…8868d](https://genlayer-explorer.vercel.app/tx/0x9b509f9f5be2a5cf8fd94a61acde0346406ab05b755312d0a7ac8f6e4388868d) produced `REFUND`, fee `0`, distributable `50`, `settlement_attempts=0`, and reason `SETTLEMENT_DEADLINE_REFUND`; no source evidence was fetched. A historical Silver refund claim after rotation [0x2a6163…c18943](https://genlayer-explorer.vercel.app/tx/0x2a6163f2b3eb831c35e8c876e2cead238c620e7d6e52ba2b0f503886a8c18943) paid 25, and [0xa581b9…3f914](https://genlayer-explorer.vercel.app/tx/0xa581b998f413724577a081dc3542fcf53b7744ec3510b1428c1bf405e263f914) proved duplicate-claim rejection.

## Preserved synthetic demonstration

The earlier [synthetic proof](https://metal-swap.vercel.app/comparison/metalswap-synthetic-2026-09-14-07-30-00z) remains intact: 25/25 credits, SILVER outcome, 1-credit fee, 49-credit payout, finalized gate, duplicate rejection, rotation, and historical position readback. Its pair is MetalSwap `0x04d331073ba620FC165Cf7841e71e9F1270f44c7` and SettlementGate `0x7EfCc55ccD29Eb63bf727e5b5213a1D44c450759`, deployed from `6a31ea0ca02d7f08ae8c67f7fa6cd1384d4e05c1`. Synthetic outcomes are public, developer-generated, deterministic, and predictable; delayed publication does not make them unpredictable.

## What validators verify

- Frozen source identity and exact `xau` / `xag` requests; successful 2xx transport; non-empty UTF-8 body no larger than 96 KiB; valid bounded JSON with at most 1,500 points.
- Exact symbols, currency, unit, history window, fresh sampler state, ordered timestamps, positive six-decimal bounded prices, and coverage.
- Latest-at-or-before boundary selection, maximum `180s` staleness, maximum `60s` cross-metal skew, recomputed alignment fields, and canonical SHA-256 agreement.
- Independent leader/validator reads. Disagreement, missing data, malformed data, or transport failure remains pending until the deterministic fee-free deadline refund.
- Exact integer relative-return comparison, fee/pool conservation, proportional floor payout, cutoff enforcement, owner-only opening, authenticated finality, idempotent finality retry, bounded pagination, historical reads, and duplicate-claim rejection.

Arithmetic is contract code; no LLM compares prices. The hosted proof JSON is for human audit and is not contract evidence.

## Checks and limits

- Direct focused suite: `28 passed`.
- Contract linter and validation: passed.
- Integration suite: `3 collected`, skipped without an explicitly configured integration source.
- Frontend typecheck, lint, production build, and browser tests: passed for this release.
- Direct tests use mocked HTTP evidence; the StudioNet links above are the live observed behavior.

XAUS is still indicative/non-executable and has shown intermittent availability. There is no independent second price provider. Demo credits have no cash value. Therefore the synthetic prototype and indicative real-observation demonstration are submission-ready, but real-price trading is not production-ready.

The machine-readable record is [`last-deployment.json`](last-deployment.json). Paste-ready Portal copy is [`PORTAL_DESCRIPTION.md`](PORTAL_DESCRIPTION.md).
