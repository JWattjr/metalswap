# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: Next.js App Router with React, TypeScript, and a small Python GenLayer Intelligent Contract; selected to match the reviewed GenLayer workspace patterns while keeping the app inexpensive to run.

## Users

People exploring a GenLayer testnet who want to take a short, clearly labeled prediction position on whether gold or silver will outperform over the next 15-minute UTC interval.

## Product Purpose

MetalSwap lets users choose GOLD OUTPERFORMS or SILVER OUTPERFORMS for the upcoming 15-minute interval, observe the provisional interval, and claim a protocol-finalized payout or refund. Success means the full market lifecycle is understandable and auditable without implying commodity ownership, leverage, or guaranteed returns.

## Positioning

The market compares relative percentage performance between two metal benchmarks instead of asking whether one price went up or down in isolation. GenLayer independently verifies the four boundary observations and the evidence record; deterministic on-chain arithmetic decides the winner and payout path.

## Operating Context

Markets align to UTC quarter-hours. Entry opens for the upcoming interval and closes at its start. After expiry, anyone may request settlement; protocol finality and claim availability are separate states. The frontend is an untrusted convenience layer for previews, cached chart data, wallet actions, and lifecycle display.

## Capabilities and Constraints

- One pair only: gold and silver.
- One duration only: 15 minutes, aligned to UTC quarter-hours.
- Two positions only: GOLD OUTPERFORMS and SILVER OUTPERFORMS.
- Compare relative returns with positive fixed-point integer prices using exact cross multiplication: `gold_close × silver_open` versus `silver_close × gold_open`.
- Freeze instrument identifiers, currency, units, precision, timestamp selection, gap/skew limits, evidence sources, fee, and settlement deadline before entries fund a market.
- Reject zero/invalid prices, mismatched or stale evidence, late entries, changed market rules, duplicate settlement, overpayment, and double claims.
- Missing, stale, conflicting, or malformed evidence becomes `PENDING_EVIDENCE` with bounded retries and deterministic refund after the frozen deadline.
- Equal relative returns and single-sided pools refund without fees.
- Demo credits are explicitly synthetic and not real funds. No leverage, liquidation, physical metal ownership, token-backed commodity claims, mainnet, or additional pairs.
- The initial app is a synthetic-evidence demonstration because public sources checked so far either provide indicative intraday observations, daily-only history, or require paid/API-key access. Real-price evidence is an open deployment decision until validator retrieval and permissions are proven.
- Finality is read from the GenLayer transaction lifecycle; `ACCEPTED` is provisional and cannot authorize a claim. No contract self-inspection of finality is assumed.

## Brand Commitments

The product name is MetalSwap. Copy must say prediction position, demo credits, synthetic replay, provisional/finalized, and data limitations where relevant. It must not imply custody, ownership, real liquidity, profits, live settlement evidence, or autonomous scheduling.

## Evidence on Hand

- The build brief is the authoritative product specification.
- GenLayer documentation confirms that an accepted result is provisional, finality is a separate protocol state, and finalized messages are the safe boundary for irreversible effects: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality
- XAUS documents public gold and silver spot data plus a 2-minute intraday series, but also labels it indicative and not settlement-grade: https://xaus.com/api/
- AlyawmGold documents no-key gold/silver history only at daily, monthly, and yearly intervals: https://alyawmgold.com/developers
- A verified synthetic deployment and finalized configuration receipts are recorded in `deploy/DEPLOYMENT.md`; no real-price evidence record is claimed.

## Product Principles

- Make the relative-performance mechanism legible before asking for a stake.
- Keep previews observational; keep evidence agreement, outcome, and payout arithmetic authoritative on-chain.
- Treat missing evidence as pending or refund, never as a guessed winner.
- Make provisional acceptance, protocol finality, settlement, and claims visibly distinct.
- Label synthetic values at the point of use and never fabricate liquidity, users, volume, profits, or history.

## Accessibility & Inclusion

Use semantic controls, keyboard operation, visible focus, readable contrast, reduced-motion support, tabular numerals for market data, text labels for every state/source/unit, and 44px minimum primary action targets on small screens.
